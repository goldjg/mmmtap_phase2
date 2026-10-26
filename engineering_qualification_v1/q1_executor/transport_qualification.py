"""Executable offline transport qualification using the existing Q1 engine."""
from pathlib import Path
import os
import shutil
import sqlite3
import subprocess
import sys
import time

from .model import PACKAGE, decode, digest, encode, raw_hash, validate_manifest
from .transport import extension, unb64, process_identity


def fixture(root, scenarios=None, *, selected=None, budget=10):
    root.mkdir(parents=False, exist_ok=False)
    original, _ = validate_manifest(PACKAGE / "fixtures")
    for ref in original["packets"].values():
        shutil.copyfile(PACKAGE / "fixtures" / ref["path"], root / ref["path"])
    if selected:
        original["positions"] = [p for p in original["positions"] if p["id"] in selected]
    original["campaign_id"] = "synthetic-q1-transport-v1-" + digest([scenarios, sorted(selected or []), budget])[:12]
    for p in original["positions"]:
        p["case_id"] = original["campaign_id"]
    original["attempt_ceiling"] = original["simulated_budget_units"] = budget
    original["transport"] = extension(scenarios)
    original["manifest_sha256"] = digest({k: v for k, v in original.items() if k != "manifest_sha256"})
    (root / "manifest.json").write_bytes(encode(original))
    validate_manifest(root)
    return root


def snapshot(root):
    return {p.relative_to(root).as_posix(): raw_hash(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def demo(root):
    from .engine import create, resume, verify
    root.mkdir(parents=False, exist_ok=False)
    frozen = fixture(root / "fixture", {"invalid": "malformed", "exception": "partial_failure",
                                       "unknown-identity": "identity_unknown", "interruption": "running_interrupt"})
    campaign = create(root / "campaign", frozen)
    child = subprocess.run([sys.executable, "-m", "engineering_qualification_v1.q1_executor", "resume",
                            "--offline-subprocess", "--campaign", str(campaign),
                            "--interrupt-after-transport-start", "interruption"], capture_output=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if child.returncode != 75:
        raise ValueError("expected_running_invocation_interruption_75:" + child.stderr.decode())
    before_recovery = verify(campaign)["summary"]
    with sqlite3.connect(campaign / "campaign.sqlite3") as db:
        abandoned = decode(db.execute("SELECT record FROM transports WHERE id='interruption'").fetchone()[0])
    deadline = time.monotonic() + 2
    while True:
        live = []
        for old in abandoned["processes"]:
            current = process_identity(old["pid"])
            if current and current["start_ticks"] == old["start_ticks"] and current["state"] not in ("Z", "X"):
                live.append(current)
        if not live:
            break
        if time.monotonic() >= deadline:
            raise ValueError("isolated_process_survived_executor_death:" + str(live))
        time.sleep(0.01)
    resumed = resume(campaign, offline_subprocess=True)
    before = snapshot(campaign)
    twice = resume(campaign, offline_subprocess=True)
    if twice != resumed or snapshot(campaign) != before:
        raise ValueError("transport_resume_not_byte_idempotent")
    audit = verify(campaign)
    if audit["summary"]["states"] != {"completed": 6, "invalid": 1, "blocked": 4, "interrupted": 1, "unavailable": 3}:
        raise ValueError("transport_representative_graph_accounting_failed")
    with sqlite3.connect(campaign / "campaign.sqlite3") as db:
        interrupted_calls = db.execute("SELECT count(*) FROM invocations WHERE id='interruption'").fetchone()[0]
        records = {ident: decode(raw) for ident, raw in db.execute("SELECT id,record FROM transports") if raw}
    if interrupted_calls != 1 or unb64(records["interruption"]["stdout_b64"]) != b"partial-before-hang":
        raise ValueError("interrupted_transport_bytes_or_attempt_count")
    result = {"classification": "SYNTHETIC OFFLINE ENGINEERING; NO LIVE PROVIDERS",
              "interruption_exit": child.returncode, "before_recovery": before_recovery,
              "after_recovery": resumed, "second_resume": twice, "all_campaign_files_unchanged": True,
              "interrupted_attempt_invocations": interrupted_calls, "transport_records": records,
              "abandoned_process_tree_stopped_by_os": True, "abandoned_processes": abandoned["processes"],
              "live_execution_authorized": False}
    (root / "report.json").write_bytes(encode(result))
    return result


def probes(root):
    """Real malicious processes. Preserve each probe's campaign and raw records."""
    from .engine import create, resume, verify
    root.mkdir(parents=False, exist_ok=False)
    results = {}
    for scenario in ("valid", "malformed", "partial_failure", "timeout", "crash", "identity_mismatch", "identity_unknown",
                     "forbidden_file", "spawn", "exec", "network", "source_write", "policy_write", "session_seed", "reuse"):
        frozen = fixture(root / (scenario + "-fixture"), {"baseline": scenario}, selected={"baseline"}, budget=1)
        campaign = create(root / (scenario + "-campaign"), frozen)
        resume(campaign, offline_subprocess=True)
        audit = verify(campaign)
        with sqlite3.connect(campaign / "campaign.sqlite3") as db:
            rec = decode(db.execute("SELECT record FROM transports").fetchone()[0])
        observation = None
        try:
            observation = decode(unb64(rec["stdout_b64"]))
        except (ValueError, UnicodeError):
            pass
        # Fixtures' reports alone do not qualify controls: require startup of
        # the pinned OS wrapper, the denial errno and actual host-side custody.
        expected_errno = 30 if scenario in ("source_write", "policy_write") else 1 if scenario in ("spawn", "exec", "network") else 2
        attack = scenario in ("forbidden_file", "spawn", "exec", "network", "source_write", "policy_write", "reuse")
        control = ("read-only mount" if scenario in ("source_write", "policy_write") else "seccomp allowlist"
                   if scenario in ("spawn", "exec", "network") else "mount/PID namespace and fresh home")
        qualified = bool(rec["bootstrap_verified"] and rec["cleanup"])
        if attack:
            qualified &= observation == {"attack": scenario, "prevented": True, "errno": expected_errno}
        results[scenario] = {"local_control": control if attack else "transport capture/validation",
                             "status": "PASS" if qualified else "BLOCKED/UNQUALIFIED",
                             "observation": observation, "outcome": audit["receipts"]["baseline"]["state"],
                             "record": rec, "summary": audit["summary"]}
    (root / "report.json").write_bytes(encode(results))
    return results
