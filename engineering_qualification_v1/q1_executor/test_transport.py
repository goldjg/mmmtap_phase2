"""Active, offline containment tests. Never substitute voluntary compliance."""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from . import engine
from .model import PACKAGE, decode, digest, encode, raw_hash, request_for, validate_manifest
from .transport import OfflineSubprocessTransport, envelope_for, specification, unb64
from .transport_qualification import demo, fixture, probes, snapshot


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        # A harmless host-side file, never a credential or research custody read.
        cls.canary = PACKAGE / "transport_evidence/forbidden-canary.txt"
        if not cls.canary.exists():
            raise AssertionError("synthetic forbidden canary must exist for real filesystem-denial testing")
        cls.canary_hash = raw_hash(cls.canary.read_bytes())
        cls.result = demo(cls.base / "demonstration")
        with patch.dict(os.environ, {"Q1_CREDENTIAL_CANARY": "synthetic-secret", "Q1_PRIOR_CONVERSATION": "never-inherit"}):
            cls.probes = probes(cls.base / "probes")
        cls.campaign = cls.base / "demonstration/campaign"

    def test_subprocess_dependency_graph_and_valid_specialist_continuation(self):
        audit = engine.verify(self.campaign)
        self.assertEqual(audit["summary"]["states"], {"completed": 6, "invalid": 1, "blocked": 4, "interrupted": 1, "unavailable": 3})
        self.assertEqual(audit["summary"]["attempt_reservations"], 10)
        self.assertEqual(audit["summary"]["subprocess_transport_launch_intents"], 10)
        self.assertEqual(audit["summary"]["subprocess_bootstraps_verified"], 10)
        self.assertEqual(audit["summary"]["fake_provider_invocations"], 0)
        for ident in ("baseline", "native", "intermediate", "carl", "final"):
            self.assertEqual(audit["receipts"][ident]["state"], "completed")
            self.assertEqual(audit["receipts"][ident]["schema"], "q1-offline-subprocess-v1-receipt")
        self.assertEqual(audit["receipts"]["intermediate"]["baseline_disposition_pair"], ["pass", "review_required"])
        self.assertEqual(audit["receipts"]["final"]["preceding_disposition_pair"], ["review_required", "pass"])
        self.assertEqual(audit["receipts"]["final"]["baseline_disposition_pair"], ["pass", "pass"])

    def test_invocation_is_after_durable_reservation_and_sealed_preparation(self):
        audit = engine.verify(self.campaign)
        by_id = {}
        for e in audit["history"]:
            by_id.setdefault(e["position"], []).append(e["kind"])
        with sqlite3.connect(self.campaign / "campaign.sqlite3") as db:
            requests = dict(db.execute("SELECT id,request FROM attempts"))
            for ident, envelope, record in db.execute("SELECT * FROM transports"):
                e, r = decode(envelope), decode(record)
                self.assertEqual(raw_hash(requests[ident]), e["request_sha256"])
                self.assertEqual(e["attempt_id"], digest({"manifest": audit["manifest"]["manifest_sha256"], "position": ident}))
                self.assertEqual(r["configuration_sha256"], audit["manifest"]["transport"]["configuration_sha256"])
                kinds = by_id[ident]
                self.assertLess(kinds.index("reserved"), kinds.index("transport_prepared"))
                self.assertLess(kinds.index("transport_prepared"), kinds.index("transport_invoked"))
                self.assertEqual(kinds.count("transport_invoked"), 1)
                self.assertTrue(r["cleanup"])
        self.assertFalse((self.campaign / ".transport-work").exists())

    def test_running_interruption_keeps_raw_prefix_and_never_reinvokes(self):
        self.assertEqual(self.result["interruption_exit"], 75)
        self.assertEqual(self.result["interrupted_attempt_invocations"], 1)
        self.assertTrue(self.result["abandoned_process_tree_stopped_by_os"])
        self.assertGreaterEqual(len(self.result["abandoned_processes"]), 2)
        self.assertTrue(self.result["all_campaign_files_unchanged"])
        self.assertEqual(unb64(self.result["transport_records"]["interruption"]["stdout_b64"]), b"partial-before-hang")
        self.assertEqual(self.result["transport_records"]["interruption"]["status"], "interrupted")
        before = snapshot(self.campaign)
        for _ in range(2): engine.resume(self.campaign, offline_subprocess=True)
        self.assertEqual(before, snapshot(self.campaign))
        audit = engine.verify(self.campaign)
        for ident in ("interruption", "interruption-child"):
            self.assertIsNone(audit["receipts"][ident]["disposition"])
        # A killed supervisor PID is not reused as a signal target on recovery.
        with patch.object(os, "kill", side_effect=AssertionError("must not signal saved PID")):
            engine.resume(self.campaign, offline_subprocess=True)

    def test_interrupt_after_reservation_before_invocation(self):
        frozen = fixture(self.base / "before-invoke-fixture", selected={"baseline"}, budget=1)
        campaign = engine.create(self.base / "before-invoke", frozen)
        run = subprocess.run([sys.executable, "-m", "engineering_qualification_v1.q1_executor", "resume", "--offline-subprocess",
                              "--campaign", str(campaign), "--interrupt-after-reservation", "baseline"], capture_output=True)
        self.assertEqual(run.returncode, 75, run.stderr.decode())
        before = engine.verify(campaign)["summary"]
        self.assertEqual(before["subprocess_transport_launch_intents"], 0)
        result = engine.resume(campaign, offline_subprocess=True)
        self.assertEqual(result["states"], {"interrupted": 1})
        self.assertEqual(result["subprocess_transport_launch_intents"], 0)
        engine.resume(campaign, offline_subprocess=True)

    def test_malicious_process_fs_tools_network_and_readonly_inputs(self):
        for scenario in ("forbidden_file", "spawn", "exec", "network", "source_write", "policy_write"):
            with self.subTest(scenario=scenario):
                result = self.probes[scenario]
                self.assertEqual(result["status"], "PASS")
                self.assertTrue(result["record"]["bootstrap_verified"])
                self.assertTrue(result["observation"]["prevented"])
                self.assertEqual(result["observation"]["errno"], 30 if "write" in scenario else 2 if scenario == "forbidden_file" else 1)
        self.assertEqual(raw_hash(self.canary.read_bytes()), self.canary_hash)

    def test_interruption_after_saved_response_never_promotes_or_reinvokes(self):
        frozen = fixture(self.base / "receipt-gap-fixture", selected={"baseline"}, budget=1)
        campaign = engine.create(self.base / "receipt-gap", frozen)
        code = ("import os,sys;from pathlib import Path;from engineering_qualification_v1.q1_executor import engine as e;"
                "e.finish=lambda *a,**k:os._exit(75);e.resume(Path(sys.argv[1]),offline_subprocess=True)")
        run = subprocess.run([sys.executable, "-c", code, str(campaign)], capture_output=True)
        self.assertEqual(run.returncode, 75, run.stderr.decode())
        audit = engine.verify(campaign)
        self.assertEqual(audit["summary"]["subprocess_transport_launch_intents"], 1)
        self.assertEqual(engine.resume(campaign, offline_subprocess=True)["states"], {"interrupted": 1})
        r = engine.verify(campaign)["receipts"]["baseline"]
        self.assertIsNone(r["disposition"])
        self.assertIsNotNone(r["response_sha256"])
        before = snapshot(campaign);engine.resume(campaign, offline_subprocess=True)
        self.assertEqual(before, snapshot(campaign))

    def test_session_reuse_environment_and_workspace_isolation(self):
        seeded = self.probes["session_seed"]["observation"]
        self.assertTrue(seeded["seeded"])
        self.assertEqual(seeded["environment"], specification()["environment"])
        self.assertNotIn("Q1_CREDENTIAL_CANARY", seeded["environment"])
        self.assertNotIn("Q1_PRIOR_CONVERSATION", seeded["environment"])
        self.assertEqual(self.probes["reuse"]["observation"], {"attack": "reuse", "prevented": True, "errno": 2})
        contexts = [p["record"]["context_id"] for p in self.probes.values()]
        self.assertEqual(len(set(contexts)), len(contexts))

    def test_malformed_partial_timeout_crash_and_identity_failures(self):
        self.assertEqual(self.probes["valid"]["outcome"], "completed")
        self.assertEqual(self.probes["malformed"]["outcome"], "invalid")
        for scenario in ("partial_failure", "timeout", "crash", "identity_unknown", "identity_mismatch"):
            self.assertEqual(self.probes[scenario]["outcome"], "unavailable")
        self.assertEqual(unb64(self.probes["partial_failure"]["record"]["stdout_b64"]), b'{"partial":')
        self.assertEqual(self.probes["partial_failure"]["record"]["returncode"], 23)
        self.assertEqual(self.probes["crash"]["record"]["returncode"], 24)
        self.assertEqual(self.probes["timeout"]["record"]["status"], "timeout")
        self.assertEqual(self.probes["timeout"]["record"]["returncode"], -9)
        self.assertTrue(self.probes["timeout"]["record"]["uncertain_completion"])
        self.assertIsNone(self.probes["identity_unknown"]["record"]["observed_identity"])
        self.assertEqual(self.probes["identity_mismatch"]["record"]["identity_status"], "mismatch")

    def test_duplicate_launch_request_refused_without_process_creation(self):
        with engine.lock(self.campaign):
            db = engine.connect(self.campaign)
            try:
                m = engine.verify_database(db, self.campaign)["manifest"]
                p = m["positions"][0]
                req = decode(db.execute("SELECT request FROM attempts WHERE id='baseline'").fetchone()[0])
                with patch.object(subprocess, "Popen", side_effect=AssertionError("duplicate process created")):
                    with self.assertRaisesRegex(ValueError, "duplicate_transport_launch"):
                        engine.execute_transport(db, self.campaign, m, p, req, None)
            finally: db.close()

    def test_cancellation_kills_non_cooperative_process_and_captures_partial(self):
        frozen = fixture(self.base / "cancel-fixture", {"baseline": "timeout"}, selected={"baseline"}, budget=1)
        m, _ = validate_manifest(frozen);p = m["positions"][0]
        raw = encode(request_for(m, p, {}, frozen));env = envelope_for(m, p, raw)
        cancel = threading.Event()
        def observe(rec):
            if rec["stdout_b64"]:cancel.set()
        result = OfflineSubprocessTransport(specification()).invoke(env, raw, self.base / "cancel-work", observe, cancel=cancel)
        self.assertEqual(result.record["status"], "cancelled")
        self.assertEqual(result.record["returncode"], -9)
        self.assertEqual(result.raw, b"partial-before-hang")
        self.assertFalse((self.base / "cancel-work").exists())

    def test_explicit_offline_feature_and_manifest_controls_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "explicit_offline_subprocess_selection"):
            engine.resume(self.campaign)
        for kind in ("network", "tool", "executable", "request", "scenario"):
            frozen = fixture(self.base / ("bad-" + kind), selected={"baseline"}, budget=1)
            m = decode((frozen / "manifest.json").read_bytes())
            if kind == "network":m["transport"]["specification"]["network"] = "host"
            elif kind == "tool":m["transport"]["specification"]["tools"] = "allowed"
            elif kind == "executable":m["transport"]["specification"]["bindings"]["adapter"]["sha256"] = "0"*64
            elif kind == "scenario":m["transport"]["scenarios"]["baseline"] = "real_provider"
            else:m["positions"][0]["packet_bindings"]["source"] = "0"*64
            m["transport"]["configuration_sha256"] = digest(m["transport"]["specification"])
            m["manifest_sha256"] = digest({k:v for k,v in m.items() if k != "manifest_sha256"})
            (frozen / "manifest.json").write_bytes(encode(m))
            with self.assertRaises(ValueError):validate_manifest(frozen)

    def test_evidence_tampering_rejected_by_readonly_verifier(self):
        for kind in ("raw", "envelope", "transport", "identity", "receipt", "event"):
            root = self.base / ("corrupt-" + kind);shutil.copytree(self.campaign, root)
            with sqlite3.connect(root / "campaign.sqlite3") as db:
                if kind == "raw":db.execute("UPDATE responses SET raw=? WHERE id='baseline'", (b'{}',))
                elif kind in ("envelope", "transport", "identity"):
                    column = "envelope" if kind == "envelope" else "record"
                    rec = decode(db.execute("SELECT " + column + " FROM transports WHERE id='baseline'").fetchone()[0])
                    if kind == "envelope":rec["request_sha256"] = "0"*64
                    elif kind == "identity":rec["observed_identity"]["version"] = "foreign"
                    else:rec["status"] = "completed";rec["stdout_b64"] = "e30="
                    db.execute("UPDATE transports SET " + column + "=? WHERE id='baseline'", (encode(rec),))
                elif kind == "receipt":
                    rec = decode(db.execute("SELECT body FROM receipts WHERE id='baseline'").fetchone()[0])
                    rec["transport_record_sha256"] = "0"*64
                    db.execute("UPDATE receipts SET body=? WHERE id='baseline'", (encode(rec),))
                else:db.execute("DELETE FROM events WHERE seq=4")
            before = snapshot(root)
            with self.assertRaises((ValueError, KeyError, TypeError)):engine.verify(root)
            self.assertEqual(before, snapshot(root))

    def test_verifier_no_invocation_and_original_completed_campaigns_still_verify(self):
        with patch.object(OfflineSubprocessTransport, "invoke", side_effect=AssertionError("audit invoked adapter")):
            before = snapshot(self.campaign);engine.verify(self.campaign)
            self.assertEqual(before, snapshot(self.campaign))
            for path in (PACKAGE/"evidence/demo-campaign", PACKAGE/"full_matrix_evidence/demonstration/normal-campaign",
                         PACKAGE/"full_matrix_evidence/demonstration/adverse-campaign"):
                self.assertEqual(engine.verify(path)["summary"]["verification"], "PASS")


if __name__ == "__main__":
    unittest.main()
