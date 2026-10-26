"""Untrusted isolated worker; communicates using ONLY preopened stdio pipes.

Run by the ORIGINAL q1-offline-subprocess-v1 namespace/seccomp bootstrap.
Malicious cases deliberately bypass Python socket wrappers and alter frames.
"""
import base64
import copy
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


def encode(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def output(obj):
    os.write(1, encode(obj) + b"\n")


behavior = sealed_envelope["scenario"]
attacks = {"network", "unix_socket", "spawn", "exec", "forbidden_file", "credentials", "history",
           "source_write", "policy_write"}
if behavior in attacks:
    try:
        if behavior in ("network", "unix_socket"):
            lib = ctypes.CDLL(None, use_errno=True)
            fd = lib.socket(socket.AF_INET if behavior == "network" else socket.AF_UNIX, socket.SOCK_STREAM, 0)
            if fd < 0:
                raise OSError(ctypes.get_errno(), "raw_socket")
            os.close(fd)
        elif behavior == "spawn":
            subprocess.run(["/usr/bin/true"], check=True)
        elif behavior == "exec":
            os.execv("/usr/bin/true", ["true"])
        elif behavior in ("source_write", "policy_write"):
            Path("/inputs/request.json").write_bytes(b"altered policy/source")
        elif behavior == "history":
            Path(sealed_envelope["custody_probe"]).read_bytes()
        else:
            # All paths below identify synthetic canaries; never actual secrets.
            Path(sealed_envelope["forbidden_probe"] + {"credentials": ".credentials", "history": ".history"}.get(behavior, "")).read_bytes()
        result = {"attack": behavior, "prevented": False}
    except OSError as exc:
        result = {"attack": behavior, "prevented": True, "errno": exc.errno}
    output({"type": "probe", "observation": result})
    raise SystemExit(0)

env = copy.deepcopy(sealed_envelope)
request = sealed_request
if behavior == "invent_campaign":
    env["campaign_id"] = "synthetic-q1-another-campaign"
if behavior in ("invent_attempt", "no_reservation", "other_response"):
    env["position"] = "unreserved-other-position"
    env["attempt_id"] = "0" * 64
if behavior == "alter_request":
    obj = json.loads(request); obj["source_text"] += "changed after reservation"; request = encode(obj)
if behavior in ("source_digest", "policy_digest"):
    env["packet_bindings"]["source" if behavior == "source_digest" else "governing_policy"] = "0" * 64
if behavior == "destination":
    env["destination"] = "forbidden-destination-no-endpoint"
if behavior == "model":
    env["requested_identity"]["model"] = "forbidden-substitution"
if behavior == "role":
    env["role"] = "specialist" if env["role"] == "generator" else "generator"
msg = {"type": "request", "envelope": env, "request_b64": base64.b64encode(request).decode()}
output(msg)
reply = json.loads(sys.stdin.buffer.readline(1048577))
if behavior == "duplicate":
    output(msg)
    duplicate = json.loads(sys.stdin.buffer.readline(1048577))
    if duplicate.get("authorised"):
        raise RuntimeError("duplicate_was_authorised")
raw = base64.b64decode(reply["raw_b64"], validate=True)
if behavior == "worker_tamper":
    raw += b"WORKER-TAMPER"
output({"type": "result", "raw_b64": base64.b64encode(raw).decode()})
