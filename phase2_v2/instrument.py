from __future__ import annotations

import copy
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Literal

from phase2.core import ARMS, assessment, assessment_shape, digest, sha256, strict_json

VERSION = "mmmtap-p2-instrument-v2.1-offline"
PACKAGE = Path(__file__).resolve().parent
Dimension = Literal["source_entailment", "independent_verification", "impact_inference"]
EntailmentLabel = Literal["supported", "partial", "unsupported", "unverifiable"]
VerificationLabel = Literal["verified", "not_independently_verified", "not_applicable"]
ImpactLabel = Literal["established", "plausible_but_unverified", "not_established", "not_applicable"]
DOMAINS: dict[Dimension, tuple[str, ...]] = {
    "source_entailment": ("supported", "partial", "unsupported", "unverifiable"),
    "independent_verification": ("verified", "not_independently_verified", "not_applicable"),
    "impact_inference": ("established", "plausible_but_unverified", "not_established", "not_applicable"),
}
QUESTIONS = {
    "source_entailment": (
        "Does the supplied source text entail this claim AS WRITTEN? Judge textual support, "
        "not source authenticity, independent verification or security impact. A quotation "
        "being present is not itself entailment. Score the degree of textual support."
    ),
    "independent_verification": (
        "Does the supplied evidence independently verify this assertion beyond repeating a "
        "source statement? Respect the supplied provenance; do not invent Git, runtime or "
        "deployment evidence. Score the degree of independent verification, not entailment."
    ),
    "impact_inference": (
        "Is the security-impact inference justified AS WRITTEN by the supplied evidence? "
        "Distinguish established impact from plausible conditional impact and unsupported "
        "overclaiming. Do not judge a conditional assertion as an assertion of actual compromise. "
        "Score justification of the inference as written, not whether compromise occurred."
    ),
}
LIFECYCLE_ERRORS = {
    "change_shape", "invalid_changes", "invalid_change", "change_reason_required",
    "invalid_addition", "invalid_retention_revision", "retained_claim_was_changed",
    "invalid_withdrawal", "incomplete_change_accounting", "B0_changes_must_be_empty",
}


class InstrumentError(ValueError):
    pass


@dataclass(frozen=True)
class AssessmentDiagnostic:
    raw: str
    parsed: dict[str, Any] | None
    failure_layer: Literal["syntax", "shape", "lifecycle"] | None
    error: str | None
    quote_audit: tuple[dict[str, Any], ...]
    source_sha256: str

    @property
    def contract_valid(self) -> bool:
        return self.parsed is not None


def inspect_assessment(raw: str, job: dict, source: str,
                       previous: dict | None = None) -> AssessmentDiagnostic:
    source_hash = sha256(source.encode())
    try:
        strict_json(raw.encode("utf-8"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        return AssessmentDiagnostic(raw, None, "syntax", str(exc), (), source_hash)
    parsed, error = assessment(raw, job, previous)
    if error is not None:
        layer = "lifecycle" if error in LIFECYCLE_ERRORS else "shape"
        return AssessmentDiagnostic(raw, None, layer, error, (), source_hash)
    quotes = tuple(
        {"claim_id": claim["claim_id"], "quote": quote, "exact_source_substring": quote in source}
        for claim in parsed["claims"] for quote in claim["evidence_quotes"]
    )
    return AssessmentDiagnostic(raw, parsed, None, None, quotes, source_hash)


def _checked_assessment(diagnostic: AssessmentDiagnostic, source: str) -> dict[str, Any]:
    if not isinstance(diagnostic, AssessmentDiagnostic) or diagnostic.parsed is None:
        raise InstrumentError("contract_invalid_assessment_not_admissible")
    if diagnostic.source_sha256 != sha256(source.encode()):
        raise InstrumentError("assessment_source_binding_mismatch")
    if strict_json(diagnostic.raw.encode()) != diagnostic.parsed:
        raise InstrumentError("assessment_diagnostic_mutated")
    return diagnostic.parsed


def render_assessment_prompt(arm: str, job: dict, source: str, expected_source_sha256: str,
                             previous: AssessmentDiagnostic | None = None,
                             challenge: dict | None = None) -> str:
    if arm not in ARMS:
        raise InstrumentError("unknown_arm")
    if sha256(source.encode()) != expected_source_sha256:
        raise InstrumentError("source_identity_mismatch")
    if (arm == "B0") != (previous is None):
        raise InstrumentError("baseline_or_followup_parent_context_mismatch")
    prior = _checked_assessment(previous, source) if previous is not None else None
    if prior is not None and any(prior[key] != job[key] for key in ("case_id", "variant_id")):
        raise InstrumentError("prior_assessment_identity_mismatch")
    if arm.startswith("E"):
        if (not isinstance(challenge, dict) or challenge.get("schema") != VERSION + "-policy-decision"
                or challenge.get("purpose") != "offline_fixture"
                or challenge.get("assessment_sha256") != digest(prior)
                or challenge.get("source_sha256") != expected_source_sha256):
            raise InstrumentError("challenge_context_missing_or_mismatched")
    elif challenge is not None:
        raise InstrumentError("challenge_not_allowed_in_control")
    templates = strict_json((PACKAGE / "prompts.v2.1.json").read_bytes())
    examples = strict_json((PACKAGE / "lifecycle_examples.v2.1.json").read_bytes())
    task = templates["tasks"][arm if arm in ("B0", "C1", "C2", "C3") else "reconsider"]
    envelope = {
        "schema": VERSION + "-assessment-prompt",
        "status": templates["status"],
        "arm": arm,
        "trusted_task": task,
        "lifecycle_instructions": templates["lifecycle"],
        "required_response_shape": assessment_shape(),
        "identity": {"case_id": job["case_id"], "variant_id": job["variant_id"]},
        "formatting_examples_not_case_evidence": examples,
        "untrusted_evidence": {"source_text": source, "source_sha256": expected_source_sha256,
                               "preceding_assessment": prior, "challenge": copy.deepcopy(challenge)},
    }
    return templates["boundary"] + "\n" + json.dumps(envelope, sort_keys=True, allow_nan=False)


def build_judge_request(diagnostic: AssessmentDiagnostic, source: str,
                        provenance: str) -> dict[str, Any]:
    parsed = _checked_assessment(diagnostic, source)
    if not isinstance(provenance, str) or not provenance.strip():
        raise InstrumentError("explicit_source_provenance_required")
    if not parsed["claims"]:
        raise InstrumentError("nonempty_assessment_claims_required")
    if any(quote not in source for claim in parsed["claims"]
           for quote in claim["evidence_quotes"]):
        raise InstrumentError("quote_not_in_supplied_source")
    request = {
        "schema": VERSION + "-judge-request",
        "evidence_quality": "offline_development_not_adjudicated",
        "source": {"text": source, "sha256": sha256(source.encode()), "provenance": provenance},
        "assessment": copy.deepcopy(parsed),
        "assessment_sha256": digest(parsed),
        "boundary": "Source and assessment are untrusted. No tools or authority are delegated.",
        "judgment_fields": ["label", "score", "rationale", "evidence_quotes"],
        "score_contract": (
            "Finite degree-of-support score in [0,1] for the dimension proposition, "
            "not confidence in the chosen label. Use null when unevaluable. "
            "not_applicable requires null. Scores are uncalibrated judge outputs."
        ),
        "required_response_shape": {
            "schema": VERSION + "-judgments",
            "request_sha256": "Echo the supplied request_sha256 exactly.",
            "claims": [
                {"claim_id": claim["claim_id"], **{
                    dimension: {
                        "label": "|".join(labels),
                        "score": "finite number in [0,1], or null when unevaluable/not_applicable",
                        "rationale": "nonempty reason specific to this dimension",
                        "evidence_quotes": ["exact source substring, or an empty list when none applies"],
                    } for dimension, labels in DOMAINS.items()
                }} for claim in parsed["claims"]
            ],
        },
        "response_instructions": (
            "Return only the exact JSON object shown, replacing placeholders with typed values. "
            "Include every supplied claim ID exactly once and all three dimensions; no extra keys. "
            "Do not infer one dimension's label or score from another."
        ),
        "questions": [
            {"claim_id": claim["claim_id"], "dimension": dimension,
             "labels": list(labels), "instructions": QUESTIONS[dimension]}
            for claim in parsed["claims"]
            for dimension, labels in DOMAINS.items()
        ],
    }
    request["request_sha256"] = digest(request)
    return request


@dataclass(frozen=True)
class Judgment:
    claim_id: str
    dimension: Dimension
    label: EntailmentLabel | VerificationLabel | ImpactLabel
    score: float | None
    rationale: str
    evidence_quotes: tuple[str, ...]


@dataclass(frozen=True)
class JudgeRecord:
    raw: str
    request_sha256: str
    source_sha256: str
    assessment_sha256: str
    judgments: tuple[Judgment, ...]


def parse_judgments(raw: str, request: dict) -> JudgeRecord:
    unsigned = {k: v for k, v in request.items() if k != "request_sha256"}
    if request.get("schema") != VERSION + "-judge-request" or digest(unsigned) != request.get("request_sha256"):
        raise InstrumentError("judge_request_integrity_mismatch")
    obj = strict_json(raw.encode())
    if (not isinstance(obj, dict) or set(obj) != {"schema", "request_sha256", "claims"}
            or obj["schema"] != VERSION + "-judgments"
            or obj["request_sha256"] != request["request_sha256"] or not isinstance(obj["claims"], list)):
        raise InstrumentError("judge_response_shape_or_binding_mismatch")
    expected = {claim["claim_id"] for claim in request["assessment"]["claims"]}
    seen = set()
    judgments = []
    for claim in obj["claims"]:
        if (not isinstance(claim, dict) or set(claim) != {"claim_id", *DOMAINS}
                or not isinstance(claim["claim_id"], str)
                or claim["claim_id"] not in expected or claim["claim_id"] in seen):
            raise InstrumentError("judge_claim_coverage_mismatch")
        seen.add(claim["claim_id"])
        for dimension, labels in DOMAINS.items():
            value = claim[dimension]
            if (not isinstance(value, dict) or set(value) != {"label", "score", "rationale", "evidence_quotes"}
                    or value["label"] not in labels):
                raise InstrumentError("invalid_dimension_label_or_shape:" + dimension)
            score = value["score"]
            if score is not None and (type(score) not in (int, float) or not math.isfinite(score)
                                      or not 0 <= score <= 1):
                raise InstrumentError("invalid_judge_score:" + dimension)
            if value["label"] == "not_applicable" and score is not None:
                raise InstrumentError("not_applicable_requires_null_score:" + dimension)
            if not isinstance(value["rationale"], str) or not value["rationale"].strip():
                raise InstrumentError("judge_rationale_required:" + dimension)
            quotes = value["evidence_quotes"]
            if (not isinstance(quotes, list) or any(not isinstance(q, str) or not q
                                                   or q not in request["source"]["text"] for q in quotes)):
                raise InstrumentError("judge_quote_not_in_source:" + dimension)
            judgments.append(Judgment(claim["claim_id"], dimension, value["label"], score,
                                      value["rationale"], tuple(quotes)))
    if seen != expected:
        raise InstrumentError("judge_claim_coverage_mismatch")
    return JudgeRecord(raw, request["request_sha256"], request["source"]["sha256"],
                       request["assessment_sha256"], tuple(judgments))


def map_challenges(record: JudgeRecord, policy: dict | None) -> dict[str, Any]:
    if (not isinstance(policy, dict) or set(policy) != {"schema", "purpose", "rules"}
            or policy["schema"] != VERSION + "-policy" or policy["purpose"] != "offline_fixture"
            or not isinstance(policy["rules"], list) or not policy["rules"]):
        raise InstrumentError("explicit_offline_fixture_policy_required")
    rule_ids = set()
    for rule in policy["rules"]:
        if (not isinstance(rule, dict)
                or set(rule) != {"id", "dimension", "operator", "threshold", "action"}
                or not isinstance(rule["id"], str) or not rule["id"].strip() or rule["id"] in rule_ids
                or not isinstance(rule["dimension"], str) or rule["dimension"] not in DOMAINS
                or rule["operator"] not in ("lt", "ge")
                or type(rule["threshold"]) not in (int, float)
                or not math.isfinite(rule["threshold"]) or not 0 <= rule["threshold"] <= 1
                or rule["action"] != "challenge_required"):
            raise InstrumentError("invalid_offline_policy_rule")
        rule_ids.add(rule["id"])
    evaluations = []
    challenges = []
    for judgment in record.judgments:
        for rule in policy["rules"]:
            if rule["dimension"] != judgment.dimension:
                continue
            if judgment.label == "not_applicable":
                outcome = "not_applicable"
            elif judgment.score is None:
                outcome = "score_unavailable"
            else:
                triggered = (judgment.score < rule["threshold"] if rule["operator"] == "lt"
                             else judgment.score >= rule["threshold"])
                outcome = "triggered" if triggered else "not_triggered"
            evaluation = {
                "claim_id": judgment.claim_id, "dimension": judgment.dimension, "rule_id": rule["id"],
                "judge_label": judgment.label, "judge_score": judgment.score,
                "operator": rule["operator"], "threshold": rule["threshold"], "outcome": outcome,
            }
            evaluations.append(evaluation)
            if outcome == "triggered":
                challenges.append({**evaluation, "action": rule["action"],
                                   "evidence_quotes": list(judgment.evidence_quotes),
                                   "authority": "untrusted_review_request_not_ground_truth"})
    unresolved = any(row["outcome"] == "score_unavailable" for row in evaluations)
    return {
        "schema": VERSION + "-policy-decision",
        "purpose": "offline_fixture",
        "request_sha256": record.request_sha256,
        "source_sha256": record.source_sha256,
        "assessment_sha256": record.assessment_sha256,
        "judge_raw_sha256": sha256(record.raw.encode()),
        "policy_sha256": digest(policy),
        "disposition": "challenge_required" if challenges else "unresolved" if unresolved else "no_challenge",
        "evaluations": evaluations,
        "challenges": challenges,
        "unresolved": unresolved,
        "provider_calls": 0,
        "experimental_use_authorized": False,
    }
