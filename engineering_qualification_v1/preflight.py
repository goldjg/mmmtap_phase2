"""Offline qualification preflight. Exit 1: integrity failure; 2: launch blocked.

Only reads local files and emits JSON on stdout. Never imports inspected code,
accesses credentials, reserves attempts, or invokes an adapter or subprocess.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

VERSION = "mmmtap-engineering-preflight-v1"
PACKAGE = Path(__file__).resolve().parent
HEX = re.compile(r"[0-9a-f]{64}")


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_json_key:" + key)
        result[key] = value
    return result


def load(path):
    def reject(value):
        raise ValueError("nonfinite_json:" + value)
    return json.loads(path.read_bytes(), object_pairs_hook=unique_object, parse_constant=reject)


def file_hash(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing_or_nonregular_hash_input:" + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root, name, *, leaf_symlink=False):
    if not isinstance(name, str):
        raise ValueError("invalid_evidence_path_type")
    relative = Path(name)
    if (not name or relative.is_absolute()
            or ".." in relative.parts or relative.as_posix() != name or name == "."):
        raise ValueError("unsafe_evidence_path:" + str(name))
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise ValueError("symlinked_evidence_root")
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        if current.is_symlink() and not (leaf_symlink and index == len(relative.parts) - 1):
            raise ValueError("symlinked_evidence_path:" + name)
    return current


def verify_files(root, entries):
    """Exact byte bindings, including ancestor symlink and duplicate rejection."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("empty_or_invalid_inventory")
    seen, failures = set(), []
    for entry in entries:
        name = entry["path"]
        if name in seen:
            raise ValueError("duplicate_inventory_path:" + name)
        seen.add(name)
        if (type(entry["bytes"]) is not int or entry["bytes"] < 0
                or not isinstance(entry["sha256"], str) or not HEX.fullmatch(entry["sha256"])):
            raise ValueError("invalid_inventory_binding:" + name)
        try:
            path = safe_path(root, name)
            if not path.is_file():
                failures.append({"path": name, "reason": "missing_or_nonregular"})
            elif path.stat().st_size != entry["bytes"] or file_hash(path) != entry["sha256"]:
                failures.append({"path": name, "reason": "byte_binding_mismatch"})
        except (OSError, ValueError) as exc:
            failures.append({"path": name, "reason": str(exc)})
    return {"expected_files": len(seen), "verified_files": len(seen) - len(failures),
            "failures": failures}


def custody(root, expected_manifest_hash):
    manifest = safe_path(root, "operator_execution_v1/evidence/PRESERVATION_BASELINE.json")
    if file_hash(manifest) != expected_manifest_hash:
        raise ValueError("preservation_baseline_binding_mismatch")
    baseline = load(manifest)
    if not isinstance(baseline, dict) or len(baseline) != 40538:
        raise ValueError("expected_40538_preserved_entries")
    failures = []
    for name, expected in baseline.items():
        try:
            path = safe_path(root, name, leaf_symlink=expected["kind"] == "symlink")
            if expected["kind"] == "symlink":
                same = path.is_symlink() and str(path.readlink()) == expected["target"]
            elif expected["kind"] == "file":
                same = path.is_file() and not path.is_symlink() and file_hash(path) == expected["sha256"]
            else:
                raise ValueError("unknown_preservation_entry_kind")
            if not same:
                failures.append(name)
        except (OSError, ValueError):
            failures.append(name)
    # Report counts only: original custody filenames may contain private context.
    return {"original_entries": len(baseline), "verified_entries": len(baseline) - len(failures),
            "changed_or_missing_count": len(failures), "baseline_sha256": file_hash(manifest)}


def result(name, status, evidence):
    return {"check": name, "status": status, "evidence": evidence}


def preflight(source_root, custody_root=None):
    bindings = load(PACKAGE / "bindings.v1.json")
    checks = []
    frozen = verify_files(source_root, bindings["files"])
    checks.append(result("inspected_source_and_configuration", "FAIL" if frozen["failures"] else "PASS", frozen))
    for name, prefix in (("rd05_original_package_integrity", "phase2_v2/rd05_offline/"),
                         ("comparison_package_integrity", "rd05_comparison/v1/"),
                         ("frozen_instrument_and_lifecycle_integrity", "phase2_v2/instrument.py")):
        group = verify_files(source_root, [entry for entry in bindings["files"] if entry["path"].startswith(prefix)])
        checks.append(result(name, "FAIL" if group["failures"] else "PASS", group))
    checks.append(result("proposed_campaign_size", "BLOCKED/UNKNOWN" if frozen["failures"] else "PASS", {
        "source": "phase2_v2/QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md",
        "inputs": 3, "generators": 3, "engineering_repetitions": 1,
        "matched_units": 9, "generator_positions": 99, "specialist_positions": 54,
        "native_positions": 27, "carl_jev_positions": 27, "scheduled_positions": 153,
        "basis": "unchanged proposal, not an executable or approved manifest",
        "plan_integrity": "FAIL" if frozen["failures"] else "PASS"}))
    for name, detail in bindings["launch_gaps"].items():
        checks.append(result(name, "BLOCKED/UNKNOWN", {
            **detail, "assessment_basis": "inspected baseline implementation" if not frozen["failures"]
            else "baseline bindings failed; current implementation cannot be certified"}))
    if custody_root is None:
        checks.append(result("original_40538_entry_custody", "BLOCKED/UNKNOWN",
                             "Original custody root not supplied; sanitized public copies cannot establish original custody."))
    else:
        try:
            audit = custody(custody_root, bindings["preservation_baseline_sha256"])
            checks.append(result("original_40538_entry_custody", "FAIL" if audit["changed_or_missing_count"] else "PASS", audit))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks.append(result("original_40538_entry_custody", "FAIL", str(exc)))
    return {
        "schema": VERSION, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable, "source_root": str(source_root.absolute()),
        "inspected_commit": bindings["inspected_commit"],
        "executable_and_configuration_sha256": {
            name: file_hash(PACKAGE / name)
            for name in ("__init__.py", "preflight.py", "bindings.v1.json")},
        "checks": checks, "provider_calls": 0, "launch_authorized": False,
        "automatic_progression": False, "release_execution_available": False,
        "overall": "FAIL" if any(check["status"] == "FAIL" for check in checks) else "BLOCKED/UNKNOWN",
        "meaning": "Offline evidence inspection only; never permission to launch or evidence of scientific validity.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=PACKAGE.parent)
    parser.add_argument("--custody-root", type=Path)
    args = parser.parse_args()
    try:
        report = preflight(args.source_root, args.custody_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"schema": VERSION, "overall": "FAIL", "error": str(exc),
                  "provider_calls": 0, "launch_authorized": False, "automatic_progression": False}
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 1 if report["overall"] == "FAIL" else 2


if __name__ == "__main__":
    sys.exit(main())
