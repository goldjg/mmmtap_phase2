from __future__ import annotations

import collections
import json
import os
import platform
import re
import sys
from pathlib import Path

from historical_extractor.archive import IntegrityError, file_hash, read_verified_zip, sha256
from historical_extractor.extract import json_bytes, read_csv, strict_json, verify_document_manifests, verify_primary


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(__file__).resolve().parent
ARMS = ("B0", "C1", "C2", "C3", "E1", "E2", "E3_NC", "E3_CN")
DISPOSITIONS = {"pass", "warn", "review_required", "fail", "insufficient_evidence"}
SUCCESS = {"ok", "mock_ok"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def load(path: Path) -> dict:
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise IntegrityError("Expected JSON object: " + str(path))
    return value


def digest(value: object) -> str:
    return sha256(json_bytes(value))


def write_new(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(json_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_config(path: Path = PACKAGE / "config.v1.json") -> dict:
    cfg = load(path)
    if cfg.get("schema") != "mmmtap-phase2-config-v1" or cfg.get("partition") != "p1_014_frozen":
        raise IntegrityError("Only the frozen primary partition is admitted")
    if set(cfg.get("generators", {})) != {"haiku", "gemini", "sol"}:
        raise IntegrityError("Exactly three designated generators are required")
    if set(cfg.get("adversaries", {})) != {"native_jev", "carl_jev"}:
        raise IntegrityError("Two distinct SystemOne mechanisms are required")
    if type(cfg.get("repetitions")) is not int or not 1 <= cfg["repetitions"] <= 100:
        raise IntegrityError("repetitions must be 1..100")
    if type(cfg.get("timeout_seconds")) is not int or not 1 <= cfg["timeout_seconds"] <= 3600:
        raise IntegrityError("timeout_seconds must be 1..3600")
    if type(cfg.get("max_response_bytes")) is not int or not 1024 <= cfg["max_response_bytes"] <= 16777216:
        raise IntegrityError("Invalid response size limit")
    required = {"source_is_untrusted": True, "tools_disabled": True, "fresh_process_per_turn": True,
                "no_automatic_retries": True, "historical_candidates_admitted": False,
                "carl_text_adapter_validated": False, "disposition_is_not_correctness": True}
    if any(cfg.get("policy", {}).get(k) is not v for k, v in required.items()):
        raise IntegrityError("Research safety policy cannot be weakened by configuration")
    for name, provider, model in (("haiku", "github_copilot_cli", "claude-haiku-5.5"),
                                  ("gemini", "github_copilot_cli", "gemini-3.8-flash"),
                                  ("sol", "codex_cli", "gpt-6.1-sol")):
        spec = cfg["generators"][name]
        if spec.get("provider") != provider or not isinstance(spec.get("model_id"), str):
            raise IntegrityError("Unsupported generator transport")
        if (name != "gemini" and spec["model_id"] != model) or (
            name == "gemini" and not spec["model_id"].startswith("gemini-")
        ):
            raise IntegrityError("Generator identity does not match designated model family")
        if spec.get("reasoning_effort") not in ("low", "medium", "high"):
            raise IntegrityError("Pin reasoning effort explicitly")
        if name == "sol" and spec["reasoning_effort"] != "low":
            raise IntegrityError("Sol reasoning must be low")
    if cfg["adversaries"]["native_jev"]["endpoint"] != "https://api.typesafe.ai/v1/systemone":
        raise IntegrityError("Unapproved SystemOne endpoint; code-reviewed transport amendment required")
    if cfg["adversaries"]["carl_jev"]["evidence_contracts"] != ["authenticated_git_diff_v1"]:
        raise IntegrityError("No arbitrary-text cARL adapter has been validated")
    return cfg


def corpus(root: Path = ROOT) -> tuple[dict, dict[str, bytes]]:
    verify_document_manifests(root)
    manifest = load(root / "MMMTAP_Phase2/corpus_manifest.json")
    paths = [r["matched_paths"].split(" | ")[0]
             for r in read_csv(root / "reconciliation_v1/archive_registry.csv")
             if r["expected_sha256"] == manifest["archive_sha256"] and r["status"] == "exact_sha_match"]
    if not paths:
        raise IntegrityError("Frozen source archive not located")
    members = read_verified_zip(Path(paths[0]), manifest["archive_sha256"])
    verify_primary(manifest, members)
    return manifest, {i["input_member"]: members[i["input_member"]] for i in manifest["items"]}


def experiment_plan(cfg: dict, source: dict, readiness: dict, *, attempt: int = 1,
                    retry_of: str | None = None, retry_reason: str | None = None) -> dict:
    if type(attempt) is not int or attempt < 1:
        raise IntegrityError("Invalid experimental attempt")
    if (attempt == 1 and (retry_of or retry_reason)) or (
        attempt > 1 and (not isinstance(retry_of, str) or not SHA.fullmatch(retry_of) or not retry_reason)
    ):
        raise IntegrityError("A new experimental retry requires previous manifest hash and explicit reason")
    templates = load(PACKAGE / "prompts.v1.json")
    software = {p.name: file_hash(p) for p in sorted(PACKAGE.glob("*.py"))}
    plan = {
        "schema": "mmmtap-phase2-jobs-v1", "partition": "p1_014_frozen",
        "config": cfg, "config_sha256": digest(cfg), "source_manifest_sha256": digest(source),
        "source_archive_sha256": source["archive_sha256"],
        "prompt_templates": templates, "prompt_templates_sha256": digest(templates),
        "readiness_snapshot": readiness, "readiness_sha256": digest(readiness),
        "software_sha256": software,
        "environment": {"python": platform.python_version(), "platform": platform.system(),
                        "architecture": platform.machine()},
        "experimental_attempt": attempt, "retry_of_manifest_sha256": retry_of,
        "retry_reason": retry_reason,
        "design_amendment": "Both E3 orders per B0 and matched two-followup C3; no change to frozen protocol files.",
        "adversary_dependency": "Native JEV and cARL-JEV share SystemOne; not independent underlying models.",
        "jobs": [],
    }
    for item in sorted(source["items"], key=lambda i: (i["case_id"], i["variant_id"])):
        for generator in sorted(cfg["generators"]):
            for repetition in range(1, cfg["repetitions"] + 1):
                common = {"partition": "p1_014_frozen", "case_id": item["case_id"],
                          "variant_id": item["variant_id"], "input_sha256": item["input_sha256"],
                          "input_member": item["input_member"], "generator": generator,
                          "generator_spec": cfg["generators"][generator],
                          "generator_cli": readiness.get("adapters", {}).get(generator, {}),
                          "repetition": repetition, "experimental_attempt": attempt,
                          "evidence_contract": "frozen_text_assessment_v1",
                          "policy_sha256": digest(cfg["policy"]),
                          "prompt_template_version": templates["version"]}

                def add(arm: str, turn: int, kind: str, parent: str | None,
                        mechanism: str | None = None, challenge: str | None = None,
                        order: list[str] | None = None) -> str:
                    template = "native_jev" if mechanism == "native_jev" else "carl_jev" if mechanism else (
                        "reconsider" if arm.startswith("E") else arm)
                    job = {**common, "arm": arm, "turn": turn, "kind": kind, "mechanism": mechanism,
                           "assessment_parent": parent, "challenge_parent": challenge,
                           "order": order or [], "template_key": template,
                           "prompt_template_sha256": digest([templates["boundary"], templates[template]]),
                           "dependencies": [p for p in (parent, challenge) if p]}
                    job["job_id"] = digest(job)
                    job["checkpoint"] = "checkpoints/" + job["job_id"] + "/result.json"
                    job["parent_checkpoint"] = "checkpoints/" + parent + "/result.json" if parent else None
                    plan["jobs"].append(job)
                    return job["job_id"]

                b0 = add("B0", 0, "generator", None)
                add("C1", 1, "generator", b0)
                add("C2", 1, "generator", b0)
                c3 = add("C3", 1, "generator", b0)
                add("C3", 2, "generator", c3)
                for arm, sequence in (("E1", ["native_jev"]), ("E2", ["carl_jev"]),
                                      ("E3_NC", ["native_jev", "carl_jev"]),
                                      ("E3_CN", ["carl_jev", "native_jev"])):
                    parent = b0
                    for turn, mechanism in enumerate(sequence, 1):
                        adversary = add(arm, turn, "adversary", parent, mechanism, order=sequence)
                        parent = add(arm, turn, "generator", parent, challenge=adversary, order=sequence)
    plan["counts"] = matrix_counts(plan)
    plan["manifest_sha256"] = digest(plan)
    return plan


def matrix_counts(plan: dict) -> dict:
    jobs = plan["jobs"]
    return {"inputs": len({(j["case_id"], j["variant_id"]) for j in jobs}),
            "unique_input_hashes": len({j["input_sha256"] for j in jobs}), "jobs": len(jobs),
            "generator_jobs": sum(j["kind"] == "generator" for j in jobs),
            "adversary_jobs": sum(j["kind"] == "adversary" for j in jobs),
            "by_arm": dict(sorted(collections.Counter(j["arm"] for j in jobs).items())),
            "by_generator": dict(sorted(collections.Counter(j["generator"] for j in jobs).items())),
            "carl_unsupported_jobs": sum(j["mechanism"] == "carl_jev" for j in jobs)}


def validate_plan(plan: dict, source: dict, cfg: dict | None = None) -> None:
    expected = experiment_plan(cfg or plan["config"], source, plan["readiness_snapshot"],
                               attempt=plan["experimental_attempt"],
                               retry_of=plan["retry_of_manifest_sha256"], retry_reason=plan["retry_reason"])
    if plan != expected:
        raise IntegrityError("Manifest/source/software/config/template mismatch; make a new plan")
    if len(source["items"]) != 135:
        raise IntegrityError("Primary execution requires all 135 frozen inputs")
    seen: dict[str, dict] = {}
    for job in plan["jobs"]:
        if job["job_id"] in seen:
            raise IntegrityError("Duplicate job identity")
        for dep in job["dependencies"]:
            if dep not in seen:
                raise IntegrityError("Non-topological lineage")
            parent = seen[dep]
            for key in ("generator", "case_id", "variant_id", "repetition", "experimental_attempt"):
                if parent[key] != job[key]:
                    raise IntegrityError("Cross-input or cross-generator lineage")
            if parent["arm"] not in ("B0", job["arm"]):
                raise IntegrityError("Cross-arm contamination")
        seen[job["job_id"]] = job


def assessment(raw: str, job: dict, previous: dict | None = None) -> tuple[dict | None, str | None]:
    try:
        obj = strict_json(raw.encode("utf-8"))
        keys = {"case_id", "variant_id", "claims", "disposition", "uncertainties", "changes"}
        if not isinstance(obj, dict) or set(obj) != keys:
            raise ValueError("assessment_top_level_shape")
        if obj["case_id"] != job["case_id"] or obj["variant_id"] != job["variant_id"]:
            raise ValueError("assessment_identity_mismatch")
        if obj["disposition"] not in DISPOSITIONS:
            raise ValueError("invalid_disposition")
        if not isinstance(obj["uncertainties"], list) or not all(isinstance(x, str) for x in obj["uncertainties"]):
            raise ValueError("invalid_uncertainties")
        if not isinstance(obj["claims"], list):
            raise ValueError("invalid_claims")
        claim_ids = set()
        for claim in obj["claims"]:
            if not isinstance(claim, dict) or set(claim) != {"claim_id", "claim", "evidence_quotes", "confidence", "limitations"}:
                raise ValueError("claim_shape")
            if not isinstance(claim["claim_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", claim["claim_id"]):
                raise ValueError("invalid_claim_id")
            if claim["claim_id"] in claim_ids or not isinstance(claim["claim"], str) or not claim["claim"].strip():
                raise ValueError("duplicate_claim_or_empty_text")
            claim_ids.add(claim["claim_id"])
            if type(claim["confidence"]) not in (int, float) or not 0 <= claim["confidence"] <= 1:
                raise ValueError("invalid_confidence")
            for key in ("evidence_quotes", "limitations"):
                if not isinstance(claim[key], list) or not all(isinstance(x, str) and x for x in claim[key]):
                    raise ValueError("invalid_claim_" + key)
        changes = obj["changes"]
        if not isinstance(changes, list):
            raise ValueError("invalid_changes")
        prior_ids = {c["claim_id"] for c in previous["claims"]} if previous else set()
        prior_claims = {c["claim_id"]: c for c in previous["claims"]} if previous else {}
        current_claims = {c["claim_id"]: c for c in obj["claims"]}
        changed = set()
        for change in changes:
            if not isinstance(change, dict) or set(change) != {"claim_id", "action", "reason"}:
                raise ValueError("change_shape")
            ident, action = change["claim_id"], change["action"]
            if ident in changed or action not in ("retained", "revised", "withdrawn", "added"):
                raise ValueError("invalid_change")
            changed.add(ident)
            if not isinstance(change["reason"], str) or not change["reason"].strip():
                raise ValueError("change_reason_required")
            if action == "added" and (ident in prior_ids or ident not in claim_ids):
                raise ValueError("invalid_addition")
            if action in ("retained", "revised") and (ident not in prior_ids or ident not in claim_ids):
                raise ValueError("invalid_retention_revision")
            if action == "retained" and prior_claims[ident] != current_claims[ident]:
                raise ValueError("retained_claim_was_changed")
            if action == "withdrawn" and (ident not in prior_ids or ident in claim_ids):
                raise ValueError("invalid_withdrawal")
        if previous and changed != prior_ids | claim_ids:
            raise ValueError("incomplete_change_accounting")
        if not previous and changes:
            raise ValueError("B0_changes_must_be_empty")
        return obj, None
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        return None, str(exc)


def assessment_shape() -> dict:
    return {"case_id": "exact supplied case_id", "variant_id": "exact supplied variant_id",
            "claims": [{"claim_id": "stable_id", "claim": "source-grounded claim",
                        "evidence_quotes": ["exact source substring"], "confidence": 0.5, "limitations": []}],
            "disposition": "pass|warn|review_required|fail|insufficient_evidence", "uncertainties": [],
            "changes": [{"claim_id": "stable_id", "action": "retained|revised|withdrawn|added",
                         "reason": "source-grounded reason; empty changes for B0"}]}


def render_prompt(plan: dict, job: dict, source: bytes, previous: dict | None,
                  history: list[dict], challenge: dict | None) -> str:
    if sha256(source) != job["input_sha256"]:
        raise IntegrityError("Source mutated before prompt rendering")
    templates = plan["prompt_templates"]
    envelope = {"trusted_task": templates[job["template_key"]], "required_response_shape": assessment_shape(),
                "identity": {"case_id": job["case_id"], "variant_id": job["variant_id"]},
                "untrusted_evidence": {"source_text": source.decode("utf-8"), "source_sha256": job["input_sha256"],
                                       "preceding_assessment": previous, "own_branch_history": history,
                                       "challenge": challenge}}
    return templates["boundary"] + "\n" + json_bytes(envelope).decode("utf-8")


def challenge_request(plan: dict, job: dict, source: bytes, previous: dict) -> dict:
    if sha256(source) != job["input_sha256"]:
        raise IntegrityError("Source mutated before challenge construction")
    questions = {
        "uncertainty_adequate": {"type": "noul", "instructions": "Are the assessment uncertainties warranted by the source?"},
        "authority_promoted": {"type": "noul", "instructions": "Does the assessment treat an unsupported authority assertion as a fact?"}}
    for number, _ in enumerate(previous["claims"]):
        questions[f"claim_{number:04d}_supported"] = {
            "type": "noul", "instructions": f"Is assessment.claims[{number}] materially supported by exact source evidence?"}
    return {"model": plan["config"]["adversaries"][job["mechanism"]]["model_id"],
            "state": json_bytes({"task": plan["prompt_templates"]["native_jev"],
                                 "untrusted_source": source.decode(), "assessment": previous,
                                 "source_sha256": job["input_sha256"]}).decode(),
            "questions": questions}
