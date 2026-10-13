"""Offline readiness assembly and separately authorised single-adapter qualification."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from .core import ROOT, IntegrityError, corpus, digest, json_bytes, load, render_prompt, write_new, assessment, challenge_request
from .integration import (freeze, verify_instruments, plan_v4, validate_v4, ScriptedAdapters, live_invoke_v4)
from .engine import execute, Ledger, now, usage_metrics
from .adapters import Response
from .adjudication import blind_export, checked_records
from .isolation import sha256_file

OUT = ROOT / "forensic_remediation_v1/v5"
QUALIFICATION_REGISTRY = ROOT / ".qualification_attempts_v4"


def assemble(out: Path = OUT) -> dict:
    source, members = corpus()
    if (out / "instruments").exists():
        verify_instruments(out / "instruments")
        frozen = load(out / "instruments/manifest.json")
    else:
        frozen = freeze(out / "instruments", out / "bin/carl-assessment-challenge-v5")
    write_new(out / "frozen_instruments_manifest.json", frozen)
    from .isolation_controls import validate_controls
    isolation = validate_controls(out / "isolation_controls_final", out / "instruments")
    isolation["catalog_evidence"] = {"path":"../adapter_qualification_v1/adapter_readiness_v2.json",
        "sha256":sha256_file(ROOT/"adapter_qualification_v1/adapter_readiness_v2.json"),
        "basis":"prior_authenticated_catalog_not_fresh_inference_or_current_served_identity"}
    write_new(out / "generator_isolation_evidence.json", isolation)
    readiness = {"schema": "mmmtap-offline-readiness-v4", "live_qualified": False,
                 "isolation_evidence_sha256": sha256_file(out / "generator_isolation_evidence.json"),
                 "adapters": {name: {"qualification": "strict_isolation_blocked" if name in
                    ("haiku", "gemini", "sol") else "offline_contract_only_live_unqualified",
                    "live_capable": False} for name in ("haiku", "gemini", "sol", "native_jev", "carl_jev")}}
    plan = plan_v4(out / "instruments", source, readiness)
    validate_v4(plan)
    write_new(out / "execution_plan_v5.json", plan)
    write_new(out / "adapter_readiness_v4.json", readiness)
    rows = []
    for item in source["items"]:
        for gen in ("haiku", "gemini", "sol"):
            for arm in ("B0", "C1", "C2", "C3", "E1", "E2", "E3_NC", "E3_CN"):
                rows.append({"case_id": item["case_id"], "variant_id": item["variant_id"], "generator": gen,
                    "arm": arm, "input_sha256": item["input_sha256"],
                    "contract_feasibility": "supported_path_b_supplied_evidence" if arm in ("E2", "E3_NC", "E3_CN") else "supported",
                    "live_feasibility": "blocked_pending_live_qualification",
                    "requires_authenticated_git": False, "historical_admitted": False,
                    "path_a": "unsupported_contract",
                    "blockers": "generator_isolation_retry_review_and_live_smoke" +
                        (";SystemOne_transport_policy_identity_qualification" if arm.startswith("E") else "")})
    with (out / "arm_feasibility_matrix.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tmp = Path(tempfile.mkdtemp(prefix="mmmtap-full-offline-"))
    run, archive = tmp / "end_to_end_mock", None
    write_new(out / "end_to_end_intent.json", {
        "schema": "mmmtap-full-mock-first-attempt-v1", "mode": "mock_not_research",
        "manifest_sha256": plan["manifest_sha256"], "scratch": str(run),
        "archive_target": "end_to_end_mock.tar.gz", "automatic_retry": False, "live_calls": 0})
    try:
        mock = ScriptedAdapters(plan)
        result = execute(plan, members, run, mode="mock", mock=mock)
        if result["status_counts"] != {"mock_ok": 6885}:
            archive = archive_mock_run(run, out)
            raise IntegrityError("end_to_end_chain_failed; immutable archive retained: " + json.dumps(
                {"summary": result, "archive": archive}))
        before = {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()}
        resume = execute(plan, members, run, mode="mock", mock=mock)
        if resume["new_checkpoints"] != 0 or before != {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()}:
            archive = archive_mock_run(run, out)
            raise IntegrityError("resume_changed_first_attempt; immutable archive retained")
        _, records = checked_records(run)
        packets = blind_export(run, members, out / "blinded_mock", out / "private_unblinding_mock.json")
        actual = [r for r in records.values() if r["parsed"] and "claims" in r["parsed"]]
        archive = archive_mock_run(run, out)
        validation = {"schema": "mmmtap-end-to-end-offline-v2", "mode": "mock_not_research",
                      "chain": "frozen_source_to_scripted_claims_to_mock_SystemOne_to_reconsideration_to_blinded_export",
                      "first_run": result, "resume": resume, "blinded": packets, "archive": archive,
                      "inputs": 135, "generators": 3, "nonempty_assessments": len(actual),
                      "claims_per_assessment": sorted({len(r["parsed"]["claims"]) for r in actual}),
                      "change_actions": sorted({c["action"] for r in actual for c in r["parsed"]["changes"]}),
                      "path_b_policy_replays": sum(j["mechanism"]=="carl_jev" and j["job_id"] in records for j in plan["jobs"]),
                      "live_calls": 0, "adjudicated_improvement": None, "frozen_inputs_preserved": True}
    finally:
        if run.exists() and archive is None:
            if not (out / "end_to_end_mock.tar.gz").exists():
                archive = archive_mock_run(run, out)
            else:
                write_new(out / "end_to_end_archive_failure.json", {
                    "status": "incomplete_archive_do_not_delete_scratch", "scratch": str(run)})
        if not run.exists() or archive is not None and archive["verified_byte_identical"]:
            shutil.rmtree(tmp)
    write_new(out / "end_to_end_validation.json", validation)
    return validation


def archive_mock_run(run: Path, out: Path) -> dict:
    """Keep exact checkpoint bytes without consuming several GiB of shared persistent disk."""
    inventory = {}
    paths = sorted(run.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise IntegrityError("Mock archive symlink refused")
    archive_path = out / "end_to_end_mock.tar.gz"
    with tarfile.open(archive_path, "x:gz", compresslevel=1) as archive:
        for path in paths:
            if path.is_file():
                name = "end_to_end_mock/" + str(path.relative_to(run))
                inventory[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
                archive.add(path, arcname=name, recursive=False)
    observed = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            if not member.isfile() or member.name in observed or member.name not in inventory:
                raise IntegrityError("Unexpected mock archive entry")
            with archive.extractfile(member) as stream:
                observed[member.name] = {"sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
                                         "bytes": member.size}
    if observed != inventory:
        raise IntegrityError("Lossless checkpoint archive verification failed")
    write_new(out / "end_to_end_mock_files.json", {"schema": "mmmtap-archived-checkpoints-v1", "files": inventory})
    return {"file": archive_path.name, "sha256": sha256_file(archive_path), "entries": len(inventory),
            "compression": "gzip_level_1_lossless",
            "uncompressed_bytes": sum(v["bytes"] for v in inventory.values()),
            "file_manifest": "end_to_end_mock_files.json", "verified_byte_identical": True,
            "storage": "lossless_archive_of_mock_first_attempts_after_immutable_resume; no_prior_evidence_removed"}


def qualify(plan: dict, members: dict, out: Path, adapter: str, *, authorised: bool,
            parent_run: Path | None = None) -> dict:
    """Exactly one reserved diagnostic attempt, never a pilot or certification."""
    if not authorised:
        raise ValueError("Separate explicit live authorisation required")
    validate_v4(plan)
    if adapter not in (*plan["config"]["generators"], *plan["config"]["adversaries"]):
        raise ValueError("Unknown adapter")
    if out.exists() or out.is_symlink():
        raise FileExistsError("Qualification output already reserved")
    generator = adapter if adapter in plan["config"]["generators"] else "haiku"
    job = next(j for j in plan["jobs"] if j["case_id"] == "synthetic-token-logging" and
               j["variant_id"] == "baseline" and j["generator"] == generator and j["arm"] == "B0")
    parent_job = job if adapter in plan["config"]["adversaries"] else None
    if parent_job:
        job = next(j for j in plan["jobs"] if j["assessment_parent"] == job["job_id"] and
                   j["arm"] == ("E1" if adapter == "native_jev" else "E2") and j["kind"] == "adversary")
    identity = digest({"manifest_sha256": plan["manifest_sha256"], "adapter": adapter,
                       "purpose": "live_qualification_v4"})
    if QUALIFICATION_REGISTRY.is_symlink():
        raise IntegrityError("Qualification registry symlink refused")
    QUALIFICATION_REGISTRY.mkdir(mode=0o700, exist_ok=True)
    if plan["experimental_attempt"] > 1:
        previous_id = digest({"manifest_sha256": plan["retry_of_manifest_sha256"], "adapter": adapter,
                              "purpose": "live_qualification_v4"})
        if not (QUALIFICATION_REGISTRY / (previous_id + ".json")).is_file():
            raise IntegrityError("Explicit qualification retry requires its prior workspace reservation")
    intent = {"schema": "mmmtap-workspace-qualification-reservation-v1", "attempt_id": identity,
              "adapter": adapter, "mode": "live_qualification_not_experiment", "output": str(out.absolute()),
              "manifest_sha256": plan["manifest_sha256"], "implementation_sha256": plan["implementation_sha256"],
              "instruments_sha256": plan["instruments_sha256"], "job_id": job["job_id"],
              "max_adapter_invocations": 1, "retry_of_manifest_sha256": plan["retry_of_manifest_sha256"], "at": now()}
    reservation_path = QUALIFICATION_REGISTRY / (identity + ".json")
    write_new(reservation_path, intent)
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_new(out / "qualification_intent.json", {**intent, "registry_sha256": sha256_file(reservation_path)})
    folder = out / "checkpoints" / job["job_id"]
    folder.mkdir(mode=0o700, parents=True)
    write_new(out / "run.json", {"manifest_sha256": plan["manifest_sha256"], "mode": "live",
                               "purpose": "qualification_only",
                               "selected_job_ids": [job["job_id"]], "attempt_id": identity})
    write_new(out / "manifest.json", plan)
    ledger = Ledger(out / "ledger.jsonl")
    payload, parent_hashes = None, {p: None for p in job["dependencies"]}
    response = Response(provenance={"transport_attempts": 0, "cli_invocations": 0})
    try:
        source = members[job["input_member"]]
        if parent_job:
            if parent_run is None:
                raise IntegrityError("actual_successful_generator_parent_run_required")
            parent_plan, parents = checked_records(parent_run)
            if parent_plan != plan or parent_job["job_id"] not in parents:
                raise IntegrityError("Parent plan/identity mismatch")
            parent = parents[parent_job["job_id"]]
            if parent["mode"] != "live" or parent["status"] != "ok" or not parent["parsed"]["claims"]:
                raise IntegrityError("A real valid nonempty generator assessment is required")
            if adapter == "carl_jev":
                from .path_b import build_request
                payload = build_request(plan, job, parent_run, members, json_bytes(plan["source_manifest"]), identity)
            else:
                payload = challenge_request(plan, job, source, parent["parsed"])
            destination = out / "checkpoints" / parent_job["job_id"]
            destination.mkdir(mode=0o700)
            for name in ("intent.json", "payload.json", "raw.json", "result.json"):
                shutil.copyfile(parent_run / "checkpoints" / parent_job["job_id"] / name, destination / name)
            ledger.append({"event": "started", "job_id": parent_job["job_id"],
                           "intent_sha256": sha256_file(destination / "intent.json"), "budget_reservation": 0,
                           "source": str(parent_run), "reason": "immutable_external_parent_copy_no_inference"})
            ledger.append({"event": "completed", "job_id": parent_job["job_id"],
                           "result_sha256": sha256_file(destination / "result.json")})
            parent_hashes[parent_job["job_id"]] = sha256_file(destination / "result.json")
        else:
            payload = render_prompt(plan, job, source, None, [], None)
            response = Response(error="strict_generator_isolation_blocked",
                                provenance={"transport_attempts": 0, "cli_invocations": 0, "live_calls": 0})
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        response.error = "preparation_failed:" + type(exc).__name__
        write_new(out / "failure.json", {"error": response.error, "transport_attempts": 0,
                                         "phase": "preparation", "attempt_id": identity})
    write_new(folder / "intent.json", {"job": job, "mode": "live", "manifest_sha256": plan["manifest_sha256"],
                                     "attempt_id": identity, "parent_checkpoint_sha256": parent_hashes,
                                     "registry_sha256": sha256_file(reservation_path),
                                     "preparation_reserved_by": str(reservation_path)})
    ledger.append({"event": "started", "job_id": job["job_id"], "intent_sha256": sha256_file(folder / "intent.json"),
                   "budget_reservation": 1})
    write_new(folder / "payload.json", {"payload": payload, "parent_checkpoint_sha256": parent_hashes})
    if not response.error:
        try:
            response = live_invoke_v4(plan, job, payload, authorised=True)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            response = Response(error="adapter_exception:" + type(exc).__name__,
                                provenance={"transport_attempts": None, "execution_outcome": "unknown_no_retry"})
    write_new(folder / "raw.json", response.record())
    parsed, error = None, response.error
    if not error:
        if job["kind"] == "generator":
            parsed, error = assessment(response.message.decode(), job)
        else:
            try:
                parsed = json.loads(response.message)
                if not isinstance(parsed, dict):
                    raise ValueError("adversary_object_required")
            except (ValueError, UnicodeError) as exc:
                parsed, error = None, "parser_failure:" + type(exc).__name__
    record = {"schema": "mmmtap-checkpoint-v1", "mode": "live", "job_id": job["job_id"],
              "manifest_sha256": plan["manifest_sha256"], "input_sha256": job["input_sha256"],
              "attempt_id": identity, "implementation_sha256": plan["implementation_sha256"],
              "instruments_sha256": plan["instruments_sha256"],
              "status": "ok" if parsed is not None and not error else "execution_failed",
              "schema_valid": parsed is not None, "parsed": parsed, "reason": error,
              "parent_checkpoint_sha256": parent_hashes, "correctness": "not_adjudicated",
              "metrics": usage_metrics(response, "live", plan["config"]),
              "artifact_sha256": {n: sha256_file(folder/n) for n in ("intent.json","payload.json","raw.json")}}
    write_new(folder / "result.json", record)
    ledger.append({"event": "completed", "job_id": job["job_id"], "result_sha256": sha256_file(folder/"result.json")})
    result = {"adapter": adapter, "parse_status": record["status"], "attempt_id": identity,
                "live_qualified": False, "operator_review_required": True,
                "provider_identity": response.provenance.get("provider_confirmed_model"),
                "raw_sha256": sha256_file(folder/"raw.json"), "automatic_pilot_approval": False,
                "checkpoint_sha256": sha256_file(folder / "result.json"),
                "transport_attempts": response.provenance.get("transport_attempts")}
    write_new(out / "qualification_result.json", result)
    write_new(QUALIFICATION_REGISTRY / (identity + ".result.json"), result)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("assemble")
    v = sub.add_parser("validate")
    v.add_argument("--manifest", type=Path, default=OUT/"execution_plan_v5.json")
    q = sub.add_parser("qualify")
    q.add_argument("--manifest", type=Path, default=OUT/"execution_plan_v5.json")
    q.add_argument("--adapter", required=True)
    q.add_argument("--out", required=True, type=Path)
    q.add_argument("--parent-run", type=Path)
    q.add_argument("--authorize-live", action="store_true")
    args=parser.parse_args()
    if args.command == "assemble":
        print(json.dumps(assemble(), indent=2))
    elif args.command == "validate":
        validate_v4(load(args.manifest))
        print("validated: proposed instruments; live execution disabled")
    else:
        if not args.authorize_live:
            parser.error("Separate explicit live authorisation required")
        _, members = corpus()
        print(json.dumps(qualify(load(args.manifest), members, args.out, args.adapter,
                                 authorised=args.authorize_live, parent_run=args.parent_run)))


if __name__ == "__main__":
    main()
