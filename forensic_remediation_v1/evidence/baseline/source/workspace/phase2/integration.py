"""Versioned proposed instruments, v3 planning and explicitly scripted offline adapters."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from historical_extractor.extract import strict_json

from .core import (ROOT, PACKAGE, IntegrityError, challenge_request, corpus, digest, experiment_plan,
                   json_bytes, load, matrix_counts, read_config, write_new)
from .isolation import sha256_file
from .adapters import Response, NativeJEVAdapter, parse_systemone
from .adapters_v2 import GeneratorAdapter, PathBAdapter, copilot_argv, codex_argv

CONTRACT = "supplied_frozen_text_assessment_challenge_v1"
VERSION = "mmmtap-integration-v3"
PILOT_CASES = {"synthetic-benign-docs", "synthetic-token-logging", "synthetic-public-metadata"}


def freeze(directory: Path, binary: Path) -> dict:
    """Create new instruments; never amend a frozen version in place."""
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    cfg = copy.deepcopy(read_config())
    cfg["schema"] = "mmmtap-phase2-config-v2"
    cfg["instrument_status"] = "proposed_frozen_for_qualification_not_experimental_approval"
    cfg["isolation_runtime"] = {"binary": "/usr/bin/bwrap", "sha256": sha256_file(Path("/usr/bin/bwrap")),
                               "version": "mmmtap-p2-bwrap-isolation-v1"}
    copilot = Path.home() / ".local/bin/copilot"
    codex = Path.home() / ".codex/packages/standalone/releases/0.162.1-aarch64-unknown-linux-musl/bin/codex"
    for name, spec in cfg["generators"].items():
        spec["binary"] = str(codex if name == "sol" else copilot)
        spec["binary_sha256"] = sha256_file(Path(spec["binary"]))
        spec["argv"] = codex_argv() if name == "sol" else copilot_argv(spec["model_id"])
        spec["identity_basis"] = "requested_or_client_reported_not_provider_attestation"
    policy_root = directory / "carl_policy"
    for p in sorted((ROOT / "path_b_policy_v1").rglob("*")):
        if p.is_file():
            dst = policy_root / p.relative_to(ROOT / "path_b_policy_v1")
            dst.parent.mkdir(parents=True, exist_ok=True)
            raw = p.read_bytes()
            # New independent version, retaining the exact old numeric policy semantics.
            if p.suffix == ".md":
                raw = raw.replace(b"OFFLINE FIXTURE ONLY.", b"PROPOSED INSTRUMENT V1; NOT APPROVED FOR EXPERIMENTAL USE.")
            dst.write_bytes(raw)
    cfg["adversaries"]["carl_jev"] = {
        "provider": "carl_assessment_challenge_v1", "binary": str(binary.resolve()),
        "binary_sha256": sha256_file(binary), "model_id": cfg["adversaries"]["native_jev"]["model_id"],
        "key_env": "JEVKEY", "endpoint": cfg["adversaries"]["native_jev"]["endpoint"],
        "evidence_contracts": [CONTRACT], "policy_root": str(policy_root.resolve()),
        "policy_files": {str(p.relative_to(policy_root)): sha256_file(p)
                         for p in policy_root.rglob("*") if p.is_file()}}
    cfg["policy"]["carl_text_adapter_validated"] = False
    cfg["policy"]["carl_path_b_offline_contract"] = True
    cfg["policy"]["live_qualified"] = False
    write_new(directory / "config.v2.json", cfg)
    templates = load(PACKAGE / "prompts.v1.json")
    write_new(directory / "prompts.v1.snapshot.json", templates)
    a = {"case_id": "schema", "variant_id": "baseline", "claims": [{"claim_id": "c"}]}
    native = challenge_request({"config": cfg, "prompt_templates": templates},
        {"mechanism": "native_jev", "input_sha256": sha256_file(PACKAGE / "__init__.py")},
        (PACKAGE / "__init__.py").read_bytes(), a)
    write_new(directory / "questions.v1.json", {
        "schema": "mmmtap-matched-question-pack-v1", "fixed": {k: v for k, v in native["questions"].items()
                                                               if not k.startswith("claim_")},
        "per_claim": {"id_format": "claim_%04d_supported", "type": "noul",
                     "instructions_format": "Is assessment.claims[%d] materially supported by exact source evidence?"},
        "task": templates["native_jev"], "change_from_v1": "none"})
    write_new(directory / "evidence_schema.v1.json", {
        "schema": "mmmtap-path-b-evidence-contract-v1", "contract": CONTRACT,
        "request_schema": "carl-assessment-challenge-v1-request", "authenticated_git": False,
        "deployment_state": "not_asserted", "origin_kind": "archive_member",
        "bindings": ["source", "archive", "member", "manifest", "assessment", "parent", "native_request"],
        "executable_validator": "cARL internal/assessment/request.go; frozen source snapshot below",
        "capacity": {"source_bytes": 1048576, "claims": 128, "artifact_bytes": 8388608}})
    # Include the executable evidence validator, not only a descriptive shape.
    croot = ROOT.parent / "cARL-semantic-eval"
    for path in sorted((croot / "internal/assessment").glob("*.go")):
        target = directory / "carl_source" / path.name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(path.read_bytes())
    files = {str(p.relative_to(directory)): sha256_file(p) for p in sorted(directory.rglob("*")) if p.is_file()}
    manifest = {"schema": "mmmtap-frozen-instruments-v1", "status": cfg["instrument_status"],
                "files": files, "live_calls": 0, "question_change": "none",
                "policy_change": "new proposed copy of offline fixture; same thresholds; not PI approval"}
    write_new(directory / "manifest.json", manifest)
    return manifest


def verify_instruments(directory: Path) -> dict:
    manifest = load(directory / "manifest.json")
    actual = {str(p.relative_to(directory)): sha256_file(p) for p in directory.rglob("*")
              if p.is_file() and p != directory / "manifest.json"}
    if actual != manifest["files"]:
        raise IntegrityError("Frozen instruments changed")
    cfg = load(directory / "config.v2.json")
    if (cfg["schema"] != "mmmtap-phase2-config-v2" or cfg["partition"] != "p1_014_frozen"
            or cfg["policy"]["historical_candidates_admitted"] is not False):
        raise IntegrityError("Unapproved partition or configuration")
    for spec in cfg["generators"].values():
        if sha256_file(Path(spec["binary"])) != spec["binary_sha256"]:
            raise IntegrityError("Generator binary changed")
    spec = cfg["adversaries"]["carl_jev"]
    if sha256_file(Path(cfg["isolation_runtime"]["binary"])) != cfg["isolation_runtime"]["sha256"]:
        raise IntegrityError("Isolation runtime changed")
    if sha256_file(Path(spec["binary"])) != spec["binary_sha256"]:
        raise IntegrityError("Path B binary changed")
    return cfg


def plan_v3(directory: Path, source: dict, readiness: dict) -> dict:
    cfg = verify_instruments(directory)
    plan = experiment_plan(cfg, source, readiness)
    plan["integration_version"] = VERSION
    plan["instruments_directory"] = str(directory.resolve())
    plan["instruments_sha256"] = sha256_file(directory / "manifest.json")
    plan["source_manifest"] = source
    plan["supersedes"] = {"file": "execution_plan_v2.json", "sha256": sha256_file(ROOT / "execution_plan_v2.json"),
                          "status": "superseded_no_rewrite"}
    plan["live_execution_enabled"] = False
    plan["design_amendment"] += " Path B supplied evidence replaces Path A only in this proposed new plan."
    ids = {}
    for old in plan["jobs"]:
        previous_id = old.pop("job_id")
        for key in ("checkpoint", "parent_checkpoint"):
            old.pop(key)
        for key in ("assessment_parent", "challenge_parent"):
            old[key] = ids[old[key]] if old[key] else None
        old["dependencies"] = [ids[d] for d in old["dependencies"]]
        old["instruments_sha256"] = plan["instruments_sha256"]
        old["adversary_contract"] = CONTRACT if old["mechanism"] == "carl_jev" else old["evidence_contract"]
        if old["mechanism"] == "carl_jev":
            old["template_key"] = "native_jev"
            old["prompt_template_sha256"] = digest([plan["prompt_templates"]["boundary"], plan["prompt_templates"]["native_jev"]])
        ident = digest(old)
        old["job_id"] = ident
        old["checkpoint"] = "checkpoints/" + ident + "/result.json"
        old["parent_checkpoint"] = "checkpoints/" + old["assessment_parent"] + "/result.json" if old["assessment_parent"] else None
        ids[previous_id] = ident
    plan["counts"] = matrix_counts(plan)
    plan["counts"]["carl_unsupported_jobs"] = 0
    plan["counts"]["live_unqualified_jobs"] = len(plan["jobs"])
    plan["manifest_sha256"] = digest({k: v for k, v in plan.items() if k != "manifest_sha256"})
    return plan


def validate_v3(plan: dict) -> None:
    if plan.get("integration_version") != VERSION:
        raise IntegrityError("Not an integration v3 plan")
    if plan != plan_v3(Path(plan["instruments_directory"]), plan["source_manifest"], plan["readiness_snapshot"]):
        raise IntegrityError("Plan/source/software/instruments drift")
    source, _ = corpus()
    if plan["source_manifest"] != source or len(source["items"]) != 135:
        raise IntegrityError("Only unchanged 135-input primary corpus permitted")


CLAIMS = {
    "synthetic-token-logging": ("Access tokens in INFO logs can expose bearer credentials to log readers.",
                              "The application logs OAuth access tokens at INFO level for troubleshooting.", "review_required"),
    "synthetic-public-metadata": ("Unauthenticated internet clients can read internal service metadata.",
                                 "unauthenticated internet-facing HTTP endpoint", "review_required"),
    "synthetic-benign-docs": ("The described spelling-only change does not alter runtime security controls.",
                            "changes no runtime code, permissions, deployment configuration, or security policy.", "pass"),
}


class ScriptedAdapters:
    """Source-grounded authored fixture claims, never model-derived or adjudicated."""
    test_carl_supported = True
    identity = "mmmtap-nonempty-scripted-chain-v1"

    def __init__(self, plan: dict):
        self.plan = plan
        self.calls = []

    def invoke(self, job: dict, payload, previous: dict | None) -> Response:
        self.calls.append(job["job_id"])
        if job["kind"] == "generator":
            text, quote, disposition = CLAIMS[job["case_id"]]
            envelope = strict_json(payload.split("\n", 1)[1].encode())
            if quote not in envelope["untrusted_evidence"]["source_text"]:
                raise IntegrityError("Scripted claim quote missing from frozen source")
            obj = {"case_id": job["case_id"], "variant_id": job["variant_id"],
                   "claims": [{"claim_id": "claim1", "claim": text, "evidence_quotes": [quote], "confidence": 0.7,
                               "limitations": ["Authored offline fixture; runtime behavior not independently verified."]}],
                   "disposition": disposition, "uncertainties": ["Mocked assessment; not research evidence."],
                   "changes": [] if previous is None else [{"claim_id": "claim1", "action": "retained",
                       "reason": "The exact supplied source still supports the same limited observation."}]}
            return Response(message=json_bytes(obj), stdout=json_bytes({"mode": "mock", "assessment": obj}),
                            exit_status=0, provenance={"evidence_mode": "mock", "fixture": self.identity})
        native = strict_json(base64.b64decode(payload["native_request"])) if job["mechanism"] == "carl_jev" else payload
        answer = {"model": "MOCK_SYSTEMONE_NOT_PROVIDER", "answers": {k: {"noul": 0.1 if k == "authority_promoted" else 0.8}
                                                                   for k in native["questions"]}}
        if job["mechanism"] == "carl_jev":
            return PathBAdapter(self.plan["config"]["adversaries"]["carl_jev"], self.plan["config"]).invoke(
                payload, mock_response=answer)
        parse_systemone(json_bytes(answer), native)
        return Response(message=json_bytes({"mechanism": "native_jev", "evidence_mode": "mock", **answer}),
                        stdout=json_bytes(answer), exit_status=0, provenance={"evidence_mode": "mock"})


def live_invoke_v3(plan: dict, job: dict, payload, *, authorised=False) -> Response:
    if not authorised:
        return Response(error="live_authorisation_required")
    cfg = plan["config"]
    if job["kind"] == "generator":
        return GeneratorAdapter(cfg["generators"][job["generator"]], cfg).invoke(payload, authorised=True)
    if job["mechanism"] == "carl_jev":
        return PathBAdapter(cfg["adversaries"]["carl_jev"], cfg).invoke(payload, authorised=True)
    return NativeJEVAdapter(cfg["adversaries"]["native_jev"], cfg).invoke(payload, job["evidence_contract"], authorised=True)
