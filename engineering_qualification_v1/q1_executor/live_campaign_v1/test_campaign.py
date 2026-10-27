import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from .contract import build, validate_manifest, request_for, native_request, MODEL
from .routing import fixture_cli_entity, parse_cli_entity
from .launch import require_live_authority
from ..model import decode, digest, encode
from ..systemone_typed_v1.contract import bindings


class CampaignContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "packets"
        cls.m = build(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_original_graph_and_subscription_routes(self):
        ps = self.m["positions"]
        self.assertEqual(len(ps), 153)
        self.assertEqual(sum(p["kind"] == "generator" for p in ps), 99)
        self.assertEqual(sum(p["route"] == "native" for p in ps), 27)
        self.assertEqual(sum(p["route"] == "carl" for p in ps), 27)
        self.assertEqual(sum(len(p["dependencies"]) for p in ps), 198)
        self.assertEqual({r["provider"] for k,r in self.m["production_campaign"]["routes"].items()
                          if k in ("gemini", "haiku", "sol")}, {"github_copilot_cli", "codex_cli"})

    def test_disabled_even_with_resealed_approval(self):
        with self.assertRaisesRegex(ValueError, "Q1_LIVE_LAUNCH_BLOCKED"):
            require_live_authority(self.m)
        for change in ("approval", "retries", "maximum_local_dispatches"):
            m = copy.deepcopy(self.m); m["production_campaign"][change] = True
            m["manifest_sha256"] = digest({k:v for k,v in m.items() if k != "manifest_sha256"})
            with self.assertRaises(ValueError): validate_manifest(self.root, m, encode(m))

    def test_real_event_parser_and_separate_codex_identity(self):
        for p in [p for p in self.m["positions"] if p["arm"] == "B0"][:3]:
            req = request_for(self.m, p, {}, self.root)
            raw = encode(fixture_cli_entity(req["instrument_request"], "valid"))
            message, usage, identity = parse_cli_entity(raw, req)
            self.assertEqual(decode(message)["case_id"], p["case_id"])
            self.assertEqual(usage["input_tokens"], 101)
            if p["generator"] == "sol": self.assertIsNone(identity["observed_model"])
            entity = decode(raw); entity["model"] = "substitution"
            with self.assertRaises(ValueError): parse_cli_entity(encode(entity), req)

    def test_extra_CLI_attempt_and_tool_events_rejected(self):
        p = self.m["positions"][0]; req = request_for(self.m, p, {}, self.root)
        import base64
        for event in ({"type": "model.call_start", "data": {"model": p["identity"]["model"]}},
                      {"type": "tool.execution_start"}):
            entity = fixture_cli_entity(req["instrument_request"], "valid")
            stdout = base64.b64decode(entity["stdout_b64"]) + b"\n" + encode(event)
            entity["stdout_b64"] = base64.b64encode(stdout).decode()
            with self.assertRaises(ValueError): parse_cli_entity(encode(entity), req)

    def test_same_Choice1_catalog_for_multiple_claims(self):
        assessment = {"claims": [{"claim_id": "one"}, {"claim_id": "two"}]}
        raw = native_request("source", assessment)
        request = bindings(raw, b"source", assessment, ["one", "two"])
        self.assertEqual(request["model"], MODEL)
        self.assertEqual(len(request["questions"]), 4)
        self.assertEqual(request["questions"]["claim_0001_supported"]["instructions"],
                         "Is assessment.claims[1] materially supported by exact source evidence?")

    def test_serial_dummy_source_lifetime_and_erase(self):
        # The parent never reads or copies its environment or any actual key.
        script = '''import os
from engineering_qualification_v1.q1_executor.live_campaign_v1 import credential as c
with c.session():
 a=c.issue();assert a==b'PUBLIC-DUMMY-CAMPAIGN';assert 'JEVKEY' not in os.environ
 a[:]=b'\\x00'*len(a)
 b=c.issue();assert b==b'PUBLIC-DUMMY-CAMPAIGN';assert c.configured()
 b[:]=b'\\x00'*len(b)
assert c._token is None and not c._active
'''
        run = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True,
                             env={"LANG": "C.UTF-8", "JEVKEY": "PUBLIC-DUMMY-CAMPAIGN"})
        self.assertEqual(run.returncode, 0, "dummy lifetime failed")
        self.assertEqual(run.stdout, b"")
        self.assertEqual(run.stderr, b"")

    def test_already_aborted_transaction_keeps_original_error(self):
        import sqlite3
        from ..engine import transaction
        db = sqlite3.connect(":memory:", isolation_level=None)
        try:
            with self.assertRaisesRegex(OSError, "original_storage_error"):
                with transaction(db):
                    db.execute("ROLLBACK")
                    raise OSError("original_storage_error")
        finally: db.close()

    def test_actual_carl_compiler_capture_replays_and_rejects_policy_tamper(self):
        import base64
        from unittest.mock import patch
        p = self.m["positions"][0]
        first = request_for(self.m, p, {}, self.root)
        message, _, _ = parse_cli_entity(encode(fixture_cli_entity(first["instrument_request"], "valid")), first)
        receipts = {p["id"]: {"state": "completed", "diagnostics": {"parsed": decode(message)}}}
        p = self.m["positions"][7]
        actual = request_for(self.m, p, receipts, self.root)
        with patch(__package__ + ".contract.prepare_carl", side_effect=AssertionError("unexpected_recompilation")):
            self.assertEqual(request_for(self.m, p, receipts, self.root, captured=actual), actual)
        altered = copy.deepcopy(actual)
        prepared = decode(base64.b64decode(altered["carl_prepared_b64"]))
        prepared["policy"]["rules"][0]["rule"]["threshold"] = 0.001
        altered["carl_prepared_b64"] = base64.b64encode(encode(prepared)).decode()
        with self.assertRaisesRegex(ValueError, "carl_prepared_input_policy_or_parent_binding_changed"):
            request_for(self.m, p, receipts, self.root, captured=altered)


if __name__ == "__main__": unittest.main()
