from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from phase2.adapters import Response
from phase2.adapters_v2 import GeneratorAdapter, parse_events
from phase2.adjudication import checked_records
from phase2.core import IntegrityError, digest, json_bytes, load, write_new
from phase2.engine import Ledger
from phase2.isolation import RunResult, sandbox_env, sha256_file
from operator_execution_v1.checks import namespace_controls
from operator_execution_v1.planning import PACKAGE, base_plan, estimate, make_manifest, validate_manifest
from operator_execution_v1.profiles import authorise
from operator_execution_v1.runtime import OperatorMock, execute, interrupt_handlers, prerequisites, safe_runs_root
from operator_execution_v1.transports import Watchdog, _capture, generator, run_once, systemone


class OperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = base_plan()
        cls.smoke = make_manifest("smoke", base=cls.base)
        cls.pilot = make_manifest("pilot", base=cls.base)
        cls.full = make_manifest("full", base=cls.base)
        cls.strict = make_manifest("full", "strict_isolation", base=cls.base)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mmmtap-operator-test-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_two_deterministic_profiles_and_complete_matrix(self):
        self.assertEqual(self.full, make_manifest("full", base=self.base))
        self.assertEqual(self.full["counts"]["inputs"], 135)
        self.assertEqual(self.full["counts"]["jobs"], 6885)
        self.assertEqual(self.full["counts"]["generator_jobs"], 4455)
        self.assertEqual(self.full["counts"]["adversary_jobs"], 2430)
        self.assertEqual(self.full["counts"]["by_adapter"], {
            "haiku": 1485, "gemini": 1485, "sol": 1485, "native_jev": 1215, "carl_jev": 1215})
        self.assertNotEqual(self.full["manifest_sha256"], self.strict["manifest_sha256"])
        self.assertTrue(set(j["job_id"] for j in self.full["jobs"]).isdisjoint(
            j["job_id"] for j in self.strict["jobs"]))
        for plan in (self.full, self.strict):
            validate_manifest(plan)
            self.assertFalse(plan["operator_execution"]["profile"]["satisfies_strict_isolation"])
            self.assertEqual(plan["question_pack"], self.base["question_pack"])
            self.assertEqual(plan["config"], self.base["config"])
            self.assertEqual(plan["prompt_templates"], self.base["prompt_templates"])

    def test_stage_selection_keeps_all_controls(self):
        self.assertEqual(self.smoke["counts"]["jobs"], 5)
        self.assertEqual(set(self.smoke["counts"]["by_adapter"].values()), {1})
        self.assertEqual(self.pilot["counts"]["jobs"], 153)
        self.assertEqual(self.pilot["counts"]["inputs"], 3)
        self.assertEqual(set(j["arm"] for j in self.pilot["jobs"]),
                         {"B0", "C1", "C2", "C3", "E1", "E2", "E3_NC", "E3_CN"})
        self.assertEqual({j["generator"] for j in self.pilot["jobs"]}, {"haiku", "gemini", "sol"})
        for plan in (self.smoke, self.pilot, self.full):
            self.assertEqual(plan["operator_execution"]["max_concurrency"], 1)
            self.assertFalse(plan["operator_execution"]["automatic_retries"])
            self.assertFalse(plan["operator_execution"]["model_fallback"])

    def test_every_stage_requires_its_own_deliberate_authorisation(self):
        with patch("operator_execution_v1.runtime.invoke") as invoke:
            for stage, plan in (("smoke", self.smoke), ("pilot", self.pilot), ("full", self.full)):
                for authorised in (None, *(s for s in ("smoke", "pilot", "full") if s != stage)):
                    with self.assertRaises(IntegrityError):
                        execute(plan, self.root, mode="live", max_calls=len(plan["jobs"]),
                                authorised_stage=authorised, accept_lower_assurance=True,
                                approve_instruments=True, review_note="offline negative test")
                for accept, approve in ((False, True), (True, False)):
                    with self.assertRaises(IntegrityError):
                        authorise(plan, stage, authorised_stage=stage, accept_lower_assurance=accept,
                                  approve_instruments=approve, review_note="offline negative test")
            invoke.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_strict_remains_hard_blocked_even_with_flags(self):
        with patch("operator_execution_v1.runtime.invoke") as invoke:
            with self.assertRaisesRegex(IntegrityError, "strict_generator_isolation_blocked"):
                execute(self.strict, self.root, mode="live", max_calls=6885,
                        authorised_stage="full", accept_lower_assurance=True,
                        approve_instruments=True, review_note="This cannot override strict qualification.")
            self.assertEqual(GeneratorAdapter({}, {}).invoke("unused", authorised=True).error,
                             "strict_generator_isolation_blocked")
            invoke.assert_not_called()

    def test_altered_profile_or_model_or_source_is_rejected(self):
        for field in ("profile", "model", "source"):
            plan = copy.deepcopy(self.smoke)
            if field == "profile":
                plan["operator_execution"]["profile"]["satisfies_strict_isolation"] = True
            elif field == "model":
                plan["config"]["generators"]["haiku"]["model_id"] = "substitute"
            else:
                plan["jobs"][0]["input_sha256"] = "0" * 64
            plan["manifest_sha256"] = digest({k: v for k, v in plan.items() if k != "manifest_sha256"})
            with self.assertRaises(IntegrityError):
                validate_manifest(plan)

    def test_mock_cannot_be_passed_to_live_execution(self):
        with self.assertRaisesRegex(IntegrityError, "Mock adapters"):
            execute(self.smoke, self.root, mode="live", max_calls=5, authorised_stage="smoke",
                    accept_lower_assurance=True, approve_instruments=True, mock=OperatorMock(self.smoke))

    def test_smoke_does_not_start_later_stages_and_mock_is_not_approval(self):
        result = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(result["status_counts"], {"mock_ok": 5})
        self.assertFalse(result["automatic_next_stage"])
        self.assertFalse((self.root / "pilot").exists())
        self.assertFalse((self.root / "full").exists())
        with self.assertRaisesRegex(IntegrityError, "Mocks"):
            prerequisites(self.pilot, self.root)

    def test_nonempty_matched_chains_immutable_resume(self):
        mock = OperatorMock(self.pilot)
        result = execute(self.pilot, self.root, mode="mock", max_calls=153, mock=mock)
        self.assertEqual(result["status_counts"], {"mock_ok": 153})
        run = self.root / "pilot"
        plan, records = checked_records(run)
        payloads = {}
        for job in plan["jobs"]:
            record = records[job["job_id"]]
            self.assertEqual(record["evidence_quality"], "mock_not_research")
            self.assertFalse(record["satisfies_strict_isolation"])
            folder = run / "checkpoints" / job["job_id"]
            self.assertEqual((folder / "intent.json").stat().st_mode & 0o222, 0)
            self.assertEqual((folder / "result.json").stat().st_mode & 0o222, 0)
            if job["kind"] == "generator":
                self.assertTrue(record["parsed"]["claims"])
                self.assertTrue(all(row["exact_source_substring"] for row in record["quote_audit"]))
            else:
                raw = load(folder / "raw.json")
                payload = load(folder / "payload.json")["payload"]
                if job["mechanism"] == "carl_jev":
                    self.assertEqual(raw["provenance"]["replay_exit_status"], 0)
                    self.assertEqual(raw["provenance"]["transport_attempts"], 0)
                    self.assertEqual(raw["provenance"]["network"], "disabled")
                    payload = json.loads(base64.b64decode(payload["native_request"]))
                state = json.loads(payload["state"])
                self.assertTrue(state["untrusted_source"])
                self.assertTrue(state["assessment"]["claims"])
                self.assertIn("claim_0000_supported", payload["questions"])
                payloads[(job["case_id"], job["generator"], job["arm"], job["mechanism"], job["turn"])] = payload
        for case in {j["case_id"] for j in plan["jobs"]}:
            for gen in ("haiku", "gemini", "sol"):
                self.assertEqual(payloads[(case, gen, "E1", "native_jev", 1)],
                                 payloads[(case, gen, "E2", "carl_jev", 1)])
                for arm in ("C3", "E3_NC", "E3_CN"):
                    self.assertEqual({j["turn"] for j in plan["jobs"] if j["case_id"] == case
                                      and j["generator"] == gen and j["arm"] == arm}, {1, 2})
        before = {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()}
        with patch.object(mock, "invoke", side_effect=AssertionError("Resume must not invoke")):
            resumed = execute(plan, self.root, mode="mock", max_calls=153, mock=mock)
        self.assertEqual(resumed["new_checkpoints"], 0)
        self.assertEqual(resumed["preserved_checkpoints"], 153)
        self.assertEqual(before, {str(p): sha256_file(p) for p in (run / "checkpoints").rglob("*") if p.is_file()})

    def test_preparation_failure_is_reserved_before_rendering(self):
        with patch("operator_execution_v1.runtime.render_prompt", side_effect=ValueError("injected preparation failure")):
            first = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(first["status_counts"], {"execution_failed": 3, "blocked_parent": 2})
        self.assertEqual(first["adapter_attempt_reservations"], 3)
        self.assertEqual(first["invocations_this_session"], 0)
        with patch("operator_execution_v1.runtime.render_prompt", side_effect=AssertionError("No repair/retry")):
            second = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(second["new_checkpoints"], 0)

    def test_failed_adapter_is_not_retried_and_unknown_count_is_not_zero(self):
        class Failed(OperatorMock):
            def invoke(self, job, payload, previous):
                raise OSError("offline injected transport loss")
        result = execute(self.smoke, self.root, mode="mock", max_calls=5, mock=Failed(self.smoke))
        self.assertEqual(result["status_counts"], {"execution_failed": 3, "blocked_parent": 2})
        raw_attempts = [load(p)["provenance"]["transport_attempts"]
                        for p in (self.root / "smoke/checkpoints").glob("*/raw.json")]
        self.assertEqual(raw_attempts.count(None), 3)
        with patch.object(Failed, "invoke", side_effect=AssertionError("No retry")):
            result = execute(self.smoke, self.root, mode="mock", max_calls=5, mock=Failed(self.smoke))
        self.assertEqual(result["new_checkpoints"], 0)

    def test_budget_is_persisted_and_chunk_resume_skips_attempts(self):
        first = execute(self.smoke, self.root, mode="mock", max_calls=5, stop_after=1)
        self.assertEqual(first["adapter_attempt_reservations"], 1)
        self.assertFalse(first["complete"])
        self.assertEqual(first["stopped_reason"], "operator_chunk_limit")
        with self.assertRaises(IntegrityError):
            execute(self.smoke, self.root, mode="mock", max_calls=4)
        resumed = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(resumed["preserved_checkpoints"], 1)
        self.assertEqual(resumed["new_checkpoints"], 4)
        self.assertEqual(resumed["adapter_attempt_reservations"], 5)

    def test_hard_death_keeps_incomplete_intent_without_replay(self):
        plan_path = self.root / "plan.json"
        write_new(plan_path, self.smoke)
        script = (
            "import os;from pathlib import Path\n"
            "from phase2.core import load\n"
            "from operator_execution_v1.runtime import execute,OperatorMock\n"
            "class Die(OperatorMock):\n"
            " def invoke(self,*args): os._exit(77)\n"
            f"p=load(Path({str(plan_path)!r}))\n"
            f"execute(p,Path({str(self.root)!r}),mode='mock',max_calls=5,mock=Die(p))\n"
        )
        result = subprocess.run([sys.executable, "-c", script], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 77, result.stderr.decode())
        folder = next((self.root / "smoke/checkpoints").iterdir())
        intent_hash = sha256_file(folder / "intent.json")
        self.assertFalse((folder / "result.json").exists())
        resumed = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(resumed["status_counts"], {"incomplete_attempt": 1, "mock_ok": 4})
        self.assertEqual(resumed["adapter_attempt_reservations"], 5)
        self.assertFalse((folder / "result.json").exists())
        self.assertEqual(intent_hash, sha256_file(folder / "intent.json"))

    def test_interrupt_checkpoints_and_resume_does_not_reissue(self):
        class Interrupted(OperatorMock):
            def invoke(self, *args):
                raise KeyboardInterrupt
        first = execute(self.smoke, self.root, mode="mock", max_calls=5, mock=Interrupted(self.smoke))
        self.assertEqual(first["status_counts"], {"interrupted_attempt": 1, "not_attempted": 4})
        resumed = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(resumed["status_counts"], {"interrupted_attempt": 1, "mock_ok": 4})
        self.assertEqual(resumed["preserved_checkpoints"], 1)

    def test_result_before_completion_event_is_recovered_not_reissued(self):
        execute(self.smoke, self.root, mode="mock", max_calls=5, stop_after=1)
        path = self.root / "smoke/ledger.jsonl"
        events = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(events[0])
        result = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(result["preserved_checkpoints"], 1)
        self.assertEqual(result["new_checkpoints"], 4)
        self.assertEqual(sum(e["event"] == "recovered_completion" for e in Ledger(path).events), 1)

    def test_stage_completion_written_before_ledger_is_recovered(self):
        execute(self.smoke, self.root, mode="mock", max_calls=5)
        path = self.root / "smoke/ledger.jsonl"
        events = path.read_bytes().splitlines(keepends=True)
        self.assertEqual(json.loads(events[-1])["event"], "stage_completion")
        path.write_bytes(b"".join(events[:-1]))
        completion = sha256_file(self.root / "smoke/completion.json")
        resumed = execute(self.smoke, self.root, mode="mock", max_calls=5)
        self.assertEqual(resumed["new_checkpoints"], 0)
        anchors = [e["sha256"] for e in Ledger(path).events if e["event"] == "stage_completion"]
        self.assertEqual(anchors, [completion])

    def test_completed_attempt_tampering_is_not_accepted(self):
        execute(self.smoke, self.root, mode="mock", max_calls=5, stop_after=1)
        path = next((self.root / "smoke/checkpoints").glob("*/raw.json"))
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(IntegrityError, "artifact changed"):
            execute(self.smoke, self.root, mode="mock", max_calls=5)

    def test_workspace_registry_blocks_cross_directory_live_replay(self):
        report = {"blocking_infrastructure": [],
                  "credentials": {name: {"present": False} for name in self.smoke["counts"]["by_adapter"]}}
        arguments = dict(mode="live", max_calls=5, authorised_stage="smoke",
                         accept_lower_assurance=True, approve_instruments=True)
        with patch("operator_execution_v1.runtime.REGISTRY", self.root / "registry"), \
                patch("operator_execution_v1.runtime.preflight", return_value=report), \
                patch("operator_execution_v1.runtime.invoke") as invoke:
            result = execute(self.smoke, self.root / "one", **arguments)
            self.assertEqual(result["status_counts"], {"adapter_unavailable": 3, "blocked_parent": 2})
            with self.assertRaisesRegex(IntegrityError, "already reserved"):
                execute(self.smoke, self.root / "two", **arguments)
            self.assertEqual(execute(self.smoke, self.root / "one", **arguments)["new_checkpoints"], 0)
            invoke.assert_not_called()

    def test_interrupt_after_preflight_does_not_overwrite_or_block_resume(self):
        report = {"blocking_infrastructure": [],
                  "credentials": {name: {"present": False} for name in self.smoke["counts"]["by_adapter"]}}
        arguments = dict(mode="live", max_calls=5, authorised_stage="smoke",
                         accept_lower_assurance=True, approve_instruments=True)
        with patch("operator_execution_v1.runtime.REGISTRY", self.root / "registry"), \
                patch("operator_execution_v1.runtime.preflight", return_value=report), \
                patch("operator_execution_v1.runtime.invoke") as invoke:
            with patch("operator_execution_v1.runtime.corpus", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    execute(self.smoke, self.root / "run", **arguments)
            before = sha256_file(self.root / "run/smoke/preflight-000001.json")
            result = execute(self.smoke, self.root / "run", **arguments)
            self.assertTrue(result["complete"])
            self.assertEqual(before, sha256_file(self.root / "run/smoke/preflight-000001.json"))
            self.assertTrue((self.root / "run/smoke/preflight-000002.json").exists())
            invoke.assert_not_called()

    def test_missing_predecessor_and_no_review_note_block_next_stage(self):
        with self.assertRaises(OSError):
            prerequisites(self.pilot, self.root)
        with self.assertRaisesRegex(IntegrityError, "review note"):
            authorise(self.pilot, "pilot", authorised_stage="pilot", accept_lower_assurance=True,
                      approve_instruments=True, review_note="")

    def test_frozen_evidence_is_never_an_output_directory(self):
        for path in (PACKAGE, PACKAGE.parent, PACKAGE.parent / "forensic_remediation_v1", Path("/")):
            with self.assertRaises(IntegrityError):
                safe_runs_root(path)

    def test_cost_units_are_separate_and_unknown_is_not_zero(self):
        result = estimate(self.full, 6885)
        self.assertTrue(all(row["estimated_charge"] is None for row in result["full_stage_scenario"].values()))
        result = estimate(self.smoke, 5, input_tokens=1000, output_tokens=100, rates={
            "haiku": {"unit": "Copilot_AI_Credits", "input_per_million": 2,
                      "output_per_million": 5, "basis": "authored test rate, not a real quote"}})
        self.assertEqual(result["full_stage_scenario"]["haiku"]["estimated_charge"], 0.0025)
        self.assertIsNone(result["full_stage_scenario"]["sol"]["estimated_charge"])
        for cap in (0, 6, True):
            with self.assertRaises(IntegrityError):
                estimate(self.smoke, cap)

    def test_no_live_adapter_without_authorisation(self):
        job = next(j for j in self.smoke["jobs"] if j["kind"] == "generator")
        adversary = next(j for j in self.smoke["jobs"] if j["kind"] == "adversary")
        with patch("operator_execution_v1.transports.run_once") as process:
            self.assertIn("authorisation", generator(self.smoke, job, "not a request").error)
            self.assertIn("authorisation", systemone(self.smoke, adversary, {}).error)
            process.assert_not_called()


class ProcessTests(unittest.TestCase):
    def test_real_filesystem_environment_and_process_positive_negative_controls(self):
        result = namespace_controls()
        self.assertEqual(result["rows"]["research_process_denial"]["subprocess_errno"], 1)
        self.assertEqual(result["live_calls"], 0)

    def test_watchdog_kills_tool_retry_and_model_switch_events(self):
        cases = [
            ("github_copilot_cli", '{"type":"tool.execution_start"}', "tool"),
            ("github_copilot_cli", '{"type":"model.call_failure"}', "failure"),
            ("github_copilot_cli", '{"type":"model.call_start","data":{"model":"wrong"}}', "model_switch"),
            ("codex_cli", '{"type":"item.started","item":{"type":"command_execution"}}', "non_assessment"),
        ]
        for provider, event, reason in cases:
            script = f"import time;print({event!r},flush=True);time.sleep(60)"
            result = run_once([sys.executable, "-c", script], stdin=b"", env=sandbox_env(),
                              timeout=5, limit=4096, watchdog=Watchdog(provider, "requested"))
            self.assertIn(reason, result.watchdog_reason)
            self.assertTrue(result.killed)
            self.assertLess(result.latency_seconds, 5)
            self.assertEqual(result.stdout.strip().decode(), event)

    def test_partial_debug_tool_marker_kills_without_waiting_for_newline(self):
        script = "import sys,time;sys.stderr.write('ToolCall: exec');sys.stderr.flush();time.sleep(60)"
        result = run_once([sys.executable, "-c", script], stdin=b"", env=sandbox_env(),
                          timeout=5, limit=4096, watchdog=Watchdog("codex_cli", "gpt-6.1-sol"))
        self.assertIn("tool_routing", result.watchdog_reason)
        self.assertLess(result.latency_seconds, 5)

    def test_complete_stdout_tool_event_without_newline_is_detected(self):
        event = '{"type":"tool.execution_start"}'
        script = f"import sys,time;sys.stdout.write({event!r});sys.stdout.flush();time.sleep(60)"
        result = run_once([sys.executable, "-c", script], stdin=b"", env=sandbox_env(),
                          timeout=5, limit=4096, watchdog=Watchdog("github_copilot_cli", "claude-haiku-5.5"))
        self.assertIn("tool", result.watchdog_reason)
        self.assertLess(result.latency_seconds, 5)

    def test_partial_normal_event_does_not_double_count_a_single_call(self):
        event = '{"type":"model.call_start","data":{"model":"claude-haiku-5.5"}}'
        script = f"import sys,time;sys.stdout.write({event!r});sys.stdout.flush();time.sleep(.1);print()"
        result = run_once([sys.executable, "-c", script], stdin=b"", env=sandbox_env(),
                          timeout=5, limit=4096, watchdog=Watchdog("github_copilot_cli", "claude-haiku-5.5"))
        self.assertIsNone(result.watchdog_reason)
        self.assertIsNone(result.error)
        self.assertEqual(result.exit_status, 0)

    def test_codex_visible_configuration_switch_and_retries_are_rejected(self):
        for line in (b"Configuring session: model=other-model", b"retrying request", b"reconnecting stream"):
            self.assertIsNotNone(Watchdog("codex_cli", "gpt-6.1-sol")("stderr", line))

    def test_sigint_sigterm_capture_partial_output_and_kill_child(self):
        for signum in (signal.SIGINT, signal.SIGTERM):
            timer = threading.Timer(0.3, lambda: os.kill(os.getpid(), signum))
            with interrupt_handlers():
                timer.start()
                try:
                    result = run_once([sys.executable, "-c", "import os,time;print(os.getpid(),flush=True);time.sleep(60)"],
                                      stdin=b"", env=sandbox_env(), timeout=10, limit=4096)
                finally:
                    timer.join()
            self.assertIn("operator_interrupted", result.error)
            self.assertTrue(result.stdout.strip())
            with self.assertRaises(ProcessLookupError):
                os.kill(int(result.stdout.strip()), 0)

    def test_timeouts_and_output_caps_fail_without_retry(self):
        for script, timeout, limit, reason in (
            ("import time;time.sleep(60)", 0.1, 4096, "timeout"),
            ("print('x'*100000)", 5, 1024, "output_size_limit"),
        ):
            result = run_once([sys.executable, "-c", script], stdin=b"", env=sandbox_env(),
                              timeout=timeout, limit=limit)
            self.assertIn(reason, result.error)
            self.assertLessEqual(len(result.stdout), limit)
            self.assertTrue(result.killed or result.exit_status == 0)

    def test_known_encoded_credentials_are_withheld_not_published(self):
        key = "offline-dummy-credential-not-a-real-secret"
        for raw in (key.encode(), json_bytes({"key": key}), base64.b64encode(key.encode())):
            response = Response()
            _capture(response, RunResult(stdout=raw, started=True, exit_status=0), [key])
            self.assertEqual(response.error, "credential_evidence_withheld")
            self.assertEqual(response.stdout, b"")
            self.assertEqual(response.provenance["raw_capture"]["stdout"]["capture"], "withheld_known_credential")


if __name__ == "__main__":
    unittest.main()
