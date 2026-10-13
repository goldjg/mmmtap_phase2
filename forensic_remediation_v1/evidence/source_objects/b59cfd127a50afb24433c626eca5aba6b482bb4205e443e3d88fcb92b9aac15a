"""Offline readiness assembly and separately authorised single-adapter qualification."""
from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path
import shutil

from .core import ROOT, corpus, digest, json_bytes, load, render_prompt, write_new, assessment, challenge_request
from .integration import (PILOT_CASES, freeze, plan_v3, validate_v3, ScriptedAdapters, live_invoke_v3)
from .engine import execute, Ledger, now
from .adjudication import blind_export, checked_records
from .isolation import sha256_file

OUT = ROOT / "integration_readiness_v1"


def assemble(out: Path = OUT) -> dict:
    source, members = corpus()
    frozen = freeze(out / "instruments", out / "bin/carl-assessment-challenge-v2")
    write_new(out / "frozen_instruments_manifest.json", frozen)
    isolation = load(out / "isolation_controls_final/summary.json")
    prior = {}
    for name in ("cop_v1flags", "cop_placeholder", "cop_excluded", "cdx_v1_overrides"):
        origin = ROOT/".runtime_probe"/name/"capture"
        target = out/"prior_diagnostics"/name
        target.mkdir(parents=True)
        for filename in ("requests.jsonl", "stdout.bin", "stderr.bin", "outcome.json"):
            if (origin/filename).is_file():
                shutil.copyfile(origin/filename, target/filename)
        prior[name] = {p.name: sha256_file(p) for p in target.iterdir()}
    isolation["prior_diagnostics_sha256"] = prior
    isolation["catalog_evidence"] = {"path":"../adapter_qualification_v1/adapter_readiness_v2.json",
        "sha256":sha256_file(ROOT/"adapter_qualification_v1/adapter_readiness_v2.json"),
        "basis":"prior_authenticated_catalog_not_fresh_inference_or_current_served_identity"}
    write_new(out / "generator_isolation_evidence.json", isolation)
    readiness = {"schema": "mmmtap-offline-readiness-v3", "live_qualified": False,
                 "isolation_evidence_sha256": sha256_file(out / "generator_isolation_evidence.json"),
                 "adapters": {name: {"qualification": "not_live_qualified", "live_capable": False}
                              for name in ("haiku", "gemini", "sol", "native_jev", "carl_jev")}}
    plan = plan_v3(out / "instruments", source, readiness)
    validate_v3(plan)
    write_new(out / "execution_plan_v3.json", plan)
    write_new(out / "adapter_readiness_v3.json", readiness)
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
    mock = ScriptedAdapters(plan)
    run = out / "end_to_end_mock"
    selected = {(c, "baseline") for c in PILOT_CASES}
    result = execute(plan, members, run, mode="mock", selected_inputs=selected, mock=mock)
    if result["status_counts"] != {"mock_ok": 153}:
        raise RuntimeError("end_to_end_chain_failed:" + json.dumps(result))
    before = {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()}
    resume = execute(plan, members, run, mode="mock", selected_inputs=selected, mock=mock)
    if resume["new_checkpoints"] != 0 or before != {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()}:
        raise RuntimeError("resume_changed_first_attempt")
    _, records = checked_records(run)
    packets = blind_export(run, members, out / "blinded_mock", out / "private_unblinding_mock.json")
    actual = [r for r in records.values() if r["parsed"] and "claims" in r["parsed"]]
    validation = {"schema": "mmmtap-end-to-end-offline-v1", "mode": "mock_not_research",
                  "chain": "frozen_source_to_scripted_claims_to_mock_SystemOne_to_reconsideration_to_blinded_export",
                  "first_run": result, "resume": resume, "blinded": packets,
                  "inputs": 3, "generators": 3, "nonempty_assessments": len(actual),
                  "claims_per_assessment": sorted({len(r["parsed"]["claims"]) for r in actual}),
                  "path_b_policy_replays": sum(j["mechanism"]=="carl_jev" and j["job_id"] in records for j in plan["jobs"]),
                  "live_calls": 0, "adjudicated_improvement": None, "frozen_inputs_preserved": True}
    write_new(out / "end_to_end_validation.json", validation)
    return validation


def qualify(plan: dict, members: dict, out: Path, adapter: str, *, authorised: bool,
            parent_run: Path | None = None) -> dict:
    """Exactly one reserved diagnostic attempt, never a pilot or certification."""
    if not authorised:
        raise ValueError("Separate explicit live authorisation required")
    validate_v3(plan)
    if adapter not in (*plan["config"]["generators"], *plan["config"]["adversaries"]):
        raise ValueError("Unknown adapter")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_new(out / "qualification_intent.json", {"adapter": adapter, "mode": "live_qualification_not_experiment",
        "manifest_sha256": plan["manifest_sha256"], "max_adapter_invocations": 1, "at": now()})
    generator = adapter if adapter in plan["config"]["generators"] else "haiku"
    job = next(j for j in plan["jobs"] if j["case_id"] == "synthetic-token-logging" and
               j["variant_id"] == "baseline" and j["generator"] == generator and j["arm"] == "B0")
    source = members[job["input_member"]]
    parent_job = None
    if adapter in plan["config"]["generators"]:
        payload = render_prompt(plan, job, source, None, [], None)
    else:
        if parent_run is None:
            write_new(out / "failure.json", {"error": "actual_successful_generator_parent_run_required", "calls": 0})
            raise ValueError("Actual generator parent run required")
        parent_plan, parents = checked_records(parent_run)
        if parent_plan != plan or job["job_id"] not in parents:
            raise ValueError("Parent plan/identity mismatch")
        parent = parents[job["job_id"]]
        if parent["mode"] != "live" or parent["status"] != "ok" or not parent["parsed"]["claims"]:
            raise ValueError("A real, valid nonempty generator assessment is required")
        arm = "E1" if adapter == "native_jev" else "E2"
        parent_job = job
        job = next(j for j in plan["jobs"] if j["assessment_parent"] == job["job_id"] and
                   j["arm"] == arm and j["kind"] == "adversary")
        if adapter == "carl_jev":
            from .path_b import build_request
            payload = build_request(plan, job, parent_run, members, json_bytes(plan["source_manifest"]), "qual-" + job["job_id"])
        else:
            payload = challenge_request(plan, job, source, parent["parsed"])
    folder = out / "checkpoints" / job["job_id"]
    folder.mkdir(mode=0o700, parents=True)
    write_new(out / "run.json", {"manifest_sha256": plan["manifest_sha256"], "mode": "live",
                               "purpose": "qualification_only",
                               "selected_job_ids": ([parent_job["job_id"]] if parent_job else []) + [job["job_id"]]})
    write_new(out / "manifest.json", plan)
    ledger = Ledger(out / "ledger.jsonl")
    if parent_job:
        destination = out / "checkpoints" / parent_job["job_id"]
        destination.mkdir()
        for name in ("intent.json", "payload.json", "raw.json", "result.json"):
            shutil.copyfile(parent_run / "checkpoints" / parent_job["job_id"] / name, destination / name)
        ledger.append({"event": "started", "job_id": parent_job["job_id"],
                       "intent_sha256": sha256_file(destination / "intent.json"), "budget_reservation": 0,
                       "source": str(parent_run), "reason": "immutable_external_parent_copy_no_inference"})
        ledger.append({"event": "completed", "job_id": parent_job["job_id"],
                       "result_sha256": sha256_file(destination / "result.json")})
    parent_hashes = {} if job["kind"] == "generator" else {
        job["assessment_parent"]: sha256_file(parent_run / job["parent_checkpoint"])}
    write_new(folder / "intent.json", {"job": job, "mode": "live", "manifest_sha256": plan["manifest_sha256"],
                                     "parent_checkpoint_sha256": parent_hashes})
    ledger.append({"event": "started", "job_id": job["job_id"], "intent_sha256": sha256_file(folder / "intent.json"),
                   "budget_reservation": 1})
    write_new(folder / "payload.json", {"payload": payload})
    try:
        response = live_invoke_v3(plan, job, payload, authorised=True)
    except (OSError, ValueError, RuntimeError) as exc:
        from .adapters import Response
        response = Response(error="adapter_exception:" + type(exc).__name__)
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
              "status": "ok" if parsed is not None and not error else "execution_failed",
              "schema_valid": parsed is not None, "parsed": parsed, "reason": error,
              "parent_checkpoint_sha256": parent_hashes, "correctness": "not_adjudicated",
              "artifact_sha256": {n: sha256_file(folder/n) for n in ("intent.json","payload.json","raw.json")}}
    write_new(folder / "result.json", record)
    ledger.append({"event": "completed", "job_id": job["job_id"], "result_sha256": sha256_file(folder/"result.json")})
    write_new(out / "qualification_result.json", {"adapter": adapter, "parse_status": record["status"],
                "live_qualified": False, "operator_review_required": True,
                "provider_identity": response.provenance.get("provider_confirmed_model"),
                "raw_sha256": sha256_file(folder/"raw.json"), "automatic_pilot_approval": False})
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("assemble")
    v = sub.add_parser("validate")
    v.add_argument("--manifest", type=Path, default=OUT/"execution_plan_v3.json")
    q = sub.add_parser("qualify")
    q.add_argument("--manifest", type=Path, default=OUT/"execution_plan_v3.json")
    q.add_argument("--adapter", required=True)
    q.add_argument("--out", required=True, type=Path)
    q.add_argument("--parent-run", type=Path)
    q.add_argument("--authorize-live", action="store_true")
    args=parser.parse_args()
    if args.command == "assemble":
        print(json.dumps(assemble(), indent=2))
    elif args.command == "validate":
        validate_v3(load(args.manifest))
        print("validated: proposed instruments; live execution disabled")
    else:
        if not args.authorize_live:
            parser.error("Separate explicit live authorisation required")
        _, members = corpus()
        print(json.dumps(qualify(load(args.manifest), members, args.out, args.adapter,
                                 authorised=args.authorize_live, parent_run=args.parent_run)))


if __name__ == "__main__":
    main()
