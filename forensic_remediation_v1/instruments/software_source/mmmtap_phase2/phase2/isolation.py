"""Process-level isolation for experimental assessors (mmmtap-p2-bwrap-isolation-v1).

Standard library only and free of package-relative imports so the identical file
can be bound read-only into the offline loopback sandbox. Nothing here performs
inference; callers decide whether a run is a loopback mock or an authorised call.

Boundary: a bubblewrap mount/PID/IPC/UTS/user namespace with no host network
(unless live transport is explicitly requested), an owner-only staging tree that
is deleted after each attempt, an explicit minimal environment passed through
Popen (never argv), and binaries pinned by SHA-256 before and after each run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.parse

ISOLATION_VERSION = "mmmtap-p2-bwrap-isolation-v1"
BWRAP = "/usr/bin/bwrap"
SANDBOX_HOME = "/home/assessor"
SANDBOX_WORK = "/work"
BASE_ENV = {"PATH": "/usr/bin:/bin", "HOME": SANDBOX_HOME, "LANG": "C.UTF-8", "NO_COLOR": "1", "TMPDIR": "/tmp"}
REDACTED = b"[CREDENTIAL REDACTED]"


class IsolationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_binary(path: Path, expected: str | None) -> str:
    actual = sha256_file(path)
    if expected is not None and actual != expected:
        raise IsolationError("pinned_binary_hash_mismatch")
    return actual


def bwrap_argv(command: list[str], *, ro_binds=(), rw_binds=(), network: str = "none",
               cwd: str = SANDBOX_WORK) -> list[str]:
    """Build a bubblewrap argv. Secrets never appear here: the environment is the Popen env."""
    if network not in ("none", "host"):
        raise IsolationError("network must be none or host")
    argv = [BWRAP, "--unshare-all"]
    if network == "host":
        argv.append("--share-net")
    argv += ["--die-with-parent", "--new-session", "--hostname", "assessor",
             "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
             "--symlink", "usr/sbin", "/sbin", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
             "--ro-bind-try", "/etc/ssl", "/etc/ssl",
             "--ro-bind-try", "/etc/ca-certificates", "/etc/ca-certificates",
             "--ro-bind-try", "/etc/nsswitch.conf", "/etc/nsswitch.conf",
             "--ro-bind-try", "/etc/hosts", "/etc/hosts"]
    if network == "host":
        argv += ["--ro-bind-try", "/etc/resolv.conf", "/etc/resolv.conf",
                 "--ro-bind-try", "/run/systemd/resolve", "/run/systemd/resolve"]
    argv += ["--dir", SANDBOX_HOME, "--dir", SANDBOX_WORK]
    # Directory binds first, then read-only binds: a later directory bind would hide earlier file binds.
    for src, dst in rw_binds:
        argv += ["--bind", str(src), str(dst)]
    for src, dst in ro_binds:
        argv += ["--ro-bind", str(src), str(dst)]
    argv += ["--chdir", cwd, "--"] + [str(part) for part in command]
    return argv


def sandbox_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(BASE_ENV)
    for key, value in (extra or {}).items():
        if not isinstance(value, str):
            raise IsolationError("environment values must be strings")
        env[key] = value
    return env


class Staging:
    """Owner-only per-attempt tree (home, work, capture); removed on exit."""

    def __init__(self, prefix: str = "mmmtap-p2-assessor-") -> None:
        self.prefix = prefix
        self.root: Path | None = None
        self.removed = False

    def __enter__(self) -> "Staging":
        self.root = Path(tempfile.mkdtemp(prefix=self.prefix))
        os.chmod(self.root, 0o700)
        for name in ("home", "work", "capture"):
            (self.root / name).mkdir(mode=0o700)
        return self

    def path(self, name: str) -> Path:
        assert self.root is not None
        return self.root / name

    def inventory(self, name: str) -> list[str]:
        """Names only (never contents) of files the assessor left behind."""
        base = self.path(name)
        return sorted(str(p.relative_to(base)) + ("/" if p.is_dir() else "")
                      for p in base.rglob("*")) if base.exists() else []

    def __exit__(self, *exc) -> None:
        if self.root is not None and self.root.exists():
            shutil.rmtree(self.root)
        self.removed = self.root is not None and not self.root.exists()


def redact(value: bytes, secrets: list[str]) -> tuple[bytes, bool]:
    original = value
    for secret in sorted({s for s in secrets if isinstance(s, str) and len(s) > 5}, key=len, reverse=True):
        value = value.replace(secret.encode(), REDACTED)
    return value, value != original


def sensitive_bytes(value: bytes, secrets: list[str]) -> bool:
    """Detect known credentials through JSON/base64 envelopes, with fail-closed bounds."""
    secrets = [s for s in secrets if isinstance(s, str) and s]
    if not secrets:
        return False
    variants = set()
    for secret in secrets:
        raw = secret.encode()
        variants.update((raw, base64.b64encode(raw), base64.urlsafe_b64encode(raw),
                         urllib.parse.quote(secret, safe="").encode(),
                         json.dumps(secret, ensure_ascii=True)[1:-1].encode()))
    seen = set()
    budget = 64 << 20

    def scan(raw: bytes, depth: int) -> bool:
        nonlocal budget
        if raw in seen:
            return False
        seen.add(raw)
        budget -= len(raw)
        if depth > 64 or budget < 0:
            return True
        if any(part in raw for part in variants):
            return True
        candidates = [raw]
        # Inspect every string, including discarded duplicate fields in malformed receipts.
        for match in re.finditer(rb'"(?:[^"\\]|\\.)*"', raw):
            try:
                decoded = json.loads(match[0]).encode("utf-8")
            except (ValueError, UnicodeError):
                continue
            candidates.append(decoded)
            if any(part in decoded for part in variants):
                return True
        for candidate in candidates:
            try:
                decoded = base64.b64decode(candidate, validate=True)
            except (ValueError, binascii.Error):
                continue
            if decoded and scan(decoded, depth + 1):
                return True
        return False

    return scan(value, 0)


@dataclass
class RunResult:
    stdout: bytes = b""
    stderr: bytes = b""
    exit_status: int | None = None
    latency_seconds: float = 0.0
    error: str | None = None
    watchdog_reason: str | None = None
    watchdog_elapsed_seconds: float | None = None
    killed: bool = False
    started: bool = False
    events: list[dict] = field(default_factory=list)


def stream_run(argv: list[str], *, stdin: bytes, env: dict[str, str], timeout: float, limit: int,
               watchdog=None, cwd: str | None = None) -> RunResult:
    """Run once with streaming capture; kill the process group on timeout, size limit or watchdog."""
    start = time.monotonic()
    result = RunResult()
    partial = {"stdout": b"", "stderr": b""}
    buffers = {"stdout": bytearray(), "stderr": bytearray()}

    def stop(reason: str, *, watchdog_hit: bool = False) -> None:
        if watchdog_hit:
            result.watchdog_reason = reason
            result.watchdog_elapsed_seconds = round(time.monotonic() - start, 6)
        elif result.error is None:
            result.error = reason
        try:
            os.killpg(child.pid, signal.SIGKILL)
            result.killed = True
        except ProcessLookupError:
            pass

    try:
        with tempfile.TemporaryFile() as stdin_file, selectors.DefaultSelector() as selector:
            stdin_file.write(stdin)
            stdin_file.seek(0)
            child = subprocess.Popen(argv, stdin=stdin_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env, cwd=cwd, start_new_session=True)
            result.started = True
            try:
                selector.register(child.stdout, selectors.EVENT_READ, "stdout")
                selector.register(child.stderr, selectors.EVENT_READ, "stderr")
                while selector.get_map():
                    remaining = timeout - (time.monotonic() - start)
                    if remaining <= 0:
                        stop("timeout_execution_outcome_uncertain_no_retry")
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        name = key.data
                        space = limit - len(buffers[name])
                        buffers[name].extend(data[:space])
                        if len(data) > space:
                            stop("output_size_limit")
                            break
                        if watchdog is not None and result.watchdog_reason is None:
                            lines = (partial[name] + data).split(b"\n")
                            partial[name] = lines.pop()
                            for line in lines:
                                reason = watchdog(name, line)
                                if reason:
                                    stop(reason, watchdog_hit=True)
                                    break
                    if result.error or result.watchdog_reason:
                        break
                child.wait(timeout=max(0.01, timeout - (time.monotonic() - start)))
            except subprocess.TimeoutExpired:
                stop("timeout_execution_outcome_uncertain_no_retry")
            finally:
                if child.poll() is None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                        result.killed = True
                    except ProcessLookupError:
                        pass
                    child.wait()
                # Drain whatever was already written so killed runs keep their evidence.
                for name, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
                    try:
                        os.set_blocking(stream.fileno(), False)
                        while len(buffers[name]) < limit:
                            chunk = os.read(stream.fileno(), 65536)
                            if not chunk:
                                break
                            buffers[name].extend(chunk[:limit - len(buffers[name])])
                    except (BlockingIOError, OSError, ValueError):
                        pass
                    stream.close()
                result.exit_status = child.returncode
    except OSError as exc:
        result.error = "process_error:" + type(exc).__name__
    result.stdout, result.stderr = bytes(buffers["stdout"]), bytes(buffers["stderr"])
    result.latency_seconds = round(time.monotonic() - start, 6)
    return result


class CopilotWatchdog:
    """Kill Copilot at the first sign of an internal retry, extra model call or tool execution.

    Copilot CLI 1.0.95 retries 5xx/429 internally and exposes no switch to disable that;
    the experiment instead fails closed and preserves the first-attempt evidence.
    """

    def __init__(self) -> None:
        self.starts = 0

    def __call__(self, stream: str, line: bytes) -> str | None:
        if stream != "stdout" or not line.strip():
            return None
        try:
            event = json.loads(line)
        except ValueError:
            return None
        kind = event.get("type") if isinstance(event, dict) else None
        if not isinstance(kind, str):
            return None
        if kind == "model.call_failure":
            return "transport_failure_observed_retry_not_permitted"
        if kind == "model.call_start":
            self.starts += 1
            if self.starts > 1:
                return "multiple_model_calls_observed"
        if kind.startswith("tool.") or kind.startswith("subagent."):
            return "tool_or_subagent_event_observed"
        data = event.get("data")
        if kind == "assistant.message" and isinstance(data, dict) and data.get("toolRequests"):
            return "assistant_tool_request_observed"
        return None


CODEX_TOOL_MARKERS = (b"ToolCall:", b"codex.tool_call", b"custom_tool_call", b"function_call_output",
                      b"codex_core::tools::router")


class CodexWatchdog:
    """Kill Codex when its debug log or JSON stream shows tool routing or a non-assessment item."""

    def __call__(self, stream: str, line: bytes) -> str | None:
        if stream == "stderr":
            return "tool_routing_observed_in_debug_log" if any(m in line for m in CODEX_TOOL_MARKERS) else None
        try:
            event = json.loads(line)
        except ValueError:
            return None
        if not isinstance(event, dict):
            return None
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") not in ("agent_message", "reasoning", "error"):
            return "non_assessment_item_observed"
        return None


WATCHDOGS = {"copilot_v2": CopilotWatchdog, "codex_v2": CodexWatchdog}


def stage_codex_auth(host_auth: Path, home: Path) -> dict:
    """Copy host Codex auth into a fresh owner-only CODEX_HOME; record hashes only."""
    raw = host_auth.read_bytes()
    target = home / "auth.json"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
    secrets: list[str] = []
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise IsolationError("auth_file_must_be_an_object")

    def walk(value) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and len(value) > 5:
            secrets.append(value)

    walk(parsed)
    return {"host_sha256_before": hashlib.sha256(raw).hexdigest(), "secrets": secrets}


DATETIME_PREFIX = re.compile(r"^<current_datetime>[^<>]{1,64}</current_datetime>\n\n$")
