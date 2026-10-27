"""Versioned offline one-shot transport. No scheduler, registry or evidence store.

The executor supplies an already reserved request and durable event callback.
Only a hash-bound local fixture is selectable. No provider/CLI/SDK adapter or
network-enabled configuration is implemented or authorized.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import time
from typing import Callable, Protocol

from .model import PACKAGE, decode, digest, encode, raw_hash, read_file, validate_response

VERSION = "q1-offline-subprocess-v1"
SCENARIOS = {"valid", "malformed", "partial_failure", "timeout", "crash", "identity_mismatch",
             "identity_unknown", "forbidden_file", "spawn", "exec", "network", "reuse",
             "source_write", "policy_write", "session_seed", "running_interrupt"}


def now():
    return datetime.now(timezone.utc).isoformat()


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def unb64(value):
    return base64.b64decode(value, validate=True)


def process_identity(pid):
    try:
        fields = Path("/proc").joinpath(str(pid), "stat").read_text().split(") ", 1)[1].split()
        return {"pid": pid, "start_ticks": fields[19], "state": fields[0]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def process_tree(pid):
    result = []
    def visit(ident):
        info = process_identity(ident)
        if info is None:
            return
        result.append(info)
        try:
            children = Path(f"/proc/{ident}/task/{ident}/children").read_text().split()
        except (FileNotFoundError, ProcessLookupError):
            return
        for child in children: visit(int(child))
    visit(pid)
    return result


@dataclass(frozen=True)
class TransportResult:
    record: dict
    raw: bytes
    observed: dict | None


class Transport(Protocol):
    def invoke(self, envelope: dict, sealed_request: bytes, workspace: Path,
               persist: Callable[[dict], None], *, cancel=None) -> TransportResult: ...


def specification():
    libraries = list(Path("/usr/lib").glob("*/libseccomp.so.2"))
    if len(libraries) != 1:
        raise ValueError("required_libseccomp_unavailable_or_ambiguous")
    paths = {"python": Path(sys.executable).resolve(), "bwrap": Path("/usr/bin/bwrap"),
             "seccomp": libraries[0].resolve(), "bootstrap": PACKAGE / "transport_bootstrap.py",
             "adapter": PACKAGE / "transport_fixture.py"}
    return {"contract": VERSION, "offline_only": True, "network": "denied", "tools": "denied",
            "backend": "bwrap-mount-pid-user-ipc-uts-and-seccomp-allowlist",
            "bindings": {k: {"path": str(p), "sha256": raw_hash(p.read_bytes())} for k, p in paths.items()},
            "versions": {"python": sys.version, "transport": VERSION,
                         "bwrap_and_libseccomp": "exact_executable_library_sha256_bindings"},
            "environment": {"HOME": "/home/assessor", "LANG": "C.UTF-8", "PATH": "/usr/bin:/bin", "TMPDIR": "/work", "PWD": "/work"},
            "timeout_seconds": 2, "max_stream_bytes": 1048576}


def extension(scenarios=None):
    spec = specification()
    return {"version": VERSION, "specification": spec, "configuration_sha256": digest(spec),
            "scenarios": scenarios or {}}


def validate_extension(m):
    from .broker_v1.contract import is_broker, validate_extension as broker_validate
    if is_broker(m):
        return broker_validate(m)
    ext = m["transport"]
    if (set(ext) != {"version", "specification", "configuration_sha256", "scenarios"}
            or ext["version"] != VERSION or ext["specification"] not in (
                specification(), decode(read_file(PACKAGE, "legacy-transport-specification.v1.json")))
            or ext["configuration_sha256"] != digest(ext["specification"])
            or not isinstance(ext["scenarios"], dict)
            or any(k not in {p["id"] for p in m["positions"]} or v not in SCENARIOS
                   for k, v in ext["scenarios"].items())):
        raise ValueError("offline_transport_manifest_binding")


def envelope_for(m, p, sealed_request):
    from .broker_v1.contract import is_broker, envelope_for as broker_envelope
    return (broker_envelope if is_broker(m) else base_envelope_for)(m, p, sealed_request)


def base_envelope_for(m, p, sealed_request):
    ext = m["transport"]
    spec = ext["specification"]
    return {"contract": VERSION, "attempt_id": digest({"manifest": m["manifest_sha256"], "position": p["id"]}),
            "request_sha256": raw_hash(sealed_request), "role": p["kind"],
            "manifest_sha256": m["manifest_sha256"], "position": p["id"],
            "configuration_sha256": ext["configuration_sha256"],
            "requested_identity": {**p["identity"], "version": "synthetic-adapter-v1",
                                   "judge": "synthetic-shared-systemone-v1" if p["kind"] == "specialist" else None},
            "network": "denied", "tools": "denied", "conversation": "new_local_context_no_session_import",
            "scenario": ext["scenarios"].get(p["id"], "valid"),
            "adapter_sha256": spec["bindings"]["adapter"]["sha256"],
            "seccomp_library": spec["bindings"]["seccomp"]["path"],
            # Public synthetic canary only. Never probe a credential or custody file.
            "forbidden_probe": str(Path(spec["bindings"]["adapter"]["path"]).parent / "transport_evidence" / "forbidden-canary.txt")}


def launch_argv(spec, workspace):
    return [spec["bindings"]["bwrap"]["path"], "--unshare-user", "--unshare-pid", "--unshare-ipc",
                "--unshare-uts", "--die-with-parent", "--new-session", "--cap-drop", "ALL", "--hostname", "q1-offline",
                "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib", "--symlink", "usr/bin", "/bin",
                "--proc", "/proc", "--dev", "/dev", "--size", "16777216", "--tmpfs", "/work",
                "--size", "16777216", "--tmpfs", "/home",
                "--dir", "/home/assessor", "--ro-bind", str((workspace / "inputs").absolute()), "/inputs",
                "--size", "16777216", "--tmpfs", "/response", "--chdir", "/work", "--",
                spec["bindings"]["python"]["path"], "-I", "-S", "-B", "/inputs/bootstrap.py"]


class OfflineSubprocessTransport:
    def __init__(self, spec):
        if spec != specification():
            raise ValueError("only_pinned_offline_fixture_transport_permitted")
        self.spec = spec

    def invoke(self, envelope, sealed_request, workspace, persist, *, cancel=None):
        if raw_hash(sealed_request) != envelope["request_sha256"] or envelope["contract"] != VERSION:
            raise ValueError("sealed_transport_request_mismatch")
        if workspace.exists():
            raise ValueError("transport_workspace_reuse_refused")
        workspace.mkdir(mode=0o700, parents=True)
        inputs = workspace / "inputs"
        inputs.mkdir(mode=0o700)
        (inputs / "request.json").write_bytes(sealed_request)
        (inputs / "envelope.json").write_bytes(encode(envelope))
        for name, key in (("adapter.py", "adapter"), ("bootstrap.py", "bootstrap")):
            pin = self.spec["bindings"][key]
            raw = Path(pin["path"]).read_bytes()
            if raw_hash(raw) != pin["sha256"]:
                raise ValueError("transport_executable_changed:" + key)
            (inputs / name).write_bytes(raw)
        for p in inputs.iterdir():
            p.chmod(0o400)
        argv = launch_argv(self.spec, workspace)
        rec = {"contract": VERSION, "attempt_id": envelope["attempt_id"],
               "request_sha256": envelope["request_sha256"], "configuration_sha256": envelope["configuration_sha256"],
               "context_id": envelope["attempt_id"], "workspace": str(workspace.absolute()),
               "argv": argv, "environment": self.spec["environment"],
               "launch_intent_at": now(), "started_at": None, "ended_at": None, "pid": None,
               "status": "launch_intent", "returncode": None, "uncertain_completion": True,
               "stdout_b64": "", "stderr_b64": "", "observed_identity": None,
               "identity_provenance": "not_observed", "identity_status": "unknown",
               "bootstrap_verified": False, "cleanup": False}
        rec["processes"] = []
        persist(rec)  # committed before Popen: ambiguity never permits a second launch.
        proc = None
        streams = {"stdout": bytearray(), "stderr": bytearray()}
        selector = selectors.DefaultSelector()
        try:
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=self.spec["environment"], cwd=workspace, close_fds=True, start_new_session=True)
            rec.update(started_at=now(), pid=proc.pid, status="running", processes=process_tree(proc.pid))
            persist(rec)
            for name in streams:
                stream = getattr(proc, name); os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            deadline = time.monotonic() + self.spec["timeout_seconds"]
            forced = None
            while selector.get_map():
                if forced is None:
                    forced = "cancelled" if cancel is not None and cancel.is_set() else (
                        "timeout" if time.monotonic() >= deadline else None)
                    if forced:
                        os.killpg(proc.pid, signal.SIGKILL)
                for key, _ in selector.select(0.02):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj); continue
                    streams[key.data].extend(chunk)
                    if len(streams[key.data]) > self.spec["max_stream_bytes"]:
                        forced = "output_limit"; os.killpg(proc.pid, signal.SIGKILL)
                        del streams[key.data][self.spec["max_stream_bytes"]:]
                    rec["stdout_b64"], rec["stderr_b64"] = (b64(bytes(streams[n])) for n in ("stdout", "stderr"))
                    try:
                        ack = decode(bytes(streams["stderr"]).splitlines()[0])
                        rec["bootstrap_verified"] = ack == {"bootstrap": VERSION, "attempt_id": envelope["attempt_id"],
                                                            "request_sha256": envelope["request_sha256"], "seccomp_loaded": True}
                    except (ValueError, IndexError, UnicodeError):
                        pass
                    rec["processes"] = process_tree(proc.pid) or rec["processes"]
                    persist(rec)  # raw partial bytes survive executor interruption.
            proc.wait(timeout=2)
            rec.update(returncode=proc.returncode, status=forced or ("completed" if proc.returncode == 0 else "process_failure"),
                       uncertain_completion=forced is not None)
        except OSError as exc:
            rec.update(status="launch_failure", error=str(exc), uncertain_completion=False)
        finally:
            if proc is not None:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=2)
                proc.stdout.close(); proc.stderr.close()
            selector.close()
            shutil.rmtree(workspace)
            rec.update(ended_at=now(), cleanup=True)
        lines = bytes(streams["stderr"]).splitlines()
        try:
            ack = decode(lines[0])
            rec["bootstrap_verified"] = ack == {"bootstrap": VERSION, "attempt_id": envelope["attempt_id"],
                                                "request_sha256": envelope["request_sha256"], "seccomp_loaded": True}
        except (ValueError, IndexError, UnicodeError):
            pass
        if not rec["bootstrap_verified"]:
            rec.update(status="containment_unavailable", uncertain_completion=True)
        else:
            try:
                ident = decode(lines[-1])
                rec["observed_identity"] = ident["observed_identity"]
                rec["identity_provenance"] = ident["provenance"]
                rec["identity_status"] = "unknown" if ident["observed_identity"] is None else (
                    "matched" if ident["observed_identity"] == envelope["requested_identity"] else "mismatch")
            except (ValueError, IndexError, KeyError, TypeError, UnicodeError):
                pass
        rec["stdout_b64"], rec["stderr_b64"] = (b64(bytes(streams[n])) for n in ("stdout", "stderr"))
        persist(rec)
        return TransportResult(rec, bytes(streams["stdout"]), rec["observed_identity"])


def outcome(p, req, rec):
    from .live_campaign_v1 import VERSION as CAMPAIGN
    if rec["contract"] == CAMPAIGN:
        from .live_campaign_v1.contract import outcome as campaign_outcome
        return campaign_outcome(p, req, rec)
    from .systemone_https_v1 import VERSION as HTTPS_VERSION
    if rec["contract"] == HTTPS_VERSION:
        from .systemone_https_v1.contract import outcome as https_outcome
        return https_outcome(p, req, rec)
    if rec["status"] != "completed":
        return "unavailable", "transport_" + rec["status"], {"parsed": None, "availability": "transport_failure"}
    if rec["identity_status"] != "matched":
        return "unavailable", "transport_identity_" + rec["identity_status"], {"parsed": None, "availability": "identity_failure"}
    return validate_response(p, req, unb64(rec["stdout_b64"]), p["identity"])


def verify_record(rec, envelope, spec, root, previous):
    from .broker_v1 import VERSION as BROKER_VERSION
    from .systemone_https_v1 import VERSION as HTTPS_VERSION
    from .live_campaign_v1 import VERSION as CAMPAIGN
    if spec["contract"] in (BROKER_VERSION, HTTPS_VERSION, CAMPAIGN):
        from .broker_v1.contract import verify_record as broker_verify
        return broker_verify(rec, envelope, spec, root, previous)
    return base_verify_record(rec, envelope, spec, root, previous)


def base_verify_record(rec, envelope, spec, root, previous):
    """Read-only structural/monotonic replay. Process output is not attestation."""
    required = {"contract", "attempt_id", "request_sha256", "configuration_sha256", "context_id", "workspace", "argv",
                "environment", "launch_intent_at", "started_at", "ended_at", "pid", "status", "returncode",
                "uncertain_completion", "stdout_b64", "stderr_b64", "observed_identity", "identity_provenance",
                "identity_status", "bootstrap_verified", "cleanup", "processes"}
    if set(rec) not in (required, required | {"error"}):
        raise ValueError("transport_record_shape")
    for key in ("contract", "attempt_id", "request_sha256", "configuration_sha256"):
        if rec[key] != envelope[key]:
            raise ValueError("transport_record_identity_or_request_binding")
    if (rec["context_id"] != envelope["attempt_id"] or rec["environment"] != spec["environment"]
            or rec["status"] not in {"launch_intent", "running", "completed", "process_failure", "timeout",
                                     "cancelled", "output_limit", "launch_failure", "containment_unavailable", "interrupted"}
            or rec["identity_status"] not in {"matched", "mismatch", "unknown"}):
        raise ValueError("transport_controls_or_status_changed")
    work = rec["workspace"]
    work_path = Path(work)
    if (not work_path.is_absolute() or ".." in work_path.parts or work_path.name != envelope["attempt_id"]
            or work_path.parent.name != ".transport-work" or work_path.as_posix() != work):
        raise ValueError("transport_workspace_binding")
    argv = rec["argv"]
    expected = [spec["bindings"]["bwrap"]["path"], "--unshare-user", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
                "--die-with-parent", "--new-session", "--cap-drop", "ALL", "--hostname", "q1-offline", "--ro-bind", "/usr", "/usr",
                "--symlink", "usr/lib", "/lib", "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev",
                "--size", "16777216", "--tmpfs", "/work", "--size", "16777216", "--tmpfs", "/home",
                "--dir", "/home/assessor", "--ro-bind", work + "/inputs", "/inputs",
                "--size", "16777216", "--tmpfs", "/response", "--chdir", "/work", "--",
                spec["bindings"]["python"]["path"], "-I", "-S", "-B", "/inputs/bootstrap.py"]
    if argv != expected:
        raise ValueError("transport_argv_or_workspace_changed")
    for name in ("stdout_b64", "stderr_b64"):
        raw = unb64(rec[name])
        if len(raw) > spec["max_stream_bytes"] or b64(raw) != rec[name]:
            raise ValueError("transport_stream_size_or_encoding")
        if previous and not raw.startswith(unb64(previous[name])):
            raise ValueError("transport_partial_bytes_changed")
    if previous:
        if (previous["status"] not in ("launch_intent", "running")
                or previous["launch_intent_at"] != rec["launch_intent_at"]
                or previous["started_at"] is not None and previous["started_at"] != rec["started_at"]
                or previous["pid"] is not None and previous["pid"] != rec["pid"]):
            raise ValueError("transport_nonmonotonic_progress")
    elif rec["status"] != "launch_intent":
        raise ValueError("transport_missing_launch_intent")
    if rec["status"] == "completed" and (rec["returncode"] != 0 or not rec["bootstrap_verified"] or not rec["cleanup"]):
        raise ValueError("transport_false_success")
    if rec["identity_status"] == "matched" and rec["observed_identity"] != envelope["requested_identity"]:
        raise ValueError("transport_false_identity_match")
    computed_identity = "unknown" if rec["observed_identity"] is None else (
        "matched" if rec["observed_identity"] == envelope["requested_identity"] else "mismatch")
    if rec["identity_status"] != computed_identity:
        raise ValueError("transport_identity_classification_changed")
    lines = unb64(rec["stderr_b64"]).splitlines()
    try:
        ack = decode(lines[0])
        verified = ack == {"bootstrap": VERSION, "attempt_id": envelope["attempt_id"],
                           "request_sha256": envelope["request_sha256"], "seccomp_loaded": True}
    except (ValueError, IndexError, UnicodeError):
        verified = False
    if rec["bootstrap_verified"] != verified:
        raise ValueError("transport_bootstrap_ack_changed")
    times = [datetime.fromisoformat(rec[k]) for k in ("launch_intent_at", "started_at", "ended_at") if rec[k] is not None]
    if any(t.tzinfo is None for t in times) or times != sorted(times):
        raise ValueError("transport_timestamp_order")
    if rec["status"] not in ("launch_intent", "running") and rec["ended_at"] is None:
        raise ValueError("transport_missing_terminal_time")


def validate_manifest(root, m, raw):
    # Delegate the original manifest and scientific contracts unchanged.
    from .model import validate_slice_manifest
    base = {k: v for k, v in m.items() if k != "transport"}
    base["manifest_sha256"] = digest({k: v for k, v in base.items() if k != "manifest_sha256"})
    if "full_matrix" in base:
        from .full_matrix import validate
        validate(root, base, encode(base))
    else:
        validate_slice_manifest(root, base, encode(base))
    validate_extension(m)
    if m["manifest_sha256"] != digest({k: v for k, v in m.items() if k != "manifest_sha256"}) or raw != encode(m):
        raise ValueError("transport_manifest_digest")
    return m, raw
