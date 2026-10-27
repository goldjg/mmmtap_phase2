"""Focused contract, provenance, construct-separation and real-executor tests."""
import copy
from decimal import Decimal
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from . import VERSION
from .contract import bindings, parse, derive_carl, exact_json
from .replay import selection, load_record, observe, unb64, corrupt
from .acceptance import fixture, run_case
from .. import engine
from ..contracts import load
from ..model import decode, digest, encode, raw_hash, validate_response, validate_manifest
from ..transport_qualification import snapshot


class TypedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {s["id"]: load_record(s["id"]) for s in selection()["samples"]}

    def parse(self, context, raw=None, **kw):
        raw = unb64(context["response_b64"]) if raw is None else raw
        request = unb64(context["request_b64"])
        source = decode(decode(request)["state"])["untrusted_source"].encode()
        args = dict(source_raw=source, assessment=context["assessment"], claim_ids=context["claim_ids"],
                    request_sha256=context["request_sha256"], response_sha256=raw_hash(raw),
                    qualification_choice=context["qualification_choice"])
        args.update(kw)
        return parse(request, raw, **args)

    def test_all_five_bodies_exact_values_model_usage_and_claim_associations(self):
        with patch.object(socket, "socket", side_effect=AssertionError("offline only")), patch.object(subprocess, "Popen", side_effect=AssertionError("pure parser")):
            for ident, c in self.records.items():
                with self.subTest(sample=ident):
                    raw = unb64(c["response_b64"])
                    o = observe(c, raw)
                    entity = exact_json(raw)
                    direct = o["direct_systemone"]
                    self.assertEqual(direct["response_sha256"], raw_hash(raw))
                    self.assertEqual(direct["request_sha256"], raw_hash(unb64(c["request_b64"])))
                    self.assertEqual(direct["returned_model"]["value"], entity["model"])
                    self.assertEqual(direct["usage"], {k: int(v) for k,v in entity["usage"].items()})
                    claim_obs = [v for v in direct["observations"] if v["scope"] == "claim"]
                    self.assertEqual([v["claim_id"] for v in claim_obs], c["claim_ids"])
                    self.assertEqual([v["claim_index"] for v in claim_obs], list(range(len(c["claim_ids"]))))
                    for v in direct["observations"]:
                        self.assertEqual(v["noul_decimal"], entity["answers"][v["question_id"]]["noul"])
                    for name in ("uncertainty_adequate", "authority_promoted"):
                        v = next(v for v in direct["observations"] if v["question_id"] == name)
                        self.assertEqual(v["scope"], "assessment")
                        self.assertNotIn("claim_id", v)
                        self.assertNotIn("claim_index", v)

    def test_decimal_tokens_never_rounded_or_turned_into_degree_scores(self):
        c = self.records["native-low"]
        raw = unb64(c["response_b64"]).replace(b'0.27', b'0.27000000000000000000000000000000000001')
        o = self.parse(c, raw)
        v = next(v for v in o["direct_systemone"]["observations"] if v["scope"] == "claim")
        self.assertEqual(v["noul_decimal"], "0.27000000000000000000000000000000000001")
        self.assertEqual(v["measurement"], "probability_of_yes")
        self.assertNotIn("score", v)
        self.assertEqual(o["reference_judgments"]["fields"]["support_degree_scores"]["status"], "unavailable")

    def test_all_missing_extra_duplicate_wrong_types_rejected_for_all_five(self):
        for c in self.records.values():
            for kind in ("missing", "extra", "duplicate", "wrong_type"):
                with self.subTest(sample=c["sample_id"], negative=kind):
                    raw = corrupt(unb64(c["response_b64"]), kind)
                    self.assertNotEqual(raw_hash(raw), c["response_sha256"])
                    with self.assertRaises(ValueError):
                        self.parse(c, raw)

    def test_bool_string_null_out_of_range_nonfinite_and_invented_fields_rejected(self):
        c = self.records["native-low"]
        for value in (True, "0.27", None, -0.1, 1.1, float("inf")):
            obj = decode(unb64(c["response_b64"]))
            obj["answers"]["claim_0000_supported"]["noul"] = value
            import json
            with self.assertRaises(ValueError):
                self.parse(c, json.dumps(obj).encode())
        for field in ("governing_policy", "release_authority", "independent_verification"):
            obj = decode(unb64(c["response_b64"])); obj[field] = "invented"
            with self.assertRaises(ValueError): self.parse(c, encode(obj))
        for field in ("label", "score", "rationale", "evidence_quotes"):
            obj = decode(unb64(c["response_b64"]));obj["answers"]["claim_0000_supported"][field] = "invented"
            with self.assertRaises(ValueError):self.parse(c,encode(obj))
        obj = decode(unb64(c["response_b64"]))
        del obj["answers"]["claim_0000_supported"]["type"]
        with self.assertRaises(ValueError):self.parse(c,encode(obj))

    def test_request_order_and_exact_wording_are_enforced_answer_object_order_is_irrelevant(self):
        c = self.records["native-multi"]
        with self.assertRaisesRegex(ValueError, "frozen_claim_order"):
            self.parse(c, claim_ids=list(reversed(c["claim_ids"])))
        assessment = copy.deepcopy(c["assessment"]);assessment["claims"].reverse()
        with self.assertRaisesRegex(ValueError, "assessment_binding"):
            self.parse(c,assessment=assessment)
        for change in ("wording", "missing", "extra", "swapped_questions", "duplicate_claim_id"):
            req = decode(unb64(c["request_b64"]))
            if change == "wording":req["questions"]["uncertainty_adequate"]["instructions"] += " for each claim"
            elif change == "missing":del req["questions"]["claim_0001_supported"]
            elif change == "extra":req["questions"]["independent_verification"] = {"type":"noul"}
            elif change == "swapped_questions":
                req["questions"]["claim_0000_supported"],req["questions"]["claim_0001_supported"] = req["questions"]["claim_0001_supported"],req["questions"]["claim_0000_supported"]
            else:
                a=copy.deepcopy(c["assessment"]);a["claims"][1]["claim_id"]=a["claims"][0]["claim_id"]
                state=decode(req["state"]);state["assessment"]=a;req["state"]=encode(state).decode()
            with self.assertRaises(ValueError):
                bindings(encode(req), decode(req["state"])["untrusted_source"].encode(),
                         a if change == "duplicate_claim_id" else c["assessment"], c["claim_ids"])
        obj = decode(unb64(c["response_b64"]))
        obj["answers"] = dict(reversed(list(obj["answers"].items())))
        self.assertEqual([v["claim_id"] for v in self.parse(c, encode(obj))["direct_systemone"]["observations"] if v["scope"] == "claim"], c["claim_ids"])

    def test_wrong_raw_source_assessment_request_digests_rejected(self):
        c = self.records["native-low"]
        for args in ({"request_sha256":"0"*64}, {"response_sha256":"0"*64}, {"source_raw":b"wrong"}):
            with self.assertRaises(ValueError): self.parse(c, **args)

    def test_native_and_carl_question_semantics_and_shared_judge_remain_matched(self):
        for a,b in (("native-low","carl-low"),("native-multi","carl-multi")):
            native,carl=self.records[a],self.records[b]
            self.assertEqual(native["request_b64"],carl["request_b64"])
            self.assertEqual(native["assessment_sha256"],carl["assessment_sha256"])
            x,y=observe(native,unb64(native["response_b64"])),observe(carl,unb64(carl["response_b64"]))
            self.assertEqual(x["direct_systemone"]["returned_model"],y["direct_systemone"]["returned_model"])
            self.assertIsNone(x["derived_carl"]);self.assertIsNotNone(y["derived_carl"])

    def test_carl_trace_is_derived_and_original_quotes_are_generator_input(self):
        c=self.records["carl-low"]
        o=observe(c,unb64(c["response_b64"]));d=o["derived_carl"]
        self.assertEqual(d["disposition"],c["historical_result"]["disposition"])
        self.assertEqual(d["challenges"],c["historical_result"]["challenges"])
        self.assertIn("not_judge",d["origin"])
        self.assertEqual(d["quote_provenance"]["origin"],"generator_assessment_input_not_provider_selection")
        self.assertTrue(any(p["matched"] for p in d["predicates"]))
        for p in d["predicates"]:self.assertEqual(p["dependency"]["response_sha256"],c["response_sha256"])
        self.assertEqual(o["reference_judgments"]["fields"]["evidence_policy_justification"]["status"],"unavailable")
        self.assertEqual(o["reference_judgments"]["fields"]["provider_selected_quotations"]["status"],"unavailable")

    def test_no_falsehood_release_authority_reference_judgments_or_historical_reclassification(self):
        for c in self.records.values():
            o=observe(c,unb64(c["response_b64"]))
            for v in o["direct_systemone"]["observations"]:
                self.assertTrue(set(v).isdisjoint({"false","truth","label","score","correctness","release_authority","governing_policy"}))
            for field in o["reference_judgments"]["fields"].values():
                self.assertEqual(field["status"],"unavailable");self.assertIsNone(field["value"]);self.assertTrue(field["reason"])
            if o["derived_carl"]:
                self.assertFalse(o["derived_carl"]["governing_authority"]);self.assertFalse(o["derived_carl"]["release_authority"])
            self.assertNotIn("disposition",o["direct_systemone"])
            self.assertIn("no_governing_policy_or_release_authority",o["authority"])
        low=observe(self.records["native-low"],unb64(self.records["native-low"]["response_b64"]))
        self.assertEqual(next(v["noul_decimal"] for v in low["direct_systemone"]["observations"] if v["scope"]=="claim"),"0.27")

    def test_frozen_v2_validator_still_rejects_every_raw_systemone_body(self):
        instrument,_,_=load()
        for c in self.records.values():
            source=decode(decode(unb64(c["request_b64"]))["state"])["untrusted_source"]
            diagnostic=instrument.inspect_assessment(encode(c["assessment"]).decode(),c["assessment"],source)
            req=instrument.build_judge_request(diagnostic,source,"historical_replay")
            with self.assertRaises(ValueError):instrument.parse_judgments(unb64(c["response_b64"]).decode(),req)

    def test_choice_is_preserved_only_as_historical_auxiliary_observation(self):
        o=self.parse(self.records["smoke-choice"])
        choice=o["direct_systemone"]["auxiliary_observations"]["side_effect_choice"]
        self.assertEqual(choice["choice"],"none");self.assertEqual(choice["confidence_decimal"],"1.0")
        self.assertEqual(choice["probabilities_decimal"],{"file_write":"0.0","network":"0.0","none":"1.0"})
        self.assertEqual(choice["scope"],"supplied_source")
        with self.assertRaises(ValueError):self.parse(self.records["smoke-choice"],qualification_choice=False)


class ExecutorChoice1Tests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)

    def test_real_broker_native_carl_raw_custody_and_continuations(self):
        report=run_case(self.root,"pair",["native-multi","carl-multi"])
        self.assertEqual(report["summary"]["states"],{"completed":5})
        self.assertEqual(report["summary"]["broker_dispatch_intents"],5)
        details=report["specialists"]
        self.assertNotEqual(details["native-multi"]["role_identity"],details["carl-multi"]["role_identity"])
        self.assertEqual(details["native-multi"]["role_identity"]["underlying_judge"],details["carl-multi"]["role_identity"]["underlying_judge"])
        for d in details.values():
            self.assertTrue(d["exact_original_body"]);self.assertTrue(d["continuation_received_exact_observation"])
            self.assertFalse(d["observation"]["replay_provenance"]["historical_outcomes_reclassified"])
        campaign=self.root/"pair/campaign"
        with engine.connect(campaign,readonly=True) as db:
            a=decode(db.execute("SELECT request FROM attempts WHERE id='carl-multi-continuation'").fetchone()[0])
            b=decode(db.execute("SELECT request FROM attempts WHERE id='baseline'").fetchone()[0])
            self.assertEqual(a["governing_policy"],b["governing_policy"])
            self.assertFalse(a["governing_policy"]["release_authority"])
        before=snapshot(campaign)
        engine.verify(campaign)
        self.assertEqual(before,snapshot(campaign))

    def test_all_four_parser_failures_keep_raw_and_block_continuations(self):
        for kind in ("missing","extra","duplicate","wrong_type"):
            report=run_case(self.root,kind,["native-multi"],negative_inputs={"native-multi":kind})
            self.assertEqual(report["summary"]["states"],{"completed":1,"invalid":1,"blocked":1})
            self.assertEqual(report["summary"]["broker_complete_responses"],2)
            self.assertIsNotNone(report["specialists"]["native-multi"]["response_sha256"])

    def test_crash_reservation_consumed_once_and_repeated_resume_is_readonly(self):
        report=run_case(self.root,"crash",["carl-low"],crash="carl-low")
        self.assertEqual(report["summary"]["attempt_reservations"],2)
        self.assertEqual(report["summary"]["broker_dispatch_intents"],1)
        self.assertEqual(report["summary"]["states"],{"completed":1,"interrupted":1,"blocked":1})
        self.assertTrue(report["readonly_and_repeated_resume_files_unchanged"])

    def test_unknown_contract_unmatched_source_and_reordered_claims_fail_closed(self):
        root=fixture(self.root/"fixture",["native-multi"])
        original=decode((root/"manifest.json").read_bytes())
        for mutation in ("version","source","claim_order","role","unsealed_context"):
            m=copy.deepcopy(original)
            if mutation=="version":m["specialist_observation"]["version"]="unapproved-version"
            elif mutation=="source":
                (root/"source.txt").write_bytes(b"wrong");m["packets"]["source"]["sha256"]=raw_hash(b"wrong")
            elif mutation in ("claim_order","unsealed_context"):
                packet=decode((root/"replay.json").read_bytes())
                if mutation=="claim_order":packet["records"]["native-multi"]["assessment"]["claims"].reverse()
                else:packet["records"]["native-multi"]["response_metadata"]["fabricated"]="metadata"
                raw=encode(packet);(root/"replay.json").write_bytes(raw);m["packets"]["replay"]["sha256"]=raw_hash(raw)
            else:m["positions"][1]["path"]="carl_simulation"
            m["manifest_sha256"]=digest({k:v for k,v in m.items() if k!="manifest_sha256"})
            (root/"manifest.json").write_bytes(encode(m))
            with self.assertRaises(ValueError):validate_manifest(root)
            # Restore sealed fixture for the next negative input.
            from .replay import load_record
            c=load_record('native-multi');(root/'source.txt').write_bytes(decode(decode(unb64(c['request_b64']))['state'])['untrusted_source'].encode())
            (root/'replay.json').write_bytes(encode({'version':VERSION,'records':{'native-multi':c}}))


if __name__ == "__main__":unittest.main()
