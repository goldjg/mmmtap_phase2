"""Source-bound proposed v4 instruments and explicitly scripted offline adapters."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import sys
from historical_extractor.extract import strict_json

from .core import (ROOT, PACKAGE, IntegrityError, challenge_request, corpus, digest, experiment_plan,
                   json_bytes, load, matrix_counts, read_config, write_new, question_pack, assessment_shape)
from .isolation import sha256_file
from .adapters import Response, NativeJEVAdapter, parse_systemone
from .adapters_v2 import GeneratorAdapter, PathBAdapter, copilot_argv, codex_argv
from .software import (local_sources, source_hashes, tree_identity, verify_build,
                       build_receipt_path, verify_generator_closure)

CONTRACT = "supplied_frozen_text_assessment_challenge_v1"
VERSION = "mmmtap-integration-v4"
PILOT_CASES = {"synthetic-benign-docs", "synthetic-token-logging", "synthetic-public-metadata"}


def freeze(directory: Path, binary: Path) -> dict:
    """Create new instruments; never amend a frozen version in place."""
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    build = verify_build(binary)
    before_sources = source_hashes()
    cfg = copy.deepcopy(read_config())
    cfg["schema"] = "mmmtap-phase2-config-v4"
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
        spec["strict_isolation_qualification"] = "blocked"
        spec["strict_isolation_blockers"] = (
            ["internal_tools_not_preventively_denied", "live_egress_not_provider_scoped"] if name == "sol" else
            ["internal_retries_not_preventively_disabled", "live_egress_not_provider_scoped",
             "authenticated_route_not_qualified"])
        if name == "sol":
            spec["release_root"] = str(codex.parent.parent)
            release = tree_identity(codex.parent.parent)
            spec["release_sha256"] = digest(release)
            write_new(directory / "codex_release.v1.json", release)
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
        "build_receipt_sha256": sha256_file(build_receipt_path(binary)),
        "key_env": "JEVKEY", "endpoint": cfg["adversaries"]["native_jev"]["endpoint"],
        "evidence_contracts": [CONTRACT], "policy_root": str(policy_root.resolve()),
        "policy_files": {str(p.relative_to(policy_root)): sha256_file(p)
                         for p in policy_root.rglob("*") if p.is_file()}}
    cfg["policy"]["carl_text_adapter_validated"] = False
    cfg["policy"]["carl_path_b_offline_contract"] = True
    cfg["policy"]["live_qualified"] = False
    write_new(directory / "config.v4.json", cfg)
    templates = load(PACKAGE / "prompts.v1.json")
    write_new(directory / "prompts.v1.snapshot.json", templates)
    write_new(directory / "questions.v1.json", question_pack())
    write_new(directory / "assessment_shape.v1.json", assessment_shape())
    write_new(directory / "evidence_schema.v1.json", evidence_schema())
    write_new(directory / "roles.v1.json", roles(cfg, templates))
    write_new(directory / "provider_response_schema.v1.json", provider_schema())
    write_new(directory / "path_b_build.v1.json", build)
    sources = local_sources()
    for name, path in sources.items():
        target = directory / "software_source" / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(path.read_bytes())
        target.chmod(0o600)
    python = Path(sys.executable).resolve()
    write_new(directory / "software.v1.json", {
        "schema": "mmmtap-software-closure-v1", "sources": before_sources,
        "python": {"binary": str(python), "sha256": sha256_file(python), "version": sys.version},
        "path_b_binary_sha256": cfg["adversaries"]["carl_jev"]["binary_sha256"],
        "path_b_build_receipt_sha256": cfg["adversaries"]["carl_jev"]["build_receipt_sha256"],
        "os_boundary": "host_kernel_and_readonly_usr_not_hermetic_image; strict_live_generators_blocked"})
    if before_sources != source_hashes():
        raise IntegrityError("Source changed during freezing; incomplete snapshot retained")
    files = {str(p.relative_to(directory)): sha256_file(p) for p in sorted(directory.rglob("*")) if p.is_file()}
    manifest = {"schema": "mmmtap-frozen-instruments-v4", "status": cfg["instrument_status"],
                "files": files, "live_calls": 0, "question_change": "none",
                "policy_change": "new proposed copy of offline fixture; same thresholds; not PI approval",
                "implementation_sha256": sha256_file(directory / "software.v1.json")}
    write_new(directory / "manifest.json", manifest)
    return manifest


def evidence_schema() -> dict:
    return {
        "schema": "mmmtap-path-b-evidence-contract-v1", "contract": CONTRACT,
        "request_schema": "carl-assessment-challenge-v1-request", "authenticated_git": False,
        "deployment_state": "not_asserted", "origin_kind": "archive_member",
        "bindings": ["source", "archive", "member", "manifest", "assessment", "parent", "native_request"],
        "executable_validator": "cARL internal/assessment/request.go; frozen source snapshot below",
        "capacity": {"source_bytes": 1048576, "claims": 128, "artifact_bytes": 8388608}}


def provider_schema() -> dict:
    return {"schema": "mmmtap-systemone-typed-response-v1", "required": ["model", "answers"],
            "optional": ["usage"], "unknown_fields": "reject", "field_matching": "exact_case_sensitive",
            "duplicates": "reject_before_decoding", "numbers": "finite_IEEE754; probabilities_0_to_1",
            "model": "nonempty_unpadded_string_without_ASCII_controls_or_unpaired_surrogates",
            "noul_answer": {"required": ["noul"], "optional": []},
            "choice_answer": {"required": ["choice"], "optional": ["probabilities"],
                              "probabilities": "exact_criteria_set; sorted_key_sum; tolerance_0.001"},
            "usage": {"shape": "absent_null_or_object", "counters": [
                "input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens", "total_tokens"],
                "counter_type": "integer_0_to_9223372036854775807"},
            "capacity": {"response_bytes": 8388608, "nesting": 64},
            "semantics": "provider_evidence_only; cARL_policy_disposition_remains_separate"}


def roles(cfg: dict, templates: dict) -> dict:
    return {"schema": "mmmtap-role-boundaries-v1", "boundary": templates["boundary"],
            "generators": {name: {"model_id": s["model_id"], "role": "source_assessor_no_tools"}
                           for name, s in cfg["generators"].items()},
            "adversaries": {"native_jev": "untrusted_typed_SystemOne_judgements",
                            "carl_jev": "same_typed_evidence_plus_frozen_deterministic_policy"},
            "policy_authority": "only_explicit_frozen_carl_policy; challenge_not_generator_instruction"}


def verify_instruments(directory: Path) -> dict:
    manifest = load(directory / "manifest.json")
    if manifest.get("schema") != "mmmtap-frozen-instruments-v4":
        raise IntegrityError("Historical instruments lack v4 software binding; retained read-only")
    if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
        raise IntegrityError("Frozen instrument symlink")
    actual = {str(p.relative_to(directory)): sha256_file(p) for p in directory.rglob("*")
              if p.is_file() and p != directory / "manifest.json"}
    if actual != manifest["files"]:
        raise IntegrityError("Frozen instruments changed")
    cfg = load(directory / "config.v4.json")
    if (cfg["schema"] != "mmmtap-phase2-config-v4" or cfg["partition"] != "p1_014_frozen"
            or cfg["policy"]["historical_candidates_admitted"] is not False):
        raise IntegrityError("Unapproved partition or configuration")
    software = load(directory / "software.v1.json")
    if software["sources"] != source_hashes() or manifest["implementation_sha256"] != sha256_file(directory / "software.v1.json"):
        raise IntegrityError("Frozen implementation differs from runtime software")
    if any(actual.get("software_source/" + name) != expected for name, expected in software["sources"].items()):
        raise IntegrityError("Frozen source bytes differ from implementation manifest")
    from . import core
    templates = load(core.PACKAGE / "prompts.v1.json")
    snapshots = {"prompts.v1.snapshot.json": templates, "questions.v1.json": question_pack(),
                 "assessment_shape.v1.json": assessment_shape(), "evidence_schema.v1.json": evidence_schema(),
                 "provider_response_schema.v1.json": provider_schema(), "roles.v1.json": roles(cfg, templates)}
    if any(load(directory / name) != expected for name, expected in snapshots.items()):
        raise IntegrityError("Frozen prompt/question/schema/role semantics differ from runtime")
    if sha256_file(Path(software["python"]["binary"])) != software["python"]["sha256"] or software["python"]["version"] != sys.version:
        raise IntegrityError("Frozen Python executable differs from runtime")
    for name, spec in cfg["generators"].items():
        verify_generator_closure(spec)
        if spec["argv"] != (codex_argv() if name == "sol" else copilot_argv(spec["model_id"])):
            raise IntegrityError("Frozen CLI arguments differ from runtime")
        if spec["strict_isolation_qualification"] != "blocked":
            raise IntegrityError("This implementation has no strict live generator qualification")
    spec = cfg["adversaries"]["carl_jev"]
    if sha256_file(Path(cfg["isolation_runtime"]["binary"])) != cfg["isolation_runtime"]["sha256"]:
        raise IntegrityError("Isolation runtime changed")
    if sha256_file(Path(spec["binary"])) != spec["binary_sha256"]:
        raise IntegrityError("Path B binary changed")
    if (sha256_file(build_receipt_path(Path(spec["binary"]))) != spec["build_receipt_sha256"]
            or verify_build(Path(spec["binary"])) != load(directory / "path_b_build.v1.json")):
        raise IntegrityError("Path B build differs from frozen implementation")
    policy_root = Path(spec["policy_root"])
    if policy_root.resolve() != (directory / "carl_policy").resolve() or {
            str(p.relative_to(policy_root)): sha256_file(p) for p in policy_root.rglob("*") if p.is_file()
    } != spec["policy_files"]:
        raise IntegrityError("Frozen policy selection/content differs from runtime")
    return cfg


def plan_v4(directory: Path, source: dict, readiness: dict, *, attempt: int = 1,
            retry_of: str | None = None, retry_reason: str | None = None) -> dict:
    cfg = verify_instruments(directory)
    plan = experiment_plan(cfg, source, readiness, templates=load(directory / "prompts.v1.snapshot.json"),
                           attempt=attempt, retry_of=retry_of, retry_reason=retry_reason)
    plan["integration_version"] = VERSION
    plan["instruments_directory"] = str(directory.resolve())
    plan["instruments_sha256"] = sha256_file(directory / "manifest.json")
    plan["implementation_sha256"] = sha256_file(directory / "software.v1.json")
    plan["question_pack"] = load(directory / "questions.v1.json")
    plan["assessment_shape"] = load(directory / "assessment_shape.v1.json")
    plan["evidence_schema"] = load(directory / "evidence_schema.v1.json")
    plan["roles"] = load(directory / "roles.v1.json")
    plan["provider_response_schema"] = load(directory / "provider_response_schema.v1.json")
    plan["source_manifest"] = source
    plan["supersedes"] = {"file": "integration_readiness_v1/execution_plan_v3.json",
                          "sha256": sha256_file(ROOT / "integration_readiness_v1/execution_plan_v3.json"),
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
        old["implementation_sha256"] = plan["implementation_sha256"]
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


def validate_v4(plan: dict) -> None:
    if plan.get("integration_version") != VERSION:
        raise IntegrityError("Not an integration v4 plan; v3 retained as historical evidence")
    if plan != plan_v4(Path(plan["instruments_directory"]), plan["source_manifest"], plan["readiness_snapshot"],
                       attempt=plan["experimental_attempt"], retry_of=plan["retry_of_manifest_sha256"],
                       retry_reason=plan["retry_reason"]):
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
    identity = "mmmtap-challenge-sensitive-scripted-chain-v2"

    def __init__(self, plan: dict):
        self.plan = plan
        self.calls = []

    def invoke(self, job: dict, payload, previous: dict | None) -> Response:
        self.calls.append(job["job_id"])
        if job["kind"] == "generator":
            envelope = strict_json(payload.split("\n", 1)[1].encode())
            evidence = envelope["untrusted_evidence"]
            source_text = evidence["source_text"]
            if not source_text.strip():
                raise IntegrityError("Nonempty frozen source required by authored fixture")
            if job["case_id"] in CLAIMS:
                text, quote, disposition = CLAIMS[job["case_id"]]
                if quote not in source_text:
                    raise IntegrityError("Scripted claim quote missing from frozen source")
            else:
                text = "Authored mock observation: the supplied source contains the quoted excerpt."
                quote, disposition = source_text.strip()[:160], "insufficient_evidence"
            initial = {"claim_id": "claim1", "claim": text, "evidence_quotes": [quote], "confidence": 0.7,
                       "limitations": ["Authored offline fixture; runtime behavior not independently verified."]}
            claims = [initial] if previous is None else copy.deepcopy(previous["claims"])
            changes = [] if previous is None else [{"claim_id": c["claim_id"], "action": "retained",
                "reason": "Authored neutral control retains the identical source-bound observation."} for c in claims]
            if job["challenge_parent"]:
                challenge = evidence["challenge"]
                expected = {"adversary_job_id": job["challenge_parent"], "assessment_sha256": digest(previous)}
                if not isinstance(challenge, dict) or challenge.get("mock_fixture_binding") != expected:
                    raise IntegrityError("Missing or cross-branch authored mock challenge")
                mechanism = next(j["mechanism"] for j in self.plan["jobs"] if j["job_id"] == job["challenge_parent"])
                signals = (challenge.get("signals") if mechanism == "carl_jev" else
                           {k: a["noul"] for k, a in challenge.get("answers", {}).items()})
                if not isinstance(signals, dict) or "claim_0000_supported" not in signals:
                    raise IntegrityError("Mock challenge lacks required underlying judgement")
                if signals["claim_0000_supported"] < 0.5:
                    first = claims[0]
                    if mechanism == "native_jev":
                        first["claim"] += " Authored mock revision explicitly narrows this observation to supplied text."
                        first["confidence"] = 0.4
                        changes[0] = {"claim_id": first["claim_id"], "action": "revised",
                                      "reason": "Authored mock responds to the supplied low support judgement."}
                    else:
                        if not any(c["claim_id"] == first["claim_id"] for c in challenge.get("challenges", [])):
                            raise IntegrityError("Policy fixture must actually challenge the selected claim")
                        claims = claims[1:]
                        changes[0] = {"claim_id": first["claim_id"], "action": "withdrawn",
                                      "reason": "Authored mock withdrawal in response to this actual policy challenge."}
                    next_id = "claim" + str(max(int(c["claim_id"][5:]) for c in previous["claims"]) + 1)
                    claims.append({**copy.deepcopy(initial), "claim_id": next_id,
                                   "claim": "Authored mock replacement: the quoted bytes occur in the supplied source."})
                    changes.append({"claim_id": next_id, "action": "added",
                                    "reason": "Authored mock adds a limited literal-source observation; not adjudicated truth."})
            obj = {"case_id": job["case_id"], "variant_id": job["variant_id"],
                   "claims": claims,
                   "disposition": disposition, "uncertainties": ["Mocked assessment; not research evidence."],
                   "changes": changes}
            return Response(message=json_bytes(obj), stdout=json_bytes({"mode": "mock", "assessment": obj}),
                            exit_status=0, provenance={"evidence_mode": "mock", "fixture": self.identity})
        native = strict_json(base64.b64decode(payload["native_request"])) if job["mechanism"] == "carl_jev" else payload
        answer = {"model": "MOCK_SYSTEMONE_NOT_PROVIDER", "answers": {
            k: {"noul": 0.1 if k == "authority_promoted" else 0.2 if k == "claim_0000_supported" else 0.8}
            for k in native["questions"]}, "usage": {"input_tokens": 11, "output_tokens": 7}}
        binding = {"adversary_job_id": job["job_id"], "assessment_sha256": digest(previous)}
        if job["mechanism"] == "carl_jev":
            response = PathBAdapter(self.plan["config"]["adversaries"]["carl_jev"], self.plan["config"]).invoke(
                payload, mock_response=answer)
            if not response.error:
                response.message = json_bytes({**strict_json(response.message), "mock_fixture_binding": binding})
            return response
        parsed = parse_systemone(json_bytes(answer), native)
        return Response(message=json_bytes({**parsed, "evidence_mode": "mock", "mock_fixture_binding": binding}),
                        stdout=json_bytes(answer), usage=parsed["usage"], exit_status=0,
                        provenance={"evidence_mode": "mock", "fixture": self.identity})


def live_invoke_v4(plan: dict, job: dict, payload, *, authorised=False) -> Response:
    if not authorised:
        return Response(error="live_authorisation_required")
    cfg = plan["config"]
    if job["kind"] == "generator":
        return GeneratorAdapter(cfg["generators"][job["generator"]], cfg).invoke(payload, authorised=True)
    if job["mechanism"] == "carl_jev":
        return PathBAdapter(cfg["adversaries"]["carl_jev"], cfg).invoke(payload, authorised=True)
    return NativeJEVAdapter(cfg["adversaries"]["native_jev"], cfg).invoke(payload, job["evidence_contract"], authorised=True)
