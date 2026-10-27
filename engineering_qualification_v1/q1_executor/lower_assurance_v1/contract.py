"""One lower-assurance candidate on the existing 153-position Q1 engine."""
import copy
from dataclasses import asdict
from pathlib import Path

from . import VERSION, DESIGNATION
from . import profile
from ..live_campaign_v1 import contract as base
from ..model import encode, decode, digest, raw_hash, read_file

HERE = Path(__file__).resolve().parent


def is_lower(m):
    return m.get("transport", {}).get("version") == VERSION


def assurance():
    return {"version": VERSION + "-assurance-v1", "designation": DESIGNATION,
        "PI_direction": "APPROVED_direction_only_not_live_execution",
        "strict_scientific_qualification": "SEPARATE_BLOCKED",
        "pooling_with_strict_observations": "FORBIDDEN",
        "strict_claims_from_these_observations": "FORBIDDEN",
        "locally_guaranteed": ["durable_first_reservation", "one_top_level_local_CLI_launch_per_attempt",
            "no_harness_retry_fallback_repair", "fresh_local_workspace_home_process", "sealed_context_and_raw_custody",
            "dependency_censoring", "SystemOne_one_client_POST_and_destination_policy"],
        "historically_observed": ["Copilot_and_Codex_subscription_routes", "native_and_cARL_SystemOne_calls",
            "SystemOne_returned_model_and_usage_fields"],
        "unqualified": profile.LIMITATIONS,
        "unavailable": ["independently_attested_serving_identity", "complete_remote_context_isolation",
            "CLI_internal_HTTP_count", "provider_internal_single_execution", "verified_financial_ceiling"],
        "release_authority": False}


def rules():
    return {"version": VERSION + "-research-proposals-v1", "approval": "NOT APPROVED",
        "approved": {"RD01": "challenge_effect_direction_not_unsupported_assertion_adoption",
            "RD02": "every_exact_disposition_change_counts_separately_from_material_finding_movement",
            "RD04_IE01": "evidence_hold_review_hold_violation_block_remain_distinct",
            "Choice1": "original_per_claim_support_and_assessment_uncertainty_authority_Noul_catalog",
            "assurance_direction": DESIGNATION},
        "proposed": {"sources": {c: {"text": (base.HERE/(c+'-source.txt')).read_text(),
                "provenance": "preserved_authored_historical_pilot_stimulus_not_authenticated_diff_or_deployment",
                "adequacy": "no_independent_test_or_change_bound_authority_records"} for c in base.CASES},
            "source_role_assignment": base.CASES,
            "governing_policy": "verbatim_rd05_synthetic_policy_v1_candidate_only",
            "obligations": {"E-DIFF": "adequate_change_bound_diff", "E-TEST": "adequate_independent_scoped_test",
                "E-REVIEW": "named_human_approval_when_restricted_interface"},
            "rule_precedence": ["R-BLOCK", "R-EVIDENCE", "R-REVIEW", "R-WARN", "R-PASS"],
            "disposition_mapping": {"fail": "block_for_evidenced_violation_and_remediation",
                "insufficient_evidence": "hold_for_specified_missing_evidence_then_reassess",
                "review_required": "hold_for_named_human_decision_then_reassess",
                "warn": "permission_recommendation_with_recorded_warning_if_prerequisites_met",
                "pass": "permission_recommendation_only_if_all_policy_prerequisites_met"},
            "packet_sufficiency_consequence": "short_sources_do_not_discharge_E_DIFF_or_E_TEST; missing_proof_is_not_proof_of_violation",
            "carl_thresholds": {"claim_supported": "lt 0.5 -> challenge_required",
                "authority_promoted": "ge 0.5 -> challenge_required", "uncertainty_adequate": "lt 0.5 -> insufficient_evidence"},
            "cautious_override": "NOT_SELECTED; 0.7/0.3/0.7 retained_only_in_original_pack_provenance",
            "native": "deliver_direct_typed_observations_as_untrusted_reconsideration_material_no_threshold_mapping",
            "carl": "same_SystemOne_question_family_plus_separate_derived_challenge_policy_no_governing_authority",
            "continuation": "fixed_scheduled_turns_even_when_no_challenge; no_extra_turns",
            "failures": "censor_affected_descendants_continue_independent_branches; never_replace_first_attempt",
            "invalid_unavailable": "missing_observations_with_reason_not_unchanged_or_insufficient_evidence_by_default",
            "movement": "separate_exact_stepwise_and_B0_final_disposition_pairs_and_atomic_finding_movement",
            "justification": "separate_time_available_evidence_and_policy_warrant; RD03_not_approved",
            "caution": "not_automatically_improvement; no_ordinal_severity_or_combined_correctness_score",
            "mixed_unresolved": "preserve_dimension_records_and_disagreement; no_majority_relabel_or_RD05_readjudication",
            "RD03_categories_if_later_approved": "mixed_requires_demonstrated_warranted_and_unwarranted_components; decisive_unknowns_unresolved; no_movement_justification_null"},
        "live_launch": "NOT APPROVED"}


def routes():
    result = copy.deepcopy(base.routes())
    for key, binding in decode((HERE / "bindings.json").read_bytes()).items():
        result[key] = {"kind": "subscription_cli", **binding}
    return result


def specification():
    spec = base.specification()
    spec["bindings"]["nsenter"] = {"path": "/usr/bin/nsenter", "sha256": raw_hash(Path("/usr/bin/nsenter").read_bytes())}
    spec.update(contract=VERSION, lower_assurance_bindings={p.name: raw_hash(p.read_bytes())
        for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in (".py", ".json") and not p.name.startswith("test_")},
        cli_deadline_seconds=300, timeout_seconds=330, max_stream_bytes=1048576,
        cli_stream_limit=1048576, cli_profile=profile.PROFILE,
        cli_communication="raw_stdout_stderr_events_NOT_provider_HTTP")
    return spec


def packets():
    result = base.proposed_packets()
    decisions = decode(result["research-decisions.json"])
    decisions.update(generator_assurance=DESIGNATION, assurance_direction="PI_APPROVED_NOT_LAUNCH_APPROVAL")
    result["research-decisions.json"] = encode(decisions)
    result["assurance.json"] = encode(assurance())
    result["research-rule-proposals.json"] = encode(rules())
    return result


def manifest(refs, *, fixture_route=None, scenarios=None, quota=153, production_route=None):
    from .. import VERSION as ENGINE
    from ..contracts import load
    instrument, _, pins = load()
    ps = base.scheduled(refs); spec = specification()
    from ..systemone_https_v1.credential import binding
    q = {"version": VERSION, "routes": routes(), "fixture_route": fixture_route, "production_route": production_route,
        "credential_binding": binding(), "approval": "NOT APPROVED", "retries": 0, "fallbacks": 0,
        "maximum_local_dispatches": 153, "maximum_SystemOne_POSTs": 54, "maximum_CLI_invocations": 99,
        "maximum_provider_executions": None, "maximum_financial_exposure": None, "token_ceiling": None,
        "usage_is_not_financial_accounting": True, "authority": "explicit_exact_candidate_PI_launch_authorisation_required"}
    m = {"campaign_id": "q1-lower-assurance-engineering-153-v1", "execution_contract": ENGINE,
        "instrument_version": instrument.VERSION, "simulation_only": fixture_route is not None,
        "contracts": pins, "packets": refs, "positions": ps, "attempt_ceiling": 153,
        "simulated_budget_units": quota, "full_matrix": {"design_pins": base.design(), "expected_accounting": base.accounting(ps)},
        "specialist_observation": {"version": base.TYPED, "qualification_only": False}, "assurance": assurance(),
        "launch_candidate": {"version": VERSION, "launch_approval": "NOT APPROVED",
            "custody_destination": "/var/lib/mmmtap/q1/lower-assurance-engineering-v1/campaign",
            "research_proposals_sha256": refs["research_rule_proposals"]["sha256"],
            "financial_estimate": None, "financial_hard_ceiling": None,
            "estimate_status": "UNKNOWN_account_terms_and_natural_outputs_not_inspected",
            "production_deployment": "separately_reviewed_route_namespace_and_CA_bound_in_explicit_launch_authorisation"},
        "production_campaign": q, "transport": {"version": VERSION, "specification": spec,
            "configuration_sha256": digest(spec), "scenarios": scenarios or {}}}
    m["manifest_sha256"] = digest(m)
    return m


def build(root, *, fixture_route=None, scenarios=None, quota=153, production_route=None):
    root.mkdir(mode=0o700)
    refs = {}
    for name, raw in packets().items():
        (root / name).write_bytes(raw)
        key = name.replace("-", "_").removesuffix(".json").removesuffix(".txt")
        refs[key] = {"path": name, "sha256": raw_hash(raw)}
    m = manifest(refs, fixture_route=fixture_route, scenarios=scenarios, quota=quota, production_route=production_route)
    (root / "manifest.json").write_bytes(encode(m)); validate_manifest(root, m, encode(m)); return m


def validate_manifest(root, m, raw):
    actual = packets()
    refs = {name.replace("-", "_").removesuffix(".json").removesuffix(".txt"):
        {"path": name, "sha256": raw_hash(value)} for name,value in actual.items()}
    if any(read_file(root,n) != b for n,b in actual.items()): raise ValueError("lower_assurance_packet_changed")
    q = m["production_campaign"]
    base.validate_route(q["fixture_route"], fixture=True); base.validate_route(q["production_route"], fixture=False)
    if type(m["simulated_budget_units"]) is not int or not 1 <= m["simulated_budget_units"] <= 153:
        raise ValueError("lower_assurance_reservation_budget")
    scenarios = m["transport"]["scenarios"]
    if (set(scenarios)-{p["id"] for p in m["positions"]} or any(s not in {
        "valid", "invalid_assessment", "identity_unknown", "identity_mismatch", "http_500", "empty_claims", "bad_quote",
        "cli_timeout", "cli_interrupt", "cli_tools", "cli_model", "cli_filesystem", "cli_namespace", "cli_credential_echo"} for s in scenarios.values())
            or not m["simulation_only"] and scenarios): raise ValueError("lower_assurance_fault_binding")
    expected = manifest(refs, fixture_route=q["fixture_route"], scenarios=scenarios,
        quota=m["simulated_budget_units"], production_route=q["production_route"])
    for key in ("adapter", "bootstrap"):
        expected["transport"]["specification"]["bindings"][key]["path"] = m["transport"]["specification"]["bindings"][key]["path"]
    expected["transport"]["configuration_sha256"] = digest(expected["transport"]["specification"])
    expected["manifest_sha256"] = digest({k:v for k,v in expected.items() if k != "manifest_sha256"})
    if m != expected or raw != encode(m): raise ValueError("lower_assurance_manifest_or_designation_changed")
    return m, raw


def require_execution(m):
    if not m["simulation_only"]:
        from .admission import require_authorisation
        require_authorisation(m)


def envelope_for(m, p, sealed):
    env = base.envelope_for(m, p, sealed)
    env.update(broker_contract=VERSION, assurance_sha256=digest(m["assurance"]))
    if p["kind"] == "generator":
        env["destination"] = {"transport": "subscription_CLI", "provider": p["identity"]["provider"],
                              "binary_sha256": m["production_campaign"]["routes"][p["route"]]["binary_sha256"]}
    env["idempotency_token"] = digest({"broker": VERSION, "attempt": env["attempt_id"], "request": env["request_sha256"]})
    return env


def request_for(m, p, receipts, root, *, captured=None):
    req = base.request_for(m, p, receipts, root, captured=captured)
    req.update(schema=VERSION+"-sealed-request", assurance=m["assurance"], assurance_sha256=digest(m["assurance"]))
    req["launch_authorisation_sha256"] = None if m["simulation_only"] else raw_hash(read_file(root,"launch-authorisation.json"))
    return req


def outcome(p, req, rec):
    if p["kind"] == "specialist": return base.outcome(p, req, rec)
    from .cli import parsed_outcome
    return parsed_outcome(p, req, rec)
