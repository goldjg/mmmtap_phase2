from __future__ import annotations

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from historical_extractor.archive import IntegrityError, file_hash
from phase2.adapters import (
    GeneratorAdapter, NativeJEVAdapter, NoRedirect, Response, codex_overrides,
    parse_cli_events, redact_bytes, run_process,
)
from phase2.core import ROOT, digest, json_bytes, load, read_config, write_new
from phase2.qualification import audit_plan, fixture, freeze_manifest, invoke_once


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.cfg = read_config()

    def test_old_plan_independent_audit(self):
        plan = load(ROOT / "execution_plan_v2.json")
        source = load(ROOT / "MMMTAP_Phase2/corpus_manifest.json")
        audit = audit_plan(plan, source)
        self.assertEqual((audit["inputs"], audit["distinct_input_hashes"], audit["jobs"]), (135, 108, 6885))
        self.assertEqual(audit["adversarial_results_reused_across_branches"], 0)

    def test_old_plan_tampered_lineage_refused(self):
        plan = load(ROOT / "execution_plan_v2.json")
        source = load(ROOT / "MMMTAP_Phase2/corpus_manifest.json")
        plan["jobs"][2]["assessment_parent"] = plan["jobs"][1]["job_id"]
        plan["manifest_sha256"] = digest({k: v for k, v in plan.items() if k != "manifest_sha256"})
        with self.assertRaises(IntegrityError):
            audit_plan(plan, source)

    def test_feature_overrides_disable_unbounded_retries_and_host_state(self):
        values = codex_overrides()
        for expected in ("features.unbounded_connection_retries=false", "features.multi_agent=false",
                         "features.hooks=false", "features.plugins=false", "features.apps=false",
                         "features.daemon_auto_start=false", "project_doc_max_bytes=0",
                         "model_providers.openai.request_max_retries=0",
                         "model_providers.openai.stream_max_retries=0",
                         "features.skip_host_skill_discovery=true"):
            self.assertIn(expected, values)

    def test_credential_redaction_in_stdout_stderr_and_usage(self):
        secret = "unit-test-credential-never-real"
        def process(argv, prompt, cwd, env, timeout, limit):
            (cwd / "usage.json").write_text(json.dumps({"test_echo": secret}))
            raw = json_bytes({"type": "assistant.message", "data": {"content": secret}})
            return Response(stdout=raw, stderr=secret.encode(), exit_status=0)
        with patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": secret}, clear=True), \
             patch("phase2.adapters.executable", return_value=sys.executable), \
             patch("phase2.adapters.run_process", side_effect=process):
            result = GeneratorAdapter(self.cfg["generators"]["haiku"], self.cfg).invoke("fixture", authorised=True)
        self.assertNotIn(secret, json.dumps(result.record()))
        self.assertTrue(result.provenance["credential_redaction"])
        self.assertIsNone(result.provenance["provider_confirmed_model"])

    def test_two_adapter_turns_have_distinct_empty_homes(self):
        homes = []
        def process(argv, prompt, cwd, env, timeout, limit):
            homes.append(str(cwd))
            self.assertEqual(env["HOME"], str(cwd))
            self.assertTrue(env["XDG_CONFIG_HOME"].startswith(str(cwd)))
            self.assertFalse((cwd / "AGENTS.md").exists())
            self.assertNotIn("COPILOT_CUSTOM_INSTRUCTIONS_DIRS", env)
            self.assertNotIn("CODEX_THREAD_ID", env)
            return Response(stdout=json_bytes({"type": "assistant.message", "data": {"content": "{}"}}), exit_status=0)
        with patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "fake-token-for-unit-test",
                                     "COPILOT_CUSTOM_INSTRUCTIONS_DIRS": "/inherited",
                                     "CODEX_THREAD_ID": "inherited"}, clear=True), \
             patch("phase2.adapters.executable", return_value=sys.executable), \
             patch("phase2.adapters.run_process", side_effect=process):
            adapter = GeneratorAdapter(self.cfg["generators"]["haiku"], self.cfg)
            adapter.invoke("first", authorised=True)
            adapter.invoke("second", authorised=True)
        self.assertEqual(len(set(homes)), 2)
        self.assertTrue(all(not Path(p).exists() for p in homes))

    def test_nonzero_process_exit_has_one_attempt(self):
        response = run_process([sys.executable, "-c", "raise SystemExit(7)"], "", self.path, {}, 5, 1024)
        self.assertEqual(response.exit_status, 7)
        self.assertEqual(response.provenance["transport_attempts"], 1)

    def test_native_http_error_and_timeout_no_retry(self):
        spec = self.cfg["adversaries"]["native_jev"]
        for error in (urllib.error.HTTPError(spec["endpoint"], 429, "limited", {}, io.BytesIO(b"rate limited")),
                      TimeoutError("test timeout")):
            with self.subTest(error=type(error)), patch.dict(os.environ, {"JEVKEY": "unit-test-placeholder"}), \
                 patch("urllib.request.build_opener") as opener:
                opener.return_value.open.side_effect = error
                response = NativeJEVAdapter(spec, self.cfg).invoke(
                    {"state": "fixture", "model": "jev-latest", "questions": {"q": {"type": "noul"}}},
                    "frozen_text_assessment_v1", authorised=True)
            self.assertIsNotNone(response.error)
            self.assertEqual(opener.return_value.open.call_count, 1)
            self.assertEqual(response.provenance["transport_attempts"], 1)

    def test_redirect_refuses_credential_forwarding(self):
        with self.assertRaises(urllib.error.HTTPError):
            NoRedirect().redirect_request(
                type("Request", (), {"full_url": "https://api.typesafe.ai/v1/systemone"})(),
                None, 307, "redirect", {}, "https://not-approved.invalid")

    def test_qualification_no_authorisation_no_files(self):
        with self.assertRaises(IntegrityError):
            invoke_once(self.path, "native_jev", authorised=False)
        self.assertFalse((self.path / "attempts").exists())

    def test_carl_cannot_be_smuggled_into_smoke_partition(self):
        with self.assertRaises(IntegrityError):
            freeze_manifest(self.path, ["carl_jev"])

    def test_failed_first_smoke_cannot_retry(self):
        freeze_manifest(self.path, ["native_jev"])
        with patch("phase2.qualification.NativeJEVAdapter.invoke",
                   return_value=Response(error="test_failure", provenance={"transport_attempts": 1})) as adapter:
            first = invoke_once(self.path, "native_jev", authorised=True)
            before = file_hash(self.path / "attempts/native_jev/result.json")
            with self.assertRaises(FileExistsError):
                invoke_once(self.path, "native_jev", authorised=True)
        self.assertEqual(first["status"], "failed")
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(before, file_hash(self.path / "attempts/native_jev/result.json"))

    def test_interrupted_reservation_never_replays(self):
        freeze_manifest(self.path, ["native_jev"])
        with patch("phase2.qualification.NativeJEVAdapter.invoke", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                invoke_once(self.path, "native_jev", authorised=True)
        with patch("phase2.qualification.NativeJEVAdapter.invoke") as adapter, self.assertRaises(FileExistsError):
            invoke_once(self.path, "native_jev", authorised=True)
        adapter.assert_not_called()
        self.assertTrue((self.path / "attempts/native_jev/intent.json").exists())

    def test_mock_response_never_qualifies_live(self):
        freeze_manifest(self.path, ["native_jev"])
        with patch("phase2.qualification.NativeJEVAdapter.invoke",
                   return_value=Response(message=b"{}", provenance={"mock": True})):
            result = invoke_once(self.path, "native_jev", authorised=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["parser_error"], "mock_response_forbidden_in_live_qualification")

    def test_five_reservations_exhaust_global_budget(self):
        from phase2.engine import Ledger
        freeze_manifest(self.path, ["native_jev"])
        (self.path / "attempts").mkdir()
        ledger = Ledger(self.path / "attempts/ledger.jsonl")
        for number in range(5):
            ledger.append({"event": "reserved", "adapter": str(number), "live_reservation": 1})
        with patch("phase2.qualification.NativeJEVAdapter.invoke") as adapter, self.assertRaises(IntegrityError):
            invoke_once(self.path, "native_jev", authorised=True)
        adapter.assert_not_called()

    def test_fixture_has_source_grounded_questions_and_choice(self):
        plan = load(ROOT / "execution_plan_v2.json")
        _, payload = fixture(plan, "native_jev")
        state = json.loads(payload["state"])
        self.assertIn('return "Hello, " + name', state["untrusted_source"])
        self.assertIn("claim_0000_supported", payload["questions"])
        self.assertEqual(payload["questions"]["side_effect_choice"]["type"], "choice")

    def test_qualification_fixture_does_not_inherit_corpus_membership(self):
        plan = load(ROOT / "execution_plan_v2.json")
        job, _ = fixture(plan, "haiku")
        self.assertEqual(job["partition"], "adapter_qualification_only")
        self.assertEqual(job["input_member"], "inline:qualification-source")
        self.assertNotIn("job_id", job)
        self.assertNotIn("checkpoint", job)

    def test_cli_model_report_is_not_inferred_from_assistant_text(self):
        raw = json_bytes({"type": "item.completed", "item": {"type": "agent_message", "text": "I am GPT-6.1 Sol"}})
        _, _, provenance = parse_cli_events(raw, "codex_cli")
        self.assertIsNone(provenance["observed_model"])

    def test_real_copilot_metadata_shape_is_not_a_tool_call(self):
        events = [
            {"type": "session.tools_updated", "data": {"model": "claude-haiku-5.5"}},
            {"type": "model.call_start", "data": {"model": "claude-haiku-5.5"}},
            {"type": "assistant.message", "data": {"content": "{}", "model": "claude-haiku-5.5", "toolRequests": []}},
            {"type": "session.usage_checkpoint", "data": {"accountingSnapshot": {"modelMetrics": {
                "claude-haiku-5.5": {"requests": {"count": 1}, "usage": {"inputTokens": 12, "outputTokens": 2}}}}}},
        ]
        message, usage, provenance = parse_cli_events(b"\n".join(json_bytes(e) for e in events), "github_copilot_cli")
        self.assertEqual(message, b"{}")
        self.assertEqual(usage["input_tokens"], 12)
        self.assertEqual(provenance["observed_model"], "claude-haiku-5.5")
        events[-1]["data"]["promptCacheBreakState"] = [{"models": {"claude-haiku-5.5": {"tool_count": 21}}}]
        with self.assertRaisesRegex(ValueError, "tool_exposure"):
            parse_cli_events(b"\n".join(json_bytes(e) for e in events), "github_copilot_cli")

    def test_embedded_tool_requests_and_hidden_extra_calls_rejected(self):
        raw = json_bytes({"type": "assistant.message", "data": {"content": "{}", "toolRequests": [{"name": "bash"}]}})
        with self.assertRaisesRegex(ValueError, "tool_requests"):
            parse_cli_events(raw, "github_copilot_cli")
        raw = b"\n".join(json_bytes({"type": "model.call_start", "data": {}}) for _ in range(2))
        with self.assertRaisesRegex(ValueError, "multiple_model_calls"):
            parse_cli_events(raw, "github_copilot_cli")

    def test_native_probability_representation_is_validated(self):
        from phase2.adapters import parse_systemone
        request = {"questions": {"q": {"type": "choice", "criteria": {"none": "", "write": ""}}}}
        response = {"model": "jev-test", "answers": {"q": {"choice": "none", "probabilities": {"none": 1.0, "write": 0.0}}}}
        self.assertEqual(parse_systemone(json_bytes(response), request)["answers"]["q"]["choice"], "none")
        response["answers"]["q"]["probabilities"]["none"] = True
        with self.assertRaisesRegex(ValueError, "probabilities"):
            parse_systemone(json_bytes(response), request)


if __name__ == "__main__":
    unittest.main()
