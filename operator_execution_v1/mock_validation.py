"""Retain complete smoke/pilot first attempts using offline fixtures only."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from phase2.adjudication import checked_records
from phase2.core import IntegrityError, corpus, digest, json_bytes, load, write_new
from phase2.isolation import sha256_file
from .planning import FILENAMES, PACKAGE, software, validate_manifest
from .runtime import OperatorMock, execute


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrityError(message)


def validate_stage(plan: dict, directory: Path) -> dict:
    checked_plan, records = checked_records(directory)
    require(checked_plan == plan and len(records) == len(plan["jobs"]), "Incomplete mock checkpoint set")
    _, members = corpus()
    payloads, path_b_count = {}, 0
    for job in plan["jobs"]:
        ident = job["job_id"]
        record = records[ident]
        folder = directory / "checkpoints" / ident
        require(record["status"] == "mock_ok" and record["evidence_quality"] == "mock_not_research"
                and not record["satisfies_strict_isolation"], "Mock evidence mislabelled or failed")
        require(all(p.stat().st_mode & 0o222 == 0 for p in folder.iterdir()), "Writable checkpoint")
        if job["kind"] == "generator":
            require(bool(record["parsed"]["claims"]), "Empty assessment fixture")
            require(all(row["exact_source_substring"] for row in record["quote_audit"]), "Ungrounded mock quote")
            if job["challenge_parent"]:
                require(record["challenge_used"] == records[job["challenge_parent"]]["parsed"],
                        "Challenge lineage mismatch")
            continue
        payload = load(folder / "payload.json")["payload"]
        raw = load(folder / "raw.json")
        if job["mechanism"] == "carl_jev":
            wire = base64.b64decode(payload["native_request"], validate=True)
            payload = json.loads(wire)
            require(wire == json_bytes(payload), "Noncanonical matched Path B request")
            require(raw["provenance"]["replay_exit_status"] == 0
                    and raw["provenance"]["transport_attempts"] == 0
                    and raw["provenance"]["network"] == "disabled", "Path B was not an offline replay")
            path_b_count += 1
        state = json.loads(payload["state"])
        require(state["untrusted_source"] == members[job["input_member"]].decode(),
                "Adversary did not receive exact source evidence")
        require(state["assessment"] == records[job["assessment_parent"]]["parsed"]
                and bool(state["assessment"]["claims"]), "Adversary did not receive actual parent claims")
        expected_questions = {"uncertainty_adequate", "authority_promoted"} | {
            f"claim_{i:04d}_supported" for i in range(len(state["assessment"]["claims"]))}
        require(set(payload["questions"]) == expected_questions, "Frozen question coverage changed")
        payloads[(job["case_id"], job["generator"], job["arm"], job["turn"])] = json_bytes(payload)
    pairs = 0
    for (case, generator, arm, turn), payload in payloads.items():
        if arm == "E1":
            require(payloads[(case, generator, "E2", turn)] == payload,
                    "Native JEV and Path B did not use byte-identical evidence/questions")
            pairs += 1
    if plan["operator_execution"]["stage"] == "pilot":
        for case in {job["case_id"] for job in plan["jobs"]}:
            for generator in ("haiku", "gemini", "sol"):
                for arm in ("C3", "E3_NC", "E3_CN"):
                    require({job["turn"] for job in plan["jobs"] if job["case_id"] == case
                             and job["generator"] == generator and job["arm"] == arm} == {1, 2},
                            "Missing matched two-turn control/order")
    return {"checkpoints": len(records), "matched_native_path_b_pairs": pairs,
            "nonempty_source_and_claim_challenges": len(payloads), "contained_path_b_replays": path_b_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
    before = software()
    runs = args.out / "runs"
    stages = {}
    for stage in ("smoke", "pilot"):
        plan = load(PACKAGE / FILENAMES[stage])
        validate_manifest(plan)
        mock = OperatorMock(plan)
        if stage == "smoke":
            paused = execute(plan, runs, mode="mock", max_calls=5, stop_after=1, mock=mock)
            require(paused["stopped_reason"] == "operator_chunk_limit"
                    and paused["new_checkpoints"] == 1, "Smoke did not pause after one invocation")
        result = execute(plan, runs, mode="mock", max_calls=len(plan["jobs"]), mock=mock)
        require(result["complete"] and result["status_counts"] == {"mock_ok": len(plan["jobs"])},
                "Mock stage failed")
        directory = runs / stage
        verified = validate_stage(plan, directory)
        hashes = {str(p.relative_to(directory)): sha256_file(p)
                  for p in (directory / "checkpoints").rglob("*") if p.is_file()}
        calls = list(mock.calls)
        resumed = execute(plan, runs, mode="mock", max_calls=len(plan["jobs"]), mock=mock)
        require(resumed["new_checkpoints"] == 0 and resumed["invocations_this_session"] == 0
                and mock.calls == calls, "Resume reissued a first attempt")
        require(hashes == {str(p.relative_to(directory)): sha256_file(p)
                           for p in (directory / "checkpoints").rglob("*") if p.is_file()},
                "Resume changed immutable checkpoint bytes")
        stages[stage] = {**verified, "manifest_sha256": plan["manifest_sha256"],
                         "initial_completion": result, "resume": resumed,
                         "checkpoint_sha256": hashes, "first_attempt_bytes_preserved": True}
    full = load(PACKAGE / FILENAMES["full"])
    strict = load(PACKAGE / "STRICT_EXECUTION_MANIFEST.json")
    for plan in (full, strict):
        validate_manifest(plan)
        require(plan["counts"]["inputs"] == 135 and plan["counts"]["jobs"] == 6885, "Full matrix incomplete")
    require(before == software(), "Source changed during mock evidence collection")
    result = {"schema": "mmmtap-operator-retained-mock-validation-v1",
              "operator_software_sha256": digest(before), "stages": stages,
              "full_matrix_planned_not_executed": full["counts"],
              "strict_full_matrix_planned_not_executed": strict["counts"],
              "real_provider_calls": 0, "evidence_quality": "mock_not_research"}
    write_new(args.out / "summary.json", result)
    print(json.dumps({"stages": {name: {key: row[key] for key in (
        "checkpoints", "matched_native_path_b_pairs", "contained_path_b_replays",
        "nonempty_source_and_claim_challenges", "first_attempt_bytes_preserved")}
        for name, row in stages.items()}, "real_provider_calls": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
