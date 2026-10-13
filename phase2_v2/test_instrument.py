from __future__ import annotations

import base64
import copy
from collections import Counter
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

from phase2.core import ARMS, assessment, sha256
from .continuation import plan_continuation
from .instrument import (
    InstrumentError, VERSION, build_judge_request, inspect_assessment,
    map_challenges, parse_judgments, render_assessment_prompt,
)

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
EXAMPLES = json.loads((PACKAGE / "lifecycle_examples.v2.1.json").read_text())
FIXTURES = json.loads((PACKAGE / "challenge_fixtures.v2.1.json").read_text())
JOB = {"case_id": "offline-docs", "variant_id": "baseline"}


def fixture_context(case: dict) -> tuple:
    job = {"case_id": case["case_id"], "variant_id": "baseline"}
    obj = {**job, "claims": [case["claim"]], "disposition": "review_required",
           "uncertainties": [], "changes": []}
    diagnostic = inspect_assessment(json.dumps(obj), job, case["source"])
    request = build_judge_request(diagnostic, case["source"], "authored_supplied_description")
    response = {"schema": VERSION + "-judgments", "request_sha256": request["request_sha256"],
                "claims": [{"claim_id": case["claim"]["claim_id"], **copy.deepcopy(case["judgments"])}]}
    return job, obj, request, response


class AssessmentInstrumentTests(TestCase):
    def test_all_examples_comply_with_unchanged_strict_validator(self) -> None:
        prior = EXAMPLES["prior"]
        self.assertIsNone(assessment(json.dumps(prior), JOB)[1])
        for example in EXAMPLES["examples"]:
            with self.subTest(name=example["name"]):
                raw = json.dumps(example["response"])
                result = inspect_assessment(raw, JOB, EXAMPLES["source"], prior)
                self.assertTrue(result.contract_valid)
                self.assertEqual(result.parsed, assessment(raw, JOB, prior)[0])
                self.assertTrue(all(row["exact_source_substring"] for row in result.quote_audit))
                self.assertEqual(result.raw, raw)

    def test_syntax_shape_and_lifecycle_failures_are_not_repaired(self) -> None:
        prior = EXAMPLES["prior"]
        response = copy.deepcopy(EXAMPLES["examples"][0]["response"])
        malformed = [("{", "syntax"), ('{"x":1,"x":2}', "syntax"),
                     ('{"x":NaN}', "syntax"), ('{"x":Infinity}', "syntax")]
        extra = {**response, "uncertainties_note": "extra field"}
        malformed.append((json.dumps(extra), "shape"))
        missing = {**response, "changes": []}
        malformed.append((json.dumps(missing), "lifecycle"))
        for field, value in (("claim", "Reworded claim"), ("confidence", 0.8),
                             ("limitations", ["Changed limit"]), ("evidence_quotes", ["Changed quote"])):
            revised = copy.deepcopy(response)
            revised["claims"][0][field] = value
            malformed.append((json.dumps(revised), "lifecycle"))
        malformed.append((json.dumps({**prior, "changes": response["changes"]}), "lifecycle"))
        for index, (raw, layer) in enumerate(malformed):
            with self.subTest(index=index):
                previous = None if index == len(malformed) - 1 else prior
                result = inspect_assessment(raw, JOB, EXAMPLES["source"], previous)
                self.assertFalse(result.contract_valid)
                self.assertIsNone(result.parsed)
                self.assertEqual(result.failure_layer, layer)
                self.assertEqual(result.raw, raw)
                with self.assertRaisesRegex(InstrumentError, "not_admissible"):
                    build_judge_request(result, EXAMPLES["source"], "supplied_description")
                with self.assertRaisesRegex(InstrumentError, "not_admissible"):
                    render_assessment_prompt(
                        "C3", JOB, EXAMPLES["source"], sha256(EXAMPLES["source"].encode()), result,
                    )

    def test_quote_membership_is_separate_from_contract_compliance(self) -> None:
        obj = copy.deepcopy(EXAMPLES["prior"])
        obj["claims"][0]["evidence_quotes"] = ["Not present in source"]
        result = inspect_assessment(json.dumps(obj), JOB, EXAMPLES["source"])
        self.assertTrue(result.contract_valid)
        self.assertFalse(result.quote_audit[0]["exact_source_substring"])
        with self.assertRaisesRegex(InstrumentError, "quote_not_in"):
            build_judge_request(result, EXAMPLES["source"], "supplied_description")
        empty = {**EXAMPLES["prior"], "claims": []}
        result = inspect_assessment(json.dumps(empty), JOB, EXAMPLES["source"])
        self.assertTrue(result.contract_valid)
        with self.assertRaisesRegex(InstrumentError, "nonempty_assessment"):
            build_judge_request(result, EXAMPLES["source"], "supplied_description")

    def test_control_prompts_explain_lifecycle_and_do_not_add_challenges(self) -> None:
        for arm in ("B0", "C1", "C2", "C3"):
            with self.subTest(arm=arm):
                prior = None if arm == "B0" else EXAMPLES["prior"]
                diagnostic = (inspect_assessment(json.dumps(prior), JOB, EXAMPLES["source"])
                              if prior is not None else None)
                rendered = render_assessment_prompt(
                    arm, JOB, EXAMPLES["source"], sha256(EXAMPLES["source"].encode()), diagnostic,
                )
                envelope = json.loads(rendered.split("\n", 1)[1])
                self.assertEqual(envelope["arm"], arm)
                self.assertEqual(envelope["untrusted_evidence"]["preceding_assessment"], prior)
                self.assertIsNone(envelope["untrusted_evidence"]["challenge"])
                lifecycle = " ".join(envelope["lifecycle_instructions"])
                self.assertIn("entire claim object", lifecycle)
                self.assertIn("union of preceding and current claims", lifecycle)
                self.assertIn("C1, C2 or either C3 turn", lifecycle)
                self.assertEqual(envelope["formatting_examples_not_case_evidence"], EXAMPLES)
        for arm, prior, digest in (("B0", EXAMPLES["prior"], sha256(EXAMPLES["source"].encode())),
                                  ("C3", None, sha256(EXAMPLES["source"].encode())),
                                  ("C2", EXAMPLES["prior"], "0" * 64)):
            with self.assertRaises(InstrumentError):
                render_assessment_prompt(arm, JOB, EXAMPLES["source"], digest, prior)

    def test_pilot_generator_contract_results_remain_identical_to_v1(self) -> None:
        pilot = ROOT / "operator_runs_v1/pilot"
        manifest = json.loads((pilot / "manifest.json").read_text())
        checked = 0
        counts = Counter()
        for job in manifest["jobs"]:
            if job["kind"] != "generator":
                continue
            folder = pilot / "checkpoints" / job["job_id"]
            result = json.loads((folder / "result.json").read_text())
            counts[result["status"]] += 1
            if result["status"] == "blocked_parent":
                continue
            raw = base64.b64decode(json.loads((folder / "raw.json").read_text())["message"]).decode()
            payload = json.loads((folder / "payload.json").read_text())["payload"]
            envelope = json.loads(payload.split("\n", 1)[1])
            evidence = envelope["untrusted_evidence"]
            previous = evidence["preceding_assessment"]
            inspected = inspect_assessment(raw, job, evidence["source_text"], previous)
            with self.subTest(job_id=job["job_id"]):
                self.assertEqual(inspected.parsed, result["parsed"])
                self.assertEqual(inspected.error, result["reason"])
                self.assertEqual(inspected.contract_valid, result["status"] == "ok")
            checked += 1
        self.assertEqual(checked, 91)
        self.assertEqual(counts, {"ok": 63, "schema_invalid": 28, "blocked_parent": 8})

    def test_invalid_lifecycle_transitions_and_claim_fields_stay_invalid(self) -> None:
        prior = EXAMPLES["prior"]
        base = EXAMPLES["examples"][0]["response"]
        invalid = []
        for field, value in (("confidence", True), ("claim_id", "invalid id"),
                             ("claim", ""), ("evidence_quotes", [""]), ("limitations", [None])):
            obj = copy.deepcopy(base)
            obj["claims"][0][field] = value
            invalid.append(obj)
        for action in ("added", "withdrawn", "invented"):
            obj = copy.deepcopy(base)
            obj["changes"][0]["action"] = action
            invalid.append(obj)
        invalid.append({**base, "changes": base["changes"] * 2})
        invalid.append({**base, "claims": base["claims"] * 2})
        obj = copy.deepcopy(base)
        obj["changes"][0]["reason"] = ""
        invalid.append(obj)
        obj = copy.deepcopy(base)
        obj["claims"] = []
        invalid.append(obj)
        obj = copy.deepcopy(base)
        obj["case_id"] = "wrong"
        invalid.append(obj)
        for index, obj in enumerate(invalid):
            with self.subTest(index=index):
                raw = json.dumps(obj)
                result = inspect_assessment(raw, JOB, EXAMPLES["source"], prior)
                self.assertFalse(result.contract_valid)
                self.assertEqual((result.parsed, result.error), assessment(raw, JOB, prior))
                self.assertEqual(result.raw, raw)


class ChallengeInstrumentTests(TestCase):
    def test_positive_negative_and_conditional_fixtures(self) -> None:
        for case in FIXTURES["cases"]:
            with self.subTest(case=case["case_id"]):
                _, _, request, response = fixture_context(case)
                raw = json.dumps(response)
                record = parse_judgments(raw, request)
                decision = map_challenges(record, FIXTURES["policy"])
                self.assertEqual([r["dimension"] for r in decision["challenges"]],
                                 case["expected_challenge_dimensions"])
                self.assertEqual(record.raw, raw)
                self.assertEqual(decision["request_sha256"], request["request_sha256"])
                self.assertFalse(decision["experimental_use_authorized"])
                self.assertEqual(len(record.judgments), 3)
                self.assertEqual(request["required_response_shape"]["schema"], VERSION + "-judgments")
                self.assertEqual(set(request["required_response_shape"]["claims"][0]),
                                 {"claim_id", "source_entailment", "independent_verification", "impact_inference"})
                self.assertEqual(request["assessment_sha256"], decision["assessment_sha256"])
                self.assertEqual(decision["provider_calls"], 0)

    def test_reordered_multiple_claims_bind_by_id_and_do_not_mutate_inputs(self) -> None:
        benign, unsupported = FIXTURES["cases"][:2]
        job, obj, _, _ = fixture_context(benign)
        obj["claims"].append(copy.deepcopy(unsupported["claim"]))
        diagnostic = inspect_assessment(json.dumps(obj), job, benign["source"])
        request = build_judge_request(diagnostic, benign["source"], "supplied_description")
        response = {
            "schema": VERSION + "-judgments", "request_sha256": request["request_sha256"],
            "claims": [{"claim_id": case["claim"]["claim_id"], **case["judgments"]}
                       for case in (unsupported, benign)],
        }
        before = copy.deepcopy((request, response, FIXTURES["policy"]))
        record = parse_judgments(json.dumps(response), request)
        decision = map_challenges(record, FIXTURES["policy"])
        self.assertEqual([r["claim_id"] for r in decision["challenges"]], ["permissions"])
        self.assertEqual((request, response, FIXTURES["policy"]), before)

    def test_missing_verification_does_not_become_source_contradiction(self) -> None:
        _, _, request, response = fixture_context(FIXTURES["cases"][0])
        record = parse_judgments(json.dumps(response), request)
        self.assertEqual(map_challenges(record, FIXTURES["policy"])["disposition"], "no_challenge")
        policy = copy.deepcopy(FIXTURES["policy"])
        policy["rules"] = [{"id": "test_verification_review", "dimension": "independent_verification",
                            "operator": "lt", "threshold": 0.5, "action": "challenge_required"}]
        decision = map_challenges(record, policy)
        self.assertEqual(decision["challenges"][0]["dimension"], "independent_verification")
        self.assertNotIn("unsupported_claim", json.dumps(decision))
        self.assertEqual(response["claims"][0]["source_entailment"]["score"], 0.95)

    def test_surprising_judge_score_is_preserved_not_overridden(self) -> None:
        _, _, request, response = fixture_context(FIXTURES["cases"][0])
        response["claims"][0]["source_entailment"]["score"] = 0.2
        record = parse_judgments(json.dumps(response), request)
        decision = map_challenges(record, FIXTURES["policy"])
        self.assertEqual(decision["challenges"][0]["judge_score"], 0.2)
        self.assertEqual(decision["challenges"][0]["judge_label"], "supported")
        self.assertEqual(decision["challenges"][0]["authority"], "untrusted_review_request_not_ground_truth")

    def test_threshold_boundaries_and_missing_scores_are_explicit(self) -> None:
        _, _, request, response = fixture_context(FIXTURES["cases"][0])
        for operator, score, outcome in (("lt", 0.499, "triggered"), ("lt", 0.5, "not_triggered"),
                                         ("ge", 0.5, "triggered"), ("ge", 0.499, "not_triggered"),
                                         ("lt", None, "score_unavailable")):
            with self.subTest(operator=operator, score=score):
                policy = copy.deepcopy(FIXTURES["policy"])
                policy["rules"] = [policy["rules"][0]]
                policy["rules"][0]["operator"] = operator
                response["claims"][0]["source_entailment"]["score"] = score
                record = parse_judgments(json.dumps(response), request)
                result = map_challenges(record, policy)
                self.assertEqual(result["evaluations"][0]["outcome"], outcome)
                self.assertEqual(result["unresolved"], score is None)
                if score is None:
                    self.assertEqual(result["disposition"], "unresolved")

    def test_judgment_shape_coverage_binding_and_numeric_failures(self) -> None:
        _, _, request, response = fixture_context(FIXTURES["cases"][0])
        variants = []
        bad = copy.deepcopy(response)
        bad["request_sha256"] = "0" * 64
        variants.append(bad)
        variants.append({**response, "claims": []})
        variants.append({**response, "claims": response["claims"] * 2})
        for dimension, key, value in (
            ("source_entailment", "label", "verified"),
            ("source_entailment", "score", True),
            ("source_entailment", "score", -0.1),
            ("source_entailment", "score", 1.1),
            ("source_entailment", "rationale", ""),
            ("source_entailment", "evidence_quotes", ["invented"]),
            ("impact_inference", "score", 0.5),
        ):
            bad = copy.deepcopy(response)
            bad["claims"][0][dimension][key] = value
            variants.append(bad)
        bad = copy.deepcopy(response)
        del bad["claims"][0]["impact_inference"]
        variants.append(bad)
        for index, obj in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(InstrumentError):
                parse_judgments(json.dumps(obj), request)
        for value in ("NaN", "Infinity", "-Infinity"):
            raw = json.dumps(response).replace('"score": 0.95', '"score": ' + value)
            with self.assertRaises(ValueError):
                parse_judgments(raw, request)
        duplicate = json.dumps(response).replace(
            '"score": 0.95', '"score": 0.95, "score": 0.1',
        )
        with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
            parse_judgments(duplicate, request)
        mutated = copy.deepcopy(request)
        mutated["source"]["text"] = "changed"
        with self.assertRaisesRegex(InstrumentError, "integrity_mismatch"):
            parse_judgments(json.dumps(response), mutated)

    def test_request_source_binding_and_no_experimental_policy_defaults(self) -> None:
        job, obj, _, _ = fixture_context(FIXTURES["cases"][0])
        source = FIXTURES["cases"][0]["source"]
        diagnostic = inspect_assessment(json.dumps(obj), job, source)
        with self.assertRaisesRegex(InstrumentError, "binding_mismatch"):
            build_judge_request(diagnostic, "different source", "description")
        diagnostic.parsed["claims"][0]["confidence"] = 0.5
        with self.assertRaisesRegex(InstrumentError, "diagnostic_mutated"):
            build_judge_request(diagnostic, source, "description")
        _, _, request, response = fixture_context(FIXTURES["cases"][0])
        record = parse_judgments(json.dumps(response), request)
        for policy in (None, {}, {**FIXTURES["policy"], "purpose": "experimental"}):
            with self.assertRaisesRegex(InstrumentError, "explicit_offline"):
                map_challenges(record, policy)
        policy = copy.deepcopy(FIXTURES["policy"])
        policy["rules"][0]["threshold"] = True
        with self.assertRaisesRegex(InstrumentError, "invalid_offline"):
            map_challenges(record, policy)
        for field, value in (("threshold", float("nan")), ("threshold", -0.1),
                             ("dimension", "claim_supported"), ("operator", "le"),
                             ("action", "deploy")):
            policy = copy.deepcopy(FIXTURES["policy"])
            policy["rules"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(InstrumentError):
                map_challenges(record, policy)
        policy = copy.deepcopy(FIXTURES["policy"])
        policy["rules"] *= 2
        with self.assertRaisesRegex(InstrumentError, "invalid_offline"):
            map_challenges(record, policy)

    def test_existing_arms_and_challenge_binding(self) -> None:
        case = FIXTURES["cases"][0]
        job, prior, request, response = fixture_context(case)
        decision = map_challenges(parse_judgments(json.dumps(response), request), FIXTURES["policy"])
        diagnostic = inspect_assessment(json.dumps(prior), job, case["source"])
        for arm in ARMS:
            with self.subTest(arm=arm):
                text = render_assessment_prompt(
                    arm, job, case["source"], sha256(case["source"].encode()),
                    None if arm == "B0" else diagnostic, decision if arm.startswith("E") else None,
                )
                envelope = json.loads(text.split("\n", 1)[1])
                self.assertEqual(envelope["untrusted_evidence"]["challenge"],
                                 decision if arm.startswith("E") else None)
        with self.assertRaisesRegex(InstrumentError, "not_allowed_in_control"):
            render_assessment_prompt("C3", job, case["source"], sha256(case["source"].encode()), diagnostic, decision)
        with self.assertRaisesRegex(InstrumentError, "missing_or_mismatched"):
            render_assessment_prompt("E2", job, case["source"], sha256(case["source"].encode()), diagnostic)

    def test_schema_validity_alone_cannot_release_assessment_or_challenge_dependency(self) -> None:
        jobs = [
            {"job_id": "assessment", "dependencies": [], "adapter": "g"},
            {"job_id": "judge", "dependencies": ["assessment"], "adapter": "j"},
            {"job_id": "followup", "dependencies": ["assessment", "judge"], "adapter": "g"},
        ]
        for outcomes, verified, expected in (
            ({"assessment": "ok"}, {"assessment"}, False),
            ({"assessment": "ok", "judge": "ok"}, {"assessment"}, False),
            ({"assessment": "ok", "judge": "schema_invalid"}, {"assessment", "judge"}, False),
            ({"assessment": "ok", "judge": "ok"}, {"assessment", "judge"}, True),
        ):
            with self.subTest(outcomes=outcomes, verified=verified):
                result = plan_continuation(
                    jobs, outcomes, explicitly_authorized=True, reserved_attempts=len(outcomes),
                    max_attempts=3, credentials_available={"g": True, "j": True}, identity_verified=True,
                    verified_outcome_job_ids=frozenset(verified),
                )
                self.assertEqual("followup" in result["ready_job_ids"], expected)

    def test_offline_fixture_pipeline_cannot_open_network_connections(self) -> None:
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            for case in FIXTURES["cases"]:
                _, _, request, response = fixture_context(case)
                result = map_challenges(parse_judgments(json.dumps(response), request), FIXTURES["policy"])
                self.assertEqual(result["provider_calls"], 0)


if __name__ == "__main__":
    main()
