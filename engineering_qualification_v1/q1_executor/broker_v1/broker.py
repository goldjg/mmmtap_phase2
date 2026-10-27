"""Trusted local broker. The executor database is the only durable authority.

No sockets, URLs, credentials, SDKs, retries or live adapters. Each dispatch
opens one pinned local mock process after committing intent in the Q1 journal.
"""
import argparse
import ctypes
import hashlib
import hmac
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from . import VERSION, DESTINATION
from .contract import HERE, envelope_for, message, is_broker
from ..model import decode, digest, encode, raw_hash
from ..transport import b64, unb64
from .. import engine

TRANSITIONS = {
    None: {"authorised"}, "authorised": {"dispatch_intent", "interrupted"},
    "dispatch_intent": {"mock_process_started", "terminal_failure", "interrupted"},
    "mock_process_started": {"accepted", "terminal_failure", "interrupted"},
    "accepted": {"partial_response", "complete_response", "terminal_failure", "interrupted"},
    "partial_response": {"partial_response", "complete_response", "terminal_failure", "interrupted"},
    "complete_response": set(), "terminal_failure": set(), "interrupted": set(),
}
REJECTIONS = {"invalid_message", "grant_mismatch", "reservation_required", "sealed_request_mismatch",
              "duplicate_dispatch", "invalid_campaign_evidence", "message_limit"}


def death_guard():
    # Called by trusted broker/service before processing input. Parent loss does
    # not leave an orphan with custody access. Saved PIDs are never kill targets.
    parent = os.getppid()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid() != parent or parent == 1:
        raise RuntimeError("broker_parent_lost_or_pdeathsig_unavailable")


def records(db, ident):
    # Filter in SQLite; never repeatedly decode unrelated raw-response frames
    # in the Python supervisor. The complete verifier still audits every event.
    return [decode(r[0])["data"] for r in db.execute(
        "SELECT body FROM events WHERE json_extract(body,'$.position')=? "
        "AND json_extract(body,'$.kind')='broker_event' ORDER BY seq", (ident,))]


def binding(env):
    return {"contract": env["broker_contract"], "attempt_id": env["attempt_id"], "campaign_id": env["campaign_id"],
            "manifest_sha256": env["manifest_sha256"], "position": env["position"],
            "request_sha256": env["request_sha256"], "envelope_sha256": digest(env),
            "packet_bindings": env["packet_bindings"], "role": env["role"],
            "requested_identity": env["requested_identity"], "destination": env["destination"],
            "idempotency_token": env["idempotency_token"], "deadline_seconds": env["deadline_seconds"],
            "response_byte_limit": env["response_byte_limit"]}


def append(db, ident, rec):
    with engine.transaction(db):
        engine.event(db, "broker_event", ident, rec)


def rejected(db, ident, incoming, reason):
    if reason not in REJECTIONS:
        raise ValueError("unknown_rejection")
    with engine.transaction(db):
        engine.event(db, "broker_rejected", ident, {"reason": reason, "message_sha256": digest(incoming)})
    return {"type": "reply", "authorised": False, "reason": reason, "raw_b64": ""}


def authorise(db, root, ident, manifest_hash, incoming):
    """A pipe is routing, never authorisation. Reconstruct committed evidence.

    BEGIN IMMEDIATE serialises independent competing broker processes too. The
    journal's intent consumes the existing reservation; no new attempt registry.
    """
    with engine.transaction(db):
        try:
            report = engine.verify_database(db, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("invalid_campaign_evidence") from exc
        m = report["manifest"]
        if not is_broker(m) or m["manifest_sha256"] != manifest_hash:
            raise ValueError("grant_mismatch")
        p = next((p for p in m["positions"] if p["id"] == ident), None)
        row = db.execute("SELECT request FROM attempts WHERE id=?", (ident,)).fetchone()
        state = db.execute("SELECT state FROM positions WHERE id=?", (ident,)).fetchone()
        t = db.execute("SELECT envelope,record FROM transports WHERE id=?", (ident,)).fetchone()
        if p is None or row is None or t is None:
            raise ValueError("reservation_required")
        env = envelope_for(m, p, row[0])
        if (incoming != message(env, row[0]) or encode(incoming) != encode(message(env, row[0]))
                or t[0] != encode(env)):
            raise ValueError("sealed_request_mismatch")
        if records(db, ident):
            raise ValueError("duplicate_dispatch")
        if state[0] != "started" or not t[1]:
            raise ValueError("reservation_required")
        rec = {**binding(env), "stage": "authorised", "raw_b64": "", "observed_identity": None,
               "uncertain_completion": False, "reason": None, "frame_integrity": True}
        from ..systemone_https_v1.contract import is_https, require_fixture
        if is_https(m):
            require_fixture(m)
            rec["https"] = None
        engine.event(db, "broker_event", ident, rec)
    return m, env, rec


def dispatch(db, ident, incoming, m, env, rec, *, credential_fd=None, credential_protection=None):
    from ..systemone_https_v1.contract import is_https
    if is_https(m):
        from ..systemone_https_v1.https import dispatch as https_dispatch
        return https_dispatch(db, ident, incoming, m, env, rec,
                              credential_fd=credential_fd, credential_protection=credential_protection)
    scenario = env["scenario"]
    if scenario == "before_dispatch":
        os._exit(71)  # reservation consumed; no intent and no mock process.
    rec = dict(rec, stage="dispatch_intent", uncertain_completion=True)
    append(db, ident, rec)  # full synchronous commit BEFORE provider Popen.
    if scenario == "after_intent":
        os._exit(73)  # deliberately ambiguous: lack of ACK proves nothing.
    key = os.urandom(32)
    spec = m["transport"]["specification"]
    service = HERE / "provider.py"
    if raw_hash(service.read_bytes()) != spec["broker_bindings"]["provider.py"]:
        raise ValueError("pinned_mock_changed")
    proc = None
    selector = selectors.DefaultSelector()
    buf, seq, accepted = bytearray(), 0, False
    deadline = time.monotonic() + env["deadline_seconds"]
    raw = bytearray()
    reason = None
    try:
        proc = subprocess.Popen([spec["bindings"]["python"]["path"], "-I", "-S", "-B", str(service)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                close_fds=True, env={"LANG": "C.UTF-8"})
        rec = dict(rec, stage="mock_process_started")
        append(db, ident, rec)
        payload = {"request_b64": incoming["request_b64"], "envelope": env, "key": key.hex()}
        proc.stdin.write(encode(payload) + b"\n"); proc.stdin.close()
        os.set_blocking(proc.stdout.fileno(), False)
        selector.register(proc.stdout, selectors.EVENT_READ)
        done = False
        while not done:
            if time.monotonic() >= deadline:
                reason = "deadline_exceeded"; break
            for selected, _ in selector.select(0.01):
                chunk = os.read(selected.fileobj.fileno(), 65536)
                if not chunk:
                    reason = "connection_loss"; done = True; break
                buf.extend(chunk)
                if len(buf) > spec["max_ipc_bytes"]:
                    reason = "provider_frame_limit"; done = True; break
                while b"\n" in buf:
                    line, _, rest = buf.partition(b"\n"); buf = bytearray(rest)
                    frame = decode(line)
                    signature = frame.pop("mac")
                    # Simulated corruption at the local communication boundary.
                    # Preserve received bytes even when the test MAC fails.
                    if scenario == "tamper" and frame["type"] == "data":
                        frame["raw_b64"] = b64(unb64(frame["raw_b64"]) + b"TAMPER")
                    authenticated = hmac.compare_digest(signature, hmac.new(key, encode(frame), hashlib.sha256).hexdigest())
                    if frame.get("raw_b64"):
                        piece = unb64(frame["raw_b64"])
                        available = env["response_byte_limit"] - len(raw)
                        raw.extend(piece[:available])
                    if (not authenticated or frame["seq"] != seq or frame["attempt_id"] != env["attempt_id"]):
                        rec = dict(rec, raw_b64=b64(raw), frame_integrity=False)
                        reason = "mock_frame_integrity_failure"; done = True; break
                    seq += 1
                    if frame["type"] == "accepted" and not accepted:
                        accepted = True
                        rec = dict(rec, stage="accepted")
                        append(db, ident, rec)
                        if scenario == "after_acceptance":
                            os._exit(72)
                    elif frame["type"] == "data" and accepted:
                        rec = dict(rec, stage="partial_response", raw_b64=b64(raw))
                        append(db, ident, rec)
                        if len(piece) > available:
                            reason = "response_byte_limit"; done = True; break
                    elif frame["type"] == "complete" and accepted:
                        rec = dict(rec, stage="complete_response", raw_b64=b64(raw),
                                   observed_identity=frame["observed_identity"], uncertain_completion=False)
                        append(db, ident, rec)
                        done = True; break
                    else:
                        reason = "mock_protocol_error"; done = True; break
        if reason:
            rec = dict(rec, stage="terminal_failure", raw_b64=b64(raw), reason=reason,
                       uncertain_completion=True)
            append(db, ident, rec)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        rec = dict(rec, stage="terminal_failure", raw_b64=b64(raw), reason="provider_protocol_or_launch_failure",
                   uncertain_completion=True)
        append(db, ident, rec)
    finally:
        selector.close()
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=2)
            proc.stdout.close()
    return {"type": "reply", "authorised": True, "record": rec, "raw_b64": rec["raw_b64"]}


def reconcile(db, root, m, p):
    history = records(db, p["id"])
    transitions = TRANSITIONS
    from ..systemone_https_v1.contract import is_https
    if is_https(m):
        from ..systemone_https_v1.audit import TRANSITIONS as transitions
    if history and transitions[history[-1]["stage"]]:
        last = history[-1]
        append(db, p["id"], dict(last, stage="interrupted", uncertain_completion=(last["stage"] != "authorised"),
                                  reason="recovery_no_retransmission"))


def receipt_binding(db, ident, *, history=None):
    history = records(db, ident) if history is None else history
    last = history[-1] if history else None
    result = {"broker_record_sha256": digest(last) if last else None,
              "broker_raw_sha256": raw_hash(unb64(last["raw_b64"])) if last else None}
    if last and "https" in last:
        result["https"] = last["https"]
    return result


def audit(db, m):
    """Read-only broker replay inside the existing hash-chain verifier."""
    from ..systemone_https_v1.contract import is_https
    if is_https(m):
        from ..systemone_https_v1.audit import audit as https_audit
        return https_audit(db, m)
    positions = {p["id"]: p for p in m["positions"]}
    histories, rejected_count = {}, 0
    for row in db.execute("SELECT body FROM events ORDER BY seq"):
        e = decode(row[0]); ident, data = e["position"], e["data"]
        if e["kind"] == "broker_rejected":
            if (set(data) != {"reason", "message_sha256"} or data["reason"] not in REJECTIONS
                    or len(data["message_sha256"]) != 64):
                raise ValueError("broker_rejection_evidence_changed")
            rejected_count += 1
        elif e["kind"] == "broker_event":
            req = db.execute("SELECT request FROM attempts WHERE id=?", (ident,)).fetchone()[0]
            env = envelope_for(m, positions[ident], req)
            expected = binding(env)
            if (set(data) != set(expected) | {"stage", "raw_b64", "observed_identity", "uncertain_completion", "reason", "frame_integrity"}
                    or any(data[k] != v for k, v in expected.items())):
                raise ValueError("broker_authorisation_binding_changed")
            old = histories.get(ident, [])
            prev = old[-1] if old else None
            if data["stage"] not in TRANSITIONS[prev["stage"] if prev else None]:
                raise ValueError("broker_duplicate_or_nonmonotonic_dispatch")
            raw = unb64(data["raw_b64"])
            if (len(raw) > env["response_byte_limit"] or b64(raw) != data["raw_b64"]
                    or prev and not raw.startswith(unb64(prev["raw_b64"]))):
                raise ValueError("broker_raw_prefix_changed")
            if data["stage"] in ("authorised", "dispatch_intent", "mock_process_started", "accepted") and raw:
                raise ValueError("broker_response_before_acceptance")
            if data["stage"] == "complete_response" and (data["uncertain_completion"] or not data["frame_integrity"]):
                raise ValueError("broker_false_completion")
            if data["stage"] != "complete_response" and data["observed_identity"] is not None:
                raise ValueError("broker_identity_before_complete_response")
            histories.setdefault(ident, []).append(data)
    for ident, raw, observed in db.execute("SELECT id,raw,observed FROM responses"):
        last = histories.get(ident, [None])[-1]
        if last and (raw != unb64(last["raw_b64"]) or decode(observed) != last["observed_identity"]):
            raise ValueError("broker_response_custody_changed")
        if not last and raw != b"":
            raise ValueError("broker_response_without_dispatch")
    stages = lambda stage: sum(any(r["stage"] == stage for r in h) for h in histories.values())
    return {"broker_authorised_requests": stages("authorised"), "broker_rejected_requests": rejected_count,
            "broker_dispatch_intents": stages("dispatch_intent"), "mock_provider_process_starts": stages("mock_process_started"),
            "mock_provider_acceptances": stages("accepted"),
            "broker_complete_responses": stages("complete_response"),
            "broker_partial_responses": stages("partial_response"),
            "broker_terminal_failures": stages("terminal_failure"),
            "broker_uncertain_completions": sum(h[-1]["uncertain_completion"] for h in histories.values()),
            "broker_reserved_not_dispatched": sum(not any(r["stage"] == "dispatch_intent" for r in histories.get(ident, []))
                                                   for (ident,) in db.execute("SELECT id FROM attempts")),
            "remote_exactly_once_claimed": False}


def main():
    death_guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--position", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--credential-control-fd", type=int)
    args = parser.parse_args()
    protection, credential_fd = None, None
    if args.credential_control_fd is not None:
        from ..systemone_https_v1.credential import broker_ready
        try:
            credential_fd, protection = broker_ready(args.credential_control_fd)
        except BaseException:
            # No traceback, exception string, FD data or key on startup failure.
            os._exit(76)
    db = engine.connect(args.campaign)
    try:
        count = 0
        while True:
            line = sys.stdin.buffer.readline(1048577)
            if not line:
                break
            count += 1
            try:
                incoming = decode(line)
            except (ValueError, UnicodeError):
                incoming = {"invalid_sha256": raw_hash(line)}
            try:
                if len(line) > 1048576 or count > 4:
                    raise ValueError("message_limit")
                m, env, rec = authorise(db, args.campaign, args.position, args.manifest, incoming)
            except ValueError as exc:
                reason = str(exc) if str(exc) in REJECTIONS else "invalid_message"
                reply = rejected(db, args.position, incoming, reason)
            else:
                if ("credential_binding" in env) != (credential_fd is not None):
                    reply = rejected(db, args.position, incoming, "grant_mismatch")
                else:
                    reply = dispatch(db, args.position, incoming, m, env, rec,
                                     credential_fd=credential_fd, credential_protection=protection)
                    if "credential_binding" in env:
                        credential_fd = None  # one dispatch consumes the channel.
            sys.stdout.buffer.write(encode(reply) + b"\n"); sys.stdout.buffer.flush()
    finally:
        if credential_fd is not None:
            try:
                os.close(credential_fd)
            except OSError:
                pass
        db.close()


if __name__ == "__main__":
    main()
