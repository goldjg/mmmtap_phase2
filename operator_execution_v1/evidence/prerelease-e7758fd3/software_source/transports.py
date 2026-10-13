"""One-shot, externally contained transports. There is no retry or fallback path."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import re
import signal
import stat
import subprocess
import tempfile
import time
import sys

from historical_extractor.extract import strict_json
from phase2.adapters import Response
from phase2.adapters_v2 import codex_argv, copilot_argv, parse_events
from phase2.core import ROOT, IntegrityError, digest, json_bytes
from phase2.isolation import (CodexWatchdog, CopilotWatchdog, IsolationError, RunResult, Staging,
                              bwrap_argv, sandbox_env, sensitive_bytes, sha256_file)
from phase2.software import verify_generator_closure
from .planning import PACKAGE, adapter


def auth_file() -> Path:
    return Path.home() / ".codex/auth.json"


def read_codex_auth() -> tuple[bytes, list[str]]:
    path = auth_file()
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise IntegrityError("Codex auth must be an owner-only regular file belonging to the operator")
    raw = path.read_bytes()
    obj = strict_json(raw)
    tokens = obj.get("tokens") if isinstance(obj, dict) else None
    if (not isinstance(tokens, dict) or not isinstance(tokens.get("access_token"), str)
            or not tokens["access_token"] or obj.get("OPENAI_API_KEY")):
        raise IntegrityError("Pinned Codex route requires ChatGPT OAuth; API-key substitution is prohibited")
    secrets = []

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value:
            secrets.append(value)

    walk(obj)
    return raw, secrets


def credentials() -> dict:
    result = {
        name: {"present": bool(os.environ.get("COPILOT_GITHUB_TOKEN")),
               "source": "COPILOT_GITHUB_TOKEN", "scope": "not_verifiable_offline",
               "authentication": "not_contacted"}
        for name in ("haiku", "gemini")
    }
    try:
        read_codex_auth()
        result["sol"] = {"present": True, "source": "~/.codex/auth.json",
                         "route": "ChatGPT_OAuth_no_API_fallback",
                         "authentication": "local_structure_only_not_remote_validated"}
    except (OSError, ValueError, TypeError) as exc:
        result["sol"] = {"present": False, "source": "~/.codex/auth.json",
                         "reason": "missing_or_unsupported_auth:" + type(exc).__name__}
    for name in ("native_jev", "carl_jev"):
        result[name] = {"present": bool(os.environ.get("JEVKEY")), "source": "JEVKEY",
                        "scope": "SystemOne_only_in_worker", "authentication": "not_contacted"}
    return result


class Watchdog:
    def __init__(self, provider: str, requested_model: str):
        self.provider, self.requested_model = provider, requested_model
        self.delegate = CodexWatchdog() if provider == "codex_cli" else CopilotWatchdog()
        self.turns = 0

    def __call__(self, stream: str, line: bytes) -> str | None:
        reason = self.delegate(stream, line)
        if reason:
            return reason
        if stream == "stderr":
            if self.provider == "codex_cli" and any(marker in line.lower() for marker in
                                                     (b"retrying", b"reconnecting", b"falling back")):
                return "retry_or_fallback_observed"
            if self.provider == "codex_cli":
                configured = re.findall(rb"Configuring session: model=([A-Za-z0-9_.-]+)", line)
                if any(model.decode("ascii") != self.requested_model for model in configured):
                    return "model_switch_observed_in_client_configuration"
            return None
        try:
            event = strict_json(line)
        except (ValueError, RecursionError):
            return None
        if not isinstance(event, dict):
            return None
        kind, data = event.get("type", ""), event.get("data", {})
        if self.provider == "codex_cli":
            if kind == "turn.started":
                self.turns += 1
                if self.turns > 1:
                    return "multiple_turns_observed"
            if kind in ("error", "turn.failed"):
                return "transport_failure_observed_no_retry"
        elif kind in ("model.call_start", "model.call_final_result") and isinstance(data, dict):
            observed = data.get("model")
            if observed is not None and observed != self.requested_model:
                return "model_switch_observed"
        return None

    def peek(self, line: bytes) -> str | None:
        return Watchdog(self.provider, self.requested_model)("stdout", line)


def run_once(argv: list[str], *, stdin: bytes, env: dict[str, str], timeout: float,
             limit: int, watchdog=None, cwd: str | None = None) -> RunResult:
    """Capture partial output on SIGINT/SIGTERM; kill the entire process group."""
    started = time.monotonic()
    result = RunResult()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    pending = {"stdout": b"", "stderr": b""}
    child = None

    def stop(reason: str, watch: bool = False):
        if watch:
            result.watchdog_reason = reason
            result.watchdog_elapsed_seconds = round(time.monotonic() - started, 6)
        else:
            result.error = result.error or reason
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
                result.killed = True
            except ProcessLookupError:
                pass

    def inspect(name: str, data: bytes):
        space = limit - len(buffers[name])
        buffers[name].extend(data[:space])
        if len(data) > space:
            stop("output_size_limit")
        if watchdog is None or result.watchdog_reason:
            return
        lines = (pending[name] + data).split(b"\n")
        pending[name] = lines.pop()
        for line in lines:
            reason = watchdog(name, line)
            if reason:
                stop(reason, True)
                return
        # Debug tool markers are meaningful even without a newline. JSON event
        # counters are advanced only for complete lines, never repeatedly.
        if name == "stderr" and pending[name]:
            reason = watchdog(name, pending[name])
            if reason:
                stop(reason, True)
        elif name == "stdout" and pending[name] and hasattr(watchdog, "peek"):
            reason = watchdog.peek(pending[name])
            if reason:
                stop(reason, True)

    try:
        with tempfile.TemporaryFile() as input_file, selectors.DefaultSelector() as selector:
            input_file.write(stdin)
            input_file.seek(0)
            child = subprocess.Popen(argv, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env, cwd=cwd, start_new_session=True)
            result.started = True
            try:
                for name in buffers:
                    selector.register(getattr(child, name), selectors.EVENT_READ, name)
                while selector.get_map() and not (result.error or result.watchdog_reason):
                    if time.monotonic() - started >= timeout:
                        stop("timeout_execution_unknown_no_retry")
                        break
                    for key, _ in selector.select(0.05):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if data:
                            inspect(key.data, data)
                        else:
                            selector.unregister(key.fileobj)
                for name, line in pending.items():
                    if watchdog and line and not result.watchdog_reason:
                        reason = watchdog(name, line)
                        if reason:
                            stop(reason, True)
                child.wait(timeout=max(0.01, timeout - (time.monotonic() - started)))
            except KeyboardInterrupt:
                stop("operator_interrupted_execution_unknown_no_retry")
            except subprocess.TimeoutExpired:
                stop("timeout_execution_unknown_no_retry")
            finally:
                if child.poll() is None:
                    stop(result.error or "process_did_not_exit")
                child.wait()
                for name in buffers:
                    stream = getattr(child, name)
                    os.set_blocking(stream.fileno(), False)
                    try:
                        while True:
                            data = os.read(stream.fileno(), 65536)
                            if not data:
                                break
                            inspect(name, data)
                    except BlockingIOError:
                        pass
                    finally:
                        stream.close()
                result.exit_status = child.returncode
    except OSError as exc:
        result.error = "process_error:" + type(exc).__name__
    result.stdout, result.stderr = bytes(buffers["stdout"]), bytes(buffers["stderr"])
    result.latency_seconds = round(time.monotonic() - started, 6)
    return result


def generator_layout(spec: dict, stage: Staging, *, offline: bool = False) -> tuple[list[str], list, dict]:
    home = stage.path("home")
    binds = [(stage.path("work"), "/work"), (PACKAGE / "process_guard.py", "/opt/process_guard.py")]
    if spec["provider"] == "codex_cli":
        (home / ".codex").mkdir(mode=0o700)
        command = codex_argv(mock=offline)
        binds.append((Path(spec["release_root"]), "/opt/codex-release"))
        env = sandbox_env({
            "CODEX_HOME": "/home/assessor/.codex",
            "PATH": "/opt/codex-release/codex-path:/opt/codex-release/bin:/usr/bin:/bin",
            "RUST_LOG": "warn,codex_core=debug",
        })
    else:
        (home / ".copilot").mkdir(mode=0o700)
        command = copilot_argv(spec["model_id"])
        binds.append((Path(spec["binary"]), "/opt/bin/copilot"))
        env = sandbox_env({"COPILOT_HOME": "/home/assessor/.copilot"})
    return ["/usr/bin/python3", "/opt/process_guard.py", *command], binds, env


def _capture(response: Response, run: RunResult, secrets: list[str]) -> None:
    response.exit_status, response.latency_seconds = run.exit_status, run.latency_seconds
    response.error = run.error or run.watchdog_reason
    response.provenance.update(
        sandbox_launch_attempts=1, sandbox_invocations=int(run.started),
        cli_invocations=None if run.started else 0,
        transport_attempts=None if run.started else 0,
        transport_count_basis="opaque_CLI_HTTP_count_unknown",
        watchdog_reason=run.watchdog_reason, watchdog_seconds=run.watchdog_elapsed_seconds,
        process_group_killed=run.killed,
        raw_capture={},
    )
    for name in ("stdout", "stderr"):
        raw = getattr(run, name)
        withheld = sensitive_bytes(raw, secrets)
        response.provenance["raw_capture"][name] = {
            "bytes_observed": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "capture": "withheld_known_credential" if withheld else "exact",
        }
        setattr(response, name, b"" if withheld else raw)
        if withheld:
            response.error = "credential_evidence_withheld"


def generator(plan: dict, job: dict, prompt: str, *, authorised: bool = False) -> Response:
    if not authorised:
        return Response(error="live_stage_authorisation_required", provenance={"transport_attempts": 0})
    if plan["operator_execution"]["profile"]["name"] != "research_controlled":
        return Response(error="strict_generator_isolation_blocked", provenance={"transport_attempts": 0})
    spec, cfg = plan["config"]["generators"][job["generator"]], plan["config"]
    response = Response(provenance={
        "provider": spec["provider"], "requested_model": spec["model_id"], "observed_model": None,
        "provider_confirmed_model": None, "binary_sha256": spec["binary_sha256"],
        "cli_version": "codex-cli 0.162.1" if spec["provider"] == "codex_cli" else "GitHub Copilot CLI 1.0.95",
        "config_sha256": digest(spec), "profile": plan["operator_execution"]["profile"],
        "network": "host_namespace_not_endpoint_filtered",
        "process_control": "seccomp_no_nonthread_children_not_universal_no_exec",
        "transport_attempts": 0, "cli_invocations": 0, "provider_internal_retries": "unobservable",
    })
    secrets = []
    stage = Staging("mmmtap-research-assessor-")
    try:
        verify_generator_closure(spec)
        with stage:
            command, binds, env = generator_layout(spec, stage)
            if spec["provider"] == "codex_cli":
                auth, secrets = read_codex_auth()
                target = stage.path("home") / ".codex/auth.json"
                target.write_bytes(auth)
                target.chmod(0o400)
                binds.append((target, "/home/assessor/.codex/auth.json"))
                response.provenance["credential_source"] = "owner_only_ChatGPT_auth_copy"
            else:
                key = os.environ.get("COPILOT_GITHUB_TOKEN")
                if not key:
                    return Response(error="isolated_copilot_credential_missing", provenance=response.provenance)
                secrets = [key]
                env["COPILOT_GITHUB_TOKEN"] = key
                response.provenance["credential_source"] = "COPILOT_GITHUB_TOKEN_only"
            argv = bwrap_argv(command, ro_binds=binds,
                              rw_binds=[(stage.path("home"), "/home/assessor")], network="host")
            response.provenance.update(argv=argv, argv_sha256=digest(argv), environment_keys=sorted(env),
                                       fresh_home=True, source_transport="stdin_only", working_directory_read_only=True)
            run = run_once(argv, stdin=prompt.encode(), env=env, timeout=cfg["timeout_seconds"],
                           limit=cfg["max_response_bytes"], watchdog=Watchdog(spec["provider"], spec["model_id"]))
            _capture(response, run, secrets)
            if not response.error and run.exit_status != 0:
                response.error = "generator_cli_failed"
            if not response.error:
                try:
                    response.message, response.usage, provenance = parse_events(
                        response.stdout, response.stderr, model=spec["model_id"],
                        provider=spec["provider"], prompt=prompt)
                    response.provenance.update(provenance)
                    response.provenance["cli_invocations"] = 1
                    response.provenance["evidence_mode"] = "lower_assurance_research_live_unadjudicated"
                except (ValueError, TypeError, KeyError, RecursionError) as exc:
                    response.error = "generator_event_contract:" + type(exc).__name__ + ":" + str(exc)
            response.provenance["home_file_names"] = stage.inventory("home")
        verify_generator_closure(spec)
    except (OSError, ValueError, TypeError, IsolationError) as exc:
        response.error = "generator_preparation_or_containment:" + type(exc).__name__
    finally:
        response.provenance["staging_removed"] = stage.removed
        if stage.root is not None and stage.root.exists() and not stage.removed:
            response.provenance["cleanup_required"] = str(stage.root)
        if response.error:
            response.message = b""
    return response


def systemone(plan: dict, job: dict, payload: dict, *, authorised: bool = False,
              mock_response: dict | None = None) -> Response:
    name = adapter(job)
    if not authorised and mock_response is None:
        return Response(error="live_stage_authorisation_required", provenance={"transport_attempts": 0})
    if mock_response is not None and name != "carl_jev":
        raise IntegrityError("Only Path B has an offline deterministic worker contract")
    if plan["operator_execution"]["profile"]["name"] != "research_controlled" and mock_response is None:
        return Response(error="strict_parent_qualification_required", provenance={"transport_attempts": 0})
    cfg = plan["config"]
    spec = dict(cfg["adversaries"][name])
    with Staging("mmmtap-research-systemone-") as stage:
        binds = [(ROOT / "phase2", "/opt/harness/phase2"),
                 (ROOT / "historical_extractor", "/opt/harness/historical_extractor"),
                 (PACKAGE / "worker.py", "/opt/worker.py"), (stage.path("work"), "/work")]
        if name == "carl_jev":
            if sha256_file(Path(spec["binary"])) != spec["binary_sha256"]:
                raise IntegrityError("Path B executable changed")
            binds += [(Path(spec["binary"]), "/opt/bin/path-b"),
                      (Path(spec["policy_root"]), "/policy")]
            spec.update(binary="/opt/bin/path-b", policy_root="/policy")
        key = "" if mock_response is not None else os.environ.get("JEVKEY", "")
        if mock_response is None and not key:
            return Response(error="systemone_credential_missing", provenance={"transport_attempts": 0})
        env = sandbox_env({"PYTHONPATH": "/opt/harness", "PYTHONDONTWRITEBYTECODE": "1"})
        if key:
            env["JEVKEY"] = key
        wire = {"adapter": name, "mode": "live" if mock_response is None else "offline_path_b",
                "spec": spec, "config": {"timeout_seconds": cfg["timeout_seconds"],
                                        "max_response_bytes": cfg["max_response_bytes"]}, "payload": payload}
        if mock_response is not None:
            wire["mock_response"] = mock_response
        argv = bwrap_argv(["/usr/bin/python3", "/opt/worker.py"], ro_binds=binds,
                          network="host" if mock_response is None else "none")
        run = run_once(argv, stdin=json_bytes(wire), env=env, timeout=cfg["timeout_seconds"] + 30,
                       limit=64 * 1024 * 1024)
        outer = Response()
        _capture(outer, run, [key] if key else [])
        if outer.error or run.exit_status != 0:
            outer.error = outer.error or "systemone_worker_failed"
            outer.provenance["execution_outcome"] = "unknown_no_retry" if run.started else "not_started"
            return outer
        try:
            value = strict_json(outer.stdout)
            for field in ("stdout", "stderr", "message"):
                value[field] = base64.b64decode(value[field], validate=True)
            value.pop("raw_encoding")
            result = Response(**value)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            return Response(stdout=outer.stdout, stderr=outer.stderr, error="worker_receipt_invalid:" + type(exc).__name__,
                            provenance={"transport_attempts": None, "execution_outcome": "unknown_no_retry"})
        result.provenance.update(
            provider=cfg["adversaries"][name]["provider"], requested_model=spec["model_id"],
            config_sha256=digest(cfg["adversaries"][name]), worker_config_sha256=digest(spec),
            containment="bubblewrap_fresh_namespace_no_repositories",
            network="disabled" if mock_response is not None else "host_not_endpoint_filtered",
            worker_invocations=1, worker_argv_sha256=digest(argv),
            environment_keys=sorted(env), provider_identity_basis="unsigned_response_model_string",
            cli_version=("source_bound_Path_B_v5" if name == "carl_jev" else None),
            worker_python=sys.version,
            profile=plan["operator_execution"]["profile"],
        )
        if result.provenance.get("credential_redaction"):
            result.error, result.message = "native_credential_echo_redacted_by_v5_transport", b""
        return result


def invoke(plan: dict, job: dict, payload, *, authorised: bool = False) -> Response:
    if job["kind"] == "generator":
        return generator(plan, job, payload, authorised=authorised)
    return systemone(plan, job, payload, authorised=authorised)
