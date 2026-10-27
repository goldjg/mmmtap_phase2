"""Executor-side supervisor for stdio IPC. No socket/syscall policy extension.

The broker is a separate trusted process with a fixed per-attempt grant. Only
the worker sees the isolated mount namespace; it never inherits the database,
repository, broker descriptors, mock integrity key or any other attempt's pipe.
"""
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import time

from . import VERSION
from .contract import specification
from .broker import records, reconcile
from .. import engine, transport
from ..model import PACKAGE, decode, encode, raw_hash


class BrokerTransport:
    def __init__(self, spec, root, ident):
        from ..systemone_https_v1.contract import specification as https_specification
        if spec not in (specification(), https_specification()):
            raise ValueError("only_pinned_offline_broker_permitted")
        self.spec, self.root, self.ident = spec, root, ident

    def invoke(self, envelope, sealed_request, workspace, persist, *, cancel=None):
        spec = self.spec
        if raw_hash(sealed_request) != envelope["request_sha256"]:
            raise ValueError("broker_sealed_request_mismatch")
        if workspace.exists():
            raise ValueError("broker_workspace_reuse_refused")
        workspace.mkdir(mode=0o700, parents=True)
        inputs = workspace / "inputs"; inputs.mkdir(mode=0o700)
        (inputs / "request.json").write_bytes(sealed_request)
        (inputs / "envelope.json").write_bytes(encode(envelope))
        for name, key in (("adapter.py", "adapter"), ("bootstrap.py", "bootstrap")):
            pin = spec["bindings"][key]
            raw = Path(pin["path"]).read_bytes()
            if raw_hash(raw) != pin["sha256"]:
                raise ValueError("broker_worker_or_bootstrap_changed")
            (inputs / name).write_bytes(raw)
        for p in inputs.iterdir():
            p.chmod(0o400)
        argv = transport.launch_argv(spec, workspace)
        rec = {"contract": spec["contract"], "attempt_id": envelope["attempt_id"],
               "request_sha256": envelope["request_sha256"], "configuration_sha256": envelope["configuration_sha256"],
               "context_id": envelope["attempt_id"], "workspace": str(workspace.absolute()),
               "argv": argv, "environment": spec["environment"], "launch_intent_at": transport.now(),
               "started_at": None, "ended_at": None, "pid": None, "status": "launch_intent",
               "returncode": None, "uncertain_completion": True, "stdout_b64": "", "stderr_b64": "",
               "observed_identity": None, "identity_provenance": "not_observed", "identity_status": "unknown",
               "bootstrap_verified": False, "cleanup": False, "processes": []}
        from ..systemone_https_v1 import VERSION as HTTPS_VERSION
        https = spec["contract"] == HTTPS_VERSION
        if https:
            rec["https"] = None
        jevkey = "credential_binding" in envelope
        credential_fds = []
        if jevkey:
            from ..systemone_https_v1.credential import configured, harden
            rec["credential_handoff"] = {"contract": envelope["credential_binding"]["version"],
                "source_configured": configured(), "launcher_protection": harden(),
                "broker_ready_before_release": False, "broker_sender_PID_authenticated": False,
                "delivery": "not_released", "broker_pid": None}
        persist(rec)
        worker = broker = None
        selector = selectors.DefaultSelector()
        pending, worker_buf, broker_buf, stderr = [], bytearray(), bytearray(), bytearray()
        worker_echo, forced, last = None, None, None
        ro = engine.connect(self.root, readonly=True)
        deadline = time.monotonic() + spec["timeout_seconds"]
        total_ipc = 0
        write_buffers = {}

        def queue_write(stream, data, label):
            fd = stream.fileno()
            if fd not in write_buffers:
                write_buffers[fd] = bytearray()
                os.set_blocking(fd, False)
                selector.register(stream, selectors.EVENT_WRITE, label)
            write_buffers[fd].extend(data)
            if len(write_buffers[fd]) > spec["max_ipc_bytes"]:
                raise ValueError("ipc_backpressure_limit")

        def start_broker():
            nonlocal broker
            argv = [
                spec["bindings"]["python"]["path"], "-B", "-m",
                "engineering_qualification_v1.q1_executor.broker_v1.broker",
                "--campaign", str(self.root), "--position", self.ident,
                "--manifest", envelope["manifest_sha256"]]
            inherited = ()
            if jevkey:
                parent_channel, broker_channel = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
                parent_channel.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
                credential_fds.extend((parent_channel, broker_channel))
                inherited = (broker_channel.fileno(),)
                argv += ["--credential-control-fd", str(broker_channel.fileno())]
            broker = subprocess.Popen(argv,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                close_fds=True, pass_fds=inherited, cwd=PACKAGE.parent.parent,
                env={"LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
            if jevkey:
                from ..systemone_https_v1.credential import handoff_from_environment
                broker_channel.close(); credential_fds.remove(broker_channel)
                try:
                    handoff = handoff_from_environment(parent_channel, broker.pid)
                finally:
                    credential_fds.remove(parent_channel)
                rec["credential_handoff"] = {**handoff, "broker_pid": broker.pid}
                persist(rec)
            for name in ("stdout", "stderr"):
                stream = getattr(broker, name); os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, "broker_" + name)

        try:
            worker = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=spec["environment"], cwd=workspace, close_fds=True, start_new_session=True)
            rec.update(started_at=transport.now(), pid=worker.pid, status="running",
                       processes=transport.process_tree(worker.pid))
            persist(rec)
            for name in ("stdout", "stderr"):
                stream = getattr(worker, name); os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, "worker_" + name)
            while selector.get_map():
                if time.monotonic() >= deadline or cancel is not None and cancel.is_set():
                    forced = "timeout" if cancel is None or not cancel.is_set() else "cancelled"
                    break
                for key, _ in selector.select(0.01):
                    if key.data.endswith("_input"):
                        fd = key.fileobj.fileno()
                        try:
                            count = os.write(fd, write_buffers[fd])
                            del write_buffers[fd][:count]
                        except BrokenPipeError:
                            write_buffers[fd].clear()
                        if not write_buffers[fd]:
                            selector.unregister(key.fileobj)
                            del write_buffers[fd]
                        continue
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total_ipc += len(chunk)
                    if total_ipc > spec["max_ipc_bytes"]:
                        forced = "output_limit"; break
                    if key.data.endswith("stderr"):
                        # Bootstrap ACK remains the first stderr line. Broker
                        # exceptions are diagnostics, never provider identity.
                        stderr.extend(chunk)
                    else:
                        buf = worker_buf if key.data == "worker_stdout" else broker_buf
                        buf.extend(chunk)
                        while b"\n" in buf:
                            line, _, rest = buf.partition(b"\n"); buf[:] = rest
                            frame = decode(line)
                            if key.data == "broker_stdout":
                                queue_write(worker.stdin, encode(frame) + b"\n", "worker_input")
                            elif frame.get("type") == "request":
                                pending.append(frame)
                            elif frame.get("type") == "result":
                                if worker_echo is not None:
                                    raise ValueError("duplicate_worker_result")
                                worker_echo = transport.unb64(frame["raw_b64"])
                            elif frame.get("type") == "probe":
                                stderr.extend(encode(frame) + b"\n")
                            else:
                                raise ValueError("invalid_worker_frame")
                try:
                    ack = decode(bytes(stderr).splitlines()[0])
                    rec["bootstrap_verified"] = ack == {"bootstrap": transport.VERSION,
                        "attempt_id": envelope["attempt_id"], "request_sha256": envelope["request_sha256"], "seccomp_loaded": True}
                except (ValueError, IndexError, UnicodeError):
                    pass
                if pending and rec["bootstrap_verified"]:
                    if broker is None:
                        start_broker()
                    for frame in pending:
                        queue_write(broker.stdin, encode(frame) + b"\n", "broker_input")
                    pending.clear()
                hist = records(ro, self.ident)
                current = hist[-1] if hist else None
                if current != last or rec["stderr_b64"] != transport.b64(stderr):
                    last = current
                    if last:
                        rec["stdout_b64"] = last["raw_b64"]
                        if https:
                            rec["https"] = last["https"]
                    rec["stderr_b64"] = transport.b64(stderr)
                    rec["processes"] = (transport.process_tree(worker.pid) +
                                        (transport.process_tree(broker.pid) if broker else [])) or rec["processes"]
                    persist(rec)
                if envelope["scenario"] in ("executor_interrupt", "jev_interrupt") and last and last["stage"] == "partial_response":
                    os._exit(75)  # real outstanding provider request, committed raw prefix.
                if broker is not None and broker.poll() is not None:
                    if envelope["scenario"] == "after_acceptance" and broker.returncode == 72:
                        os._exit(75)  # no response or terminal receipt publication.
                    if worker.poll() is None:
                        try:
                            queue_write(worker.stdin, encode({"type": "reply", "authorised": False, "raw_b64": ""}) + b"\n", "worker_input")
                        except BrokenPipeError:
                            pass
                    forced = "process_failure"
                    break
                if worker.poll() is not None:
                    # Drain every worker stream before terminating the broker.
                    if not any(k.data.startswith("worker_") for k in selector.get_map().values()):
                        break
            if worker.poll() is None:
                os.killpg(worker.pid, signal.SIGKILL)
            worker.wait(timeout=2)
            rec["returncode"] = worker.returncode
        except (OSError, ValueError, KeyError, TypeError) as exc:
            forced = "process_failure"
            # Generic errors only in the credential path: never stringify an
            # exception that might originate in a secret/channel operation.
            stderr.extend(b"\nsupervisor:credential_boundary_failure" if jevkey else ("\nsupervisor:" + str(exc)).encode())
        finally:
            for fd in credential_fds:
                try:
                    fd.close()
                except OSError:
                    pass
            for proc in (worker, broker):
                if proc is not None:
                    if proc.poll() is None:
                        if proc is worker:
                            os.killpg(proc.pid, signal.SIGKILL)
                        else:
                            proc.kill()
                    proc.wait(timeout=2)
                    for stream in (proc.stdin, proc.stdout, proc.stderr):
                        if stream and not stream.closed:
                            stream.close()
            selector.close(); ro.close()
            # Finalise only after both supervised processes are stopped, so
            # reconciliation cannot race a late provider-side journal commit.
            db = engine.connect(self.root)
            try:
                m = decode((self.root / "manifest.json").read_bytes())
                p = next(p for p in m["positions"] if p["id"] == self.ident)
                reconcile(db, self.root, m, p)
                hist = records(db, self.ident)
                last = hist[-1] if hist else None
            finally:
                db.close()
            shutil.rmtree(workspace)
        rec.update(ended_at=transport.now(), cleanup=True, stderr_b64=transport.b64(stderr))
        if last:
            rec["stdout_b64"] = last["raw_b64"]
            rec["observed_identity"] = last["observed_identity"]
            rec["identity_provenance"] = "untrusted_synthetic_mock_self_report_local_MAC_not_provider_attestation"
            if https:
                rec["https"] = last["https"]
                rec["identity_provenance"] = "local_TLS_fixture_entity_self_report_not_genuine_SystemOne_attestation"
        rec["identity_status"] = "unknown" if rec["observed_identity"] is None else (
            "matched" if rec["observed_identity"] == envelope["requested_identity"] else "mismatch")
        raw = transport.unb64(rec["stdout_b64"])
        if worker_echo is not None and worker_echo != raw:
            stderr.extend(encode({"worker_echo_sha256": raw_hash(worker_echo),
                                  "broker_raw_sha256": raw_hash(raw), "worker_echo_matches": False}) + b"\n")
            rec["stderr_b64"] = transport.b64(stderr)
        successful = bool(last and last["stage"] == "complete_response" and last["frame_integrity"]
                          and worker_echo == raw and worker.returncode == 0)
        rec.update(status=forced or ("completed" if successful else "process_failure"),
                   uncertain_completion=bool(last and last["uncertain_completion"]))
        if not rec["bootstrap_verified"]:
            rec.update(status="containment_unavailable", uncertain_completion=True)
        persist(rec)
        return transport.TransportResult(rec, raw, rec["observed_identity"])
