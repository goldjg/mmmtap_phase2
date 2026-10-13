"""Publish qualification observations without inference or changing first attempts."""
from __future__ import annotations

import base64
import csv
import io
import json
from pathlib import Path

from historical_extractor.archive import IntegrityError, file_hash
from .adapters import parse_cli_events
from .core import ROOT, assessment, corpus, load, write_new
from .engine import Ledger
from .qualification import ADAPTERS, SOURCE, audit_plan


def copilot_observations(directory: Path, manifest: dict) -> dict:
    folder = directory / "attempts/haiku"
    raw = load(folder / "raw.json")
    stdout = base64.b64decode(raw["stdout"], validate=True)
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    checkpoints = [e["data"] for e in events if e["type"] == "session.usage_checkpoint"]
    checkpoint = checkpoints[-1]
    contexts = [details for conversation in checkpoint.get("promptCacheBreakState", [])
                for details in conversation.get("models", {}).values()]
    metrics = checkpoint["accountingSnapshot"]["modelMetrics"]
    messages = [e["data"] for e in events if e["type"] == "assistant.message"]
    if len(messages) != 1:
        raise IntegrityError("Unexpected number of live assistant messages")
    parsed, error = assessment(messages[0]["content"], manifest["entries"]["haiku"]["job"])
    try:
        parse_cli_events(stdout, "github_copilot_cli")
        policy_error = None
    except ValueError as exc:
        policy_error = str(exc)
    return {
        "source_raw_sha256": file_hash(folder / "raw.json"),
        "initial_result_sha256": file_hash(folder / "result.json"),
        "analysis_mode": "offline_reparse_of_preserved_first_attempt_not_retry",
        "assessment_schema_valid": parsed is not None, "assessment_parser_error": error,
        "current_strict_parser_error": policy_error,
        "requested_model": manifest["entries"]["haiku"]["requested_model"],
        "cli_reported_model": messages[0].get("model"), "provider_confirmed_model": None,
        "provider_id": messages[0].get("providerId"),
        "model_call_starts": sum(e["type"] == "model.call_start" for e in events),
        "model_call_successes": sum(e["type"] == "model.call_final_result" and
                                    e["data"].get("result") == "success" for e in events),
        "tool_execution_events": sum(e["type"].startswith("tool.execution") for e in events),
        "retry_events": sum("retry" in e["type"] for e in events),
        "tool_requests": sum(len(e["data"].get("toolRequests", [])) for e in events if e["type"] == "assistant.message"),
        "exposed_tool_counts": [c["tool_count"] for c in contexts],
        "exposed_tools": sorted({t["name"] for c in contexts for t in c["tools"]}),
        "conversation_message_counts": [c["conversation"]["message_count"] for c in contexts],
        "reported_reasoning_efforts": sorted({c["reasoning_effort"] for c in contexts}),
        "model_metrics": metrics,
        "reported_code_changes": checkpoint["accountingSnapshot"]["codeChanges"],
        "source_quote_matches": [q in SOURCE.decode() for c in parsed["claims"] for q in c["evidence_quotes"]] if parsed else [],
        "identity_limitations": "CLI model and routing telemetry, not independent upstream version attestation.",
    }


def preserved_evidence(directory: Path) -> dict:
    amended = {}
    unchanged = 0
    for line in (ROOT / "HARNESS_SHA256SUMS.txt").read_text().splitlines():
        expected, name = line.split("  ", 1)
        current = file_hash(ROOT / name)
        if current != expected:
            if name != "phase2/adapters.py":
                raise IntegrityError("Unexpected change to prior evidence: " + name)
            backup = directory / "offline/original_implementation/adapters.py"
            if file_hash(backup) != expected:
                raise IntegrityError("Original implementation backup mismatch")
            amended[name] = {"original_sha256": expected, "current_sha256": current,
                             "original_copy": str(backup.relative_to(directory))}
        else:
            unchanged += 1
    historical = ROOT / "historical_extraction_v1"
    count = 0
    for line in (historical / "SHA256SUMS.txt").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if file_hash(historical / name) != expected:
            raise IntegrityError("Historical extraction changed")
        count += 1
    return {"original_snapshot_files_unchanged": unchanged, "amended_source_files": amended,
            "historical_output_files_unchanged": count,
            "historical_manifest_sha256": file_hash(historical / "SHA256SUMS.txt")}


def publish(directory: Path) -> None:
    manifest = load(directory / "live_smoke_manifest.json")
    ledger = Ledger(directory / "attempts/ledger.jsonl")
    reservations = [e for e in ledger.events if e["event"] == "reserved"]
    if len(reservations) != 2 or {e["adapter"] for e in reservations} != {"native_jev", "haiku"}:
        raise IntegrityError("Unexpected live invocation set; report must be reviewed")
    for name, expected in manifest["software_sha256"].items():
        if file_hash(directory / "offline/smoke_implementation" / name) != expected:
            raise IntegrityError("Smoke implementation snapshot changed")
    source, _ = corpus()
    plan = load(ROOT / "execution_plan_v2.json")
    audit = audit_plan(plan, source)
    haiku = copilot_observations(directory, manifest)
    if haiku["exposed_tool_counts"] != [21] or haiku["model_call_starts"] != 1:
        raise IntegrityError("Unexpected live tool/request evidence")
    native = load(directory / "attempts/native_jev/result.json")
    if native["status"] != "ok" or native["transport_attempts"] != 1 or native["provider_confirmed_model"] != "jev-1.13.0":
        raise IntegrityError("Native live evidence not qualified")
    evidence = preserved_evidence(directory)
    write_new(directory / "evidence_preservation.json", evidence)
    write_new(directory / "haiku_offline_reanalysis.json", haiku)
    write_new(directory / "comparability_audit.json", audit)
    reasons = {
        "haiku": "Real response, but 21 tools exposed despite empty allowlist; original parser failed; not safe for experimental execution.",
        "gemini": "Advertised and authenticated catalog available; smoke skipped after shared Copilot tool-filter safety failure.",
        "sol": "Blocked offline: reserved built-in provider retry overrides rejected; /tmp helper setup fails; negative instruction-isolation control failed.",
        "native_jev": "One real authenticated source-grounded noul/choice evaluation, resolved jev-1.13.0; alias pinning and large-state capacity remain unqualified.",
        "carl_jev": "All primary inputs lack authenticated matching Git bindings; real Git candidates remain pending with unqualified provider bridge/policy/provenance.",
    }
    outcomes = {"haiku": "blocked", "gemini": "blocked", "sol": "blocked",
                "native_jev": "qualified_with_limitations", "carl_jev": "unsupported_contract"}
    catalog = load(directory / "offline/copilot_acp_catalog.json")
    advertised = next(r["result"]["models"]["availableModels"] for r in catalog["responses"] if r.get("id") == 2)
    versions = {
        "haiku": (directory / "offline/copilot_version.stdout.txt").read_text().strip(),
        "gemini": (directory / "offline/copilot_version.stdout.txt").read_text().strip(),
        "sol": (directory / "offline/codex_version.stdout.txt").read_text().strip(),
        "native_jev": "HTTPS SystemOne API /v1/systemone",
        "carl_jev": (directory / "offline/carl_version.stdout.txt").read_text().strip(),
    }
    readiness = {}
    identities = {}
    results = {}
    for name in ADAPTERS:
        entry = manifest["entries"][name]
        folder = directory / "attempts" / name
        attempted = folder.exists()
        first = load(folder / "result.json") if attempted else None
        if attempted:
            if first["raw_sha256"] != file_hash(folder / "raw.json"):
                raise IntegrityError("First-attempt raw changed")
            completion = next(e for e in ledger.events if e["event"] == "completed" and e["adapter"] == name)
            if completion["result_sha256"] != file_hash(folder / "result.json"):
                raise IntegrityError("First-attempt result changed")
        results[name] = {"attempted": attempted, "qualification": outcomes[name], "reason": reasons[name],
                         "first_attempt": first, "retry_count": 0}
        identities[name] = {
            "requested_model": entry["requested_model"],
            "cli_reported_model": haiku["cli_reported_model"] if name == "haiku" else None,
            "provider_confirmed_model": native["provider_confirmed_model"] if name == "native_jev" else None,
            "reasoning_requested": manifest["config"]["generators"].get(name, {}).get("reasoning_effort"),
            "reasoning_reported": haiku["reported_reasoning_efforts"] if name == "haiku" else None,
            "reasoning_provider_confirmed": None,
            "evidence": "provider response" if name == "native_jev" else
                        "CLI response/routing/accounting" if name == "haiku" else
                        "authenticated advertised catalog, no inference" if name == "gemini" else
                        "local model cache, no inference" if name == "sol" else "unverified model alias; no inference",
        }
        readiness[name] = {
            "qualification": outcomes[name], "reason": reasons[name], "cli_version": versions[name],
            "binary_sha256": entry["binary_sha256"], **identities[name],
            "experimental_live_ready": False,
            "credential_source": "gh auth token in memory; isolated COPILOT_GITHUB_TOKEN" if name in ("haiku", "gemini")
                                 else "local ChatGPT auth file, not live-tested" if name == "sol" else "JEVKEY environment",
            "credentials_recorded": False,
        }
    write_new(directory / "adapter_readiness_v2.json", {
        "schema": "mmmtap-adapter-qualification-readiness-v2", "adapters": readiness,
        "advertised_gemini_models": [m for m in advertised if m["modelId"].startswith("gemini-")],
        "live_invocations": 2, "pilot_authorised": False, "historical_cases_admitted": 0,
        "note": "Qualification outcomes are not the old harness's smoke-approval receipts.",
    })
    write_new(directory / "model_identity_provenance.json", {
        "schema": "mmmtap-model-identity-provenance-v1", "adapters": identities,
        "self_reported_assessment_identity_used_as_proof": False,
    })
    write_new(directory / "live_smoke_results.json", {
        "schema": "mmmtap-live-qualification-results-v1", "manifest_sha256": manifest["manifest_sha256"],
        "authorised_maximum": 5, "actual_live_invocations": 2, "observed_provider_evaluations": 2,
        "automatic_harness_retries": 0, "pilot_calls": 0, "adapters": results,
        "haiku_offline_reanalysis": "haiku_offline_reanalysis.json",
        "stopping_reason": "Gemini skipped after Haiku exposed unsafe shared tool-filter semantics.",
        "metadata_calls": "Authenticated Copilot ACP initialize/session-new: zero prompt requests. Other offline commands captured under offline/.",
        "limitations": "No claim about unobservable provider-internal computation/retries. Haiku telemetry recorded one model call and one billed request.",
    })
    buffer = io.StringIO()
    fields = ["arm", "generator", "generator_jobs", "native_jev_jobs", "carl_jev_jobs",
              "contract_executable_jobs", "unsupported_contract_jobs", "blocked_descendants",
              "currently_executable", "blocker"]
    writer = csv.DictWriter(buffer, fields)
    writer.writeheader()
    for arm, counts in audit["by_arm"].items():
        for generator in ("haiku", "gemini", "sol"):
            jobs = [j for j in plan["jobs"] if j["arm"] == arm and j["generator"] == generator]
            writer.writerow({
                "arm": arm, "generator": generator,
                "generator_jobs": sum(j["kind"] == "generator" for j in jobs),
                "native_jev_jobs": sum(j["mechanism"] == "native_jev" for j in jobs),
                "carl_jev_jobs": sum(j["mechanism"] == "carl_jev" for j in jobs),
                "contract_executable_jobs": counts.get("contract_executable", 0) // 3,
                "unsupported_contract_jobs": counts.get("unsupported_contract", 0) // 3,
                "blocked_descendants": counts.get("blocked_parent", 0) // 3,
                "currently_executable": "false",
                "blocker": reasons[generator] + (" Authenticated Git evidence also required." if arm in ("E2", "E3_NC", "E3_CN") else ""),
            })
    with (directory / "arm_feasibility_matrix.csv").open("x") as stream:
        stream.write(buffer.getvalue())


if __name__ == "__main__":
    publish(ROOT / "adapter_qualification_v1")
    print("Qualification observations published without further inference.")
