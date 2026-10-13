from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import tool


class OfflineQualificationTests(unittest.TestCase):
    def setUp(self):
        self.policy = tool.load(tool.PACKAGE / "policy.v1.json")
        self.bundle, self.references = tool.make_bundle(self.policy)

    def endpoint(self, case_id, index=0):
        return next(t for t in self.bundle["trajectories"] if t["id"] == case_id)["endpoints"][index]

    def reseal_endpoint(self, endpoint):
        endpoint["packet"] = tool.seal({k: v for k, v in endpoint["packet"].items() if k != "sha256"})
        obj = {k: v for k, v in endpoint["assessment"].items() if k != "sha256"}
        obj["packet_sha256"] = endpoint["packet"]["sha256"]
        endpoint["assessment"] = tool.seal(obj)
        self.bundle = tool.seal({k: v for k, v in self.bundle.items() if k != "sha256"})

    def test_policy_exhaustive_partition(self):
        self.assertEqual(tool.validate_policy(self.policy), 16)
        for values in itertools.product((False, True), repeat=4):
            state = dict(zip(tool.PREDICATES, values))
            with self.subTest(state=state):
                self.assertEqual(tool.decide(self.policy, state)["disposition"], tool.expected_rule(state))

    def test_missing_ambiguous_and_contradictory_mapping_rejected(self):
        for mutate in (
            lambda p: p["rules"].pop(),
            lambda p: p["rules"][1].update(when={"blocking_violation": True}),
            lambda p: p["rules"][4]["when"].update(warning_needed=True),
            lambda p: p["precedence"].reverse(),
            lambda p: p["rules"][1].update(resolution="authorised_human_decision_and_reassessment"),
            lambda p: p["rules"][0].update(evidence_ids=["E-TEST"]),
        ):
            bad = deepcopy(self.policy)
            mutate(bad)
            with self.assertRaises(tool.QualificationError):
                tool.validate_policy(bad)
        for state in ({}, dict.fromkeys(tool.PREDICATES, None),
                      dict.fromkeys(tool.PREDICATES, 0)):
            with self.assertRaises(tool.QualificationError):
                tool.decide(self.policy, state)

    def test_unknown_rule_evidence_and_authority_rejected(self):
        for field, value in (("disposition", "approved"), ("evidence_ids", ["E-UNKNOWN"]),
                             ("id", "R-OTHER")):
            bad = deepcopy(self.policy)
            bad["rules"][0][field] = value
            with self.assertRaises(tool.QualificationError):
                tool.validate_policy(bad)
        bad = deepcopy(self.policy)
        bad["authority"]["enforcement"] = "deploy"
        with self.assertRaises(tool.QualificationError):
            tool.validate_policy(bad)

    def test_rule_and_trajectory_coverage(self):
        coverage = tool.validate_bundle(self.policy, self.bundle)
        tool.validate_references(self.bundle, self.references)
        selected = coverage["selected_rule_counts"]
        triggered = coverage["triggered_obligation_counts"]
        self.assertEqual(set(selected), set(self.policy["precedence"]))
        self.assertEqual(len(self.bundle["trajectories"]), 14)
        self.assertEqual(sum(selected.values()), 31)
        self.assertTrue(triggered)
        self.assertLessEqual(set(triggered), set(self.policy["precedence"]) - {"R-PASS"})
        self.assertEqual({c for r in self.references["references"] for c in r["coverage"]}, set(range(1, 15)))
        categories = {r["disposition_movement"] for row in self.references["references"] for r in row["suggestions"]}
        categories |= {f["category"] for row in self.references["references"]
                       for r in row["suggestions"] for f in r["finding_movements"]}
        self.assertEqual(categories, {None, "justified", "unjustified", "mixed", "unresolved"})

    def test_missing_evidence_is_not_violation_or_review(self):
        endpoint = self.endpoint("T03", 1)
        state = tool.state_from_packet(self.policy, endpoint["packet"])
        self.assertFalse(state["blocking_violation"])
        self.assertEqual(tool.decide(self.policy, state)["disposition"], "insufficient_evidence")
        review = tool.state_from_packet(self.policy, self.endpoint("T04", 1)["packet"])
        self.assertEqual(tool.decide(self.policy, review)["disposition"], "review_required")

    def test_indeterminate_evidence_holds_without_establishing_violation(self):
        state = tool.state_from_packet(self.policy, self.endpoint("T14")["packet"])
        self.assertFalse(state["blocking_violation"])
        self.assertFalse(state["evidence_sufficient"])
        self.assertEqual(tool.decide(self.policy, state)["disposition"], "insufficient_evidence")

    def test_conflicting_conditions_precedence(self):
        state = tool.state_from_packet(self.policy, self.endpoint("T12", 1)["packet"])
        self.assertTrue(state["blocking_violation"])
        self.assertTrue(state["human_review_pending"])
        self.assertTrue(state["warning_needed"])
        self.assertFalse(state["evidence_sufficient"])
        self.assertEqual(tool.decide(self.policy, state)["id"], "R-BLOCK")
        self.assertEqual(set(tool.triggered_rules(self.policy, state)),
                         {"R-BLOCK", "R-EVIDENCE", "R-REVIEW", "R-WARN"})

    def test_evidence_and_human_approval_reassessment(self):
        endpoint = self.endpoint("T03", 1)
        packet = deepcopy(endpoint["packet"])
        packet["evidence"].append(tool.artifact("E-TEST", packet["change_id"], {"scope_covered": True}))
        self.assertEqual(tool.decide(self.policy, tool.state_from_packet(self.policy, packet))["disposition"], "pass")
        packet["evidence"][0]["facts"]["restricted_interface"] = True
        self.assertEqual(tool.decide(self.policy, tool.state_from_packet(self.policy, packet))["disposition"],
                         "review_required")
        packet["evidence"].append(tool.artifact("E-REVIEW", packet["change_id"], {
            "authority": "fictional-security-reviewer", "decision": "approved"}))
        self.assertEqual(tool.decide(self.policy, tool.state_from_packet(self.policy, packet))["disposition"], "pass")
        packet["evidence"][0]["facts"]["credential_logging"] = True
        self.assertEqual(tool.decide(self.policy, tool.state_from_packet(self.policy, packet))["disposition"], "fail")

    def test_false_challenge_cannot_decide_governing_outcome(self):
        before = tool.state_from_packet(self.policy, self.endpoint("T06")["packet"])
        after = tool.state_from_packet(self.policy, self.endpoint("T06", 1)["packet"])
        self.assertEqual(before, after)
        self.assertEqual(tool.decide(self.policy, after)["disposition"], "pass")
        state = tool.state_from_packet(self.policy, self.endpoint("T07", 1)["packet"])
        self.assertEqual(tool.decide(self.policy, state)["disposition"], "insufficient_evidence")

    def test_binding_tamper_rejected_at_all_layers(self):
        for layer in ("source", "evidence", "packet", "assessment", "policy"):
            self.setUp()
            endpoint = self.endpoint("T01")
            if layer == "source":
                self.bundle["trajectories"][0]["source"]["text"] += "tamper"
            elif layer == "evidence":
                endpoint["packet"]["evidence"][0]["text"] += "tamper"
            elif layer == "packet":
                endpoint["packet"]["source_sha256"] = "0" * 64
            elif layer == "assessment":
                endpoint["assessment"]["disposition"] = "fail"
            else:
                self.policy["purpose"] += "tamper"
            with self.subTest(layer=layer), self.assertRaises(tool.QualificationError):
                tool.validate_bundle(self.policy, self.bundle)

    def test_rehashed_wrong_binding_and_duplicate_evidence_rejected(self):
        for mutate in (
            lambda e: e["packet"].update(source_sha256="0" * 64),
            lambda e: e["packet"].update(scope="production"),
            lambda e: e["packet"]["evidence"].append(deepcopy(e["packet"]["evidence"][0])),
        ):
            self.setUp()
            endpoint = self.endpoint("T01")
            mutate(endpoint)
            self.reseal_endpoint(endpoint)
            with self.assertRaises(tool.QualificationError):
                tool.validate_bundle(self.policy, self.bundle)

    def test_rehashed_evidence_contradiction_and_wrong_authority_rejected(self):
        for mode in ("contradiction", "authority", "ambiguous"):
            self.setUp()
            endpoint = self.endpoint("T01")
            evidence = endpoint["packet"]["evidence"][0]
            if mode == "contradiction":
                evidence["facts"]["credential_logging"] = True
            elif mode == "authority":
                evidence = tool.artifact("E-REVIEW", "T01", {"authority": "judge", "decision": "approved"})
                endpoint["packet"]["evidence"].append(evidence)
            else:
                evidence["facts"]["logging_scope"] = "ambiguous"
                evidence["text"] = json.dumps(evidence["facts"], sort_keys=True)
            evidence.update(sha256=tool.digest({k: v for k, v in evidence.items() if k != "sha256"}))
            self.reseal_endpoint(endpoint)
            with self.assertRaises(tool.QualificationError):
                tool.validate_bundle(self.policy, self.bundle)

    def test_sequential_intermediate_and_final_observations_independent(self):
        trajectory = next(t for t in self.bundle["trajectories"] if t["id"] == "T11")
        values = [e["assessment"]["disposition"] for e in trajectory["endpoints"]]
        self.assertEqual(values, ["pass", "review_required", "pass"])
        self.assertEqual(values[0], values[-1])
        self.assertNotEqual(values[0], values[1])
        t08 = next(t for t in self.bundle["trajectories"] if t["id"] == "T08")
        self.assertEqual(t08["endpoints"][0]["assessment"]["disposition"],
                         t08["endpoints"][1]["assessment"]["disposition"])
        self.assertNotEqual(t08["endpoints"][0]["assessment"]["findings"],
                            t08["endpoints"][1]["assessment"]["findings"])

    def test_reference_suggestions_cannot_become_ground_truth_or_leak(self):
        exported = tool.exports(self.policy, self.bundle, self.references)
        public = json.dumps({"claims": exported["claims"], "pairs": exported["pairs"]})
        for row in self.references["references"]:
            self.assertNotIn(row["title"], public)
        for key in ("suggestions", "category", "metadata", "original_id", "reported_rationale",
                    "challenge_text", "coverage"):
            self.assertNotIn(f'"{key}"', public)
        self.assertNotIn('"disposition"', json.dumps(exported["claims"]["records"]))
        self.assertEqual(exported, tool.exports(self.policy, self.bundle, self.references))
        bad = deepcopy(self.references)
        bad["references"][0]["suggestions"][0]["independent_reference"] = True
        with self.assertRaises(tool.QualificationError):
            tool.exports(self.policy, self.bundle, bad)

    def test_build_verify_reproducibility_no_network_or_processes(self):
        with ExitStack() as stack:
            denied = [stack.enter_context(patch(target, side_effect=AssertionError("external call denied")))
                      for target in ("socket.socket.connect", "socket.create_connection",
                                     "urllib.request.urlopen", "subprocess.Popen")]
            with tempfile.TemporaryDirectory() as temp:
                first, second = Path(temp) / "one", Path(temp) / "two"
                result = tool.build(first)
                tool.build(second)
                self.assertEqual(result, tool.verify(first))
                self.assertEqual(result["provider_calls"], 0)
                self.assertEqual(result["reviewers_completed"], 0)
                for path in first.rglob("*.json"):
                    self.assertEqual(path.read_bytes(), (second / path.relative_to(first)).read_bytes())
                with self.assertRaises(tool.QualificationError):
                    tool.build(first)
                for mock in denied:
                    mock.assert_not_called()

    def test_export_leak_and_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "exercise"
            tool.build(output)
            obj = tool.load(output / "claims.json")
            obj["private_answers"] = self.references
            tool.write(output / "claims.json", obj)
            with self.assertRaisesRegex(tool.QualificationError, "export separation"):
                tool.verify(output)
            (output / "claims.json").unlink()
            with self.assertRaisesRegex(tool.QualificationError, "missing or unexpected exercise files"):
                tool.verify(output)

    def test_extra_public_answers_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "exercise"
            tool.build(output)
            tool.write(output / "answers.json", self.references)
            with self.assertRaisesRegex(tool.QualificationError, "unexpected exercise files"):
                tool.verify(output)
            (output / "answers.json").unlink()
            (output / "answers.json").symlink_to(output / "custodian/references.json")
            with self.assertRaisesRegex(tool.QualificationError, "symlink"):
                tool.verify(output)

    def test_inventory_detects_mutation_and_unknown_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in tool.PACKAGE_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic inventory test\n")
            self.assertEqual(tool.inventory(root, create=True)["inventory_files"], len(tool.PACKAGE_FILES))
            self.assertEqual(tool.inventory(root)["status"], "verified")
            (root / "README.md").write_text("tamper")
            with self.assertRaisesRegex(tool.QualificationError, "hash mismatch"):
                tool.inventory(root)
            (root / "extra.json").write_text("{}")
            with self.assertRaisesRegex(tool.QualificationError, "exact package"):
                tool.inventory(root)

    def test_warning_obligation_and_rule_resolution_are_not_merged(self):
        warn = tool.decide(self.policy, tool.state_from_packet(self.policy, self.endpoint("T02", 1)["packet"]))
        self.assertEqual(warn["resolution"], "record_coverage_warning")
        self.assertEqual(self.endpoint("T02", 1)["assessment"]["conditions"],
                         ["record limited-platform-coverage warning"])
        paths = {r["disposition"]: r["resolution"] for r in self.policy["rules"]}
        self.assertEqual(len(set(paths.values())), 5)
        self.assertEqual(tool.triggered_rules(self.policy, tool.state_from_packet(
            self.policy, self.endpoint("T12", 1)["packet"])),
            ["R-BLOCK", "R-EVIDENCE", "R-REVIEW", "R-WARN"])

    def test_templates_separate_dimensions_movement_and_warrant(self):
        exported = tool.exports(self.policy, self.bundle, self.references)
        sheet = tool.annotation_template(exported, "A")
        self.assertIsNone(sheet["frozen_at"])
        for row in sheet["records"]:
            for endpoint in row["endpoint_labels"]:
                for assertion in endpoint["assertions"]:
                    for dimension in ("source_entailment", "independent_verification", "impact_inference"):
                        self.assertIsNone(assertion[dimension])
            self.assertEqual(len(row["disposition_pairs"]), len(row["disposition_justification"]))
            for pair in row["disposition_pairs"]:
                self.assertIsNone(pair["before_value"])
                self.assertIsNone(pair["after_value"])
            for item in row["disposition_justification"]:
                self.assertIsNone(item["category"])
            self.assertEqual(row["finding_justifications"], [])

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            for content in ('{"synthetic":true,"synthetic":false}', '{"x":NaN}', '{"x":Infinity}'):
                path.write_text(content)
                with self.assertRaises(tool.QualificationError):
                    tool.load(path)


if __name__ == "__main__":
    unittest.main()
