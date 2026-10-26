"""Focused broker authority checks. Full real-process qualification is the CLI.

No provider/transport mocks. These exercise the broker's independent database
checks and verify that failures leave reservation and dispatch counts intact.
"""
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from .broker import authorise
from .contract import envelope_for, message
from .qualification import fixture, snapshot
from .. import engine
from ..model import PACKAGE, decode, digest, encode, request_for, validate_manifest


class BrokerAuthorityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.fixture = fixture(self.base / "fixture")
        self.root = engine.create(self.base / "campaign", self.fixture)
        self.m = engine.verify(self.root)["manifest"]
        self.p = self.m["positions"][0]

    def test_exact_sealed_message_without_reservation_is_rejected(self):
        sealed = encode(request_for(self.m, self.p, {}, self.root))
        msg = message(envelope_for(self.m, self.p, sealed), sealed)
        before = snapshot(self.root)
        with engine.connect(self.root) as db:
            with self.assertRaisesRegex(ValueError, "reservation_required"):
                authorise(db, self.root, "baseline", self.m["manifest_sha256"], msg)
        self.assertEqual(snapshot(self.root), before)

    def test_broker_rejection_without_reservation_is_valid_durable_evidence(self):
        child = subprocess.run([sys.executable, "-B", "-m",
                                "engineering_qualification_v1.q1_executor.broker_v1.broker",
                                "--campaign", str(self.root), "--position", "baseline",
                                "--manifest", self.m["manifest_sha256"]], input=b"{}\n", capture_output=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(decode(child.stdout)["reason"], "reservation_required")
        summary = engine.verify(self.root)["summary"]
        self.assertEqual(summary["attempt_reservations"], 0)
        self.assertEqual(summary["broker_dispatch_intents"], 0)
        self.assertEqual(summary["broker_rejected_requests"], 1)

    def test_foreign_campaign_grant_is_rejected_without_writes(self):
        before = snapshot(self.root)
        with engine.connect(self.root) as db:
            with self.assertRaisesRegex(ValueError, "grant_mismatch"):
                authorise(db, self.root, "baseline", "0"*64, {})
        self.assertEqual(snapshot(self.root), before)

    def test_changed_packet_is_rejected_by_broker_before_dispatch(self):
        with engine.connect(self.root) as db:
            self.assertTrue(engine.reserve(db, self.root, self.m, self.p))
            (self.root / "source.txt").write_bytes(b"tampered after reservation")
            with self.assertRaisesRegex(ValueError, "invalid_campaign_evidence"):
                authorise(db, self.root, "baseline", self.m["manifest_sha256"], {})
            self.assertEqual(db.execute("SELECT count(*) FROM invocations").fetchone()[0], 0)

    def test_changed_request_is_rejected_by_broker_before_dispatch(self):
        with engine.connect(self.root) as db:
            self.assertTrue(engine.reserve(db, self.root, self.m, self.p))
            with engine.transaction(db):
                db.execute("UPDATE attempts SET request=?", (b"{}",))
            with self.assertRaisesRegex(ValueError, "invalid_campaign_evidence"):
                authorise(db, self.root, "baseline", self.m["manifest_sha256"], {})
            self.assertEqual(db.execute("SELECT count(*) FROM invocations").fetchone()[0], 0)

    def test_self_rehashed_control_escalations_are_rejected(self):
        for key, value in (("network", "allowed"), ("tools", "allowed"), ("destination", "arbitrary"),
                           ("provider_deadline_seconds", 100), ("max_response_bytes", 10**9)):
            with self.subTest(key=key):
                m = decode(encode(self.m)); m["transport"]["specification"][key] = value
                m["transport"]["configuration_sha256"] = digest(m["transport"]["specification"])
                m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
                (self.fixture / "manifest.json").write_bytes(encode(m))
                with self.assertRaisesRegex(ValueError, "offline_broker_manifest_binding"):
                    validate_manifest(self.fixture)

    def test_relocated_paths_are_readonly_not_launch_authority(self):
        m = decode(encode(self.m))
        m["transport"]["specification"]["bindings"]["adapter"]["path"] = "/forbidden/worker.py"
        m["transport"]["configuration_sha256"] = digest(m["transport"]["specification"])
        m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
        (self.fixture / "manifest.json").write_bytes(encode(m))
        with self.assertRaisesRegex(ValueError, "historical_transport_configuration_readonly"):
            engine.create(self.base / "cannot-launch", self.fixture)
        self.assertFalse((self.base / "cannot-launch").exists())

    def test_original_executor_duplicate_reservation_still_refused(self):
        with engine.connect(self.root) as db:
            self.assertTrue(engine.reserve(db, self.root, self.m, self.p))
            before = snapshot(self.root)
            self.assertFalse(engine.reserve(db, self.root, self.m, self.p))
        self.assertEqual(snapshot(self.root), before)

    def test_original_historical_campaigns_verify_without_writes(self):
        for name in ("evidence/demo-campaign", "full_matrix_evidence/demonstration/normal-campaign",
                     "full_matrix_evidence/demonstration/adverse-campaign", "transport_evidence/demonstration/campaign"):
            with self.subTest(campaign=name):
                root = PACKAGE / name; before = snapshot(root)
                self.assertEqual(engine.verify(root)["summary"]["verification"], "PASS")
                self.assertEqual(snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
