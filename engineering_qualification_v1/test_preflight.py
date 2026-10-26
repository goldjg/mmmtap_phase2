from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

from . import preflight as p


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "source.txt").write_bytes(b"frozen\n")
        self.entries = [{"path": "source.txt", "bytes": 7,
                         "sha256": hashlib.sha256(b"frozen\n").hexdigest()}]

    def test_exact_bytes_and_missing_files(self):
        self.assertEqual(p.verify_files(self.root, self.entries)["verified_files"], 1)
        (self.root / "source.txt").write_bytes(b"FROZEN\n")
        self.assertEqual(p.verify_files(self.root, self.entries)["failures"][0]["reason"], "byte_binding_mismatch")
        (self.root / "source.txt").unlink()
        self.assertEqual(p.verify_files(self.root, self.entries)["verified_files"], 0)

    def test_unsafe_duplicate_or_malformed_bindings(self):
        for name in ("../source.txt", "/source.txt", "a/../source.txt", "./source.txt", ".", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                p.safe_path(self.root, name)
        with self.assertRaisesRegex(ValueError, "duplicate_inventory"):
            p.verify_files(self.root, self.entries * 2)
        for value in (True, -1, 1.5):
            entries = copy.deepcopy(self.entries)
            entries[0]["bytes"] = value
            with self.assertRaisesRegex(ValueError, "invalid_inventory"):
                p.verify_files(self.root, entries)

    def test_symlink_leaf_ancestor_and_root_rejected(self):
        (self.root / "leaf").symlink_to(self.root / "source.txt")
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        for root, name in ((self.root, "leaf"), (self.root, "alias/source.txt"),
                           (self.root / "alias", "source.txt")):
            with self.subTest(root=root, name=name), self.assertRaisesRegex(ValueError, "symlink"):
                p.safe_path(root, name)

    def test_strict_json_and_manifest_binding(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            (self.root / "bad.json").write_text(text)
            with self.assertRaises(ValueError):
                p.load(self.root / "bad.json")
        directory = self.root / "operator_execution_v1/evidence"
        directory.mkdir(parents=True)
        manifest = directory / "PRESERVATION_BASELINE.json"
        manifest.write_text("{}")
        with self.assertRaisesRegex(ValueError, "baseline_binding"):
            p.custody(self.root, "0" * 64)
        with self.assertRaisesRegex(ValueError, "40538"):
            p.custody(self.root, p.file_hash(manifest))

    def test_preflight_never_calls_network_process_or_writes(self):
        # An empty source root is a genuine negative preflight, not success.
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch.object(owner, name, side_effect=AssertionError("forbidden")))
                     for owner, name in ((socket, "socket"), (socket, "create_connection"),
                                         (subprocess, "Popen"), (urllib.request, "urlopen"),
                                         (Path, "write_text"), (Path, "write_bytes"), (Path, "mkdir"))]
            report = p.preflight(self.root)
            self.assertEqual(report["overall"], "FAIL")
            self.assertFalse(report["launch_authorized"])
            self.assertFalse(report["automatic_progression"])
            self.assertEqual(report["provider_calls"], 0)
            self.assertTrue(all(row["status"] in ("PASS", "FAIL", "BLOCKED/UNKNOWN") for row in report["checks"]))
            for mock in mocks:
                mock.assert_not_called()
        self.assertEqual(sorted(x.name for x in self.root.iterdir()), ["source.txt"])

    def test_matching_source_never_grants_launch_and_missing_custody_is_unknown(self):
        bindings = p.load(p.PACKAGE / "bindings.v1.json")
        complete = {"expected_files": 1, "verified_files": 1, "failures": []}
        with patch.object(p, "verify_files", return_value=complete):
            report = p.preflight(self.root)
        self.assertEqual(report["overall"], "BLOCKED/UNKNOWN")
        self.assertFalse(report["launch_authorized"])
        rows = {row["check"]: row for row in report["checks"]}
        self.assertEqual(rows["original_40538_entry_custody"]["status"], "BLOCKED/UNKNOWN")
        self.assertEqual(rows["proposed_campaign_size"]["evidence"]["scheduled_positions"], 153)
        for gap in bindings["launch_gaps"]:
            self.assertEqual(rows[gap]["status"], "BLOCKED/UNKNOWN")


if __name__ == "__main__":
    unittest.main()
