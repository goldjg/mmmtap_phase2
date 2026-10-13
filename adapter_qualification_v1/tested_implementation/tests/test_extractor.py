from __future__ import annotations

import contextlib
import csv
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from historical_extractor.archive import IntegrityError, Limits, file_hash, read_verified_zip, sha256
from historical_extractor.extract import (
    Registry, build, compatibility, json_bytes, main, relationships, strict_json,
    verify_primary, write_report,
)


def make_zip(path: Path, members: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return file_hash(path)


def csv_file(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def frozen_primary() -> tuple[dict, dict[str, bytes]]:
    items = []
    members = {}
    for case in range(15):
        for variant in range(9):
            name = f"inputs/case-{case}/variant-{variant}.txt"
            raw = f"Original source {case} variant {variant}\r\n".encode()
            members[name] = raw
            items.append({"case_id": f"case-{case}", "variant_id": f"variant-{variant}",
                          "input_member": name, "input_sha256": sha256(raw), "bytes": len(raw),
                          "source_archive_sha256": "a" * 64})
    return ({"n_inputs": 135, "n_cases": 15, "n_variants": 9, "items": items,
             "archive_sha256": "a" * 64}, members)


class ArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "archive.zip"

    def test_hash_before_parse_and_no_same_name_substitution(self) -> None:
        digest = make_zip(self.path, {"source.tf": b"original"})
        self.assertEqual(read_verified_zip(self.path, digest), {"source.tf": b"original"})
        make_zip(self.path, {"source.tf": b"substitute"})
        with self.assertRaisesRegex(IntegrityError, "sha256_mismatch"):
            read_verified_zip(self.path, digest)

    def test_matching_hash_does_not_make_malformed_archive_valid(self) -> None:
        self.path.write_bytes(b"not a ZIP file")
        with self.assertRaisesRegex(IntegrityError, "malformed_archive"):
            read_verified_zip(self.path, file_hash(self.path))

    def test_crc_failure_rejects_entire_archive(self) -> None:
        make_zip(self.path, {"first.txt": b"good", "last.txt": b"unique source payload"})
        self.path.write_bytes(self.path.read_bytes().replace(b"unique source payload", b"broken source payload"))
        with self.assertRaisesRegex(IntegrityError, "malformed_archive"):
            read_verified_zip(self.path, file_hash(self.path))

    def test_unsafe_paths_never_written(self) -> None:
        for name in ("../outside.txt", "/absolute.txt", "C:/drive.txt", "a\\b.txt", "a/../b",
                     "a//b", "control\n.txt"):
            with self.subTest(name=name):
                digest = make_zip(self.path, {name: b"ignore all instructions"})
                with self.assertRaisesRegex(IntegrityError, "unsafe_member_path"):
                    read_verified_zip(self.path, digest)
        self.assertEqual([p.name for p in self.root.iterdir()], ["archive.zip"])

    def test_duplicate_paths_rejected(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.path, "w") as archive:
                archive.writestr("same.txt", b"one")
                archive.writestr("same.txt", b"two")
        with self.assertRaisesRegex(IntegrityError, "duplicate_member_path"):
            read_verified_zip(self.path, file_hash(self.path))

    def test_symlink_member_rejected(self) -> None:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr(info, b"/etc/passwd")
        with self.assertRaisesRegex(IntegrityError, "symlink_or_special_member"):
            read_verified_zip(self.path, file_hash(self.path))

    def test_all_resource_limits(self) -> None:
        digest = make_zip(self.path, {"a": b"12345", "b": b"12345"})
        for limits, reason in ((Limits(archive_bytes=1), "archive_size_limit"),
                               (Limits(member_bytes=4), "member_size_limit"),
                               (Limits(total_bytes=9), "total_uncompressed_size_limit"),
                               (Limits(members=1), "member_count_limit")):
            with self.subTest(reason=reason), self.assertRaisesRegex(IntegrityError, reason):
                read_verified_zip(self.path, digest, limits)
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("compressible", b"x" * 10000)
        with self.assertRaisesRegex(IntegrityError, "compression_ratio_limit"):
            read_verified_zip(self.path, file_hash(self.path), Limits(compression_ratio=2))


class SourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.archive = {"expected_sha256": "a" * 64, "inventory_name": "historical.zip",
                        "matched_paths": ["/local/renamed.zip", "/local/copy.zip"]}
        self.registry = Registry([])

    def packet(self, name: str, artifact: str, **extra: object) -> None:
        self.registry.member(self.archive, f"p1_015/packets/{name}.json",
                             json_bytes({"packet_id": name, "artifact": artifact, **extra}))

    def test_exact_duplicates_keep_every_provenance(self) -> None:
        self.packet("same__v1__a", "same source\r\n")
        self.packet("same__v1__b", "same source\r\n")
        self.registry.reconcile()
        rows = [r for r in self.registry.rows if r["kind"] == "original_input"]
        self.assertEqual(sorted(r["status"] for r in rows), ["duplicate", "pending"])
        self.assertEqual(len({r["input_sha256"] for r in rows}), 1)
        self.assertEqual(len({r["provenance"]["member"] for r in rows}), 2)
        self.assertEqual(rows[0]["canonical_candidate_id"], rows[1]["canonical_candidate_id"])

    def test_candidate_identity_does_not_depend_on_local_archive_name(self) -> None:
        other = Registry([])
        self.registry.member(self.archive, "source.tf", b"source")
        other.member({**self.archive, "matched_paths": ["/new/location.zip"],
                      "inventory_name": "renamed.zip"}, "source.tf", b"source")
        self.assertEqual(self.registry.rows[0]["candidate_id"], other.rows[0]["candidate_id"])
        self.assertNotEqual(self.registry.rows[0]["provenance"], other.rows[0]["provenance"])

    def test_byte_distinct_similar_inputs_stay_pending(self) -> None:
        self.packet("same__v1", "a  b\n")
        self.packet("same__v2", "a b\r\n")
        self.registry.reconcile()
        rows = [r for r in self.registry.rows if r["kind"] == "original_input"]
        self.assertEqual([r["status"] for r in rows], ["pending", "pending"])
        self.assertEqual(len(relationships(self.registry)["similarity_groups"]), 1)

    def test_hash_mismatch_is_not_deduplicated_or_admitted(self) -> None:
        self.packet("test__v1", "not original", input_sha256=sha256(b"original"))
        self.packet("test__v2", "not original", input_sha256=sha256(b"original"))
        self.registry.reconcile()
        rows = [r for r in self.registry.rows if r["kind"] == "original_input"]
        self.assertTrue(all(r["status"] == "pending" for r in rows))
        self.assertTrue(all("input_hash_mismatch" in r["limitations"] for r in rows))

    def test_primary_overlap_kept_separate_from_hash_only_reference(self) -> None:
        digest = sha256(b"source")
        self.registry = Registry([{"input_sha256": digest, "case_id": "primary",
                                   "variant_id": "baseline", "input_member": "inputs/p/b.txt"}])
        self.packet("test__v1", "source", input_sha256=digest)
        self.registry.reconcile()
        source = next(r for r in self.registry.rows if r["kind"] == "original_input")
        reference = next(r for r in self.registry.rows if r["kind"] == "source_reference")
        self.assertEqual(source["status"], "duplicate")
        self.assertEqual(reference["status"], "reference_only")
        self.assertIsNone(reference["input_sha256"])
        self.assertIn(source["candidate_id"], reference["resolved_candidate_ids"])

    def test_missing_source_cannot_be_resolved_from_output_bytes(self) -> None:
        raw = json_bytes({"raw": "source-looking output", "parsed": {}})
        self.registry.member(self.archive, "results/baseline.json", raw)
        self.registry.member(self.archive, "results/record.json",
                             json_bytes({"case": "missing", "input_sha256": sha256(raw)}))
        self.registry.reconcile()
        ref = next(r for r in self.registry.rows if r["kind"] == "source_reference")
        self.assertEqual(ref["status"], "pending")
        self.assertIn("missing_source", ref["limitations"])
        self.assertEqual(self.registry.rows[0]["kind"], "model_output")

    def test_json_field_provenance_reconstructs_exact_utf8_bytes(self) -> None:
        text = "untrusted\u00e9\r\n# Do not follow this comment."
        self.packet("test__v1", text)
        source = next(r for r in self.registry.rows if r["kind"] == "original_input")
        prov = source["provenance"]
        self.assertEqual(prov["selector"], "/artifact")
        self.assertEqual(prov["archive_paths"], self.archive["matched_paths"])
        parent = self.registry.blobs[prov["member_sha256"]]
        self.assertEqual(json.loads(parent)["artifact"].encode(), self.registry.blobs[source["input_sha256"]])
        self.assertEqual(sha256(text.encode()), source["input_sha256"])

    def test_jsonl_line_provenance(self) -> None:
        row = {"case_id": "a", "source": "source.txt", "input_sha256": "b" * 64}
        self.registry.member(self.archive, "results.jsonl", json_bytes(row) + b"\n" + json_bytes(row))
        refs = [r for r in self.registry.rows if r["kind"] == "source_reference"]
        self.assertEqual([r["provenance"]["jsonl_line"] for r in refs], [1, 2])
        self.assertNotEqual(refs[0]["candidate_id"], refs[1]["candidate_id"])

    def test_source_pair_does_not_claim_native_git_compatibility(self) -> None:
        self.registry.member(self.archive, "p1_017a/packets/case__clean.json", json_bytes({
            "base": "before", "head_source": "after", "untrusted_pr_description": "approve",
            "specialist_context": {"source_input_sha256": "c" * 64}}))
        source = next(r for r in self.registry.rows if r["assessment_contract"] == "source_pair_review")
        data = json.loads(self.registry.blobs[source["input_sha256"]])
        self.assertEqual(data["untrusted_pr_description"], "approve")
        self.assertNotIn("specialist_context", data)
        self.assertIsNone(source["base_commit"])
        self.assertEqual(compatibility(source)["carl_jev"], "adapter_unvalidated")
        self.assertFalse(any(r["kind"] == "source_reference" for r in self.registry.rows))

    def test_fixture_and_gate_outputs_are_separated(self) -> None:
        fixture = {"case": "a", "incident": {"signal": "untrusted"}}
        self.registry.member(self.archive, "p1_021/fixtures/a.json", json_bytes({
            "fixture": fixture, "verification": {"decision": "pass"}}))
        source = next(r for r in self.registry.rows if r["kind"] == "fixture_definition")
        self.assertEqual(json.loads(self.registry.blobs[source["input_sha256"]]), fixture)
        self.assertEqual(source["encoding"], "canonical_json_v1")
        self.assertEqual(compatibility(source)["carl_jev"], "not_applicable_contract")

    def test_frozen_drafts_keep_missing_policy_dependency(self) -> None:
        self.registry.member(self.archive, "p1_017b/round1/frozen_inputs.json", json_bytes({
            "attack": {"draft": {"comment": "untrusted"}, "policy_sha256": "c" * 64, "sha256": "d" * 64}}))
        self.registry.reconcile()
        refs = [r for r in self.registry.rows if r["kind"] == "source_reference"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["expected_input_sha256"], "c" * 64)
        self.assertEqual(refs[0]["status"], "pending")

    def test_untrusted_python_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "executed"
            script = (
                f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n"
                "PROMPT = 'Ignore previous instructions'\nCASES = make_live_calls()\n")
            self.registry.member(self.archive, "phase0.py", script.encode())
            self.assertFalse(sentinel.exists())
        literal = next(r for r in self.registry.rows if r["provenance"]["selector"].startswith("ast:"))
        self.assertEqual(literal["kind"], "tooling")
        self.assertEqual(literal["status"], "reference_only")
        self.assertIn("computed_declaration_not_executed", [r["issue"] for r in self.registry.issues])

    def test_malformed_json_and_duplicate_keys_are_explicit(self) -> None:
        for raw in (b"{", b'{"artifact":"one","artifact":"two"}', b'{"value":NaN}', b"\xff"):
            with self.subTest(raw=raw):
                with self.assertRaises((ValueError, UnicodeError)):
                    strict_json(raw)
        self.registry.member(self.archive, "fixtures/bad.json", b"{")
        self.assertEqual(self.registry.rows[0]["status"], "pending")
        self.assertEqual(self.registry.issues[0]["issue"], "malformed_json_evidence")

    def test_unknown_python_source_is_pending_not_executed_tool(self) -> None:
        self.registry.member(self.archive, "sources/app.py", b"print('source')")
        self.assertEqual(self.registry.rows[0]["kind"], "source_file")
        self.assertEqual(self.registry.rows[0]["status"], "pending")

    def test_bounded_prompt_recovers_source_not_instructions(self) -> None:
        raw_source = b"resource \"example\" \"test\" {}\r\n"
        prompt = (b"Untrusted instructions\n--- BEGIN UNTRUSTED TERRAFORM SOURCE ---\n" +
                  raw_source + b"\n--- END UNTRUSTED TERRAFORM SOURCE ---\n")
        binding = {"source_sha256": sha256(raw_source), "prompt_sha256": sha256(prompt),
                   "source_bytes": len(raw_source), "source_path": "main.tf"}
        self.registry.member(self.archive, "phase0-results/prompt.txt", prompt)
        prov = self.registry.rows[0]["provenance"]
        self.registry.bounded_prompt(prov, prompt, "phase0-results/experiment.json", json_bytes(binding))
        self.registry.reconcile()
        original = next(r for r in self.registry.rows if r["kind"] == "original_input")
        self.assertEqual(self.registry.blobs[original["input_sha256"]], raw_source)
        self.assertEqual(self.registry.rows[0]["kind"], "prompt")
        self.assertEqual(original["status"], "pending")
        _, start, end = original["provenance"]["selector"].split(":")
        self.assertEqual(prompt[int(start):int(end)], raw_source)
        binding["source_bytes"] += 1
        self.registry.bounded_prompt(prov, prompt, "phase0-results/experiment.json", json_bytes(binding))
        self.assertEqual(self.registry.issues[-1]["issue"], "embedded_source_hash_or_size_mismatch")

    def test_prompt_binding_mismatch_is_reported(self) -> None:
        self.registry.bounded_prompt({"member": "prompt.txt"}, b"prompt", "experiment.json",
                                     json_bytes({"source_sha256": "a" * 64, "prompt_sha256": "b" * 64}))
        self.assertEqual(self.registry.issues[-1]["issue"], "prompt_hash_or_delimiter_mismatch")


class PrimaryTests(unittest.TestCase):
    def test_exact_dimensions_hashes_and_crlf_bytes(self) -> None:
        manifest, members = frozen_primary()
        verify_primary(manifest, members)
        key = manifest["items"][0]["input_member"]
        members[key] = members[key].replace(b"\r\n", b"\n")
        with self.assertRaisesRegex(IntegrityError, "primary_member"):
            verify_primary(manifest, members)

    def test_missing_member(self) -> None:
        manifest, members = frozen_primary()
        del members[manifest["items"][0]["input_member"]]
        with self.assertRaisesRegex(IntegrityError, "primary_member"):
            verify_primary(manifest, members)

    def test_duplicate_identity_rejected_even_with_135_items(self) -> None:
        manifest, members = frozen_primary()
        manifest["items"][-1] = dict(manifest["items"][0])
        with self.assertRaisesRegex(IntegrityError, "identity_mismatch"):
            verify_primary(manifest, members)

    def test_changed_archive_binding(self) -> None:
        manifest, members = frozen_primary()
        manifest["items"][0]["source_archive_sha256"] = "b" * 64
        with self.assertRaisesRegex(IntegrityError, "archive_binding"):
            verify_primary(manifest, members)


class IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("MMMTAP_Phase2", "reconciliation_v1", "MMMTAP_Phase2_Eligibility"):
            (self.root / name).mkdir()
        manifest, members = frozen_primary()
        primary = self.root / "primary.zip"
        digest = make_zip(primary, members)
        manifest["archive_sha256"] = digest
        for item in manifest["items"]:
            item["source_archive_sha256"] = digest
        history = self.root / "renamed.zip"
        history_hash = make_zip(history, {
            "p1_015/packets/new__v1.json": json_bytes({"artifact": "new source", "packet_id": "new__v1"}),
            "p1_015/packets/old__v1.json": json_bytes({"artifact": next(iter(members.values())).decode()}),
            "p1_015/record.json": json_bytes({"case": "lost", "input_sha256": "d" * 64}),
        })
        mismatch = self.root / "mismatch.zip"
        make_zip(mismatch, {"source.txt": b"not the inventory archive"})
        malformed = self.root / "malformed.zip"
        malformed.write_bytes(b"broken ZIP")
        entries = [
            {"archive": "primary.zip", "sha256": digest},
            {"archive": "historical.zip", "sha256": history_hash},
            {"archive": "mismatch.zip", "sha256": "b" * 64},
            {"archive": "missing.zip", "sha256": "c" * 64},
            {"archive": "malformed.zip", "sha256": file_hash(malformed)},
        ]
        (self.root / "MMMTAP_Phase2/corpus_manifest.json").write_bytes(json_bytes(manifest))
        (self.root / "MMMTAP_Phase2/legacy_inventory.json").write_bytes(json_bytes({"archives": entries}))
        csv_file(self.root / "reconciliation_v1/discovered_zips.csv",
                 [{"path": str(p)} for p in (primary, history, mismatch, malformed)], ["path"])
        csv_file(self.root / "MMMTAP_Phase2_Eligibility/historical_archive_eligibility.csv",
                 [{"expected_sha256": r["sha256"], "classification": "pending_case_extraction"} for r in entries],
                 ["expected_sha256", "classification"])
        csv_file(self.root / "MMMTAP_Phase2_Eligibility/historical_case_name_leads.csv",
                 [{"archive_sha256": history_hash, "candidate_case_label": "lost"}],
                 ["archive_sha256", "candidate_case_label"])
        for name, checksum in (("MMMTAP_Phase2", "MANIFEST_SHA256SUMS.txt"),
                               ("reconciliation_v1", "SHA256SUMS.txt"),
                               ("MMMTAP_Phase2_Eligibility", "SHA256SUMS.txt")):
            directory = self.root / name
            (directory / checksum).write_text(
                "".join(file_hash(p) + "  " + p.name + "\n" for p in sorted(directory.iterdir())),
                encoding="utf-8")

    def test_end_to_end_counts_and_all_output_hashes(self) -> None:
        before = {p: file_hash(p) for p in self.root.rglob("*") if p.is_file()}
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.run", side_effect=AssertionError("subprocess forbidden")):
            report, blobs = build(self.root)
        summary = report["SUMMARY.json"]
        self.assertEqual(summary["archive_status_counts"], {
            "exact_sha_match": 2, "same_name_different_sha": 1, "not_located": 1, "invalid_archive": 1})
        self.assertEqual(summary["primary_inputs_verified"], 135)
        self.assertEqual(summary["all_evidence_status_counts"]["eligible"], 135)
        self.assertEqual(summary["historical_source_status_counts"]["pending"], 1)
        self.assertEqual(summary["historical_source_status_counts"]["duplicate"], 1)
        self.assertEqual(summary["additional_historical_cases_admitted"], 0)
        self.assertEqual(summary["unresolved_source_hashes"], 1)
        self.assertEqual(summary["unresolved_name_leads"], 1)
        out = self.root / "output"
        write_report(out, report, blobs)
        for line in (out / "SHA256SUMS.txt").read_text().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(file_hash(out / name), digest)
        self.assertEqual(len((out / "SHA256SUMS.txt").read_text().splitlines()),
                         len([p for p in out.rglob("*") if p.is_file()]) - 1)
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        self.assertEqual(before, {p: file_hash(p) for p in before})
        index = report["source_provenance_index.json"]
        self.assertTrue(all(r["input_sha256"] in index["content_sha256_index"]
                            for r in report["candidate_cases.json"] if r["input_sha256"]))
        self.assertTrue(all(not r["live_inference_eligible"] for r in report["candidate_cases.json"]))

    def test_dry_run_writes_nothing(self) -> None:
        before = set(self.root.rglob("*"))
        with patch("sys.argv", ["extract", "--root", str(self.root), "--dry-run"]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
        self.assertEqual(before, set(self.root.rglob("*")))

    def test_deterministic_and_no_overwrite(self) -> None:
        report, blobs = build(self.root)
        second, second_blobs = build(self.root)
        self.assertEqual(report, second)
        self.assertEqual(blobs, second_blobs)
        for name in ("one", "two"):
            write_report(self.root / name, report, blobs)
        self.assertEqual((self.root / "one/SHA256SUMS.txt").read_bytes(),
                         (self.root / "two/SHA256SUMS.txt").read_bytes())
        with self.assertRaises(FileExistsError):
            write_report(self.root / "one", report, blobs)

    def test_existing_or_escaped_output_refused(self) -> None:
        for out in (self.root / "MMMTAP_Phase2", self.root.parent / "outside"):
            with self.subTest(out=out), patch("sys.argv", ["extract", "--root", str(self.root), "--out", str(out)]), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)

    def test_report_cannot_inject_write_paths(self) -> None:
        with self.assertRaisesRegex(IntegrityError, "unsafe_report_filename"):
            write_report(self.root / "out", {"../escape.json": {}}, {})
        self.assertFalse((self.root / "out").exists())

    def test_changed_documents_fail_closed(self) -> None:
        path = self.root / "MMMTAP_Phase2/corpus_manifest.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(IntegrityError, "document_hash_mismatch"):
            build(self.root)

    def test_missing_primary_is_fatal(self) -> None:
        (self.root / "primary.zip").unlink()
        with self.assertRaisesRegex(IntegrityError, "frozen_primary_archive"):
            build(self.root)

    def test_additional_search_root_resolves_renamed_archive(self) -> None:
        new = self.root / "new-location"
        new.mkdir()
        (self.root / "renamed.zip").rename(new / "different-name.zip")
        report, _ = build(self.root, [new])
        self.assertEqual(report["SUMMARY.json"]["archive_status_counts"]["exact_sha_match"], 2)
        self.assertEqual(report["SUMMARY.json"]["discovery_issue_count"], 1)


if __name__ == "__main__":
    unittest.main()
