from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from phase2.core import ROOT, IntegrityError, challenge_request, corpus, digest, json_bytes, load
from phase2.path_b import build_request, invoke_offline


class PathBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load(ROOT / "execution_plan_v2.json")
        _, cls.sources = corpus()
        cls.manifest = (ROOT / "MMMTAP_Phase2/corpus_manifest.json").read_bytes()
        cls.checkpoints = ROOT / "execution_dry_run_v2"
        cls.jobs = {
            arm: next(j for j in cls.plan["jobs"] if j["mechanism"] == "carl_jev"
                      and j["arm"] == arm and j["generator"] == "haiku")
            for arm in ("E2", "E3_NC", "E3_CN")
        }

    def make(self, arm="E2"):
        return build_request(self.plan, self.jobs[arm], self.checkpoints,
                             self.sources, self.manifest, "offline-test")

    def test_questions_and_entire_native_payload_match(self):
        request = self.make()
        job = self.jobs["E2"]
        native_job = {**job, "mechanism": "native_jev"}
        expected = challenge_request(self.plan, native_job, self.sources[job["input_member"]],
                                     request["assessment"])
        self.assertEqual(base64.b64decode(request["native_request"]), json_bytes(expected))
        self.assertFalse(request["source"]["authenticated_git"])
        self.assertEqual(request["source"]["deployment_state"], "not_asserted")

    def test_both_orders_keep_their_own_parent(self):
        requests = {arm: self.make(arm) for arm in self.jobs}
        self.assertEqual(requests["E2"]["attempt"]["parent_job_id"],
                         requests["E3_CN"]["attempt"]["parent_job_id"])
        self.assertNotEqual(requests["E2"]["attempt"]["parent_job_id"],
                            requests["E3_NC"]["attempt"]["parent_job_id"])
        for arm, request in requests.items():
            parent = base64.b64decode(request["parent_checkpoint"])
            self.assertEqual(hashlib.sha256(parent).hexdigest(), request["parent_checkpoint_sha256"])
            self.assertEqual(request["attempt"]["branch_id"], arm)

    def test_reference_plan_tampering_rejected(self):
        plan = {**self.plan, "partition": "forged"}
        with self.assertRaisesRegex(IntegrityError, "hash mismatch"):
            build_request(plan, self.jobs["E2"], self.checkpoints, self.sources, self.manifest, "test")

    def test_source_modification_rejected(self):
        sources = {**self.sources, self.jobs["E2"]["input_member"]: b"replacement"}
        with self.assertRaises(IntegrityError):
            build_request(self.plan, self.jobs["E2"], self.checkpoints, sources, self.manifest, "test")

    def test_cross_branch_parent_rejected(self):
        plan = copy.deepcopy(self.plan)
        job = next(j for j in plan["jobs"] if j["job_id"] == self.jobs["E2"]["job_id"])
        job["assessment_parent"] = self.jobs["E3_NC"]["assessment_parent"]
        plan["manifest_sha256"] = digest({k: v for k, v in plan.items() if k != "manifest_sha256"})
        with self.assertRaisesRegex(IntegrityError, "Cross-branch"):
            build_request(plan, job, self.checkpoints, self.sources, self.manifest, "test")

    def test_adapter_environment_and_no_live_route(self):
        with patch("phase2.path_b.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, b"", b"fixture failure")
            result = invoke_offline(Path("/bin/true"), ["prepare"])
            self.assertEqual(result.returncode, 1)
            self.assertEqual(run.call_count, 1)
            self.assertNotIn("JEVKEY", run.call_args.kwargs["env"])
            self.assertNotIn("HOME", run.call_args.kwargs["env"])
        with self.assertRaises(IntegrityError):
            invoke_offline(Path("/bin/true"), ["live"])

    def test_timeout_does_not_retry(self):
        with patch("phase2.path_b.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture", 1)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                invoke_offline(Path("/bin/true"), ["evaluate-offline"], timeout=1)
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
