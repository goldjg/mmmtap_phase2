"""Verify this private evidence package without executing the retained implementation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "REMEDIATION_LEDGER.csv", "REMEDIATION_REPORT.md", "REGRESSION_EVIDENCE.json",
    "ISOLATION_VALIDATION.json", "JEV_PATH_B_EQUIVALENCE.json",
    "TRANSPORT_PROVENANCE_VALIDATION.json", "FROZEN_INSTRUMENT_VALIDATION.json",
    "PRESERVATION_CHECKS.json", "FINAL_PRESERVATION_CHECKS.json", "REMAINING_RISKS.md",
    "LIVE_REQUALIFICATION_PROCEDURE.md", "path_b_transport_contract.json",
    "CANDIDATE_V4_REJECTED.json", "v5/execution_plan_v5.json",
    "v5/instruments/manifest.json", "v5/end_to_end_validation.json",
    "v5/bin/carl-assessment-challenge-v5", "evidence/tools/publish_evidence.py",
}
SHA = re.compile(r"[0-9a-f]{64}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def files():
    require(ROOT.stat().st_mode & 0o077 == 0, "Keep the raw-evidence package owner-only")
    result = {}
    for path in sorted(ROOT.rglob("*")):
        mode = path.lstat().st_mode
        require(not stat.S_ISLNK(mode), "Package symlink refused: " + str(path))
        if stat.S_ISDIR(mode):
            continue
        require(stat.S_ISREG(mode), "Non-regular evidence refused: " + str(path))
        name = path.relative_to(ROOT).as_posix()
        require(not any(c in name for c in "\n\r\\"), "Unsafe checksum filename")
        if name != "SHA256SUMS.txt":
            result[name] = sha(path)
    require(REQUIRED <= result.keys(), "Missing required deliverables: " + str(REQUIRED - result.keys()))
    return result


def bound_sources(record):
    result = {}
    for name, ident in record["source_sha256"].items():
        if name.startswith("workspace/"):
            key = "mmmtap_phase2/" + name.removeprefix("workspace/")
        else:
            require(name.startswith("carl/"), "Unknown recorded source root")
            key = "cARL-semantic-eval/" + name.removeprefix("carl/")
        result[key] = ident
    return result


def verify_references(actual):
    plan = load("v5/execution_plan_v5.json")
    manifest = load("v5/instruments/manifest.json")
    software = load("v5/instruments/software.v1.json")
    implementation = actual["v5/instruments/software.v1.json"]
    instruments = actual["v5/instruments/manifest.json"]
    binary = actual["v5/bin/carl-assessment-challenge-v5"]
    require(plan["execution_plan_revision"] == 5 and plan["integration_version"] == "mmmtap-integration-v4",
            "Not the corrected revision-5 candidate")
    require(plan["implementation_sha256"] == manifest["implementation_sha256"] == implementation,
            "Implementation identity mismatch")
    require(plan["instruments_sha256"] == instruments, "Instrument identity mismatch")
    require(plan["manifest_sha256"] == digest({k: v for k, v in plan.items() if k != "manifest_sha256"}),
            "Execution plan semantic identity mismatch")
    require(plan["live_execution_enabled"] is False, "Live experiment gate changed")
    instrument_files = {name.removeprefix("v5/instruments/"): ident for name, ident in actual.items()
                        if name.startswith("v5/instruments/") and name != "v5/instruments/manifest.json"}
    require(instrument_files == manifest["files"], "Instrument closure mismatch")
    for name, ident in software["sources"].items():
        require(actual["v5/instruments/software_source/" + name] == ident, "Frozen source mismatch")
    require(len(software["sources"]) == 144, "Unexpected tested source closure")
    build = load("v5/bin/carl-assessment-challenge-v5.build.json")
    require(binary == software["path_b_binary_sha256"] == build["binary_sha256"],
            "Executable/source-build identity mismatch")
    require(actual["v5/bin/carl-assessment-challenge-v5.build.json"]
            == actual["v5/instruments/path_b_build.v1.json"] == software["path_b_build_receipt_sha256"],
            "Build receipt identity mismatch")
    require(build["exit_status"] == 0, "Path B build failed")
    require(build["source_sha256"] == {
        name.removeprefix("cARL-semantic-eval/"): ident for name, ident in software["sources"].items()
        if name.startswith("cARL-semantic-eval/")}, "Build source closure mismatch")
    snapshots = {"prompt_templates": "prompts.v1.snapshot.json", "question_pack": "questions.v1.json",
                 "assessment_shape": "assessment_shape.v1.json", "evidence_schema": "evidence_schema.v1.json",
                 "roles": "roles.v1.json", "provider_response_schema": "provider_response_schema.v2.json",
                 "config": "config.v4.json"}
    for key, name in snapshots.items():
        require(plan[key] == load("v5/instruments/" + name), "Plan does not consume snapshot: " + key)
    require(len(plan["jobs"]) == 6885 and len(plan["source_manifest"]["items"]) == 135,
            "Experimental matrix changed")
    for job in plan["jobs"]:
        require(job["implementation_sha256"] == implementation and job["instruments_sha256"] == instruments,
                "Job lacks current software/instrument identity")
    reports = ("REGRESSION_EVIDENCE.json", "ISOLATION_VALIDATION.json", "JEV_PATH_B_EQUIVALENCE.json",
               "TRANSPORT_PROVENANCE_VALIDATION.json", "FROZEN_INSTRUMENT_VALIDATION.json",
               "path_b_transport_contract.json")
    for name in reports:
        report = load(name)
        require(report["implementation_sha256"] == implementation and report["instruments_sha256"] == instruments,
                "Report refers to a different implementation: " + name)
        if "execution_plan_sha256" in report:
            require(report["execution_plan_sha256"] == actual["v5/execution_plan_v5.json"],
                    "Report plan anchor mismatch")
    for name in actual:
        if name.endswith(".json") and "/" not in name:
            report = load(name)
            if isinstance(report, dict) and report.get("producer_sha256"):
                ident = report["producer_sha256"]
                require(actual["evidence/source_objects/" + ident] == ident, "Missing exact report producer")
    commands = 0
    for name in actual:
        if name.startswith("evidence/commands/") and name.endswith("/command.json"):
            commands += 1
            record = load(name)
            folder = str(PurePosixPath(name).parent)
            for stream in ("stdout", "stderr"):
                require(actual[folder + "/" + stream + ".txt"] == record[stream + "_sha256"],
                        "Command stream changed")
            for ident in record["source_sha256"].values():
                require(actual["evidence/source_objects/" + ident] == ident, "Missing command source object")
            if record.get("runner_source_sha256"):
                ident = record["runner_source_sha256"]
                require(actual["evidence/source_objects/" + ident] == ident, "Missing exact command runner")
    regression = load("REGRESSION_EVIDENCE.json")
    for label, entry in regression["final_commands"].items():
        record = load(entry["command_record"])
        require(actual[entry["command_record"]] == entry["command_record_sha256"],
                "Final command record changed: " + label)
        require(record["exit_status"] == 0 and record["source_unchanged_during_command"]
                and record["real_provider_calls"] == 0 and bound_sources(record) == software["sources"],
                "Final command is failed, live or stale: " + label)
    require(regression["python"] == {"passed": 144, "skipped": 0}, "Unexpected Python result")
    require(regression["go"]["top_level_passed"] == 247
            and regression["go"]["including_subtests_passed"] == 512, "Unexpected Go result")
    for entry in regression["red_before_fix"].values():
        require(load(entry["command_record"])["exit_status"] != 0
                and entry["hash_exact_original_sources_available"], "Missing pre-fix failure evidence")
    controls = load("v5/isolation_controls_final/summary.json")
    require(len(controls["controls"]) == 48 and controls["qualification"]
            == {"haiku": "blocked", "gemini": "blocked", "sol": "blocked"}, "Strict isolation blocks changed")
    require(controls["bindings"]["sources"] == software["sources"]
            and controls["bindings"]["instruments_sha256"] == instruments, "Stale isolation controls")
    isolation = load("v5/generator_isolation_evidence.json")
    catalog = "adapter_qualification_v1/adapter_readiness_v2.json"
    baseline = load("evidence/baseline/workspace_inventory.json")
    require(isolation["catalog_evidence"]["sha256"]
            == actual["evidence/historical_references/adapter_readiness_v2.json"] == baseline[catalog]["sha256"],
            "Historical catalog reference changed")
    readiness = load("v5/adapter_readiness_v4.json")
    require(readiness["live_qualified"] is False
            and all(row["live_capable"] is False for row in readiness["adapters"].values()),
            "Offline evidence relabelled as live qualification")
    equivalence = load("JEV_PATH_B_EQUIVALENCE.json")
    require(equivalence["fixture_count"] == 65 and equivalence["all_underlying_interpretations_equal"]
            and all(row["go_equals_native"] for row in equivalence["cases"]), "Parser equivalence incomplete")
    validation = load("v5/end_to_end_validation.json")
    require(validation["mode"] == "mock_not_research" and validation["live_calls"] == 0
            and validation["first_run"]["status_counts"] == {"mock_ok": 6885}
            and validation["resume"]["new_checkpoints"] == 0
            and validation["blinded"]["exported_pairs"] == 2835, "Full mock/resume/export incomplete")
    transport = load("TRANSPORT_PROVENANCE_VALIDATION.json")
    require(transport["archive_sha256"] == validation["archive"]["sha256"]
            == actual["v5/end_to_end_mock.tar.gz"], "Mock archive anchor mismatch")
    require(transport["archive_entries_individually_verified"]
            == len(load("v5/end_to_end_mock_files.json")["files"]), "Archive inventory incomplete")
    require(transport["checkpoints"] == 6885 and transport["path_b_offline_policy_replays"] == 1215
            and transport["matched_independent_E1_E2_request_pairs"] == 405
            and transport["frozen_prompt_and_own_branch_history_verified_for_every_generator"],
            "Matched-chain provenance incomplete")
    for arm in ("E3_NC", "E3_CN", "C3"):
        require(transport["both_E3_orders_and_C3"][arm] == {"groups": 405, "turns_each": [1, 2]},
                "Missing matched-turn control")
    preserved = load("FINAL_PRESERVATION_CHECKS.json")
    require(preserved["baseline_sha256"] == actual["evidence/baseline/baseline.json"],
            "Preservation baseline anchor mismatch")
    require(all(not r["missing"] and not r["unexpected_changes"] for r in preserved["roots"].values())
            and all(r["unchanged"] for r in preserved["historical_evidence"].values()),
            "Preservation audit failed")
    require(preserved["primary_inputs"]["identities"] == 135
            and preserved["primary_inputs"]["distinct_input_hashes"] == 108
            and preserved["primary_inputs"]["all_members_match"], "Original corpus changed")
    path_a = preserved["path_a"]
    require(path_a["before_sha256"] == path_a["after_sha256"]
            and path_a["python_CarlJEVAdapter_before_sha256"] == path_a["python_CarlJEVAdapter_after_sha256"]
            and path_a["all_protected_Go_sources_unchanged"], "Path A preservation failed")
    require(plan["supersedes"]["sha256"]
            == preserved["historical_plans"]["integration_readiness_v1/execution_plan_v3.json"],
            "Historical v3 reference changed")
    rejected = load("CANDIDATE_V4_REJECTED.json")
    require(rejected["status"] == "rejected_not_current_qualification_evidence"
            and rejected["archive_sha256"] == actual[rejected["archive"]]
            and rejected["original_plan_sha256"] == actual[rejected["original_plan"]],
            "Rejected candidate history changed")
    with (ROOT / "REMEDIATION_LEDGER.csv").open(newline="") as stream:
        ledger = {row["finding_id"]: row for row in csv.DictReader(stream)}
    require(set(ledger) == {*(f"D{i}" for i in range(1, 7)), "I1", "I2",
                            *(f"R{i}" for i in range(1, 7)), "C1"}, "Incomplete finding ledger")
    require(all("pending" not in row["status"] and row["residual_limitations"] for row in ledger.values()),
            "Unreconciled finding")
    require(ledger["I1"]["status"] == ledger["R2"]["status"] == "blocked_unresolved",
            "Unresolved isolation findings silently closed")
    return {"implementation_sha256": implementation, "instruments_sha256": instruments,
            "path_b_binary_sha256": binary, "command_records_verified": commands,
            "sealed_files": len(actual), "live_qualification": "blocked"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true", help="Exclusively create the checksum manifest")
    args = parser.parse_args()
    os.umask(0o077)
    actual = files()
    result = verify_references(actual)
    seal = ROOT / "SHA256SUMS.txt"
    if args.seal:
        with seal.open("x") as stream:
            for name, ident in sorted(actual.items()):
                stream.write(ident + "  " + name + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        descriptor = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    expected = {}
    for line in seal.read_text().splitlines():
        ident, name = line.split("  ", 1)
        path = PurePosixPath(name)
        require(SHA.fullmatch(ident) and not path.is_absolute() and ".." not in path.parts
                and name not in expected and name != "SHA256SUMS.txt", "Invalid checksum entry")
        expected[name] = ident
    require(expected == files(), "Checksum coverage or artifact bytes changed")
    result["seal_sha256"] = sha(seal)
    result["status"] = "verified_local_integrity_not_provider_attestation"
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
