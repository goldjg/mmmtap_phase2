"""Deterministic stage identities built from, not written over, the sealed v5 plan."""
from __future__ import annotations

import collections
import copy
import ctypes
import math
from pathlib import Path
import platform
import sys

from phase2.core import ROOT, IntegrityError, digest, load, matrix_counts, write_new
from phase2.integration import PILOT_CASES, validate_v4
from phase2.isolation import sha256_file
from . import VERSION
from .profiles import profile

PACKAGE = Path(__file__).resolve().parent
V5 = ROOT / "forensic_remediation_v1/v5"
STAGES = ("smoke", "pilot", "full")
FILENAMES = {
    "smoke": "SMOKE_MANIFEST.json",
    "pilot": "PILOT_MANIFEST.json",
    "full": "FULL_EXECUTION_MANIFEST.json",
}
REGISTRY = ROOT / ".operator_attempts_v1"
RUNS = ROOT / "operator_runs_v1"
GIB = 1024 ** 3
STORAGE_FLOORS = {"smoke": 256 * 1024 ** 2, "pilot": 512 * 1024 ** 2, "full": 4 * GIB}


def software() -> dict:
    paths = sorted(p for p in PACKAGE.rglob("*.py")
                   if "software_source" not in p.parts and "__pycache__" not in p.parts)
    if any(p.is_symlink() for p in paths):
        raise IntegrityError("Operator source symlink refused")
    library = ctypes.CDLL("libseccomp.so.2")
    libraries = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
                 if "/libseccomp.so." in line}
    if len(libraries) != 1:
        raise IntegrityError("Cannot identify the loaded process-containment library")
    library_path = libraries.pop().resolve()
    return {
        "schema": VERSION + "-software",
        "sources": {str(p.relative_to(PACKAGE)): sha256_file(p) for p in paths},
        "v5_plan_file_sha256": sha256_file(V5 / "execution_plan_v5.json"),
        "v5_instruments_file_sha256": sha256_file(V5 / "instruments/manifest.json"),
        "v5_software_file_sha256": sha256_file(V5 / "instruments/software.v1.json"),
        "python": {"version": sys.version, "path": str(Path(sys.executable).resolve()),
                   "sha256": sha256_file(Path(sys.executable).resolve())},
        "platform": {"system": platform.system(), "architecture": platform.machine(),
                     "kernel_release": platform.release()},
        "process_containment": {
            "libseccomp": str(library_path), "libseccomp_sha256": sha256_file(library_path),
            "libseccomp_api": library.seccomp_api_get(),
            "bwrap_sha256": sha256_file(Path("/usr/bin/bwrap")),
        },
        "runtime_boundary": "host_kernel_readonly_usr_not_hermetic",
    }


def base_plan(*, verify: bool = True) -> dict:
    result = load(V5 / "execution_plan_v5.json")
    if verify:
        validate_v4(result)
    return result


def make_manifest(stage: str, selected_profile: str = "research_controlled", *,
                  base: dict | None = None, implementation: dict | None = None) -> dict:
    if stage not in STAGES:
        raise IntegrityError("Unknown operator stage")
    original = base_plan() if base is None else base
    implementation = software() if implementation is None else implementation
    plan = copy.deepcopy(original)
    execution = {
        "schema": VERSION,
        "stage": stage,
        "profile": profile(selected_profile),
        "base_plan_sha256": original["manifest_sha256"],
        "operator_software_sha256": digest(implementation),
        "selection": ("One token-logging B0 per generator; matched E1/E2 from the Haiku B0."
                      if stage == "smoke" else
                      "Three preregistered provisional strata, baseline variant, every generator and arm."
                      if stage == "pilot" else "All 135 frozen identities, every generator and arm."),
        "pilot_strata": original["config"]["pilot"],
        "max_concurrency": 1,
        "automatic_retries": False,
        "model_fallback": False,
        "budget_unit": "first_adapter_invocation_not_HTTP_requests_provider_executions_or_billing",
        "stage_transition": "never_automatic",
        "purpose": "primary_experiment" if stage == "full" else "transport_or_design_validation_not_primary_results",
        "storage_floor_bytes": STORAGE_FLOORS[stage],
        "credential_sources": {
            "haiku": "COPILOT_GITHUB_TOKEN",
            "gemini": "COPILOT_GITHUB_TOKEN",
            "sol": "owner_only_local_CODEX_auth_json_ChatGPT_only",
            "native_jev": "JEVKEY",
            "carl_jev": "JEVKEY",
        },
    }
    plan["operator_execution"] = execution
    plan["execution_plan_revision"] = "operator-v1-on-v5"
    plan["implementation_sha256"] = digest({
        "v5": original["implementation_sha256"], "operator": digest(implementation)})
    plan["live_execution_enabled"] = False
    plan["live_execution_gate"] = "Only separately authorised operator_execution_v1 stage commands."
    jobs = original["jobs"]
    if stage == "pilot":
        jobs = [j for j in jobs if j["case_id"] in PILOT_CASES and j["variant_id"] == "baseline"]
    elif stage == "smoke":
        candidates = [j for j in jobs if j["case_id"] == "synthetic-token-logging" and j["variant_id"] == "baseline"]
        jobs = [j for j in candidates if j["arm"] == "B0"]
        jobs += [j for j in candidates if j["generator"] == "haiku" and
                 j["kind"] == "adversary" and j["arm"] in ("E1", "E2")]
    plan["jobs"] = []
    ids = {}
    scope = digest(execution)
    for old in jobs:
        job = copy.deepcopy(old)
        old_id = job.pop("job_id")
        job.pop("checkpoint")
        job.pop("parent_checkpoint")
        job["base_v5_job_id"] = old_id
        job["operator_scope_sha256"] = scope
        job["implementation_sha256"] = plan["implementation_sha256"]
        for key in ("assessment_parent", "challenge_parent"):
            job[key] = ids[job[key]] if job[key] else None
        job["dependencies"] = [ids[p] for p in job["dependencies"]]
        ident = digest(job)
        job["job_id"] = ident
        job["checkpoint"] = "checkpoints/" + ident + "/result.json"
        job["parent_checkpoint"] = ("checkpoints/" + job["assessment_parent"] + "/result.json"
                                    if job["assessment_parent"] else None)
        ids[old_id] = ident
        plan["jobs"].append(job)
    plan["counts"] = matrix_counts(plan)
    plan["counts"]["carl_unsupported_jobs"] = 0
    plan["counts"]["by_adapter"] = dict(sorted(collections.Counter(adapter(j) for j in plan["jobs"]).items()))
    plan["counts"]["maximum_adapter_attempts"] = len(plan["jobs"])
    plan["counts"]["strict_qualified_adapters"] = 0
    plan["manifest_sha256"] = digest({k: v for k, v in plan.items() if k != "manifest_sha256"})
    return plan


def adapter(job: dict) -> str:
    return job["generator"] if job["kind"] == "generator" else job["mechanism"]


def validate_manifest(plan: dict) -> None:
    execution = plan["operator_execution"]
    expected = make_manifest(execution["stage"], execution["profile"]["name"])
    if plan != expected:
        raise IntegrityError("Operator plan/source/profile/software drift; old attempts cannot be resumed with changed code")
    seen = {}
    for job in plan["jobs"]:
        for ident in job["dependencies"]:
            parent = seen[ident]
            if any(parent[k] != job[k] for k in ("case_id", "variant_id", "generator", "repetition")):
                raise IntegrityError("Cross-input or cross-generator lineage")
            if parent["arm"] not in ("B0", job["arm"]):
                raise IntegrityError("Cross-arm contamination")
        if job["job_id"] in seen:
            raise IntegrityError("Duplicate job")
        seen[job["job_id"]] = job
    if execution["stage"] == "full" and plan["counts"]["inputs"] != 135:
        raise IntegrityError("Full execution must retain all 135 identities")
    if execution["stage"] == "smoke" and any(n != 1 for n in plan["counts"]["by_adapter"].values()):
        raise IntegrityError("Smoke exceeds one first attempt per adapter")


def publish_manifests() -> dict:
    original = base_plan()
    implementation = software()
    write_new(PACKAGE / "SOFTWARE.json", implementation)
    result = {}
    for stage, name in FILENAMES.items():
        plan = make_manifest(stage, base=original, implementation=implementation)
        write_new(PACKAGE / name, plan)
        result[stage] = {"path": name, "manifest_sha256": plan["manifest_sha256"], **plan["counts"]}
    strict = make_manifest("full", "strict_isolation", base=original, implementation=implementation)
    write_new(PACKAGE / "STRICT_EXECUTION_MANIFEST.json", strict)
    return result


def estimate(plan: dict, max_calls: int, *, input_tokens: int = 4000,
             output_tokens: int = 1000, rates: dict | None = None) -> dict:
    if type(max_calls) is not int or not 1 <= max_calls <= len(plan["jobs"]):
        raise IntegrityError("Call budget must be 1..the number of stage jobs")
    if any(type(n) is not int or n < 1 for n in (input_tokens, output_tokens)):
        raise IntegrityError("Explicit positive token assumptions required")
    counts = plan["counts"]["by_adapter"]
    rows = {}
    rates = rates or {}
    if set(rates) - set(counts):
        raise IntegrityError("Unknown adapter in billing assumptions")
    for name, count in counts.items():
        rate = rates.get(name)
        units = None
        if rate is not None:
            if not isinstance(rate, dict) or set(rate) != {"unit", "input_per_million", "output_per_million", "basis"}:
                raise IntegrityError("Rate needs unit, input_per_million, output_per_million and basis")
            if rate["unit"] not in ("USD", "Copilot_AI_Credits", "ChatGPT_credits") or not rate["basis"]:
                raise IntegrityError("Explicit billing unit and account-specific source required")
            for key in ("input_per_million", "output_per_million"):
                if type(rate[key]) not in (int, float) or not math.isfinite(rate[key]) or rate[key] < 0:
                    raise IntegrityError("Rates must be finite nonnegative numbers")
            units = count * (input_tokens * rate["input_per_million"] +
                             output_tokens * rate["output_per_million"]) / 1_000_000
        rows[name] = {"planned_attempts": count, "assumed_input_tokens": count * input_tokens,
                      "assumed_output_tokens": count * output_tokens,
                      "estimated_charge": units, "rate_assumption": rate}
    return {
        "schema": VERSION + "-budget", "stage": plan["operator_execution"]["stage"],
        "manifest_sha256": plan["manifest_sha256"], "maximum_call_budget": max_calls,
        "complete_matrix_attempts": len(plan["jobs"]), "full_stage_scenario": rows,
        "token_assumptions_per_call": {"input": input_tokens, "output": output_tokens},
        "estimate_kind": "planning_scenario_not_tokenization_measurement_quote_or_charge_cap",
        "budget_is_not_HTTP_or_billing_cap": True,
        "limits": ["CLI internal retries may exceed the harness invocation budget.",
                   "Missing rates remain unknown, never zero.",
                   "A reduced call budget truncates the topological schedule, not a representative sample.",
                   "Fresh sessions change caching; provider rounding, reasoning, auth and failure charges are unknown.",
                   "API token prices cannot be substituted for Copilot AI Credits or ChatGPT subscription usage."],
    }
