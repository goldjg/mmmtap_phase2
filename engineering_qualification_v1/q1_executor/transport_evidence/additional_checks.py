"""Preserve interruption, duplicate-launch and corrupt-copy acceptance evidence.

Run from repository root with PYTHONPATH=.; requires the completed demonstration.
"""
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch

from engineering_qualification_v1.q1_executor import engine
from engineering_qualification_v1.q1_executor.model import decode, encode, raw_hash
from engineering_qualification_v1.q1_executor.transport_qualification import fixture, snapshot

root = Path(__file__).resolve().parent
result = {}
for kind in ("reservation", "receipt-gap"):
    frozen = fixture(root / (kind + "-fixture"), selected={"baseline"}, budget=1)
    campaign = engine.create(root / (kind + "-campaign"), frozen)
    if kind == "reservation":
        argv = [sys.executable, "-m", "engineering_qualification_v1.q1_executor", "resume", "--offline-subprocess",
                "--campaign", str(campaign), "--interrupt-after-reservation", "baseline"]
    else:
        code = ("import os,sys;from pathlib import Path;from engineering_qualification_v1.q1_executor import engine as e;"
                "e.finish=lambda *a,**k:os._exit(75);e.resume(Path(sys.argv[1]),offline_subprocess=True)")
        argv = [sys.executable, "-c", code, str(campaign)]
    child = subprocess.run(argv, capture_output=True)
    assert child.returncode == 75, child.stderr.decode()
    before = engine.verify(campaign)["summary"]
    recovered = engine.resume(campaign, offline_subprocess=True)
    stable = snapshot(campaign)
    for _ in range(2):engine.resume(campaign, offline_subprocess=True)
    assert stable == snapshot(campaign)
    audit = engine.verify(campaign)
    assert audit["receipts"]["baseline"]["state"] == "interrupted"
    assert recovered["subprocess_transport_launch_intents"] == (0 if kind == "reservation" else 1)
    assert (audit["receipts"]["baseline"]["response_sha256"] is None) == (kind == "reservation")
    result[kind] = {"child_argv": argv, "child_exit": child.returncode, "child_stderr": child.stderr.decode(),
                    "before_recovery": before, "after_recovery": recovered, "repeated_resume_unchanged": True,
                    "control": "existing durable reservation and fail-closed interrupted receipt; no reinvocation"}

campaign = root / "demonstration/campaign"
stable = snapshot(campaign)
with engine.lock(campaign):
    db = engine.connect(campaign)
    try:
        audit = engine.verify_database(db, campaign)
        p = audit["manifest"]["positions"][0]
        req = decode(db.execute("SELECT request FROM attempts WHERE id='baseline'").fetchone()[0])
        with patch.object(subprocess, "Popen", side_effect=AssertionError("duplicate process creation")):
            try:engine.execute_transport(db, campaign, audit["manifest"], p, req, None)
            except ValueError as exc:
                assert str(exc) == "duplicate_transport_launch_refused"
                result["duplicate"] = {"rejected": True, "control": str(exc), "no_process_creation": True}
            else:raise AssertionError("duplicate accepted")
    finally:db.close()
for _ in range(2):engine.resume(campaign, offline_subprocess=True)
assert stable == snapshot(campaign)
result["demonstration_repeated_resume"] = {"all_files_unchanged": True, "file_sha256": stable}

result["corruption"] = {}
with tempfile.TemporaryDirectory() as temp:
    for kind in ("envelope", "record", "observed_identity", "raw", "receipt", "journal"):
        target = Path(temp) / kind;shutil.copytree(campaign, target)
        engine.verify(target)  # Confirm relocatable audit before corrupting anything.
        with sqlite3.connect(target / "campaign.sqlite3") as db:
            if kind in ("envelope", "record", "observed_identity"):
                column = "envelope" if kind == "envelope" else "record"
                rec = decode(db.execute("SELECT " + column + " FROM transports WHERE id='baseline'").fetchone()[0])
                if kind == "envelope":rec["request_sha256"] = "0"*64
                elif kind == "record":rec["stdout_b64"] = "e30="
                else:rec["observed_identity"]["version"] = "foreign-version"
                db.execute("UPDATE transports SET " + column + "=? WHERE id='baseline'", (encode(rec),))
            elif kind == "raw":db.execute("UPDATE responses SET raw=? WHERE id='baseline'", (b"changed",))
            elif kind == "receipt":
                rec = decode(db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0])
                rec["transport_record_sha256"] = "0"*64
                db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (encode(rec),))
            else:db.execute("DELETE FROM events WHERE seq=4")
        before = snapshot(target)
        try:engine.verify(target)
        except (ValueError, TypeError, KeyError) as exc:
            result["corruption"][kind] = {"rejected": True, "error": str(exc)}
        else:raise AssertionError("corruption accepted:" + kind)
        assert before == snapshot(target)
result["real_provider_calls"] = 0
(root / "additional_checks.json").write_bytes(encode(result))
print(encode({"verification": "PASS", "checks": list(result), "real_provider_calls": 0}).decode())
