from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from .continuation import (
    ContinuationError,
    STOP_STATUSES,
    audit_completed_stage,
    plan_continuation,
)

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "operator_runs_v1" / "pilot"
PILOT_ID = "3062def66204e79ec8bcc3b7565f3de681b5dcb411bee06a6817fb04152ddfc1"


def inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class ContinuationReplayTests(unittest.TestCase):
    def test_completed_pilot_replays_read_only_with_exact_counts(self) -> None:
        before = inventory(PILOT)
        replay = audit_completed_stage(PILOT, PILOT_ID)
        self.assertEqual(replay["terminal_checkpoints"], 153)
        self.assertEqual(replay["status_counts"], {
            "ok": 114, "schema_invalid": 28, "blocked_parent": 11,
        })
        self.assertEqual(replay["schema_error_counts"], {
            "retained_claim_was_changed": 15,
            "incomplete_change_accounting": 12,
            "assessment_top_level_shape": 1,
        })
        self.assertEqual(replay["adapter_attempt_reservations"], 142)
        self.assertEqual(replay["provider_calls_during_replay"], 0)
        self.assertFalse(replay["frozen_evidence_modified"])
        self.assertEqual(before, inventory(PILOT))

    def test_manifest_tampering_stops_replay(self) -> None:
        with self.assertRaises(ContinuationError):
            audit_completed_stage(PILOT, "0" * 64)

    def test_schema_failure_requires_explicit_authorization_and_is_not_retried(self) -> None:
        jobs = [
            {"job_id": "failed", "dependencies": [], "adapter": "g"},
            {"job_id": "descendant", "dependencies": ["failed"], "adapter": "g"},
            {"job_id": "independent", "dependencies": [], "adapter": "g"},
        ]
        outcomes = {"failed": "schema_invalid"}
        stopped = plan_continuation(
            jobs, outcomes, explicitly_authorized=False, reserved_attempts=1,
            max_attempts=3, credentials_available={"g": True}, identity_verified=True,
            verified_outcome_job_ids=frozenset(outcomes),
        )
        self.assertEqual(stopped["decision"], "stop")
        self.assertEqual(stopped["reason"], "explicit_continuation_authorization_required")
        self.assertEqual(stopped["ready_job_ids"], [])

        continued = plan_continuation(
            jobs, outcomes, explicitly_authorized=True, reserved_attempts=1,
            max_attempts=3, credentials_available={"g": True}, identity_verified=True,
            verified_outcome_job_ids=frozenset(outcomes),
        )
        self.assertEqual(continued["decision"], "continue")
        self.assertEqual(continued["ready_job_ids"], ["independent"])
        self.assertEqual(continued["blocked_parent_job_ids"], ["descendant"])
        self.assertEqual(continued["preserved_schema_invalid_job_ids"], ["failed"])
        self.assertEqual(continued["reserved_attempts"], 2)
        self.assertEqual(continued["provider_calls"], 0)

    def test_identity_credentials_unknown_status_and_budget_fail_closed(self) -> None:
        job = [{"job_id": "next", "dependencies": [], "adapter": "g"}]
        base = {
            "jobs": job, "outcomes": {}, "explicitly_authorized": True,
            "reserved_attempts": 0, "max_attempts": 1,
            "credentials_available": {"g": True}, "identity_verified": True,
        }
        self.assertEqual(plan_continuation(**{**base, "identity_verified": False})["reason"],
                         "identity_unverified")
        self.assertEqual(plan_continuation(**{**base, "credentials_available": {"g": False}})["reason"],
                         "credential_unavailable")
        self.assertEqual(plan_continuation(**{**base, "reserved_attempts": 1})["reason"],
                         "attempt_budget_exhausted")
        self.assertEqual(plan_continuation(**{
            **base, "outcomes": {"next": "unknown"},
            "verified_outcome_job_ids": frozenset({"next"}),
        })["reason"],
                         "unknown_status")
        self.assertEqual(plan_continuation(**{
            **base, "outcomes": {"next": "execution_failed"},
            "verified_outcome_job_ids": frozenset({"next"}),
        })["reason"],
                         "credential_or_ambiguous_execution_failure")

    def test_pending_child_waits_for_parent_terminal_checkpoint(self) -> None:
        jobs = [
            {"job_id": "parent", "dependencies": [], "adapter": "g"},
            {"job_id": "child", "dependencies": ["parent"], "adapter": "g"},
        ]
        first = plan_continuation(
            jobs, {}, explicitly_authorized=True, reserved_attempts=0, max_attempts=2,
            credentials_available={"g": True}, identity_verified=True,
        )
        self.assertEqual(first["ready_job_ids"], ["parent"])
        self.assertEqual(first["deferred_job_ids"], ["child"])
        self.assertEqual(first["blocked_parent_job_ids"], [])
        self.assertEqual(first["reserved_attempts"], 1)

        second = plan_continuation(
            jobs, {"parent": "ok"}, explicitly_authorized=True, reserved_attempts=1, max_attempts=2,
            credentials_available={"g": True}, identity_verified=True,
            verified_outcome_job_ids=frozenset({"parent"}),
        )
        self.assertEqual(second["ready_job_ids"], ["child"])
        self.assertEqual(second["deferred_job_ids"], [])
        self.assertEqual(second["provider_calls"], 0)

    def test_child_requires_every_parent_verified_and_ok(self) -> None:
        jobs = [
            {"job_id": "root", "dependencies": [], "adapter": "g"},
            {"job_id": "left", "dependencies": ["root"], "adapter": "g"},
            {"job_id": "right", "dependencies": [], "adapter": "g"},
            {"job_id": "child", "dependencies": ["left", "right"], "adapter": "g"},
        ]
        cases = [
            ("missing", {"root": "ok", "left": "ok"}, {"root", "left"}, "deferred"),
            ("missing_left", {"root": "ok", "right": "ok"}, {"root", "right"}, "deferred"),
            ("unverified", {"root": "ok", "left": "ok", "right": "ok"},
             {"root", "left"}, "stop"),
            ("unverified_left", {"root": "ok", "left": "ok", "right": "ok"},
             {"root", "right"}, "stop"),
            ("schema_invalid", {"root": "ok", "left": "schema_invalid", "right": "ok"},
             {"root", "left", "right"}, "blocked"),
            ("schema_invalid_right", {"root": "ok", "left": "ok", "right": "schema_invalid"},
             {"root", "left", "right"}, "blocked"),
            ("blocked_parent", {"root": "schema_invalid", "left": "blocked_parent", "right": "ok"},
             {"root", "left", "right"}, "blocked"),
            ("execution_failed", {"root": "ok", "left": "execution_failed", "right": "ok"},
             {"root", "left", "right"}, "stop"),
            ("unknown", {"root": "ok", "left": "unknown", "right": "ok"},
             {"root", "left", "right"}, "stop"),
            ("all_ok", {"root": "ok", "left": "ok", "right": "ok"},
             {"root", "left", "right"}, "ready"),
        ]
        for parent in ("left", "right"):
            for status in sorted(STOP_STATUSES):
                outcomes = {"root": "ok", "left": "ok", "right": "ok", parent: status}
                cases.append((parent + "_" + status, outcomes, set(outcomes), "stop"))
        for name, outcomes, verified, expected in cases:
            with self.subTest(name=name):
                result = plan_continuation(
                    jobs, outcomes, explicitly_authorized=True,
                    reserved_attempts=len(outcomes), max_attempts=4,
                    credentials_available={"g": True}, identity_verified=True,
                    verified_outcome_job_ids=frozenset(verified),
                )
                self.assertEqual("child" in result["ready_job_ids"], expected == "ready")
                if expected == "deferred":
                    self.assertIn("child", result["deferred_job_ids"])
                elif expected == "blocked":
                    self.assertIn("child", result["blocked_parent_job_ids"])
                    self.assertEqual(result["reserved_attempts"], len(outcomes))
                elif expected == "stop":
                    self.assertEqual(result["decision"], "stop")
                    self.assertEqual(result["ready_job_ids"], [])
                self.assertEqual(result["provider_calls"], 0)

    def test_complete_replay_never_requests_authorization_or_new_calls(self) -> None:
        jobs = [
            {"job_id": "one", "dependencies": [], "adapter": "g"},
            {"job_id": "two", "dependencies": ["one"], "adapter": "g"},
        ]
        replay = plan_continuation(
            jobs, {"one": "schema_invalid", "two": "blocked_parent"},
            explicitly_authorized=False, reserved_attempts=1, max_attempts=2,
            credentials_available={}, identity_verified=False,
            verified_outcome_job_ids=frozenset({"one", "two"}),
        )
        self.assertEqual(replay["decision"], "complete")
        self.assertEqual(replay["ready_job_ids"], [])
        self.assertEqual(replay["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
