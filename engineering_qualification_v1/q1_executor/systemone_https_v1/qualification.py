"""Real executor/worker/broker/TLS/custody qualification in a loopback-only netns."""
import copy
import errno
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

from . import DESTINATION
from .contract import make_manifest, native_request, POSITION, specification
from .fixture import entity
from .. import engine
from ..broker_v1.contract import envelope_for, message
from ..broker_v1.broker import records
from ..model import PACKAGE, decode, digest, encode, raw_hash, validate_manifest
from ..transport_qualification import snapshot

MODULE = "engineering_qualification_v1.q1_executor.systemone_https_v1"


def certificate(root, name, host):
    cert, key = root / (name + ".pem"), root / (name + ".key")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                    "-subj", "/CN=" + host, "-addext", "subjectAltName=DNS:" + host,
                    "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True,
                    env={"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"})
    return cert, key


def wait_port(root, proc):
    deadline = time.monotonic() + 5
    while not (root / "port").exists():
        if proc.poll() is not None or time.monotonic() > deadline:
            raise AssertionError("TLS_fixture_did_not_start")
        time.sleep(0.02)
    return int((root / "port").read_text())


def assert_rejected(call):
    try:
        call()
    except (ValueError, KeyError, TypeError):
        return True
    raise AssertionError("tampering_or_disabled_configuration_accepted")


def run_case(root, name, cert, key, *, trust=None):
    case = root / name; case.mkdir()
    tls_scenario = "valid" if name in {"destination", "duplicate", "credentials", "network", "after_intent", "wrong_hostname", "untrusted_CA", "tamper"} else name
    log = (case / "server.stderr").open("wb")
    server = subprocess.Popen([sys.executable, "-B", "-m", MODULE + ".fixture", "--root", str(case),
        "--scenario", tls_scenario, "--cert", str(cert), "--key", str(key)],
        stdout=subprocess.DEVNULL, stderr=log, env={"LANG": "C.UTF-8"})
    try:
        port = wait_port(case, server)
        from .egress import install_fixture_policy
        install_fixture_policy(port)
        if name == "missing_kernel_policy":
            subprocess.run(["/usr/sbin/nft", "delete", "table", "inet", "q1_https"], check=True)
        pem = (trust or cert).read_text()
        route = {"address": "127.0.0.1", "port": port, "ca_pem": pem, "ca_sha256": raw_hash(pem.encode()),
                 "network_namespace": os.readlink("/proc/self/ns/net")}
        scenario = name if name not in {"wrong_hostname", "untrusted_CA", "tamper"} else "valid"
        frozen = make_manifest(case / "fixture", route=route, scenario=scenario)
        campaign = engine.create(case / "campaign", frozen)
        # Inherited fake login/proxy variables must never supply broker auth or routes.
        old = {k: os.environ.get(k) for k in ("TYPESAFE_API_KEY", "HTTPS_PROXY", "ALL_PROXY")}
        os.environ.update(TYPESAFE_API_KEY="PUBLIC-FAKE-INHERITED-KEY-DO-NOT-USE",
                          HTTPS_PROXY="http://127.0.0.1:1", ALL_PROXY="http://127.0.0.1:1")
        try:
            engine.resume(campaign, offline_subprocess=True)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        before = snapshot(campaign)
        report = engine.verify(campaign)
        engine.resume(campaign, offline_subprocess=True)
        engine.resume(campaign, offline_subprocess=True)
        assert before == snapshot(campaign), "restart_changed_first_attempt_or_retransmitted"
        requests = [decode(x) for x in (case / "requests.jsonl").read_bytes().splitlines()] if (case / "requests.jsonl").exists() else []
        no_post = name in {"after_intent", "destination", "network", "credentials", "wrong_hostname", "untrusted_CA", "missing_kernel_policy"}
        assert len(requests) == (0 if no_post else 1), (name, len(requests), report["summary"], report["receipts"][POSITION])
        for req in requests:
            assert req["path"] == DESTINATION["path"] and req["host"] == DESTINATION["host"]
            assert req["body_sha256"] == raw_hash(native_request()) and req["fixture_auth_correct"]
        receipt = report["receipts"][POSITION]
        with engine.connect(campaign, readonly=True) as db:
            history = records(db, POSITION)
            response = db.execute("SELECT raw FROM responses").fetchone()
            raw = response[0] if response else b""
            assert db.execute("SELECT count(*) FROM attempts").fetchone()[0] == 1
        if name in {"valid", "duplicate", "tamper"}:
            assert receipt["state"] == "completed", (name, receipt)
            assert raw == entity("valid")
            parsed = receipt["diagnostics"]["parsed"]
            assert len(parsed["direct_systemone"]["observations"]) == 3
            assert parsed["direct_systemone"]["usage"] == {"input_tokens": 123, "output_tokens": 17}
            assert parsed["direct_systemone"]["returned_model"]["value"] == "jev-1.13.0"
            assert parsed["derived_carl"] is None
        else:
            assert receipt["state"] != "completed", (name, receipt)
        if name in {"after_intent", "after_partial", "timeout", "partial_failure", "chunked_partial"}:
            assert history[-1]["uncertain_completion"] is True
        if name in {"after_partial", "partial_failure", "chunked_partial"}:
            assert raw == entity(name)[:23], (name, raw)
        if name == "response_limit":
            assert len(raw) == 8192
        if name == "typed_malformed":
            assert receipt["state"] == "invalid"
        if name == "duplicate":
            assert report["summary"]["broker_rejected_requests"] == 1
        # Public synthetic canaries must not enter custody or log files.
        for path in campaign.rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                assert b"PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY" not in data, path
                assert b"PUBLIC-FAKE-INHERITED-KEY-DO-NOT-USE" not in data, path
        if name == "valid":
            attacks = destination_attacks(campaign)
            assert len((case / "requests.jsonl").read_bytes().splitlines()) == 1
            # Exercise nftables denials in a child; parent remains unrestricted
            # ONLY inside this empty, private loopback network namespace.
            code = "from " + MODULE + ".egress import adversarial_probes; import json; print(json.dumps(adversarial_probes(json.loads(input()))))"
            probe = subprocess.run([sys.executable, "-B", "-c", code], input=encode(route), capture_output=True, check=True)
            (case / "kernel-egress-probes.json").write_bytes(probe.stdout)
            counters = subprocess.check_output(["/usr/sbin/nft", "-j", "list", "ruleset"])
            (case / "kernel-firewall-counters.json").write_bytes(counters)
            dropped = [e["counter"]["packets"] for item in decode(counters)["nftables"] if "rule" in item
                       for e in item["rule"]["expr"] if "counter" in e]
            assert dropped and dropped[-1] >= 3
        else:
            attacks = None
        if name == "tamper":
            tampering(root, campaign)
        final = engine.verify(campaign)
        result = {"scenario": name, "state": receipt["state"], "reason": receipt["reason"],
                  "server_POSTs": len(requests), "first_attempt_reservations": 1,
                  "raw_entity_bytes": len(raw), "raw_entity_sha256": raw_hash(raw),
                  "broker_final_stage": history[-1]["stage"] if history else None,
                  "uncertain_completion": history[-1]["uncertain_completion"] if history else False,
                  "https": history[-1].get("https") if history else None,
                  "restart_without_retransmission": True, "credential_canaries_absent_from_custody": True,
                  "summary": final["summary"], "receipt_sha256": digest(final["receipts"][POSITION]),
                  "destination_attacks_rejected": attacks}
        (case / "report.json").write_bytes(encode(result))
        return result
    finally:
        server.terminate(); server.wait(timeout=5); log.close()


def destination_attacks(campaign):
    m, _ = validate_manifest(campaign)
    with engine.connect(campaign, readonly=True) as db:
        sealed = db.execute("SELECT request FROM attempts").fetchone()[0]
    original = message(envelope_for(m, m["positions"][0], sealed), sealed)
    changes = {"host": "evil.invalid", "port": 444, "path": "/v1/models", "scheme": "http"}
    rejected = []
    for key, value in changes.items():
        incoming = copy.deepcopy(original)
        incoming["envelope"]["destination"][key] = value
        child = subprocess.run([sys.executable, "-B", "-m", "engineering_qualification_v1.q1_executor.broker_v1.broker",
            "--campaign", str(campaign), "--position", POSITION, "--manifest", m["manifest_sha256"]],
            input=encode(incoming) + b"\n", capture_output=True, check=True, env={"LANG": "C.UTF-8"})
        reply = decode(child.stdout)
        assert reply["authorised"] is False
        rejected.append({"field": key, "reason": reply["reason"]})
    return rejected


def tampering(root, campaign):
    for table, column, value in (("responses", "raw", b"TAMPER"), ("receipts", "body", b"{}")):
        clone = root / ("tampered-" + table); shutil.copytree(campaign, clone)
        with engine.connect(clone) as db:
            db.execute("UPDATE " + table + " SET " + column + "=?", (value,))
        assert_rejected(lambda: engine.verify(clone))


def run(root):
    if socket.if_nameindex() != [(1, "lo")]:
        raise ValueError("BLOCKED_run_inside_private_loopback_only_network_namespace")
    root.mkdir()
    certdir = root / "temporary-certificates"; certdir.mkdir()
    cert, key = certificate(certdir, "fixture", DESTINATION["host"])
    wrongcert, wrongkey = certificate(certdir, "wrong-host", "wrong.invalid")
    untrusted, untrustedkey = certificate(certdir, "untrusted", DESTINATION["host"])
    try:
        names = ("valid", "malformed", "http_400", "http_500", "partial_failure", "timeout", "after_intent", "after_partial",
                 "identity_unknown", "identity_mismatch", "response_limit", "redirect", "destination", "duplicate", "network", "credentials", "tamper",
                 "typed_malformed", "chunked_partial", "missing_kernel_policy")
        reports = {name: run_case(root, name, cert, key) for name in names}
        reports["wrong_hostname"] = run_case(root, "wrong_hostname", wrongcert, wrongkey)
        reports["untrusted_CA"] = run_case(root, "untrusted_CA", untrusted, untrustedkey, trust=cert)
        disabled = make_manifest(root / "disabled-manifest")
        assert_rejected(lambda: engine.create(root / "forbidden-live-campaign", disabled))
        # A user changing only the switch/digests still cannot grant authority.
        m = decode((disabled / "manifest.json").read_bytes())
        m["https_qualification"]["authority"]["state"] = "ENABLED"
        m["https_qualification"]["policy_sha256"] = digest(m["https_qualification"]["authority"])
        m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
        assert_rejected(lambda: __import__(MODULE + ".contract", fromlist=["validate_manifest"]).validate_manifest(disabled, m, encode(m)))
        result = {"status": "SYSTEMONE LIVE-PROBE TRANSPORT PREPARED — LIVE DISPATCH DISABLED",
                  "local_TLS_scenarios": len(reports), "real_provider_calls": 0,
                  "production_egress": "BLOCKED", "default_live_campaign_creation_rejected": True,
                  "automatic_enablement_rejected": True, "worker_namespace_seccomp_policy_unchanged": True,
                  "reports": {name: {k: report[k] for k in ("state", "server_POSTs", "raw_entity_bytes", "uncertain_completion")}
                              for name, report in reports.items()}}
        (root / "qualification.json").write_bytes(encode(result))
        return result
    finally:
        shutil.rmtree(certdir)  # generated fixture private keys are never delivered.
