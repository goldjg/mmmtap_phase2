"""One reserved subscription CLI process; durable available CLI stream custody.

No provider HTTP claim. No retry, fallback, output repair or hidden second
engine. The Q1 engine owns reservations, progress records and receipts.
"""
import base64
from dataclasses import asdict
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import time

from . import VERSION
from . import profile
from .contract import require_execution
from .. import engine, transport
from ..model import decode, encode, digest, raw_hash
from ..contracts import load
from ..systemone_https_v1.credential import harden, EntityGuard

DUMMY = "PUBLIC-DUMMY-SUBSCRIPTION-CREDENTIAL"


def parse(req, rec):
    from phase2.adapters_v2 import parse_events
    route = req["provider_route"]
    message, usage, identity = parse_events(transport.unb64(rec["stdout_b64"]), transport.unb64(rec["stderr_b64"]),
        model=route["model"], provider=route["provider"], prompt=req["instrument_request"]["prompt"], mock=False)
    identity.update(serving_identity_attestation=None, provider_HTTP_attempts="UNKNOWN", provider_internal_retries="UNKNOWN",
        evidence_mode="injected_CLI_events" if req["simulation_only"] else "lower_assurance_subscription_CLI",
        raw_evidence="CLI_stdout_stderr_events_NOT_provider_HTTP")
    return message, usage, identity


def parsed_outcome(p, req, rec):
    if rec["status"] != "completed":
        return "unavailable", "CLI_" + rec["status"], {"parsed": None, "availability": "CLI_failure_or_uncertain_completion"}
    try:
        message, usage, identity = parse(req, rec)
        diagnostic = asdict(load()[0].inspect_assessment(message.decode(), p, req["source_text"], req["previous_assessment"]))
        diagnostic.update(identity=identity, usage=usage)
        return ("completed", None, diagnostic) if diagnostic["parsed"] is not None else ("invalid", diagnostic["error"], diagnostic)
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return "invalid", "CLI_event_contract_invalid", {"parsed": None, "availability": "invalid_CLI_events"}


class CLITransport:
    def __init__(self, m, root, p):
        self.m, self.root, self.p = m, root, p

    def invoke(self, envelope, sealed_request, workspace, persist, *, cancel=None):
        m, p = self.m, self.p
        require_execution(m)
        if raw_hash(sealed_request) != envelope["request_sha256"] or envelope["role"] != "generator":
            raise ValueError("CLI_sealed_request_binding")
        req = decode(sealed_request); binding = req["provider_route"]
        profile.verify_binding(binding)
        profile.initialise(workspace, binding)
        (workspace / "request.json").write_bytes(sealed_request)
        fixture = m["simulation_only"]
        argv = profile.argv(binding, workspace, fixture=fixture)
        public_env = profile.environment(binding); env = dict(public_env)
        secret_values = []
        # This is reached only after the live guard for real credentials.
        # Offline tests construct dummy-only state and never inspect host auth.
        harden()
        if fixture:
            from ..live_campaign_v1.routing import fixture_cli_entity
            data = fixture_cli_entity(req["instrument_request"],envelope["scenario"])
            (workspace/"fixture.stdout").write_bytes(base64.b64decode(data["stdout_b64"]))
            (workspace/"fixture.stderr").write_bytes(base64.b64decode(data["stderr_b64"]))
            (workspace/"scenario").write_text(envelope["scenario"])
            (workspace/"event_fixture.py").write_bytes((profile.HERE/"event_fixture.py").read_bytes())
            secret_values = [DUMMY]
            if binding["provider"] == "github_copilot_cli": env["COPILOT_GITHUB_TOKEN"] = DUMMY
            else:
                (workspace / "home/.codex/auth.json").write_bytes(encode({"tokens": {"access_token": DUMMY}}))
                (workspace / "home/.codex/auth.json").chmod(0o600)
        elif binding["provider"] == "github_copilot_cli":
            token = os.environ.get("COPILOT_GITHUB_TOKEN")
            if not token: raise ValueError("selected_Copilot_credential_not_configured")
            secret_values = [token]; env["COPILOT_GITHUB_TOKEN"] = token
        else:
            from operator_execution_v1.transports import read_codex_auth
            raw, secret_values = read_codex_auth()
            auth = workspace / "home/.codex/auth.json"; auth.write_bytes(raw); auth.chmod(0o600)
            del raw
        guards = {name: [EntityGuard(bytearray(s.encode())) for s in secret_values] for name in ("stdout", "stderr")}
        rec = {"contract": VERSION, "attempt_id": envelope["attempt_id"], "request_sha256": envelope["request_sha256"],
            "configuration_sha256": envelope["configuration_sha256"], "context_id": envelope["attempt_id"],
            "workspace": str(workspace), "argv": argv, "environment": public_env,
            "launch_intent_at": transport.now(), "started_at": None, "ended_at": None, "pid": None,
            "status": "launch_intent", "returncode": None, "uncertain_completion": True,
            "stdout_b64": "", "stderr_b64": "", "observed_identity": None, "identity_status": "unknown",
            "identity_provenance": "CLI_client_report_or_unavailable_NOT_serving_attestation",
            "cleanup": False, "cli": {"profile": profile.PROFILE, "requested_model": binding["model"],
                "client_reported_model": None, "serving_identity_attestation": None, "serving_identity_status": "unavailable", "provider_HTTP_attempts": "UNKNOWN",
                "provider_internal_retries": "UNKNOWN", "top_level_CLI_launches": 0, "usage": None,
                "fixture": fixture, "raw_evidence": "CLI_stdout_stderr_events_NOT_provider_HTTP",
                "credential_capture_refused": False, "failure": None, "assurance_sha256": digest(m["assurance"])}}
        persist(rec)  # unique invocation journal commit BEFORE Popen.
        child = None; buffers = {"stdout": bytearray(), "stderr": bytearray()}; pending = {"stdout": b"", "stderr": b""}
        from operator_execution_v1.transports import Watchdog
        watchdog = Watchdog(binding["provider"], binding["model"])
        limit = m["transport"]["specification"]["cli_stream_limit"]
        timeout = 0.7 if fixture and envelope["scenario"] == "cli_timeout" else m["transport"]["specification"]["cli_deadline_seconds"]
        deadline = time.monotonic() + timeout; failure = None
        try:
            with (workspace / "stdin").open("w+b") as input_file, selectors.DefaultSelector() as selector:
                input_file.write(req["instrument_request"]["prompt"].encode()); input_file.seek(0)
                child = subprocess.Popen(argv, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=env, cwd=workspace, close_fds=True, start_new_session=True)
                rec.update(started_at=transport.now(), pid=child.pid, status="running")
                rec["cli"]["top_level_CLI_launches"] = 1; persist(rec)
                for name in buffers:
                    os.set_blocking(getattr(child,name).fileno(),False)
                    selector.register(getattr(child,name),selectors.EVENT_READ,name)
                while selector.get_map():
                    if time.monotonic() >= deadline or cancel is not None and cancel.is_set():
                        failure = "timeout_or_interruption_execution_unknown"; break
                    for key,_ in selector.select(0.02):
                        chunk = os.read(key.fileobj.fileno(),65536); name=key.data
                        if not chunk:
                            selector.unregister(key.fileobj)
                            tail=b""
                            for guard in guards[name]: tail=guard.feed(tail,final=True)
                            capacity=limit-len(buffers[name]);buffers[name].extend(tail[:capacity])
                            if len(tail)>capacity:failure="CLI_stream_byte_limit"
                            continue
                        safe = chunk
                        for guard in guards[name]: safe=guard.feed(safe)
                        capacity=limit-len(buffers[name]);buffers[name].extend(safe[:capacity])
                        rec[name+"_b64"] = transport.b64(buffers[name]);persist(rec)
                        if len(safe)>capacity: failure="CLI_stream_byte_limit";break
                        lines=(pending[name]+safe).split(b"\n");pending[name]=lines.pop()
                        for line in lines:
                            reason=watchdog(name,line)
                            if reason: failure="CLI_watchdog_"+reason;break
                        if failure: break
                    if envelope["scenario"] == "cli_interrupt" and buffers["stdout"]:
                        os._exit(75)  # bwrap PID namespace dies; reservation stays consumed.
                    if failure: break
                if failure and child.poll() is None: os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=3)
                rec["returncode"] = child.returncode
                if child.returncode and failure is None: failure="CLI_nonzero_exit"
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            # Never include exception strings originating in credentials/output.
            failure="CLI_capture_or_process_failure"
            rec["cli"]["credential_capture_refused"] = type(exc) is ValueError and str(exc)=="credential_reflection_capture_refused"
        finally:
            if child is not None:
                if child.poll() is None: os.killpg(child.pid,signal.SIGKILL)
                child.wait()
                for stream in (child.stdout,child.stderr): stream.close()
            for group in guards.values():
                for guard in group: guard.clear()
            env.clear();secret_values.clear()
            shutil.rmtree(workspace)
        rec.update(ended_at=transport.now(),cleanup=True,status="process_failure" if failure else "completed",
                   uncertain_completion=bool(failure),stdout_b64=transport.b64(buffers["stdout"]),stderr_b64=transport.b64(buffers["stderr"]))
        rec["cli"]["failure"] = failure
        if not failure:
            try:
                _,usage,identity = parse(req,rec)
                model=identity["observed_model"];rec["cli"].update(client_reported_model=model,usage=usage)
                rec["observed_identity"] = {"provider": binding["provider"],"model":model} if model else None
                rec["identity_status"] = "matched" if model==binding["model"] else "unknown" if model is None else "mismatch"
            except (ValueError,KeyError,TypeError,UnicodeError,RecursionError): pass
        persist(rec)
        return transport.TransportResult(rec,transport.unb64(rec["stdout_b64"]),rec["observed_identity"])


def verify_record(rec, env, spec, root, previous):
    # Reconstruct the exact separately versioned argv/configuration, not the
    # strict worker argv and not an invented HTTP receipt.
    m=decode((root/'manifest.json').read_bytes());p=next(p for p in m['positions'] if p['id']==env['position'])
    binding=m['production_campaign']['routes'][p['route']]
    required={"contract","attempt_id","request_sha256","configuration_sha256","context_id","workspace","argv","environment",
        "launch_intent_at","started_at","ended_at","pid","status","returncode","uncertain_completion","stdout_b64","stderr_b64",
        "observed_identity","identity_status","identity_provenance","cleanup","cli"}
    if set(rec)!=required or rec['contract']!=VERSION:raise ValueError('CLI_record_shape_changed')
    for key in ('attempt_id','request_sha256','configuration_sha256'):
        if rec[key]!=env[key]:raise ValueError('CLI_attempt_binding_changed')
    work=Path(rec['workspace'])
    if work.name!=env['attempt_id'] or work.parent.name!='.transport-work' or rec['context_id']!=env['attempt_id']:
        raise ValueError('CLI_context_reused_or_changed')
    if rec['argv']!=profile.argv(binding,work,fixture=m['simulation_only']) or rec['environment']!=profile.environment(binding):
        raise ValueError('CLI_argv_or_environment_changed')
    if (rec['status'] not in {'launch_intent','running','completed','process_failure','interrupted'}
            or rec['cli']['top_level_CLI_launches'] not in (0,1) or rec['cli']['assurance_sha256']!=digest(m['assurance'])
            or rec['cli']['serving_identity_attestation'] is not None
            or rec['cli']['provider_HTTP_attempts']!='UNKNOWN' or rec['cli']['provider_internal_retries']!='UNKNOWN'
            or rec['cli']['raw_evidence']!='CLI_stdout_stderr_events_NOT_provider_HTTP'):
        raise ValueError('CLI_assurance_or_attempt_claim_changed')
    for name in ('stdout_b64','stderr_b64'):
        raw=transport.unb64(rec[name])
        if len(raw)>spec['cli_stream_limit'] or previous and not raw.startswith(transport.unb64(previous[name])):
            raise ValueError('CLI_raw_prefix_changed')
    if previous:
        if previous['status'] not in {'launch_intent','running'} or rec['launch_intent_at']!=previous['launch_intent_at']:
            raise ValueError('CLI_reinvocation_or_nonmonotonic_progress')
        if previous['pid'] is not None and rec['pid']!=previous['pid']:raise ValueError('CLI_PID_changed')
    elif rec['status']!='launch_intent':raise ValueError('CLI_missing_durable_launch_intent')
    if rec['status']=='completed':
        if rec['returncode']!=0 or not rec['cleanup'] or rec['cli']['top_level_CLI_launches']!=1:
            raise ValueError('CLI_false_completion')
        stored=db_request=None
        db=engine.connect(root,readonly=True)
        try: stored=decode(db.execute('SELECT request FROM attempts WHERE id=?',(p['id'],)).fetchone()[0])
        finally: db.close()
        try:
            _,usage,identity=parse(stored,rec);model=identity['observed_model']
        except (ValueError,KeyError,TypeError,UnicodeError,RecursionError):model,usage=None,None
        if (rec['cli']['client_reported_model'],rec['cli']['usage'])!=(model,usage):
            raise ValueError('CLI_identity_or_usage_not_supported_by_raw_events')
    model=rec['cli']['client_reported_model']
    observed={'provider':binding['provider'],'model':model} if model else None
    if rec['observed_identity']!=observed:raise ValueError('CLI_client_identity_changed')
