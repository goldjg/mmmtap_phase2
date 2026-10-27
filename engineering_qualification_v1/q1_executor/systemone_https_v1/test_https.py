"""Cheap boundary regressions; actual TLS adversaries live in qualification.py."""
import copy
from pathlib import Path
import tempfile
import unittest

from . import DESTINATION
from .contract import make_manifest, native_request, POSITION, outcome
from .https import destination
from .. import engine
from ..model import decode, digest, encode, validate_manifest
from ..systemone_typed_v1.contract import bindings


class Bounds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = make_manifest(self.root / "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_creation_refuses_before_reservation(self):
        with self.assertRaisesRegex(ValueError, "LIVE_DISPATCH_DISABLED"):
            engine.create(self.root / "campaign", self.fixture)
        self.assertFalse((self.root / "campaign").exists())

    def test_one_position_and_no_generator_or_parent(self):
        m, _ = validate_manifest(self.fixture)
        self.assertEqual(len(m["positions"]), 1)
        self.assertEqual(m["positions"][0]["id"], POSITION)
        self.assertEqual(m["positions"][0]["kind"], "specialist")
        self.assertEqual(m["positions"][0]["dependencies"], [])
        self.assertEqual(m["attempt_ceiling"], 1)

    def test_no_switch_enablement(self):
        m, _ = validate_manifest(self.fixture)
        m["https_qualification"]["authority"]["state"] = "ENABLED"
        m["https_qualification"]["policy_sha256"] = digest(m["https_qualification"]["authority"])
        m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
        (self.fixture / "manifest.json").write_bytes(encode(m))
        with self.assertRaisesRegex(ValueError, "authority"):
            validate_manifest(self.fixture)

    def test_question_wording_and_scope_are_original(self):
        from .contract import SOURCE, ASSESSMENT
        request = bindings(native_request(), SOURCE, ASSESSMENT, ["synthetic-lamp"])
        self.assertEqual(set(request["questions"]), {"claim_0000_supported", "uncertainty_adequate", "authority_promoted"})

    def test_alternate_destinations_fail_exactly(self):
        destination(DESTINATION)
        for key, value in (("scheme", "http"), ("host", "api.typesafe.ai.evil.invalid"),
                           ("host", "API.TYPESAFE.AI"), ("port", 444), ("path", "/v1/systemone/"),
                           ("path", "/v1/systemone?redirect=1"), ("proxy", "http://localhost")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                destination({**DESTINATION, key: value})

    def test_source_tampering_rejected(self):
        (self.fixture / "source.txt").write_bytes(b"different synthetic input")
        with self.assertRaises(ValueError):
            validate_manifest(self.fixture)

    def test_schema_alone_cannot_establish_identity(self):
        m, _ = validate_manifest(self.fixture)
        rec = {"status": "completed", "identity_status": "unknown"}
        self.assertEqual(outcome(m["positions"][0], {}, rec)[:2], ("unavailable", "transport_identity_unknown"))


if __name__ == "__main__":
    unittest.main()
