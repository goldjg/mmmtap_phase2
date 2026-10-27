"""One 153-position run of the proposed packet/route configuration, offline."""
from collections import Counter
import base64
import fcntl
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from .contract import build, VERSION, validate_manifest
from .. import engine
from ..model import decode, digest, encode, raw_hash
from ..systemone_https_v1 import DESTINATION
from ..systemone_https_v1.qualification import certificate, wait_port, assert_rejected
from ..systemone_https_v1.jevkey_qualification import setup_peer, assert_no_dummy_in_custody, command
from ..systemone_https_v1.egress import install_fixture_policy, adversarial_probes
from ..transport_qualification import snapshot

MODULE = "engineering_qualification_v1.q1_executor"
FAULTS = {
    "c01-gemini-r1-c3-g1": "invalid_assessment",
    "c01-haiku-r1-e1-s1": "identity_unknown",
    "c01-sol-r1-e2-s1": "http_500",
    "c02-haiku-r1-e3-cn-s2": "identity_mismatch",
    "c02-sol-r1-e3-nc-g1": "jev_interrupt",
    "c01-gemini-r1-c1-g1": "source_write",
    "c01-haiku-r1-c1-g1": "network",
    "c02-gemini-r1-c1-g1": "spawn",
    "c02-haiku-r1-c1-g1": "exec",
    "c03-gemini-r1-c1-g1": "forbidden_file",
    "c01-sol-r1-e3-nc-g1": "empty_claims",
    "c02-gemini-r1-e3-cn-g1": "empty_claims",
    "c02-haiku-r1-e3-nc-g1": "bad_quote",
}


def run(root):
    if "JEVKEY" in os.environ:
        raise ValueError("offline_qualification_launcher_must_not_inherit_operator_JEVKEY")
    root.mkdir(mode=0o700)
    peer, prefix = setup_peer()
    command(["/usr/sbin/ip", "link", "set", "lo", "up"])
    cert, key = certificate(root, "local-peer", DESTINATION["host"])
    dummy = "PUBLIC-DUMMY-Q1-CAMPAIGN-" + secrets.token_hex(12)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    os.write(write_fd, dummy.encode()); os.close(write_fd)
    stderr = (root / "server.stderr").open("wb")
    server = subprocess.Popen(prefix + [sys.executable, "-B", "-m", MODULE + ".live_campaign_v1.fixture",
        "--root", str(root), "--cert", str(cert), "--key", str(key), "--expected-dummy-fd", str(read_fd)],
        pass_fds=(read_fd,), env={"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL, stderr=stderr)
    os.close(read_fd)
    try:
        port = wait_port(root, server)
        route = {"address": "192.0.2.2", "port": port, "ca_pem": cert.read_text(),
            "ca_sha256": raw_hash(cert.read_bytes()), "network_namespace": os.readlink("/proc/self/ns/net"),
            "interfaces": ["lo", "q1-client"]}
        install_fixture_policy(port, route["address"])
        script = "import json,sys;from engineering_qualification_v1.q1_executor.systemone_https_v1.egress import adversarial_probes;print(json.dumps(adversarial_probes(json.loads(sys.stdin.read()))))"
        probe = subprocess.run([sys.executable, "-B", "-c", script], input=encode(route), capture_output=True,
                               env={"LANG": "C.UTF-8"})
        (root / "kernel-probe.stderr").write_bytes(probe.stderr)
        if probe.returncode:
            raise ValueError("kernel_probe_failed:" + probe.stderr.decode()[-2000:])
        kernel = decode(probe.stdout)
        manifest = build(root / "packets", fixture_route=route, scenarios=FAULTS, quota=141)
        campaign = engine.create(root / "campaign", root / "packets")
        env = {"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
               "JEVKEY": dummy, "HTTPS_PROXY": "http://127.0.0.1:1"}
        argv = [sys.executable, "-B", "-m", MODULE, "resume", "--offline-subprocess", "--campaign", str(campaign)]
        # A real executor process dies after a committed response prefix. The
        # second process starts from the same durable first-attempt authority.
        first = subprocess.run(argv, env=env, capture_output=True)
        (root / "first.stderr").write_bytes(first.stderr)
        (root / "first.stdout").write_bytes(first.stdout)
        if first.returncode != 75:
            raise AssertionError("expected_interruption_75:" + first.stderr.decode()[-2000:])
        interrupted = engine.verify(campaign)["summary"]
        second = subprocess.run(argv, env=env, capture_output=True)
        (root / "recovery.stderr").write_bytes(second.stderr)
        (root / "recovery.stdout").write_bytes(second.stdout)
        if second.returncode:
            raise AssertionError("recovery_failed:" + second.stderr.decode()[-2000:])
        report = engine.verify(campaign)
        before = snapshot(campaign)
        third = subprocess.run(argv, env=env, capture_output=True)
        assert third.returncode == 0 and snapshot(campaign) == before
        saved = report["receipts"]
        assert len(saved) == 153 and saved["c02-sol-r1-e3-nc-g1"]["state"] == "interrupted"
        assert saved["c01-gemini-r1-c3-g1"]["state"] == "invalid"
        assert saved["c01-haiku-r1-e1-s1"]["state"] == "unavailable"
        assert saved["c02-haiku-r1-e3-cn-s2"]["state"] == "unavailable"
        assert saved["c01-sol-r1-e3-nc-s2"]["state"] == "unavailable"
        assert saved["c02-gemini-r1-e3-cn-s2"]["state"] == "unavailable"
        assert saved["c02-haiku-r1-e3-nc-s2"]["state"] == "unavailable"
        posts = [decode(line) for line in (root / "posts.jsonl").read_bytes().splitlines()]
        counts = Counter(p["position"] for p in posts)
        assert set(counts.values()) == {1} and counts["c02-sol-r1-e3-nc-g1"] == 1
        assert not any(counts[i] for i in ("c01-sol-r1-e3-nc-s2", "c02-gemini-r1-e3-cn-s2", "c02-haiku-r1-e3-nc-s2"))
        assert set(p["route"] for p in posts) == {"gemini", "haiku", "sol", "native", "carl"}
        assert all(p["bearer_correct"] and p["controls_without_challenge_policy"] for p in posts)
        carl = [r["diagnostics"]["parsed"]["derived_carl"] for r in saved.values()
                if r["state"] == "completed" and r["diagnostics"]["parsed"].get("derived_carl")]
        assert any(c["challenges"] for c in carl) and any(not c["challenges"] for c in carl)
        assert all(not c["governing_authority"] and not c["release_authority"] for c in carl)
        db = engine.connect(campaign, readonly=True)
        try:
            attempts = db.execute("SELECT count(*) FROM attempts").fetchone()[0]
            records = [(i, decode(r)) for i, r in db.execute("SELECT id,record FROM transports") if r]
            worker_probes = []
            for ident, rec in records:
                for line in base64.b64decode(rec["stderr_b64"]).splitlines():
                    try: data = decode(line)
                    except (ValueError, UnicodeError): continue
                    if data.get("type") == "probe":
                        worker_probes.append({"position": ident, **data["observation"]})
            assert all(p.get("prevented", True) and p.get("JEVKEY_environment_absent", True)
                       and p.get("unexpected_inherited_descriptors", 0) == 0 for p in worker_probes)
            assert len([p for p in worker_probes if "attack" in p]) == 5
            assert len([p for p in worker_probes if "credential_boundary" in p]) > 20
            local_usage = {"input_tokens": 0, "output_tokens": 0}
            for receipt in saved.values():
                if receipt["state"] != "completed": continue
                diag = receipt["diagnostics"]
                usage = diag.get("usage") or diag.get("parsed", {}).get("direct_systemone", {}).get("usage")
                for k in local_usage: local_usage[k] += (usage or {}).get(k, 0)
        finally:
            db.close()
        assert attempts == 141
        assert any(r["reason"] == "simulated_budget_exhausted" for r in saved.values())
        assert_no_dummy_in_custody(root, dummy)
        negatives = negative_checks(root, campaign, manifest)
        result = {"contract": VERSION, "mode": "local_TLS_and_injected_CLI_event_fixtures_only",
            "manifest_sha256": manifest["manifest_sha256"], "scheduled_positions": 153,
            "scheduled_generators": 99, "scheduled_specialists": 54,
            "summary": report["summary"], "actual_local_POSTs": len(posts), "POSTs_by_route": dict(Counter(p["route"] for p in posts)),
            "outcomes": dict(Counter(r["state"] for r in saved.values())), "reservation_ceiling_exercised": attempts,
            "interruption_exit": 75, "after_interruption": interrupted, "restart_no_retransmission": True,
            "second_resume_database_unchanged": True, "kernel_egress_probes": kernel, "worker_probes": worker_probes,
            "credential_absent_from_custody": True, "fixture_usage_not_financial_accounting": local_usage,
            "carl_policy_positive_and_no_challenge_cases": True,
            "inadmissible_specialist_inputs_consumed_without_credential_or_POST": True,
            "negative_checks": negatives, "real_provider_calls": 0, "actual_CLI_invocations": 0,
            "strict_CLI_isolation_qualified": False, "live_authorisation": "NOT APPROVED"}
        (root / "acceptance.json").write_bytes(encode(result))
        # Never retain TLS fixture private key material; CA and public cert are
        # already sealed. It is unrelated to provider authentication.
        return result
    finally:
        server.terminate(); server.wait(timeout=5); stderr.close()
        peer.terminate(); peer.wait(timeout=5)
        for stream in (peer.stdin, peer.stdout): stream.close()
        key.unlink(missing_ok=True)


def negative_checks(root, campaign, m):
    from .launch import authority_lock, require_live_authority
    import copy
    import sqlite3
    checks = {}
    # All mutations operate on disposable copies, never the first attempts.
    for name, mutation in (
        ("unauthorised_destination", lambda x: x["production_campaign"]["routes"]["native"]["destination"].update(host="evil.invalid")),
        ("model_substitution", lambda x: x["production_campaign"]["routes"]["sol"].update(model="substitute")),
        ("manifest_enable_boolean", lambda x: x["production_campaign"].update(approval="APPROVED")),
        ("topology_change", lambda x: x["positions"][1].update(dependencies=[]))):
        candidate = copy.deepcopy(m); mutation(candidate)
        candidate["manifest_sha256"] = digest({k:v for k,v in candidate.items() if k != "manifest_sha256"})
        checks[name] = assert_rejected(lambda: validate_manifest(root / "packets", candidate, encode(candidate)))
    for filename, name in (("c01-source.txt", "source_packet_tamper"), ("governing-policy.json", "policy_packet_tamper")):
        target = root / "packets" / filename; original = target.read_bytes()
        target.write_bytes(original + b"tamper")
        try: checks[name] = assert_rejected(lambda: validate_manifest(root / "packets", m, encode(m)))
        finally: target.write_bytes(original)
    checks["default_live_dispatch_disabled"] = assert_rejected(lambda: require_live_authority(m))
    checks["second_fresh_campaign_same_deployment_denied"] = assert_rejected(
        lambda: engine.create(root / "duplicate-campaign", root / "packets"))
    copied = root / "copied-campaign"; shutil.copytree(campaign, copied)
    try:
        checks["copied_campaign_cannot_launch"] = assert_rejected(lambda: engine.resume(copied, offline_subprocess=True))
        dbpath = copied / "campaign.sqlite3"
        db = sqlite3.connect(dbpath)
        db.execute("UPDATE responses SET raw=? WHERE id=(SELECT id FROM responses LIMIT 1)", (b"tampered",))
        db.commit(); db.close()
        checks["raw_response_tamper"] = assert_rejected(lambda: engine.verify(copied))
    finally: shutil.rmtree(copied)
    for name, sql in (("receipt_tamper", "UPDATE receipts SET body=x'7b7d' WHERE id=(SELECT id FROM receipts LIMIT 1)"),
                       ("sealed_request_tamper", "UPDATE attempts SET request=x'7b7d' WHERE id=(SELECT id FROM attempts LIMIT 1)")):
        shutil.copytree(campaign, copied)
        try:
            db = sqlite3.connect(copied / "campaign.sqlite3"); db.execute(sql); db.commit(); db.close()
            checks[name] = assert_rejected(lambda: engine.verify(copied))
        finally: shutil.rmtree(copied)
    db = engine.connect(campaign, readonly=True)
    creation = decode(db.execute("SELECT value FROM meta WHERE key='creation'").fetchone()[0]); db.close()
    authority = Path(creation["deployment_authority"]["authority_directory"])
    with (authority / ".lock").open("rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try: checks["deployment_concurrent_instance_denied"] = assert_rejected(lambda: engine.resume(campaign, offline_subprocess=True))
        finally: fcntl.flock(stream, fcntl.LOCK_UN)
    assert len(checks) == 13 and all(checks.values())
    return checks
