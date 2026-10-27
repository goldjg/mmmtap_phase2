"""Strict raw-bound observations, never a conversion to frozen v2 judgments.

JSON number tokens are stored as decimal strings, with their exact provider
lexemes. This avoids binary-float rounding even for values beyond float64.
Object member order has no meaning; claim order comes ONLY from the sealed
request assessment and must match the caller's frozen claim-ID sequence.
"""
import base64
from decimal import Decimal
import json

from . import VERSION
from ..model import decode, digest, encode, raw_hash

CATALOG = "mmmtap-matched-question-pack-v1"
FIXED = {
    "uncertainty_adequate": {"type": "noul", "instructions": "Are the assessment uncertainties warranted by the source?"},
    "authority_promoted": {"type": "noul", "instructions": "Does the assessment treat an unsupported authority assertion as a fact?"},
}
CHOICE = {"type": "choice", "instructions": "Which side effect is explicitly implemented in the supplied source?",
          "criteria": {"file_write": "Writes a file", "network": "Sends a network request", "none": "No file or network operation"}}


class Number(str):
    """Original JSON numerical token; distinct from a JSON string or bool."""


def exact_json(raw):
    def unique(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError("duplicate_json_key:" + k)
            obj[k] = v
        return obj
    def reject(value):
        raise ValueError("nonfinite_json:" + value)
    if not isinstance(raw, bytes) or len(raw) > 8 << 20:
        raise ValueError("typed_raw_bytes_or_capacity")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_float=Number, parse_int=Number, parse_constant=reject)
    except RecursionError as exc:
        raise ValueError("typed_json_nesting_limit") from exc


def probability(value):
    if type(value) is not Number or not Decimal(value).is_finite() or not 0 <= Decimal(value) <= 1:
        raise ValueError("invalid_probability_number")
    return str(value)


def bindings(request_raw, source_raw, assessment, claim_ids, *, qualification_choice=False):
    request = decode(request_raw)
    if set(request) != {"model", "state", "questions"} or not isinstance(request["model"], str) or not request["model"]:
        raise ValueError("typed_request_shape")
    if not isinstance(request["state"], str):
        raise ValueError("typed_request_state")
    state = decode(request["state"])
    if (set(state) != {"task", "untrusted_source", "source_sha256", "assessment"}
            or not isinstance(state["task"], str) or not state["task"]
            or state["source_sha256"] != raw_hash(source_raw)
            or state["untrusted_source"] != source_raw.decode("utf-8")
            or encode(state["assessment"]) != encode(assessment)):
        raise ValueError("source_or_assessment_binding_mismatch")
    claims = assessment["claims"]
    ids = [c["claim_id"] for c in claims]
    if (not claims or any(type(i) is not str or not i for i in ids)
            or len(set(ids)) != len(ids) or ids != claim_ids):
        raise ValueError("frozen_claim_order_mismatch")
    questions = dict(FIXED)
    for i in range(len(claims)):
        questions[f"claim_{i:04d}_supported"] = {
            "type": "noul", "instructions": f"Is assessment.claims[{i}] materially supported by exact source evidence?"}
    if qualification_choice:
        questions["side_effect_choice"] = CHOICE
    if request["questions"] != questions:
        raise ValueError("exact_question_catalog_mismatch")
    return request


def unavailable_reference(claim_ids):
    reasons = {
        "source_entailment": "source-support Noul is not a frozen v2 entailment judgment",
        "independent_verification": "not asked by this question catalog",
        "impact_inference": "not asked by this question catalog",
        "evidence_policy_justification": "requires separate reference/adjudication; cARL challenge is not justification",
        "labels": "no provider labels returned",
        "support_degree_scores": "Noul is probability of yes, not degree of support",
        "provider_rationales": "no provider rationale field returned",
        "provider_selected_quotations": "no provider-selected quotation field returned; input quotes have generator origin",
    }
    return {"layer": "independent_reference_adjudication", "claim_ids": claim_ids,
            "fields": {k: {"status": "unavailable", "value": None, "reason": v} for k, v in reasons.items()}}


def parse(request_raw, response_raw, *, source_raw, assessment, claim_ids,
          request_sha256, response_sha256, qualification_choice=False, response_metadata=None):
    if raw_hash(request_raw) != request_sha256 or raw_hash(response_raw) != response_sha256:
        raise ValueError("typed_request_or_response_digest_mismatch")
    request = bindings(request_raw, source_raw, assessment, claim_ids, qualification_choice=qualification_choice)
    entity = exact_json(response_raw)
    if (type(entity) is not dict or set(entity) - {"model", "answers", "usage"}
            or not {"model", "answers"} <= set(entity)):
        raise ValueError("typed_response_fields")
    model = entity["model"]
    if (type(model) is not str or not model or model.strip() != model
            or any(ord(c) < 32 or ord(c) == 127 for c in model)):
        raise ValueError("typed_returned_model")
    answers = entity["answers"]
    if type(answers) is not dict or set(answers) != set(request["questions"]):
        raise ValueError("exact_answer_ids_mismatch")
    observations, auxiliary = [], {}
    for name, question in request["questions"].items():
        answer = answers[name]
        if type(answer) is not dict or answer.get("type") != question["type"]:
            raise ValueError("exact_answer_type_mismatch:" + name)
        if question["type"] == "noul":
            if set(answer) != {"type", "noul"}:
                raise ValueError("exact_noul_shape:" + name)
            item = {"question_id": name, "question": question,
                    "noul_decimal": probability(answer["noul"]), "measurement": "probability_of_yes",
                    "response_pointer": "/answers/" + name, "response_sha256": response_sha256,
                    "scope": "assessment"}
            if name.startswith("claim_"):
                index = int(name[len("claim_"):-len("_supported")])
                item.update(scope="claim", claim_index=index, claim_id=claim_ids[index])
            observations.append(item)
        else:
            if (set(answer) != {"type", "choice", "confidence", "probabilities"}
                    or type(answer["choice"]) is not str or answer["choice"] not in question["criteria"]
                    or type(answer["probabilities"]) is not dict
                    or set(answer["probabilities"]) != set(question["criteria"])):
                raise ValueError("exact_choice_shape")
            probs = {k: probability(v) for k, v in answer["probabilities"].items()}
            if abs(sum(Decimal(p) for p in probs.values()) - 1) > Decimal("0.001"):
                raise ValueError("choice_probability_sum")
            auxiliary[name] = {"scope": "supplied_source", "question": question, "choice": answer["choice"],
                               "confidence_decimal": probability(answer["confidence"]),
                               "probabilities_decimal": probs, "response_pointer": "/answers/" + name}
    usage = entity.get("usage")
    if usage is not None:
        counters = {"input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens", "total_tokens"}
        if (type(usage) is not dict or set(usage) - counters
                or any(type(n) is not Number or not n.isdigit() or int(n) > 9223372036854775807 for n in usage.values())):
            raise ValueError("typed_usage")
        usage = {k: int(v) for k, v in usage.items()}
    return {"schema": VERSION, "direct_systemone": {
        "request_sha256": request_sha256, "response_sha256": response_sha256,
        "source_sha256": raw_hash(source_raw), "assessment_sha256": digest(assessment),
        "request_state_sha256": raw_hash(request["state"].encode()), "claim_ids_in_request_order": claim_ids,
        "catalog": {"version": CATALOG, "sha256": digest({"schema": CATALOG, "fixed": FIXED, "per_claim": {
            "id_format": "claim_%04d_supported", "type": "noul",
            "instructions_format": "Is assessment.claims[%d] materially supported by exact source evidence?"}}),
                    "qualification_extension": "historical-side-effect-choice-v1" if qualification_choice else None},
        "question_bindings": request["questions"], "questions_sha256": digest(request["questions"]),
        "observations": observations, "auxiliary_observations": auxiliary,
        "returned_model": {"value": model, "provenance": "provider_entity_model_self_report_not_identity_attestation",
                           "response_pointer": "/model"},
        "usage": usage, "usage_provenance": "/usage" if "usage" in entity else None,
        "response_metadata": response_metadata or {},
        "unavailable": {
            "provider_request_attestation": "provider does not echo or sign request digest; association is local custody",
            "provider_selected_quotations": "absent from returned entity",
            "provider_rationales": "absent from returned entity",
            **({"usage": "absent from returned entity"} if "usage" not in entity else
               {"usage": "provider returned null"} if usage is None else {})}},
        "reference_judgments": unavailable_reference(claim_ids), "derived_carl": None,
        "authority": "untrusted_observation_no_governing_policy_or_release_authority"}


def derive_carl(observation, prepared_raw, assessment):
    """Replay ONLY a captured historical policy. No new/default thresholds.

    Never calls cARL, compiles a new pack, or accepts free-standing rule input.
    The replay loader separately pins the entire original prepared artifact.
    """
    prepared = decode(prepared_raw)
    policy = prepared["policy"]
    direct = observation["direct_systemone"]
    if digest(assessment) != direct["assessment_sha256"]:
        raise ValueError("policy_assessment_binding")
    captured = decode(base64.b64decode(prepared["input"], validate=True))
    if (encode(captured["assessment"]) != encode(assessment)
            or raw_hash(base64.b64decode(captured["native_request"], validate=True)) != direct["request_sha256"]):
        raise ValueError("policy_request_binding")
    definitions = []
    for entry in policy["trace"]["policies"]:
        raw = base64.b64decode(prepared["policy_files"][entry["canonicalDefinition"]], validate=True)
        definitions.append({"id": entry["id"], "version": entry["version"], "sha256": raw_hash(raw),
                            "path": entry["canonicalDefinition"], "applied": entry["applied"]})
    signals = {o["question_id"]: o["noul_decimal"] for o in direct["observations"]}
    predicates, challenges, disposition = [], [], "no_challenge"
    for bound in policy["rules"]:
        rule = bound["rule"]
        if not any(p["id"] == bound["pack"] and p["sha256"] == bound["pack_sha256"] and p["applied"] for p in definitions):
            raise ValueError("policy_pack_binding")
        if rule["signal"] not in ("claim_supported", "uncertainty_adequate", "authority_promoted") or rule["operator"] not in ("lt", "ge"):
            raise ValueError("unsupported_captured_rule")
        if rule["action"] not in ("challenge_required", "insufficient_evidence"):
            raise ValueError("policy_action_not_challenge")
        targets = ([o for o in direct["observations"] if o["scope"] == "claim"] if rule["signal"] == "claim_supported" else
                   [o for o in direct["observations"] if o["question_id"] == rule["signal"]])
        for target in targets:
            value = Decimal(target["noul_decimal"])
            threshold = Decimal(str(rule["threshold"]))
            matched = value < threshold if rule["operator"] == "lt" else value >= threshold
            dependency = {"response_sha256": direct["response_sha256"], "response_pointer": target["response_pointer"],
                          "question_id": target["question_id"], "scope": target["scope"]}
            predicates.append({"pack": bound["pack"], "rule_id": rule["id"], "rule": rule,
                               "dependency": dependency, "observed_noul_decimal": str(value), "matched": matched})
            if not matched:
                continue
            challenge = {"question_id": target["question_id"], "pack": bound["pack"], "rule": rule["id"],
                         "action": rule["action"], "evidence_quotes": []}
            if target["scope"] == "claim":
                index = target["claim_index"]
                challenge.update(claim_id=target["claim_id"], evidence_quotes=assessment["claims"][index]["evidence_quotes"])
            challenges.append(challenge)
            if disposition != "insufficient_evidence":
                disposition = rule["action"]
    return {"schema": VERSION + "-derived-carl", "origin": "deterministic_captured_policy_replay_not_judge",
            "prepared_sha256": raw_hash(prepared_raw), "policy_sha256": digest(policy),
            "policy_files_sha256": {k: raw_hash(base64.b64decode(v, validate=True)) for k, v in prepared["policy_files"].items()},
            "policy_identity": definitions, "implementation_sha256": prepared["implementation_sha256"],
            "policy_version": "carl-assessment-policy-v1", "threshold_approval": "not_approved_historical_replay_only",
            "predicates": predicates, "signals_decimal": signals, "challenges": challenges, "disposition": disposition,
            "quote_provenance": {"origin": "generator_assessment_input_not_provider_selection",
                                 "assessment_sha256": direct["assessment_sha256"],
                                 "claim_quote_pointers": {c["claim_id"]: f"/claims/{i}/evidence_quotes" for i, c in enumerate(assessment["claims"])}},
            "authority": "untrusted_challenge_not_generator_instruction", "governing_authority": False, "release_authority": False}
