from __future__ import annotations

from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import copy
import multiprocessing
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

from . import engine
from .__main__ import demo
from .contracts import load
from .model import PACKAGE, FakeProvider, decode, digest, encode, raw_hash, validate_manifest


def worker(root, barrier, queue):
    barrier.wait()
    try:
        engine.resume(Path(root))
        queue.put("finished")
    except ValueError as exc:
        queue.put(str(exc))


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "campaign"
        load()

    def create(self):
        return engine.create(self.root)

    def db(self):
        return engine.connect(self.root)

    def snapshot(self):
        return {p.name: raw_hash(p.read_bytes()) for p in self.root.iterdir() if p.is_file()}

    def fault(self, code):
        run = subprocess.run([sys.executable, "-c", code, str(self.root)], capture_output=True,
                             env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(run.returncode, 75, run.stderr.decode())

    def test_actual_demo_crash_two_resumes_and_intermediate_movement(self):
        report = demo(self.root)
        self.assertEqual(report["interruption_exit_status"], 75)
        self.assertTrue(report["second_resume_database_unchanged"])
        summary = report["verification"]
        self.assertEqual(summary["states"], {"completed": 6, "invalid": 1, "blocked": 4,
                                             "interrupted": 1, "unavailable": 3})
        self.assertEqual((summary["attempt_reservations"], summary["fake_provider_invocations"]), (10, 9))
        self.assertEqual(summary["simulated_expenditure_units"], 9)
        self.assertEqual(summary["remaining_simulated_budget"], 0)
        records = engine.verify(self.root)["receipts"]
        self.assertEqual(records["intermediate"]["baseline_disposition_pair"], ["pass", "review_required"])
        self.assertEqual(records["final"]["preceding_disposition_pair"], ["review_required", "pass"])
        self.assertEqual(records["final"]["baseline_disposition_pair"], ["pass", "pass"])
        for ident in ("invalid", "unknown-identity", "interruption", "budget-tail"):
            self.assertIsNone(records[ident]["disposition"])
            self.assertIsNone(records[ident]["baseline_disposition_pair"])

    def test_same_position_cannot_be_reserved_twice_and_restart_never_calls_it(self):
        self.create()
        with engine.lock(self.root):
            db = self.db()
            try:
                m = engine.verify_database(db, self.root)["manifest"]
                self.assertTrue(engine.reserve(db, self.root, m, m["positions"][0]))
                self.assertFalse(engine.reserve(db, self.root, m, m["positions"][0]))
            finally:
                db.close()
        result = engine.resume(self.root)
        self.assertEqual(result["fake_provider_invocations"], 0)
        self.assertEqual(result["attempt_reservations"], 1)
        self.assertEqual(result["states"], {"interrupted": 1, "blocked": 14})
        before = self.snapshot()
        for _ in range(2):
            engine.resume(self.root)
        self.assertEqual(before, self.snapshot())

    def test_two_process_workers_never_duplicate_an_attempt(self):
        self.create()
        ctx = multiprocessing.get_context("fork")
        barrier, queue = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=worker, args=(str(self.root), barrier, queue)) for _ in range(2)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            if process.is_alive():
                process.kill(); process.join()
                self.fail("worker did not finish")
            self.assertEqual(process.exitcode, 0)
        results = [queue.get(timeout=2) for _ in processes]
        self.assertIn("finished", results)
        self.assertTrue(all(x == "finished" or "campaign_busy" in x for x in results), results)
        report = engine.verify(self.root)
        self.assertEqual(report["summary"]["attempt_reservations"], 10)
        self.assertEqual(report["summary"]["fake_provider_invocations"], 10)
        self.assertTrue(report["summary"]["all_positions_terminal"])

    def test_sqlite_transaction_alone_prevents_concurrent_duplicate_reservations(self):
        import threading
        self.create()
        barrier = threading.Barrier(2)
        def claim():
            db = self.db()
            try:
                m, _ = validate_manifest(self.root)
                barrier.wait()
                return engine.reserve(db, self.root, m, m["positions"][0])
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(engine.verify(self.root)["summary"]["attempt_reservations"], 1)

    def test_invalid_and_exception_parents_block_without_child_attempts(self):
        self.create(); engine.resume(self.root)
        report = engine.verify(self.root)
        for parent, child in (("invalid", "invalid-child"), ("exception", "exception-child"),
                              ("unknown-identity", "identity-child")):
            self.assertNotEqual(report["receipts"][parent]["state"], "completed")
            self.assertEqual(report["receipts"][child]["state"], "blocked")
            self.assertIsNone(report["receipts"][child]["request_sha256"])
        self.assertEqual(report["receipts"]["invalid"]["diagnostics"]["failure_layer"], "lifecycle")
        self.assertIsNotNone(report["receipts"]["invalid"]["response_sha256"])
        self.assertIsNone(report["receipts"]["exception"]["response_sha256"])
        unknown = report["receipts"]["unknown-identity"]
        self.assertIsNone(unknown["observed_identity"])
        self.assertIsNotNone(unknown["response_sha256"])
        self.assertIsNone(unknown["diagnostics"]["parsed"])

    def test_crash_after_invocation_and_after_saved_response_never_reissues(self):
        for point in ("invoked", "response"):
            with self.subTest(point=point):
                self.root = self.base / point
                self.create()
                if point == "invoked":
                    mutation = "e.FakeProvider.invoke=lambda self,req,record:(record(),os._exit(75))"
                else:
                    mutation = "e.finish=lambda *args,**kwargs:os._exit(75)"
                self.fault("import os,sys;from pathlib import Path;from engineering_qualification_v1.q1_executor import engine as e;"
                           + mutation + ";e.resume(Path(sys.argv[1]))")
                before = engine.verify(self.root)["summary"]
                self.assertEqual(before["fake_provider_invocations"], 1)
                after = engine.resume(self.root)
                self.assertEqual(after["fake_provider_invocations"], 1)
                self.assertEqual(after["states"], {"interrupted": 1, "blocked": 14})
                receipt = engine.verify(self.root)["receipts"]["baseline"]
                self.assertIsNone(receipt["disposition"])
                self.assertEqual(receipt["response_sha256"] is not None, point == "response")

    def test_manifest_raw_receipt_request_journal_or_state_tampering_is_rejected(self):
        self.create(); engine.resume(self.root)
        for kind in ("manifest", "raw", "receipt", "request", "journal", "state", "missing_receipt", "missing_parent",
                     "receipt_bytes", "journal_bytes", "schema"):
            with self.subTest(kind=kind):
                copy_root = self.base / ("tamper-" + kind)
                shutil.copytree(self.root, copy_root)
                if kind == "manifest":
                    m = decode((copy_root / "manifest.json").read_bytes())
                    m["simulated_budget_units"] += 1
                    m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
                    (copy_root / "manifest.json").write_bytes(encode(m))
                else:
                    with sqlite3.connect(copy_root / "campaign.sqlite3") as db:
                        if kind == "raw":
                            db.execute("UPDATE responses SET raw=? WHERE id='baseline'", (b'{}',))
                        elif kind == "receipt":
                            raw = db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0]
                            body = decode(raw); body["disposition"] = "fail"
                            db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (encode(body),))
                        elif kind == "request":
                            raw = db.execute("SELECT request FROM attempts WHERE id='control'").fetchone()[0]
                            body = decode(raw); body["parents"]["baseline"] = "0" * 64
                            db.execute("UPDATE attempts SET request=? WHERE id='control'", (encode(body),))
                        elif kind == "journal":
                            db.execute("DELETE FROM events WHERE seq=2")
                        elif kind == "receipt_bytes":
                            raw = db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0]
                            db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (raw + b' ',))
                        elif kind == "journal_bytes":
                            raw = db.execute("SELECT body FROM events WHERE seq=1").fetchone()[0]
                            db.execute("UPDATE events SET body=? WHERE seq=1", (raw + b' ',))
                        elif kind == "schema":
                            db.execute("CREATE TABLE unexpected_evidence (id TEXT)")
                        elif kind == "state":
                            db.execute("UPDATE positions SET state='scheduled' WHERE id='baseline'")
                        elif kind == "missing_receipt":
                            db.execute("DELETE FROM receipts WHERE id='control'")
                        else:
                            db.execute("DELETE FROM positions WHERE id='baseline'")
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    engine.verify(copy_root)

    def test_source_policy_and_wrong_parent_bindings_are_rejected(self):
        for kind in ("source", "governing_policy", "challenge_policy", "position_packet", "parent"):
            with self.subTest(kind=kind):
                fixture = self.base / kind
                shutil.copytree(PACKAGE / "fixtures", fixture)
                m = decode((fixture / "manifest.json").read_bytes())
                if kind in m["packets"]:
                    target = fixture / m["packets"][kind]["path"]
                    target.write_bytes(target.read_bytes() + b' ')
                elif kind == "position_packet":
                    m["positions"][1]["packet_bindings"]["governing_policy"] = "0" * 64
                else:
                    m["positions"][1]["assessment_parent"] = "missing"
                    m["positions"][1]["dependencies"] = ["missing"]
                if kind not in m["packets"]:
                    m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
                    (fixture / "manifest.json").write_bytes(encode(m))
                with self.assertRaises(ValueError):
                    validate_manifest(fixture)

    def test_separate_budget_and_attempt_ceiling_preserve_prior_outcomes(self):
        for key in ("attempt_ceiling", "simulated_budget_units"):
            fixture = self.base / key
            shutil.copytree(PACKAGE / "fixtures", fixture)
            m = decode((fixture / "manifest.json").read_bytes()); m[key] = 2
            m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
            (fixture / "manifest.json").write_bytes(encode(m))
            self.root = self.base / ("campaign-" + key)
            engine.create(self.root, fixture)
            summary = engine.resume(self.root)
            self.assertEqual(summary["attempt_reservations"], 2)
            self.assertEqual(summary["fake_provider_invocations"], 2)
            self.assertEqual(summary["states"]["completed"], 2)
            self.assertTrue(summary["all_positions_terminal"])
            before = self.snapshot(); engine.resume(self.root)
            self.assertEqual(before, self.snapshot())

    def test_readonly_verifier_never_invokes_and_offline_engine_has_no_transport(self):
        self.create()
        with ExitStack() as stack:
            forbidden = [stack.enter_context(patch.object(owner, name, side_effect=AssertionError("network forbidden")))
                         for owner, name in ((socket, "socket"), (socket, "create_connection"),
                                             (urllib.request, "urlopen"), (subprocess, "Popen"))]
            engine.resume(self.root)
            with patch.object(FakeProvider, "invoke", side_effect=AssertionError("verifier called provider")):
                before = self.snapshot(); engine.verify(self.root)
                self.assertEqual(before, self.snapshot())
            for mock in forbidden:
                mock.assert_not_called()
        with self.assertRaisesRegex(ValueError, "only_the_local_fake"):
            engine.resume(self.root, object())

    def test_second_creation_symlinks_and_live_identity_refused(self):
        self.create()
        with self.assertRaises(FileExistsError):
            self.create()
        alias = self.base / "alias"; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            engine.verify(alias)
        fixture = self.base / "real-identity"; shutil.copytree(PACKAGE / "fixtures", fixture)
        m = decode((fixture / "manifest.json").read_bytes())
        m["positions"][0]["identity"]["provider"] = "real-provider"
        m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
        (fixture / "manifest.json").write_bytes(encode(m))
        with self.assertRaises(ValueError):
            validate_manifest(fixture)

    def test_parent_receipt_is_rechecked_before_another_reservation(self):
        self.create()
        original = engine.finish
        def corrupt_parent(db, root, m, p, state, reason):
            original(db, root, m, p, state, reason)
            if p["id"] == "baseline":
                receipt = decode(db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0])
                receipt["disposition"] = "fail"
                db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (encode(receipt),))
        with patch.object(engine, "finish", side_effect=corrupt_parent):
            with self.assertRaisesRegex(ValueError, "receipt_or_diagnostics"):
                engine.resume(self.root)
        with sqlite3.connect(self.root / "campaign.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM invocations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM attempts").fetchone()[0], 1)

    def test_malformed_raw_bytes_are_preserved_without_repair(self):
        self.create()
        def malformed(provider, request, record):
            record()
            return b'\xff{not-json', request["position"]["identity"]
        with patch.object(FakeProvider, "invoke", new=malformed):
            result = engine.resume(self.root)
        self.assertEqual(result["states"], {"invalid": 1, "blocked": 14})
        with sqlite3.connect(self.root / "campaign.sqlite3") as db:
            self.assertEqual(db.execute("SELECT raw FROM responses WHERE id='baseline'").fetchone()[0], b'\xff{not-json')
        self.assertIsNone(engine.verify(self.root)["receipts"]["baseline"]["disposition"])


if __name__ == "__main__":
    unittest.main()
