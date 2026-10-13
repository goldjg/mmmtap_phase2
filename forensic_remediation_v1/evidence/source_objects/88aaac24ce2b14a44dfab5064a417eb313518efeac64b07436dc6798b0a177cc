"""Offline-only adapter for the separately versioned cARL assessment interface.

Existing plans/checkpoints are read as provenance, never executed or rewritten.
The cARL-owned command supplies actual pack/profile composition and policy replay.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

from historical_extractor.extract import strict_json
from .core import ROOT, IntegrityError, challenge_request, corpus, digest, json_bytes, load, write_new


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def build_request(plan: dict, job: dict, checkpoint_root: Path,
                  sources: dict[str, bytes], source_manifest: bytes, attempt_id: str) -> dict:
    if plan.get("manifest_sha256") != digest({k: v for k, v in plan.items() if k != "manifest_sha256"}):
        raise IntegrityError("Reference plan content hash mismatch")
    if job not in plan["jobs"] or job["mechanism"] != "carl_jev" or job["kind"] != "adversary":
        raise IntegrityError("Select an existing cARL adversary position as a lineage reference only")
    parent_id = job["assessment_parent"]
    parent_jobs = [j for j in plan["jobs"] if j["job_id"] == parent_id]
    if len(parent_jobs) != 1:
        raise IntegrityError("Unique parent job required")
    parent_job = parent_jobs[0]
    if any(job[k] != parent_job[k] for k in ("case_id", "variant_id", "generator", "input_sha256")):
        raise IntegrityError("Cross-input or generator parent")
    expected_arm = "E3_NC" if job["arm"] == "E3_NC" else "B0"
    expected_turn = 1 if expected_arm == "E3_NC" else 0
    if parent_job["arm"] != expected_arm or parent_job["turn"] != expected_turn:
        raise IntegrityError("Cross-branch parent")
    path = checkpoint_root / "checkpoints" / parent_id / "result.json"
    raw_parent = path.read_bytes()
    parent = strict_json(raw_parent)
    if (parent["job_id"] != parent_id or parent["input_sha256"] != job["input_sha256"]
            or parent["manifest_sha256"] != plan["manifest_sha256"]
            or not parent["schema_valid"] or parent["status"] not in ("mock_ok", "ok")):
        raise IntegrityError("Invalid parent checkpoint")
    if set(parent["artifact_sha256"]) != {"intent.json", "payload.json", "raw.json"}:
        raise IntegrityError("Complete parent artifact set required")
    for name, expected in parent["artifact_sha256"].items():
        if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != expected:
            raise IntegrityError("Parent artifact hash mismatch")
    source = sources[job["input_member"]]
    manifest = strict_json(source_manifest)
    if (plan["source_archive_sha256"] != manifest["archive_sha256"]
            or plan["source_manifest_sha256"] != digest(manifest)):
        raise IntegrityError("Reference plan corpus binding mismatch")
    native = challenge_request(plan, {**job, "mechanism": "native_jev"}, source, parent["parsed"])
    return {
        "schema": "carl-assessment-challenge-v1-request",
        "attempt": {"id": attempt_id, "branch_id": job["arm"], "turn": job["turn"],
                    "parent_job_id": parent_id},
        "source": {
            "text": source.decode("utf-8"), "sha256": job["input_sha256"],
            "origin_kind": "archive_member", "archive_sha256": manifest["archive_sha256"],
            "member_path": job["input_member"],
            "manifest_sha256": hashlib.sha256(source_manifest).hexdigest(),
            "authenticated_git": False, "deployment_state": "not_asserted",
        },
        "assessment": parent["parsed"], "parent_checkpoint": b64(raw_parent),
        "parent_checkpoint_sha256": hashlib.sha256(raw_parent).hexdigest(),
        "source_manifest": b64(source_manifest), "native_request": b64(json_bytes(native)),
    }


def invoke_offline(binary: Path, args: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess:
    if not args or args[0] not in ("prepare", "evaluate-offline", "replay"):
        raise IntegrityError("Path B supports offline commands only")
    # No inherited credential or repository/session environment is passed.
    return subprocess.run([str(binary.resolve(strict=True)), *args], input=b"",
                          capture_output=True, check=False, timeout=timeout,
                          env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-plan", type=Path, default=ROOT / "execution_plan_v2.json")
    parser.add_argument("--checkpoints", type=Path, default=ROOT / "execution_dry_run_v2")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--request-out", type=Path, required=True)
    args = parser.parse_args()
    plan = load(args.reference_plan)
    jobs = [j for j in plan["jobs"] if j["job_id"] == args.job_id]
    if len(jobs) != 1:
        parser.error("job ID must identify one existing cARL position")
    _, sources = corpus()
    request = build_request(plan, jobs[0], args.checkpoints, sources,
                            (ROOT / "MMMTAP_Phase2/corpus_manifest.json").read_bytes(),
                            args.attempt_id)
    write_new(args.request_out, request)
    print(json.dumps({"status": "prepared_request_only", "live_calls": 0,
                      "request_sha256": hashlib.sha256(args.request_out.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
