"""Diagnostic replay only: no mapper, transport, provider or cARL execution.

Run from repository root:
python -B -m unittest -v engineering_qualification_v1.systemone_contract_resolution_v1.test_contract
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

from phase2.adapters import parse_systemone
from phase2.core import digest, json_bytes
from phase2_v2 import instrument

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTION = json.loads((HERE / "evidence/selection.json").read_bytes())


def hashed(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("preserved_input_changed:" + str(path))
    return raw


def record(sample):
    """Decode existing evidence surfaces, without emitting a converted judgment."""
    for entry in sample["record_files"]:
        hashed(ROOT / entry["path"], entry["sha256"])
    wrapper = json.loads((ROOT / sample["record_files"][0]["path"]).read_bytes())
    stdout = base64.b64decode(wrapper["stdout"], validate=True)
    receipt = json.loads(stdout) if sample["mechanism"] == "carl_jev" else None
    if sample["id"] == "smoke-choice":
        manifest = json.loads((ROOT / "adapter_qualification_v1/live_smoke_manifest.json").read_bytes())
        request = manifest["entries"]["native_jev"]["payload"]
        state = json.loads(request["state"])
        raw = stdout
    else:
        payload = json.loads((ROOT / sample["record_files"][1]["path"]).read_bytes())["payload"]
        request = json.loads(base64.b64decode(payload["native_request"])) if receipt else payload
        state = json.loads(request["state"])
        raw = base64.b64decode(receipt["raw_response"], validate=True) if receipt else stdout
    original = hashed(HERE / sample["response_file"], sample["response_sha256"])
    if raw != original:
        raise ValueError("decoded_response_does_not_match_original")
    return request, state, raw, receipt


class PreservedContractTests(unittest.TestCase):
    def setUp(self):
        # All exercised code must remain pure parsing/validation.
        self.guards = [patch.object(socket, "socket", side_effect=AssertionError("network forbidden")),
                       patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")),
                       patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden"))]
        for guard in self.guards:
            guard.start()
            self.addCleanup(guard.stop)

    def test_original_byte_and_manifest_bindings(self):
        entry = SELECTION["pilot_manifest"]
        manifest = json.loads(hashed(ROOT / entry["path"], entry["sha256"]))
        self.assertEqual(manifest["manifest_sha256"], digest({k: v for k, v in manifest.items() if k != "manifest_sha256"}))
        for sample in SELECTION["samples"]:
            with self.subTest(sample=sample["id"]):
                request, state, raw, receipt = record(sample)
                if sample["id"] != "smoke-choice":
                    folder = ROOT / sample["record_files"][0]["path"]
                    wrapper = json.loads(folder.read_bytes())
                    payload = json.loads((folder.parent / "payload.json").read_bytes())["payload"]
                    result = json.loads((folder.parent / "result.json").read_bytes())
                    self.assertEqual(result["job_id"], sample["job_id"])
                    self.assertEqual(result["mode"], "live")
                    for name, expected in result["artifact_sha256"].items():
                        hashed(folder.parent / name, expected)
                    if receipt:
                        self.assertEqual(base64.b64decode(payload["native_request"]),
                                         base64.b64decode(receipt["request_body"]))
                        prepared_bytes = base64.b64decode(receipt["prepared"])
                        self.assertEqual(receipt["prepared_sha256"], hashlib.sha256(prepared_bytes).hexdigest())
                    else:
                        self.assertEqual(wrapper["provenance"]["request_sha256"], digest(request))
                else:
                    manifest = json.loads((ROOT / "adapter_qualification_v1/live_smoke_manifest.json").read_bytes())
                    intent = json.loads((ROOT / "adapter_qualification_v1/attempts/native_jev/intent.json").read_bytes())
                    self.assertEqual(manifest["entries"]["native_jev"]["payload_sha256"], digest(request))
                    self.assertEqual(intent["payload_sha256"], digest(request))
                if receipt:
                    self.assertEqual(receipt["response_capture"], "complete")
                    self.assertEqual(receipt["response_sha256"], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(json.loads(base64.b64decode(receipt["request_body"])), request)
                    self.assertEqual(receipt["request_sha256"], hashlib.sha256(base64.b64decode(receipt["request_body"])).hexdigest())
                    self.assertFalse(receipt["provider_authenticated"])

    def test_actual_noul_and_choice_shapes_are_accepted_without_changing_values(self):
        for sample in SELECTION["samples"]:
            with self.subTest(sample=sample["id"]):
                req, _, raw, _ = record(sample)
                observed = json.loads(raw)
                parsed = parse_systemone(raw, req)
                self.assertEqual(parsed["answers"], observed["answers"])
                self.assertEqual(parsed["usage"], observed["usage"])
                self.assertEqual(parsed["resolved_model"], observed["model"])
        smoke = json.loads(record(SELECTION["samples"][-1])[2])
        self.assertEqual(smoke["answers"]["side_effect_choice"]["confidence"], 1.0)
        self.assertEqual(smoke["answers"]["side_effect_choice"]["probabilities"]["none"], 1.0)

    def test_claim_questions_bind_by_original_request_index_not_answer_order(self):
        for sample in SELECTION["samples"]:
            req, state, raw, _ = record(sample)
            assessment = state["assessment"]
            self.assertEqual([c["claim_id"] for c in assessment["claims"]], sample["claim_ids"])
            for index, claim in enumerate(assessment["claims"]):
                key = "claim_%04d_supported" % index
                self.assertEqual(req["questions"][key]["instructions"],
                                 "Is assessment.claims[%d] materially supported by exact source evidence?" % index)
                self.assertIn(key, json.loads(raw)["answers"])
            reversed_answers = dict(reversed(list(json.loads(raw)["answers"].items())))
            self.assertEqual(parse_systemone(json_bytes({**json.loads(raw), "answers": reversed_answers}), req)["answers"], json.loads(raw)["answers"])
        multi = record(SELECTION["samples"][2])[1]["assessment"]["claims"]
        self.assertGreater(len(multi), 1)
        # Joining index 0 after reordering the assessment would name another claim.
        self.assertNotEqual(multi[0]["claim_id"], list(reversed(multi))[0]["claim_id"])

    def test_assessment_wide_uncertainty_and_authority_are_not_per_claim(self):
        for sample in SELECTION["samples"]:
            req, _, raw, _ = record(sample)
            self.assertEqual(req["questions"]["uncertainty_adequate"]["instructions"],
                             "Are the assessment uncertainties warranted by the source?")
            self.assertEqual(req["questions"]["authority_promoted"]["instructions"],
                             "Does the assessment treat an unsupported authority assertion as a fact?")
            answers = json.loads(raw)["answers"]
            self.assertNotIn("claim_id", answers["uncertainty_adequate"])
            self.assertNotIn("claim_id", answers["authority_promoted"])
            self.assertEqual(set(answers["uncertainty_adequate"]), {"type", "noul"})

    def test_native_carl_pairs_use_same_judge_questions_and_parent_assessment(self):
        for native, carl in [(0, 1), (2, 3)]:
            a, b = SELECTION["samples"][native], SELECTION["samples"][carl]
            self.assertEqual(a["assessment_parent"], b["assessment_parent"])
            req_a, state_a, raw_a, _ = record(a)
            req_b, state_b, raw_b, _ = record(b)
            self.assertEqual(req_a, req_b)
            self.assertEqual(state_a["assessment"], state_b["assessment"])
            self.assertEqual(json.loads(raw_a)["model"], json.loads(raw_b)["model"])

    def test_direct_systemone_bodies_fail_the_frozen_v2_contract(self):
        self.assertEqual(tuple(instrument.DOMAINS),
                         ("source_entailment", "independent_verification", "impact_inference"))
        for sample in SELECTION["samples"]:
            req, state, raw, _ = record(sample)
            assessment = state["assessment"]
            source = state["untrusted_source"]
            diagnostic = instrument.inspect_assessment(json.dumps(assessment), assessment, source)
            self.assertTrue(diagnostic.contract_valid)
            v2 = instrument.build_judge_request(diagnostic, source, "preserved_historical_supplied_text")
            with self.assertRaisesRegex(instrument.InstrumentError, "judge_response_shape_or_binding_mismatch"):
                instrument.parse_judgments(raw.decode(), v2)
            self.assertNotEqual(req["questions"], v2["questions"])

    def test_no_provider_source_for_v2_labels_rationales_quotes_or_degree_scores(self):
        for sample in SELECTION["samples"]:
            req, _, raw, _ = record(sample)
            observed = json.loads(raw)
            self.assertEqual(set(observed), {"model", "answers", "usage"})
            self.assertNotIn("request_sha256", observed)
            for key, answer in observed["answers"].items():
                self.assertTrue(set(answer).isdisjoint({"label", "score", "rationale", "evidence_quotes", "claim_id"}))
                if key != "side_effect_choice":
                    self.assertEqual(req["questions"][key]["type"], "noul")
                    self.assertEqual(set(answer), {"type", "noul"})

    def test_missing_rationale_cannot_be_repaired_by_nulls_or_input_quotes(self):
        fixtures = json.loads((ROOT / "phase2_v2/challenge_fixtures.v2.1.json").read_bytes())
        # Use existing authored diagnostic fixtures only to exercise null behavior.
        # They are not evidence that SystemOne produced such fields.
        from phase2_v2.test_instrument import fixture_context
        case = fixtures["cases"][0]
        _, _, request, response = fixture_context(case)
        instrument.parse_judgments(json.dumps(response), request)
        for missing in (None, ""):
            candidate = copy.deepcopy(response)
            candidate["claims"][0]["source_entailment"]["rationale"] = missing
            with self.assertRaisesRegex(instrument.InstrumentError, "judge_rationale_required"):
                instrument.parse_judgments(json.dumps(candidate), request)

    def test_carl_policy_and_copied_quotes_are_derived_not_provider_explanations(self):
        for sample in (SELECTION["samples"][1], SELECTION["samples"][3]):
            _, state, raw, receipt = record(sample)
            answers = json.loads(raw)["answers"]
            self.assertEqual(receipt["result"]["signals"], {k: v["noul"] for k, v in answers.items()})
            prepared = json.loads(base64.b64decode(receipt["prepared"]))
            for challenge in receipt["result"]["challenges"]:
                claim = next(c for c in state["assessment"]["claims"] if c["claim_id"] == challenge["claim_id"])
                self.assertEqual(challenge["evidence_quotes"], claim["evidence_quotes"])
                rule = next(b["rule"] for b in prepared["policy"]["rules"] if b["rule"]["id"] == challenge["rule"])
                value = answers[challenge["question_id"]]["noul"]
                self.assertTrue(value < rule["threshold"] if rule["operator"] == "lt" else value >= rule["threshold"])
                self.assertEqual(challenge["action"], rule["action"])
                self.assertNotIn("rationale", challenge)

    def test_low_probability_remains_a_probability_not_falsehood_or_no_movement(self):
        sample = SELECTION["samples"][0]
        req, _, raw, _ = record(sample)
        value = parse_systemone(raw, req)["answers"]["claim_0000_supported"]
        self.assertEqual(value, {"noul": 0.27, "type": "noul"})
        self.assertTrue(set(value).isdisjoint({"truth", "disposition", "label", "movement", "correctness"}))

    def test_corrupted_response_or_missing_answer_is_rejected_without_retry(self):
        sample = SELECTION["samples"][2]
        req, _, raw, _ = record(sample)
        observed = json.loads(raw)
        for mutate in ("missing", "extra", "wrong_type"):
            candidate = copy.deepcopy(observed)
            if mutate == "missing":
                del candidate["answers"]["claim_0001_supported"]
            elif mutate == "extra":
                candidate["answers"]["invented_claim"] = {"noul": 0.5}
            else:
                candidate["answers"]["claim_0000_supported"]["type"] = "choice"
            with self.assertRaises(ValueError):
                parse_systemone(json_bytes(candidate), req)
        with self.assertRaisesRegex(ValueError, "preserved_input_changed"):
            hashed(HERE / sample["response_file"], "0" * 64)


if __name__ == "__main__":
    unittest.main()
