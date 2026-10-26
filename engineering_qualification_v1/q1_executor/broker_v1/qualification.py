"""Executed local integration/adversarial qualification, never a live launch."""
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

from . import VERSION
from .contract import HERE, extension, message
from .broker import records, authorise
from .. import engine
from ..model import PACKAGE, decode, digest, encode, raw_hash, validate_manifest
from ..transport import unb64, process_identity
from ..transport_qualification import snapshot

ATTACKS = ("invent_campaign", "invent_attempt", "alter_request", "source_digest", "policy_digest",
           "destination", "model", "role", "no_reservation", "other_response")
ISOLATION = ("network", "unix_socket", "spawn", "exec", "forbidden_file", "credentials", "history",
             "source_write", "policy_write")
FAULTS = ("malformed", "identity_unknown", "identity_mismatch", "partial_failure", "timeout",
          "connection_loss", "duplicate", "before_dispatch", "after_intent", "after_acceptance",
          "executor_interrupt", "tamper", "response_limit", "worker_tamper")


def fixture(root, scenarios=None, selected=None):
    root.mkdir()
    m, _ = validate_manifest(PACKAGE / "fixtures")
    for ref in m["packets"].values():
        shutil.copyfile(PACKAGE / "fixtures" / ref["path"], root / ref["path"])
    selected = selected or {"baseline"}
    m["positions"] = [p for p in m["positions"] if p["id"] in selected]
    m["campaign_id"] = "synthetic-q1-broker-v1-" + digest([scenarios, sorted(selected)])[:12]
    for p in m["positions"]:
        p["case_id"] = m["campaign_id"]
    m["attempt_ceiling"] = m["simulated_budget_units"] = len(selected)
    m["transport"] = extension(scenarios)
    m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
    (root / "manifest.json").write_bytes(encode(m))
    validate_manifest(root)
    return root


def audit_capture(campaign):
    before = snapshot(campaign)
    audit = engine.verify(campaign)
    assert snapshot(campaign) == before, "readonly_verification_mutated_campaign"
    with engine.connect(campaign, readonly=True) as db:
        broker_records = {p["id"]: records(db, p["id"]) for p in audit["manifest"]["positions"]}
        recs = {ident: decode(body) for ident, body in db.execute("SELECT id,record FROM transports") if body}
        raw = {ident: {"raw_sha256": raw_hash(body), "raw_bytes": len(body)}
               for ident, body in db.execute("SELECT id,raw FROM responses")}
    return {"summary": audit["summary"], "broker_records": broker_records, "transport_records": recs,
            "raw_responses": raw, "receipt_hashes": {i: digest(r) for i, r in audit["receipts"].items()},
            "receipts": audit["receipts"], "read_only_files_unchanged": True}


def stopped(processes):
    deadline = time.monotonic() + 2
    while True:
        live = [old for old in processes if (current := process_identity(old["pid"]))
                and current["start_ticks"] == old["start_ticks"] and current["state"] not in ("Z", "X")]
        if not live:
            return True
        if time.monotonic() >= deadline:
            raise AssertionError("supervised_process_survived_executor:" + str(live))
        time.sleep(0.01)


def run_case(root, name, scenarios=None, selected=None, crash=False):
    case = root / name; case.mkdir()
    frozen = fixture(case / "fixture", scenarios, selected)
    campaign = engine.create(case / "campaign", frozen)
    if crash:
        child = subprocess.run([sys.executable, "-B", "-m", "engineering_qualification_v1.q1_executor", "resume",
                                "--offline-subprocess", "--campaign", str(campaign)], capture_output=True)
        (case / "executor.stdout").write_bytes(child.stdout)
        (case / "executor.stderr").write_bytes(child.stderr)
        assert child.returncode == 75, (name, child.returncode, child.stderr)
        before = audit_capture(campaign)
        (case / "before-recovery.json").write_bytes(encode(before))
        tree = before["transport_records"]["baseline"]["processes"]
        assert stopped(tree)
        # Restart the actual broker before executor recovery. The original
        # position is still started, but its durable intent forbids dispatch.
        with engine.connect(campaign, readonly=True) as db:
            request = db.execute("SELECT request FROM attempts WHERE id='baseline'").fetchone()[0]
            envelope = decode(db.execute("SELECT envelope FROM transports WHERE id='baseline'").fetchone()[0])
        replay = subprocess.run([sys.executable, "-B", "-m",
                                 "engineering_qualification_v1.q1_executor.broker_v1.broker",
                                 "--campaign", str(campaign), "--position", "baseline",
                                 "--manifest", envelope["manifest_sha256"]],
                                input=encode(message(envelope, request)) + b"\n", capture_output=True)
        (case / "broker-restart.stdout").write_bytes(replay.stdout)
        (case / "broker-restart.stderr").write_bytes(replay.stderr)
        assert replay.returncode == 0, replay.stderr
        assert decode(replay.stdout)["reason"] == "duplicate_dispatch"
        assert engine.verify(campaign)["summary"]["broker_dispatch_intents"] == 1
    else:
        before = None
    engine.resume(campaign, offline_subprocess=True)
    if crash:
        # Also restart after terminal recovery: rejection remains valid durable
        # evidence and cannot invalidate the already published receipt.
        replay = subprocess.run([sys.executable, "-B", "-m",
                                 "engineering_qualification_v1.q1_executor.broker_v1.broker",
                                 "--campaign", str(campaign), "--position", "baseline",
                                 "--manifest", envelope["manifest_sha256"]],
                                input=encode(message(envelope, request)) + b"\n", capture_output=True)
        (case / "broker-post-recovery.stdout").write_bytes(replay.stdout)
        (case / "broker-post-recovery.stderr").write_bytes(replay.stderr)
        assert replay.returncode == 0 and decode(replay.stdout)["reason"] == "duplicate_dispatch"
    first = audit_capture(campaign)
    frozen_files = snapshot(campaign)
    for _ in range(3):
        engine.resume(campaign, offline_subprocess=True)
        assert snapshot(campaign) == frozen_files, "restart_retransmitted_or_changed_evidence"
    first.update(repeated_restarts_without_retransmission=3, crash_exit=75 if crash else None,
                 before_recovery=before, supervised_processes_stopped=True if crash else None,
                 restarted_broker_replay="REJECTED_NO_DISPATCH" if crash else None)
    (case / "report.json").write_bytes(encode(first))
    return first


def tampering(root, source):
    result = {}
    for target in ("raw", "broker_raw", "identity", "dispatch", "request", "receipt", "event", "packet"):
        copy = root / ("tampered-" + target)
        shutil.copytree(source, copy)
        with sqlite3.connect(copy / "campaign.sqlite3") as db:
            if target == "raw":
                db.execute("UPDATE responses SET raw=? WHERE id='baseline'", (b"ALTERED",))
            elif target in ("broker_raw", "identity", "dispatch", "event"):
                seq, body = next((seq, decode(body)) for seq, body in db.execute("SELECT seq,body FROM events ORDER BY seq DESC")
                                 if decode(body)["kind"] == "broker_event")
                key = {"broker_raw": "raw_b64", "identity": "observed_identity", "dispatch": "stage", "event": "destination"}[target]
                body["data"][key] = "ALTERED"
                db.execute("UPDATE events SET body=?, hash=? WHERE seq=?", (encode(body), digest(body), seq))
            elif target == "request":
                db.execute("UPDATE attempts SET request=? WHERE id='baseline'", (b"{}",))
            elif target == "receipt":
                r = decode(db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0]); r["broker_raw_sha256"] = "0"*64
                db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (encode(r),))
            else:
                (copy / "source.txt").write_bytes(b"changed sealed source")
        frozen = snapshot(copy)
        try:
            engine.verify(copy)
        except (ValueError, KeyError, TypeError):
            result[target] = "REJECTED"
        else:
            raise AssertionError("tampering_accepted:" + target)
        assert snapshot(copy) == frozen
    return result


def qualify(root):
    root = root.absolute(); root.mkdir()
    assert (PACKAGE / "transport_evidence/demonstration/campaign/campaign.sqlite3").is_file()
    canaries = {p.name: raw_hash(p.read_bytes()) for p in HERE.glob("host-canary*")}
    results = {}
    chain = {"baseline", "control", "invalid", "invalid-child", "native", "intermediate", "carl", "final"}
    results["chain"] = run_case(root, "chain", {"invalid": "malformed"}, chain)
    assert results["chain"]["summary"]["states"] == {"completed": 6, "invalid": 1, "blocked": 1}
    receipts = results["chain"]["receipts"]
    assert receipts["final"]["preceding_disposition_pair"] == ["review_required", "pass"]
    assert receipts["native"]["state"] == receipts["carl"]["state"] == "completed"
    assert receipts["invalid-child"]["reserved_at"] is None
    for name in FAULTS + ATTACKS + ISOLATION:
        report = run_case(root, name, {"baseline": name}, crash=name in ("after_acceptance", "executor_interrupt"))
        results[name] = report
        s = report["summary"]; r = report["receipts"]["baseline"]
        assert s["attempt_reservations"] == 1 and s["subprocess_bootstraps_verified"] == 1, name
        assert s["broker_dispatch_intents"] <= 1 and s["mock_provider_acceptances"] <= 1, name
        if name in ATTACKS:
            assert s["broker_rejected_requests"] == 1 and s["broker_dispatch_intents"] == 0, name
        elif name in ISOLATION:
            lines = unb64(report["transport_records"]["baseline"]["stderr_b64"]).splitlines()
            probe = next(decode(line)["observation"] for line in lines if b'"type":"probe"' in line)
            expected = 1 if name in ("network", "unix_socket", "spawn", "exec") else 30 if name in ("source_write", "policy_write") else 2
            assert probe == {"attack": name, "prevented": True, "errno": expected}, (name, probe)
            report["isolation_observation"] = probe
            assert s["broker_dispatch_intents"] == 0, name
        elif name == "duplicate":
            assert s["broker_rejected_requests"] == 1 and s["broker_dispatch_intents"] == s["mock_provider_acceptances"] == 1
            assert r["state"] == "completed"
        elif name in ("after_acceptance", "executor_interrupt"):
            assert r["state"] == "interrupted" and s["broker_uncertain_completions"] == 1
            assert s["mock_provider_acceptances"] == s["broker_dispatch_intents"] == 1
        elif name == "before_dispatch":
            assert s["broker_dispatch_intents"] == s["mock_provider_acceptances"] == 0
        elif name == "after_intent":
            assert s["broker_dispatch_intents"] == 1 and s["mock_provider_acceptances"] == 0 and s["broker_uncertain_completions"] == 1
        elif name == "malformed":
            assert r["state"] == "invalid"
        else:
            assert r["state"] == "unavailable", (name, r)
        (root / name / "report.json").write_bytes(encode(report))
    assert canaries == {p.name: raw_hash(p.read_bytes()) for p in HERE.glob("host-canary*")}
    # Independent broker rejects even the exact sealed message with no durable
    # reservation. This bypasses worker framing and exercises its own authority.
    frozen = fixture(root / "unreserved-fixture")
    unreserved = engine.create(root / "unreserved-campaign", frozen)
    with engine.connect(unreserved) as db:
        m = engine.verify_database(db, unreserved)["manifest"]
        try:
            authorise(db, unreserved, "baseline", m["manifest_sha256"], {})
        except ValueError as exc:
            assert str(exc) == "reservation_required"
        else:
            raise AssertionError("broker_allowed_unreserved_request")
    # The original reservation routine, without broker intervention, still
    # refuses a duplicate and never changes a first attempt or terminal receipt.
    campaign = root / "chain" / "campaign"
    before = snapshot(campaign)
    with engine.connect(campaign) as db:
        m = engine.verify_database(db, campaign)["manifest"]
        assert engine.reserve(db, campaign, m, m["positions"][0]) is False
    assert snapshot(campaign) == before
    negatives = tampering(root, campaign)
    sums = {key: sum(r["summary"][key] for r in results.values()) for key in (
        "attempt_reservations", "broker_authorised_requests", "broker_rejected_requests", "broker_dispatch_intents",
        "mock_provider_process_starts", "mock_provider_acceptances", "broker_uncertain_completions", "broker_terminal_failures", "broker_complete_responses")}
    report = {"contract": VERSION, "classification": "OFFLINE SYNTHETIC ENGINEERING ONLY",
              "actual_campaigns": len(results), "totals": sums,
              "cases": {k: {"summary": r["summary"], "receipt_hashes": r["receipt_hashes"], "raw_responses": r["raw_responses"],
                             "stable_restarts": 3} for k, r in results.items()},
              "tampering_rejected": negatives, "direct_unreserved_request": "REJECTED",
              "original_executor_duplicate_reservation": "REFUSED_UNCHANGED",
              "host_canaries_unchanged": canaries, "real_provider_calls": 0, "live_experiment_launches": 0,
              "scientific_outcome_claims": 0, "live_execution_authorized": False}
    (root / "acceptance.json").write_bytes(encode(report))
    return report
