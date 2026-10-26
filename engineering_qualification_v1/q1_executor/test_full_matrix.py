"""Focused offline integration and corrupt-artifact tests; no live contracts."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import copy
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from . import engine
from .full_matrix import (CASES, FIXTURE, GENERATORS, INTERRUPT, SLOTS, ancestry,
                          build, default_config, demo, design, report)
from .model import FakeProvider, decode, digest, encode, raw_hash, validate_manifest


class FullMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        design()
        cls.result = demo(cls.base / "demonstration")
        cls.normal = cls.base / "demonstration/normal-campaign"
        cls.adverse = cls.base / "demonstration/adverse-campaign"
        cls.audit = engine.verify(cls.normal)

    def test_every_frozen_node_and_edge_reproduces_original_design(self):
        self.assertEqual(len(design()["files"]), 12)
        for scenario in ("normal", "adverse"):
            root = self.base / ("reproduced-" + scenario)
            m = build(root, scenario)
            self.assertEqual(m, validate_manifest(FIXTURE / scenario)[0])
            self.assertEqual({f.name: f.read_bytes() for f in root.iterdir()},
                             {f.name: f.read_bytes() for f in (FIXTURE / scenario).iterdir()})
            ps = m["positions"]
            self.assertEqual(len({p["id"] for p in ps}), 153)
            self.assertEqual(sum(len(p["dependencies"]) for p in ps), 198)
            self.assertEqual(sum(p["kind"] == "generator" for p in ps), 99)
            for c in CASES:
                for g in GENERATORS:
                    group = [p for p in ps if p["case_id"] == c and p["generator"] == g]
                    self.assertEqual(len(group), 17)
                    self.assertEqual(len({p["arm"] for p in group}), 8)
                    self.assertEqual(sum(p["kind"] == "specialist" for p in group), 6)

    def test_normal_and_adverse_actual_durable_accounting(self):
        self.assertEqual(self.result["normal"]["summary"]["states"], {"completed": 153})
        self.assertEqual(self.result["normal"]["summary"]["attempt_reservations"], 153)
        self.assertEqual(self.result["normal"]["summary"]["fake_provider_invocations"], 153)
        adverse = self.result["adverse"]
        self.assertEqual(adverse["summary"]["states"], {
            "completed": 134, "invalid": 3, "blocked": 11, "interrupted": 1, "unavailable": 4})
        self.assertEqual(adverse["summary"]["attempt_reservations"], 141)
        self.assertEqual(adverse["summary"]["fake_provider_invocations"], 140)
        self.assertEqual(adverse["summary"]["remaining_simulated_budget"], 0)
        self.assertEqual(adverse["interruption_exit_status"], 75)
        for scenario in ("normal", "adverse"):
            self.assertTrue(self.result[scenario]["repeated_resume_evidence_unchanged"])
            self.assertEqual(self.result[scenario]["repeat_resumes"], 2)
            self.assertTrue(self.result[scenario]["summary"]["all_positions_terminal"])
            self.assertEqual(self.result[scenario]["summary"]["real_provider_calls"], 0)

    def requests(self, root):
        with sqlite3.connect(root / "campaign.sqlite3") as db:
            return {k: decode(v) for k, v in db.execute("SELECT id,request FROM attempts")}

    def test_actual_history_context_baseline_and_shared_judge_bindings(self):
        audit = self.audit
        ps = {p["id"]: p for p in audit["manifest"]["positions"]}
        saved, requests = audit["receipts"], self.requests(self.normal)
        baseline_refs = {}
        for ident, req in requests.items():
            p = ps[ident]
            history = req["history"]
            expected_history = ancestry(p, ps)
            self.assertEqual([h["position"] for h in history], expected_history)
            self.assertEqual(req["parents"], {d: digest(saved[d]) for d in p["dependencies"]})
            self.assertEqual(req["packet_bindings"], p["packet_bindings"])
            self.assertEqual(raw_hash(req["source_text"].encode()), p["packet_bindings"]["source"])
            self.assertEqual(digest(req["governing_policy"]), p["packet_bindings"]["governing_policy"])
            self.assertFalse(req["governing_policy"]["approved"])
            for h in history:
                q = ps[h["position"]]
                self.assertEqual(q["unit_id"], p["unit_id"])
                self.assertIn(q["arm"], ("B0", p["arm"]))
                self.assertEqual(h["receipt_sha256"], digest(saved[q["id"]]))
                self.assertEqual(h["observation"], saved[q["id"]]["diagnostics"]["parsed"])
                if q["kind"] == "generator" and q["arm"] != "B0":
                    self.assertEqual(h["observation"]["uncertainties"], [
                        "synthetic-private-history:" + p["unit_id"] + ":" + p["arm"]])
            if p["arm"] == "B0":
                self.assertEqual(history, [])
                self.assertIsNone(req["frozen_baseline"])
                self.assertIsNone(req["previous_assessment"])
            else:
                binding = {"position": p["baseline_id"], "receipt_sha256": digest(saved[p["baseline_id"]])}
                self.assertEqual(req["frozen_baseline"], binding)
                baseline_refs.setdefault(p["unit_id"], set()).add(digest(binding))
                self.assertEqual(req["previous_assessment"], saved[p["assessment_parent"]]["diagnostics"]["parsed"])
            if p["arm"] == "B0" or p["arm"].startswith("C"):
                self.assertIsNone(req["challenge_policy"])
                self.assertIsNone(req["simulation_review_request"])
            else:
                self.assertFalse(req["challenge_policy"]["governing_authority"])
            if p["kind"] == "specialist":
                self.assertEqual(p["identity"]["judge"], "synthetic-shared-systemone-v1")
                self.assertEqual(req["instrument_request"]["assessment_sha256"], digest(req["previous_assessment"]))
        self.assertEqual(len(baseline_refs), 9)
        self.assertTrue(all(len(refs) == 1 for refs in baseline_refs.values()))
        self.assertEqual(sum(ps[i]["arm"] == "B0" for i in requests), 9)
        judges = {digest(p["identity"]) for p in ps.values() if p["kind"] == "specialist"}
        self.assertEqual(len(judges), 1)
        self.assertEqual({p["path"] for p in ps.values() if p["kind"] == "specialist"},
                         {"native_simulation", "carl_simulation"})

    def test_intermediate_reversals_missingness_and_unavailable_observations(self):
        saved = self.audit["receipts"]
        for c in CASES:
            for g in GENERATORS:
                for arm in ("c3", "e3-nc", "e3-cn"):
                    prefix = c + "-" + g + "-r1-" + arm
                    self.assertEqual(saved[prefix + "-g1"]["baseline_disposition_pair"], ["pass", "review_required"])
                    self.assertEqual(saved[prefix + "-g2"]["preceding_disposition_pair"], ["review_required", "pass"])
                    self.assertEqual(saved[prefix + "-g2"]["baseline_disposition_pair"], ["pass", "pass"])
        audit = engine.verify(self.adverse)
        requests = self.requests(self.adverse)
        for ident, r in audit["receipts"].items():
            if r["state"] != "completed":
                self.assertIsNone(r["disposition"])
                self.assertIsNone(r["baseline_disposition_pair"])
                self.assertIsNone(r["preceding_disposition_pair"])
                self.assertIsNone(r["diagnostics"]["parsed"])
            if r["state"] == "blocked":
                self.assertNotIn(ident, requests)
        self.assertEqual(audit["receipts"][INTERRUPT]["state"], "interrupted")
        with sqlite3.connect(self.adverse / "campaign.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM invocations WHERE id=?", (INTERRUPT,)).fetchone()[0], 0)
        self.assertGreater(report(audit)["specialist_null_scores_by_dimension"]["source_entailment"], 0)

    def test_self_rehashed_topology_identity_packet_and_authority_corruptions_rejected(self):
        original = decode((FIXTURE / "normal/manifest.json").read_bytes())
        mutations = {
            "cross_arm": lambda m: m["positions"][2].update(assessment_parent=m["positions"][1]["id"], dependencies=[m["positions"][1]["id"]]),
            "cross_unit": lambda m: m["positions"][18].update(assessment_parent=m["positions"][0]["id"], dependencies=[m["positions"][0]["id"]]),
            "sequential_edge": lambda m: m["positions"][11].update(assessment_parent=m["positions"][0]["id"], dependencies=[m["positions"][0]["id"]]),
            "baseline_binding": lambda m: m["positions"][2].update(baseline_id=m["positions"][1]["id"]),
            "missing_identity": lambda m: m["positions"][0].pop("identity"),
            "unknown_identity": lambda m: m["positions"][0]["identity"].update(model="unknown"),
            "independent_judge": lambda m: m["positions"][7]["identity"].update(judge="another-judge"),
            "policy_binding": lambda m: m["positions"][0]["packet_bindings"].update(governing_policy="0" * 64),
            "source_binding": lambda m: m["positions"][0]["packet_bindings"].update(source="0" * 64),
            "role": lambda m: m["positions"][0].update(kind="specialist"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                root = self.base / ("corrupt-manifest-" + name)
                shutil.copytree(FIXTURE / "normal", root)
                m = copy.deepcopy(original); mutate(m)
                m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
                (root / "manifest.json").write_bytes(encode(m))
                with self.assertRaises(ValueError):
                    validate_manifest(root)
        for kind in ("source", "governing-policy", "challenge-policy"):
            root = self.base / ("corrupt-packet-" + kind)
            shutil.copytree(FIXTURE / "normal", root)
            path = root / ("c01-" + kind + (".txt" if kind == "source" else ".json"))
            if kind == "source":
                path.write_bytes(path.read_bytes() + b"changed")
            else:
                packet = decode(path.read_bytes()); packet["governing_authority"] = True
                path.write_bytes(encode(packet))
            with self.assertRaises(ValueError):
                validate_manifest(root)

    def test_corrupted_durable_request_identity_and_receipt_rejected_readonly(self):
        for kind in ("parent", "source", "policy", "identity", "receipt", "journal"):
            with self.subTest(kind=kind):
                root = self.base / ("corrupt-db-" + kind)
                shutil.copytree(self.normal, root)
                ident = "c01-gemini-r1-c1-g1"
                with sqlite3.connect(root / "campaign.sqlite3") as db:
                    if kind in ("parent", "source", "policy"):
                        req = decode(db.execute("SELECT request FROM attempts WHERE id=?", (ident,)).fetchone()[0])
                        if kind == "parent": req["parents"]["c01-gemini-r1-b0"] = "0" * 64
                        elif kind == "source": req["source_text"] = "foreign case"
                        else: req["governing_policy"] = req["challenge_policy"]
                        db.execute("UPDATE attempts SET request=? WHERE id=?", (encode(req), ident))
                    elif kind == "identity":
                        db.execute("UPDATE responses SET observed=? WHERE id=?", (encode({"model": "unknown"}), ident))
                    elif kind == "receipt":
                        obj = decode(db.execute("SELECT body FROM receipts WHERE id=?", (ident,)).fetchone()[0])
                        obj["packet_bindings"]["source"] = "0" * 64
                        db.execute("UPDATE receipts SET body=? WHERE id=?", (encode(obj), ident))
                    else: db.execute("DELETE FROM events WHERE seq=2")
                before = raw_hash((root / "campaign.sqlite3").read_bytes())
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    engine.verify(root)
                self.assertEqual(before, raw_hash((root / "campaign.sqlite3").read_bytes()))

    def test_concurrent_matrix_reservations_and_binding_recheck(self):
        root = self.base / "concurrent"
        engine.create(root, FIXTURE / "normal")
        m, _ = validate_manifest(root)
        barrier = threading.Barrier(2)
        def claim(_):
            db = engine.connect(root)
            try:
                barrier.wait()
                return engine.reserve(db, root, m, m["positions"][0])
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(claim, range(2))), [False, True])
        self.assertEqual(engine.verify(root)["summary"]["attempt_reservations"], 1)
        # Corrupt a parent after committing its receipt, before its first child.
        root = self.base / "boundary-check"
        engine.create(root, FIXTURE / "normal")
        original = engine.finish
        def corrupt(db, campaign, manifest, p, state, reason):
            original(db, campaign, manifest, p, state, reason)
            if p["arm"] == "B0":
                r = decode(db.execute("SELECT body FROM receipts WHERE id=?", (p["id"],)).fetchone()[0])
                r["packet_bindings"]["governing_policy"] = "0" * 64
                db.execute("UPDATE receipts SET body=? WHERE id=?", (encode(r), p["id"]))
        with patch.object(engine, "finish", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "receipt_or_diagnostics"):
                engine.resume(root)
        with sqlite3.connect(root / "campaign.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM attempts").fetchone()[0], 1)

    def test_actual_fake_context_mutation_cannot_change_other_arms_or_baseline(self):
        # A hostile injected fake mutates its own received objects after invoking.
        # It is still the permitted exact FakeProvider class, never a transport.
        root = self.base / "context-mutation"
        engine.create(root, FIXTURE / "normal")
        original = FakeProvider.invoke
        def hostile(fake, req, record):
            output = original(fake, req, record)
            if req["position"]["id"] == "c01-gemini-r1-c1-g1":
                req["previous_assessment"]["claims"][0]["claim"] = "LEAK-CANARY"
                req["governing_policy"]["approved"] = True
                req["history"][0]["observation"]["claims"] = []
            if req["position"]["id"] == "c01-gemini-r1-c2-g1":
                self.assertNotIn("LEAK-CANARY", str(req))
                self.assertFalse(req["governing_policy"]["approved"])
                raise RuntimeError("synthetic_exception_before_response")
            return output
        # Reserve only the first three positions; the fixture's budget is frozen.
        # Stop with a deliberate boundary exception after checking C2's context.
        def stop(db, campaign, m, p):
            if p["id"] == "c01-gemini-r1-c3-g1":
                raise ValueError("context_test_complete")
            return reserve(db, campaign, m, p)
        reserve = engine.reserve
        with ExitStack() as stack:
            for owner, name in ((socket, "socket"), (socket, "create_connection"),
                                (urllib.request, "urlopen"), (subprocess, "Popen")):
                stack.enter_context(patch.object(owner, name, side_effect=AssertionError("network/process forbidden")))
            stack.enter_context(patch.object(FakeProvider, "invoke", hostile))
            stack.enter_context(patch.object(engine, "reserve", stop))
            with self.assertRaisesRegex(ValueError, "context_test_complete"):
                engine.resume(root)
        audit = engine.verify(root)
        baseline = audit["receipts"]["c01-gemini-r1-b0"]
        self.assertNotIn("LEAK-CANARY", str(baseline))
        with patch.object(FakeProvider, "invoke", side_effect=AssertionError("verifier invoked provider")):
            before = {p.name: raw_hash(p.read_bytes()) for p in root.iterdir() if p.is_file()}
            engine.verify(root)
            self.assertEqual(before, {p.name: raw_hash(p.read_bytes()) for p in root.iterdir() if p.is_file()})

    def test_context_changed_between_file_verification_and_reservation_is_rejected(self):
        from . import full_matrix
        original = full_matrix.slice_request
        for key in ("source_text", "governing_policy", "challenge_policy"):
            with self.subTest(key=key):
                root = self.base / ("reservation-context-" + key)
                engine.create(root, FIXTURE / "normal")
                def altered(*args):
                    req = original(*args)
                    if key == "source_text": req[key] = "foreign source"
                    else: req[key]["governing_authority"] = True
                    return req
                with patch.object(full_matrix, "slice_request", side_effect=altered):
                    with self.assertRaisesRegex(ValueError, "matrix_request_source_or_policy_binding"):
                        engine.resume(root)
                self.assertEqual(engine.verify(root)["summary"]["attempt_reservations"], 0)


if __name__ == "__main__":
    unittest.main()
