"""Focused dummy-JEVKEY qualification of the EXISTING executor/HTTPS broker.

Run inside a fresh private user/network namespace. A veth links two private
namespaces using TEST-NET addresses; no host interface, route or firewall is
changed. Every executor child gets a constructed dummy-only environment.
"""
import base64
import ctypes
import errno
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import time

from . import DESTINATION
from .contract import make_manifest, POSITION, native_request
from .credential import write_all
from .egress import install_fixture_policy
from .fixture import entity
from .qualification import certificate, wait_port
from .. import engine
from ..broker_v1.broker import records
from ..model import decode, encode, digest, raw_hash
from ..transport_qualification import snapshot

MODULE = "engineering_qualification_v1.q1_executor.systemone_https_v1"
CLIENT = "192.0.2.1"
PEER = "192.0.2.2"
REPO = Path(__file__).resolve().parents[3]


def command(argv):
    subprocess.run(argv, check=True, capture_output=True, env={"LANG": "C.UTF-8"})


def setup_peer():
    if socket.if_nameindex() != [(1, "lo")]:
        raise ValueError("fresh_private_network_namespace_required")
    peer = subprocess.Popen(["/usr/bin/unshare", "--net", sys.executable, "-I", "-S", "-B", "-c",
        "import sys; print('READY',flush=True); sys.stdin.buffer.read()"], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env={"LANG": "C.UTF-8"})
    if peer.stdout.readline() != b"READY\n":
        raise ValueError("private_peer_namespace_unavailable")
    try:
        command(["/usr/sbin/ip", "link", "add", "q1-client", "type", "veth", "peer", "name", "q1-server"])
        command(["/usr/sbin/ip", "link", "set", "q1-server", "netns", str(peer.pid)])
        command(["/usr/sbin/ip", "addr", "add", CLIENT + "/30", "dev", "q1-client"])
        command(["/usr/sbin/ip", "link", "set", "q1-client", "up"])
        prefix = ["/usr/bin/nsenter", "--net=/proc/" + str(peer.pid) + "/ns/net", "--"]
        command(prefix + ["/usr/sbin/ip", "addr", "add", PEER + "/30", "dev", "q1-server"])
        command(prefix + ["/usr/sbin/ip", "link", "set", "q1-server", "up"])
        command(prefix + ["/usr/sbin/ip", "link", "set", "lo", "up"])
        return peer, prefix
    except BaseException:
        peer.terminate(); peer.wait(); raise


def observer_checks(pids):
    # Capless unrelated process: opening proc files is attempted, contents are
    # NEVER read. Do not use the namespace administrator's ptrace capability.
    script = '''import ctypes,errno,json,os,sys
class Header(ctypes.Structure):
 _fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
class Cap(ctypes.Structure):
 _fields_=[('e',ctypes.c_uint32),('p',ctypes.c_uint32),('i',ctypes.c_uint32)]
c=ctypes.CDLL(None,use_errno=True)
for number in range(41):c.prctl(24,number,0,0,0)
assert c.capset(ctypes.byref(Header(0x20080522,0)),ctypes.byref((Cap*2)()))==0
c.prctl(38,1,0,0,0)
result={}
for role,pid in json.loads(sys.stdin.read()).items():
 result[role]={}
 for leaf in ('environ','mem','fd/0'):
  try:
   fd=os.open('/proc/'+str(pid)+'/'+leaf,os.O_RDONLY);os.close(fd);value='UNEXPECTED_OPEN'
  except OSError as e:value=e.errno
  assert value in (errno.EACCES,errno.EPERM),(role,leaf,value)
  result[role][leaf]=value
print(json.dumps(result))
'''
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script], input=encode(pids),
                            capture_output=True, env={"LANG": "C.UTF-8"})
    assert result.returncode == 0, result.stderr.decode()
    return decode(result.stdout)


def assert_no_dummy_in_custody(root, dummy):
    needle = dummy.encode()
    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                inspect(item)
                if key.endswith("_b64") and isinstance(item, str):
                    assert needle not in base64.b64decode(item), "credential_in_encoded_custody"
        elif isinstance(value, list):
            for item in value: inspect(item)
        elif isinstance(value, str):
            assert dummy not in value, "credential_in_JSON_string"
    for path in root.rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            assert needle not in raw and base64.b64encode(needle) not in raw, path
            if path.suffix == ".json": inspect(decode(raw))
    campaign = root / "campaign"
    with engine.connect(campaign, readonly=True) as db:
        for table in ("events", "receipts", "transports", "attempts", "responses"):
            for row in db.execute("SELECT * FROM " + table):
                for cell in row:
                    if isinstance(cell, bytes):
                        assert needle not in cell
                        try: inspect(decode(cell))
                        except (ValueError, UnicodeError): pass


def run_case(root, name, prefix, cert, key):
    case = root / name; case.mkdir()
    dummy = "Q1-DUMMY-JEVKEY-" + secrets.token_hex(24)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    write_all(write_fd, struct.pack("!I", len(dummy)) + dummy.encode()); os.close(write_fd)
    tls_scenario = name if name in {"credential_probe", "credential_echo", "credential_echo_escaped", "jev_interrupt", "identity_unknown", "identity_mismatch", "after_partial"} else "valid"
    server_log = (case / "server.stderr").open("wb")
    server = subprocess.Popen(prefix + [sys.executable, "-B", "-m", MODULE + ".fixture", "--root", str(case),
        "--scenario", tls_scenario, "--cert", str(cert), "--key", str(key), "--address", PEER,
        "--expected-credential-fd", str(read_fd)], pass_fds=(read_fd,), close_fds=True,
        stdout=subprocess.DEVNULL, stderr=server_log, cwd=REPO, env={"LANG": "C.UTF-8"})
    os.close(read_fd)
    child = None
    try:
        port = wait_port(case, server)
        install_fixture_policy(port, PEER)
        route = {"address": PEER, "port": port, "ca_pem": cert.read_text(),
                 "ca_sha256": raw_hash(cert.read_bytes()), "network_namespace": os.readlink("/proc/self/ns/net"),
                 "interfaces": ["lo", "q1-client"]}
        scenario = "valid" if name == "missing" else name
        frozen = make_manifest(case / "fixture", route=route, scenario=scenario, jevkey=True)
        campaign = engine.create(case / "campaign", frozen)
        args = [sys.executable, "-B", "-m", "engineering_qualification_v1.q1_executor", "resume",
                "--offline-subprocess", "--campaign", str(campaign)]
        # Construct from scratch. Never copy/get/pop the real operator JEVKEY.
        env = {"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin", "JEVKEY": dummy,
               "UNRELATED_LOGIN_CANARY": "UNRELATED-DUMMY-NOT-FOR-BROKER", "HTTPS_PROXY": "http://127.0.0.1:1"}
        if name == "missing": del env["JEVKEY"]
        if name == "credential_bad": env["JEVKEY"] = dummy + "\r\nINVALID"
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO, env=env)
        access = None
        if name == "credential_probe":
            deadline = time.monotonic() + 8
            while not (case / "requests.jsonl").exists():
                if child.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError("credential_probe_request_not_delivered")
                time.sleep(0.005)
            with engine.connect(campaign, readonly=True) as db:
                record = decode(db.execute("SELECT record FROM transports").fetchone()[0])
            access = observer_checks({"launcher": child.pid, "broker": record["credential_handoff"]["broker_pid"]})
            (case / "release").write_bytes(b"ok")
        stdout, stderr = child.communicate(timeout=15)
        (case / "executor.stdout").write_bytes(stdout); (case / "executor.stderr").write_bytes(stderr)
        assert child.returncode == (75 if name == "jev_interrupt" else 0), (name, child.returncode, stderr)
        if name == "jev_interrupt":
            # No JEVKEY in recovery process: no read, launch or retransmission.
            command(args)
        report = engine.verify(campaign)
        before = snapshot(campaign)
        command(args); command(args)
        assert before == snapshot(campaign)
        requests = [decode(line) for line in (case / "requests.jsonl").read_bytes().splitlines()] if (case / "requests.jsonl").exists() else []
        no_post = name in {"missing", "credential_bad", "destination", "policy_digest", "alter_request", "network", "spawn", "exec", "source_write", "forbidden_file", "after_intent"}
        assert len(requests) == (0 if no_post else 1), (name, len(requests), report["summary"])
        assert all(r["fixture_auth_correct"] and r["host"] == DESTINATION["host"]
                   and r["path"] == DESTINATION["path"] and r["body_sha256"] == raw_hash(native_request()) for r in requests)
        with engine.connect(campaign, readonly=True) as db:
            record = decode(db.execute("SELECT record FROM transports").fetchone()[0])
            hist = records(db, POSITION)
            response = db.execute("SELECT raw FROM responses").fetchone()
            # An interrupted attempt is not promoted to a completed response;
            # its original prefix lives in broker/transport journal custody.
            raw = response[0] if response else base64.b64decode(record["stdout_b64"])
        probes = []
        for line in base64.b64decode(record["stderr_b64"]).splitlines():
            try:
                frame = decode(line)
                if frame.get("type") == "probe": probes.append(frame["observation"])
            except (ValueError, UnicodeError, AttributeError): pass
        boundary = [p for p in probes if "credential_boundary" in p]
        assert boundary and all(p["JEVKEY_environment_absent"] and p["unexpected_inherited_descriptors"] == 0 for p in boundary)
        receipt = report["receipts"][POSITION]
        successful = name in {"credential_probe", "credential_child"}
        assert (receipt["state"] == "completed") == successful, (name, receipt)
        if successful:
            assert raw == entity("valid")
            assert len(receipt["diagnostics"]["parsed"]["direct_systemone"]["observations"]) == 3
        if name == "credential_probe":
            script = ("import json; from " + MODULE + ".egress import adversarial_probes; "
                      "print(json.dumps(adversarial_probes(json.loads(input()))))")
            probes_result = subprocess.run([sys.executable, "-B", "-c", script], input=encode(route),
                                           capture_output=True, check=True, cwd=REPO, env={"LANG": "C.UTF-8"})
            (case / "kernel-egress-denials.json").write_bytes(probes_result.stdout)
            counters = subprocess.check_output(["/usr/sbin/nft", "-j", "list", "ruleset"], env={"LANG": "C.UTF-8"})
            (case / "kernel-firewall-counters.json").write_bytes(counters)
            drops = [e["counter"]["packets"] for item in decode(counters)["nftables"] if "rule" in item
                     for e in item["rule"]["expr"] if "counter" in e]
            assert drops and drops[-1] >= 3
        if name == "jev_interrupt": assert receipt["state"] == "interrupted" and raw
        if name in {"credential_echo", "credential_echo_escaped"}:
            assert hist[-1]["reason"] == "credential_reflection_capture_refused"
        if name in {"network", "spawn", "exec", "source_write", "forbidden_file"}:
            assert any(p.get("attack") == name and p["prevented"] for p in probes)
        assert_no_dummy_in_custody(case, dummy)
        result = {"scenario": name, "state": receipt["state"], "server_POSTs": len(requests),
            "reservations": report["summary"]["attempt_reservations"], "raw_bytes": len(raw),
            "handoff": record["credential_handoff"], "worker_probes": probes,
            "unrelated_process_access_denials": access, "dummy_absent_from_custody_logs_exceptions": True,
            "restart_without_JEVKEY_no_retransmission_or_file_changes": True,
            "last_broker_stage": hist[-1]["stage"] if hist else None,
            "uncertain_completion": hist[-1]["uncertain_completion"] if hist else None,
            "summary": report["summary"], "receipt_sha256": digest(receipt)}
        (case / "result.json").write_bytes(encode(result))
        return result
    finally:
        if child is not None and child.poll() is None: child.kill(); child.wait()
        server.terminate(); server.wait(timeout=3); server_log.close()


def negative_projections(root):
    original = root / "credential_probe/campaign"
    results = {}
    for name in ("request", "policy", "receipt"):
        clone = root / ("tampered-" + name); shutil.copytree(original, clone)
        with engine.connect(clone) as db:
            if name == "receipt": db.execute("UPDATE receipts SET body=?", (b"{}",))
            else:
                request = decode(db.execute("SELECT request FROM attempts").fetchone()[0])
                if name == "request": request["source_text"] += "tampered"
                else: request["https_qualification"]["policy_sha256"] = "0" * 64
                db.execute("UPDATE attempts SET request=?", (encode(request),))
        try: engine.verify(clone)
        except (ValueError, KeyError, TypeError): results[name] = "REJECTED"
        else: raise AssertionError("tampering_accepted:" + name)
    return results


def run(root):
    root.mkdir()
    certdir = root / "temporary-certificates"; certdir.mkdir()
    cert, key = certificate(certdir, "fixture", DESTINATION["host"])
    peer = None
    try:
        peer, prefix = setup_peer()
        cases = ("credential_probe", "credential_child", "missing", "credential_bad", "credential_echo", "credential_echo_escaped",
                 "identity_unknown", "identity_mismatch", "after_intent", "after_partial", "jev_interrupt", "destination",
                 "policy_digest", "alter_request", "network", "spawn", "exec", "source_write", "forbidden_file")
        results = {name: run_case(root, name, prefix, cert, key) for name in cases}
        result = {"status": "JEV HISTORICAL ACCESS REUSED — Q1 BROKER INTEGRATION QUALIFIED OFFLINE, LIVE PROBE PENDING APPROVAL",
            "cases": len(results), "provider_calls": 0, "real_JEVKEY_value_accessed": False,
            "operator_environment_copied": False, "worker_bootstrap_seccomp_and_mount_policy_unchanged": True,
            "network": "private-veth-two-netns-TEST-NET-only-exact-IP-port-nftables-default-drop",
            "host_routes_firewall_and_security_unchanged": True, "tampering": negative_projections(root),
            "results": {name: {k: r[k] for k in ("state", "server_POSTs", "reservations", "raw_bytes", "uncertain_completion")} for name, r in results.items()}}
        (root / "acceptance.json").write_bytes(encode(result))
        return result
    finally:
        if peer is not None:
            peer.terminate(); peer.wait(timeout=3)
        shutil.rmtree(certdir)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(encode(run(args.output.absolute())).decode())
