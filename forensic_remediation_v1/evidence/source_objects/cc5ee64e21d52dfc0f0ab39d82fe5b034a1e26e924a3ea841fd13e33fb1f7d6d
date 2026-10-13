from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from phase2.core import ROOT, IntegrityError, corpus, digest, json_bytes, load
from phase2.adapters_v2 import (GeneratorAdapter, PathBAdapter, codex_argv, copilot_argv, parse_events)
from phase2.isolation import (Staging, stream_run, sandbox_env, CopilotWatchdog, CodexWatchdog,
                             sha256_file, stage_codex_auth, redact)
from phase2.integration import freeze, plan_v3, validate_v3, ScriptedAdapters
from phase2.engine import execute
from phase2.adjudication import blind_export, checked_records


class IsolationTests(unittest.TestCase):
    def test_staging_fresh_and_clean(self):
        with Staging() as a, Staging() as b:
            self.assertNotEqual(a.root, b.root)
            self.assertEqual(a.root.stat().st_mode & 0o777, 0o700)
            (a.path("home") / "AGENTS.md").write_text("hostile")
            self.assertEqual(b.inventory("home"), [])
        self.assertTrue(a.removed and b.removed)

    def test_no_ambient_credentials_or_instructions(self):
        with patch.dict(os.environ, {"JEVKEY": "sensitive", "BASH_ENV": "hostile", "COPILOT_HOME": "hostile"}):
            env = sandbox_env()
        self.assertNotIn("JEVKEY", env)
        self.assertNotIn("BASH_ENV", env)
        self.assertNotIn("COPILOT_HOME", env)

    def test_watchdogs_reject_tools_and_retries(self):
        w = CopilotWatchdog()
        first = b'{"type":"model.call_start"}'
        self.assertIsNone(w("stdout", first))
        self.assertIsNotNone(w("stdout", first))
        self.assertIsNotNone(CopilotWatchdog()("stdout", b'{"type":"model.call_failure"}'))
        self.assertIsNotNone(CodexWatchdog()("stderr", b"ToolCall: exec"))
        self.assertIsNotNone(CodexWatchdog()("stdout", b'{"item":{"type":"command_execution"}}'))

    def test_timeout_and_size_failure_no_retry(self):
        for code, timeout, limit, expected in [
            ("import time;time.sleep(5)", 0.05, 1024, "timeout"),
            ("print('x'*100000)", 3, 1024, "output_size_limit")]:
            result = stream_run([sys.executable, "-c", code], stdin=b"", env=sandbox_env(), timeout=timeout, limit=limit)
            self.assertIn(expected, result.error)
            self.assertLessEqual(len(result.stdout), limit)

    def test_correct_cli_contracts(self):
        argv = codex_argv()
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--ephemeral", argv)
        self.assertEqual(argv[argv.index("--sandbox")+1], "read-only")
        self.assertFalse(any("model_providers.openai." in s for s in argv))
        self.assertTrue(any("request_max_retries=0" in s for s in argv))
        self.assertNotIn("-p", copilot_argv("claude-haiku-5.5"))
        self.assertIn("--available-tools=mmmtap_no_tool_placeholder", copilot_argv("claude-haiku-5.5"))

    def test_no_unauthorised_calls(self):
        with patch("phase2.adapters_v2.stream_run") as process:
            self.assertEqual(GeneratorAdapter({}, {}).invoke("text").error, "live_authorisation_required")
            self.assertEqual(PathBAdapter({}, {}).invoke({}).error, "live_authorisation_required")
            process.assert_not_called()

    def test_auth_copy_is_separate_and_redacted(self):
        with Staging() as a, Staging() as b:
            host = a.path("auth.json")
            host.write_text('{"tokens":{"access_token":"test-not-a-real-credential"}}')
            before = host.read_bytes()
            info = stage_codex_auth(host, b.path("home"))
            copied = b.path("home") / "auth.json"
            self.assertEqual(copied.stat().st_mode & 0o777, 0o600)
            self.assertEqual(copied.read_bytes(), before)
            copied.write_text('{"changed":"in-isolated-session-only"}')
            self.assertEqual(host.read_bytes(), before)
            scrubbed, changed = redact(b"test-not-a-real-credential", info["secrets"])
            self.assertTrue(changed)
            self.assertNotIn(b"test-not-a-real-credential", scrubbed)

    def test_actual_loopback_parsers_and_injection(self):
        base = ROOT / "integration_readiness_v1/isolation_controls_final"
        for name, provider, model in [("copilot_text", "github_copilot_cli", "claude-haiku-5.5"),
                                     ("codex_text", "codex_cli", "gpt-6.1-sol"), ("gemini_text", "github_copilot_cli", "gemini-3.8-flash")]:
            folder = base / name
            prompt = load(folder / "invocation.json")["spec"]["stdin"]
            out, err = (folder / "stdout.bin").read_bytes(), (folder / "stderr.bin").read_bytes()
            _, _, provenance = parse_events(out, err, model=model, provider=provider, prompt=prompt, mock=True)
            self.assertIsNone(provenance["provider_confirmed_model"])
            with self.assertRaises(ValueError):
                parse_events(out + b'\n{"type":"tool.execution_start"}', err, model=model, provider=provider, prompt=prompt, mock=True)
        out = (base / "copilot_text/stdout.bin").read_bytes()
        with self.assertRaises(ValueError):
            parse_events(out, b"", model="claude-haiku-5.5", provider="github_copilot_cli", prompt="different", mock=True)
        with self.assertRaises(ValueError):
            parse_events(out, b"", model="claude-haiku-5.5", provider="github_copilot_cli", prompt=prompt, mock=False)

    def test_exposed_tools_in_usage_telemetry_rejected(self):
        base = ROOT/"integration_readiness_v1/isolation_controls_final/copilot_text"
        prompt = load(base/"invocation.json")["spec"]["stdin"]
        events = [json.loads(l) for l in (base/"stdout.bin").read_bytes().splitlines()]
        for e in events:
            if e["type"] == "model.call_final_result":
                e["data"]["isByok"] = False
        events.append({"type":"session.usage_checkpoint","data":{
            "promptCacheBreakState":[{"models":{"claude-haiku-5.5":{"tool_count":21}}}]}})
        with self.assertRaisesRegex(ValueError,"tool_exposure"):
            parse_events(b"\n".join(json_bytes(e) for e in events),b"",model="claude-haiku-5.5",
                         provider="github_copilot_cli",prompt=prompt,mock=False)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source, cls.members = corpus()
        cls.binary = ROOT / "integration_readiness_v1/bin/carl-assessment-challenge-v2"
        freeze(cls.root / "instruments", cls.binary)
        cls.plan = plan_v3(cls.root / "instruments", cls.source, {"adapters": {}})
        cls.selection = {("synthetic-token-logging", "baseline")}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_plan_determinism_and_matrix(self):
        self.assertEqual(self.plan, plan_v3(self.root / "instruments", self.source, {"adapters": {}}))
        validate_v3(self.plan)
        self.assertEqual(self.plan["counts"]["jobs"], 6885)
        self.assertEqual(self.plan["counts"]["unique_input_hashes"], 108)
        self.assertEqual(self.plan["counts"]["inputs"], 135)
        self.assertEqual(self.plan["counts"]["carl_unsupported_jobs"], 0)
        self.assertEqual(self.plan["counts"]["live_unqualified_jobs"], 6885)
        seen = {}
        for j in self.plan["jobs"]:
            for dep in j["dependencies"]:
                self.assertIn(seen[dep]["arm"], ("B0", j["arm"]))
                self.assertEqual(seen[dep]["generator"], j["generator"])
            seen[j["job_id"]] = j

    def test_drift_and_live_gates(self):
        changed = copy.deepcopy(self.plan)
        changed["jobs"][0]["input_sha256"] = "0"*64
        changed["manifest_sha256"] = digest({k:v for k,v in changed.items() if k!="manifest_sha256"})
        with self.assertRaises(IntegrityError):
            validate_v3(changed)
        with self.assertRaises(IntegrityError):
            execute(self.plan, self.members, self.root / "forbidden", mode="live", authorised=True, max_live_calls=1)
        self.assertFalse((self.root / "forbidden").exists())
        with self.assertRaises(FileExistsError):
            freeze(self.root / "instruments", self.binary)

    def test_complete_nonempty_chain_all_arms_and_replay(self):
        out = self.root / "run"
        mock = ScriptedAdapters(self.plan)
        summary = execute(self.plan, self.members, out, mode="mock", selected_inputs=self.selection, mock=mock)
        self.assertEqual(summary["status_counts"], {"mock_ok": 51})
        self.assertEqual(len(mock.calls), len(set(mock.calls)))
        plan, records = checked_records(out)
        payloads = {}
        for job in plan["jobs"]:
            if job["job_id"] not in records:
                continue
            rec = records[job["job_id"]]
            if job["kind"] == "generator":
                self.assertEqual(len(rec["parsed"]["claims"]), 1)
                self.assertTrue(all(q["exact_source_substring"] for q in rec["quote_audit"]))
            else:
                raw = load(out / "checkpoints" / job["job_id"] / "raw.json")
                payload = load(out / "checkpoints" / job["job_id"] / "payload.json")["payload"]
                if job["mechanism"] == "carl_jev":
                    self.assertEqual(raw["provenance"]["replay_exit_status"], 0)
                    receipt = json.loads(base64.b64decode(raw["stdout"]))
                    self.assertEqual(receipt["mode"], "mock")
                    self.assertEqual(receipt["live_calls"], 0)
                    payload = json.loads(base64.b64decode(payload["native_request"]))
                payloads[(job["generator"], job["arm"], job["mechanism"])] = payload
        for g in ("haiku", "gemini", "sol"):
            self.assertEqual(payloads[(g,"E1","native_jev")],payloads[(g,"E2","carl_jev")])
        original = {str(p): sha256_file(p) for p in (out / "checkpoints").rglob("*") if p.is_file()}
        resumed = execute(self.plan, self.members, out, mode="mock", selected_inputs=self.selection, mock=mock)
        self.assertEqual(resumed["new_checkpoints"], 0)
        self.assertEqual(original, {str(p): sha256_file(p) for p in (out / "checkpoints").rglob("*") if p.is_file()})
        exported = blind_export(out, self.members, self.root / "blinded", self.root / "unblinding.json")
        self.assertEqual(exported["exported_pairs"], 21)
        packets = list((self.root / "blinded").glob("*.json"))
        for p in packets:
            obj=load(p)
            if "evidence_mode" in obj:
                self.assertEqual(obj["evidence_mode"], "mock_not_research")
                self.assertNotIn("generator", obj)
                self.assertNotIn("arm", obj)

    def test_failed_first_attempt_blocks_descendants(self):
        class Broken(ScriptedAdapters):
            identity = "malformed_first_attempt"
            def invoke(self, job, payload, previous):
                if job["kind"] == "generator":
                    from phase2.adapters import Response
                    return Response(message=b"{bad", exit_status=0)
                raise AssertionError("adversary called after bad B0")
        out = self.root / "failed"
        mock = Broken(self.plan)
        s = execute(self.plan, self.members, out, mode="mock", selected_inputs=self.selection, mock=mock)
        self.assertEqual(s["status_counts"], {"schema_invalid": 3, "blocked_parent": 48})
        self.assertEqual(execute(self.plan,self.members,out,mode="mock",selected_inputs=self.selection,mock=mock)["new_checkpoints"],0)

    def test_qualification_guard_and_immutable_failure(self):
        from phase2.readiness import qualify
        with patch("phase2.readiness.live_invoke_v3") as invoke:
            with self.assertRaises(ValueError):
                qualify(self.plan, self.members, self.root/"no-auth", "haiku", authorised=False)
            invoke.assert_not_called()
            from phase2.adapters import Response
            invoke.return_value = Response(error="unit_fixture_failure", provenance={"mode":"mock_test_only"})
            destination = self.root/"qualification-test-only"
            record = qualify(self.plan, self.members, destination, "haiku", authorised=True)
            self.assertEqual(record["status"], "execution_failed")
            with self.assertRaises(FileExistsError):
                qualify(self.plan, self.members, destination, "haiku", authorised=True)
            self.assertEqual(invoke.call_count, 1)
