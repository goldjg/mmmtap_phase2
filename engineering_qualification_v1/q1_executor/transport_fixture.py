"""Untrusted local adapter fixture. Includes deliberately non-cooperative acts.

No provider imports or transport. Executed ONLY after namespace + seccomp setup.
Its identity claims and diagnostics are self-reports, never trusted attestations.
"""
import copy
import ctypes
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import time

req = json.loads(sealed_request)
p = req["position"]
behavior = sealed_envelope["scenario"]


def output(obj):
    os.write(1, json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


if behavior in ("forbidden_file", "source_write", "policy_write", "spawn", "exec", "network", "reuse"):
    try:
        if behavior == "forbidden_file":
            Path(sealed_envelope["forbidden_probe"]).read_bytes()
        elif behavior in ("source_write", "policy_write"):
            # The actual source and policies are inside this sealed request.
            Path("/inputs/request.json").write_bytes(b"altered authority")
        elif behavior == "spawn":
            subprocess.run(["/usr/bin/true"], check=True)
        elif behavior == "exec":
            os.execv("/usr/bin/true", ["true"])
        elif behavior == "network":
            # A raw libc call bypasses Python's socket APIs and any monkey patch.
            libc = ctypes.CDLL(None, use_errno=True)
            fd = libc.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            if fd < 0:
                raise OSError(ctypes.get_errno(), "raw_socket")
            os.close(fd)
        else:
            Path("/home/assessor/prior-session.json").read_bytes()
        output({"attack": behavior, "prevented": False})
    except OSError as exc:
        output({"attack": behavior, "prevented": True, "errno": exc.errno})
    raise SystemExit(0)
if behavior == "session_seed":
    Path("/home/assessor/prior-session.json").write_text("synthetic previous conversation")
    output({"seeded": True, "environment": dict(os.environ), "cwd": os.getcwd()})
    raise SystemExit(0)
if behavior in ("timeout", "running_interrupt"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.write(1, b"partial-before-hang")
    while True:
        time.sleep(0.02)
if behavior == "partial_failure":
    os.write(1, b'{"partial":')
    raise SystemExit(23)
if behavior == "crash":
    os._exit(24)
if behavior == "malformed":
    os.write(1, b"\xff{bad-json")
else:
    if p["kind"] == "specialist":
        obj = {"schema": req["instrument_request"]["schema"].replace("judge-request", "judgments"),
               "request_sha256": req["instrument_request"]["request_sha256"], "claims": []}
        for c in req["previous_assessment"]["claims"]:
            obj["claims"].append({"claim_id": c["claim_id"], **{
                d: {"label": label, "score": score, "rationale": "Synthetic local fixture only.", "evidence_quotes": []}
                for d, label, score in (("source_entailment", "supported", 1),
                                        ("independent_verification", "not_independently_verified", None),
                                        ("impact_inference", "not_applicable", None))}})
    else:
        previous = req["previous_assessment"]
        claims = copy.deepcopy(previous["claims"]) if previous else [{
            "claim_id": "c1", "claim": "The synthetic change updates documentation.",
            "evidence_quotes": [req["source_text"].strip()], "confidence": 0.5,
            "limitations": ["Synthetic supplied text; no authenticated implementation."]}]
        obj = {"case_id": p["case_id"], "variant_id": p["variant_id"], "claims": claims,
               "disposition": p["fake_disposition"], "uncertainties": [],
               "changes": [] if previous is None else [
                   {"claim_id": c["claim_id"], "action": "retained", "reason": "Identical scripted claim object."} for c in claims]}
    output(obj)
observed = dict(sealed_envelope["requested_identity"])
if behavior == "identity_mismatch":
    observed["model"] = "unknown-local-model"
if behavior == "identity_unknown":
    observed = None
os.write(2, b"\n" + json.dumps({"observed_identity": observed,
                              "provenance": "untrusted_local_fixture_self_report_not_provider_attestation"}).encode() + b"\n")
