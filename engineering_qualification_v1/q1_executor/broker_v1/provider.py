"""Deterministic stdio mock service. No networking or production credentials.

MACs exercise local byte-integrity handling only, not real model attestation.
This standalone process never imports the repository or validators.
"""
import base64
import copy
import ctypes
import hashlib
import hmac
import json
import os
import signal
import sys
import time


def encode(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def response(req):
    if req.get("instrument_contract") == "systemone-typed-challenge-v1":
        # Bytes injected by the sealed offline replay packet, not a provider call.
        replay = req["offline_replay"]
        raw = base64.b64decode(replay["raw_b64"], validate=True)
        if hashlib.sha256(raw).hexdigest() != replay["raw_sha256"]:
            raise ValueError("sealed_replay_bytes_changed")
        return raw
    p = req["position"]
    if p["kind"] == "specialist":
        obj = {"schema": req["instrument_request"]["schema"].replace("judge-request", "judgments"),
               "request_sha256": req["instrument_request"]["request_sha256"], "claims": []}
        for c in req["previous_assessment"]["claims"]:
            obj["claims"].append({"claim_id": c["claim_id"], **{
                d: {"label": label, "score": score, "rationale": "Synthetic local broker mock only.", "evidence_quotes": []}
                for d, label, score in (("source_entailment", "supported", 1),
                                        ("independent_verification", "not_independently_verified", None),
                                        ("impact_inference", "not_applicable", None))}})
        return encode(obj)
    previous = req["previous_assessment"]
    claims = copy.deepcopy(previous["claims"]) if previous else [{
        "claim_id": "c1", "claim": "The synthetic change updates documentation.",
        "evidence_quotes": [req["source_text"].strip()], "confidence": 0.5,
        "limitations": ["Synthetic supplied text; no authenticated implementation."]}]
    return encode({"case_id": p["case_id"], "variant_id": p["variant_id"], "claims": claims,
                   "disposition": p["fake_disposition"], "uncertainties": [],
                   "changes": [] if previous is None else [
                       {"claim_id": c["claim_id"], "action": "retained", "reason": "Identical scripted claim object."}
                       for c in claims]})


def main():
    parent = os.getppid()
    if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) or parent == 1 or os.getppid() != parent:
        raise RuntimeError("mock_parent_lost")
    payload = json.loads(sys.stdin.buffer.readline(1048577))
    env, key = payload["envelope"], bytes.fromhex(payload["key"])
    seq = 0

    def send(kind, **data):
        nonlocal seq
        frame = {"type": kind, "seq": seq, "attempt_id": env["attempt_id"], **data}
        frame["mac"] = hmac.new(key, encode(frame), hashlib.sha256).hexdigest()
        seq += 1
        sys.stdout.buffer.write(encode(frame) + b"\n"); sys.stdout.buffer.flush()

    send("accepted")
    behavior = env["scenario"]
    if behavior == "connection_loss":
        os._exit(24)
    if behavior in ("timeout", "executor_interrupt", "after_acceptance"):
        if behavior != "after_acceptance":
            send("data", raw_b64=base64.b64encode(b"partial-before-timeout").decode())
        time.sleep(30)
        return
    if behavior == "partial_failure":
        send("data", raw_b64=base64.b64encode(b'{"partial":').decode())
        os._exit(23)
    req = json.loads(base64.b64decode(payload["request_b64"], validate=True))
    raw = b"\xff{bad-json" if behavior == "malformed" else response(req)
    if behavior == "response_limit":
        raw = b"X" * (env["response_byte_limit"] + 1)
    send("data", raw_b64=base64.b64encode(raw).decode())
    observed = dict(env["requested_identity"])
    if behavior == "identity_unknown":
        observed = None
    if behavior == "identity_mismatch":
        observed["model"] = "synthetic-unknown-untrusted-model"
    send("complete", observed_identity=observed)


if __name__ == "__main__":
    main()
