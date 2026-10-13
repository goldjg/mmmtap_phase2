"""Source-aware, read-only extraction; no model, Git, network, or code execution."""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import json
import os
import re
import stat
import sys
from pathlib import Path

from .archive import IntegrityError, file_hash, read_verified_zip, sha256


# JSON evidence has heterogeneous, historical schemas; it stays data throughout.
Record = dict
HASH = re.compile(r"^[0-9a-f]{64}$")
SOURCE_KEYS = ("input_sha256", "source_input_sha256", "source_diff_sha256", "diff_sha256")
OUTPUT_KEYS = {"response", "native_response", "parsed_response", "raw_parsed_response",
               "answers", "raw", "stdout", "stderr", "original_own_review",
               "peer_review_untrusted", "assessment_context", "specialist_context"}
INPUT_KINDS = {"original_input", "source_file", "fixture_definition", "synthetic_control"}
SOURCE_SUFFIXES = {".tf", ".bicep", ".js", ".ts", ".go", ".py", ".sh", ".ps1",
                   ".diff", ".patch", ".yaml", ".yml"}
RUNNER_NAMES = {"phase0.py", "jev_bridge.py", "carl_existing.py", "a2_codex.py",
                "inventory.py", "verify_packets.py"}
STATUSES = ("eligible", "duplicate", "reference_only", "pending", "excluded")


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def strict_json(raw: bytes) -> object:
    def pairs(items: list) -> dict:
        result: dict = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError("nonfinite_json_number")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def read_csv(path: Path) -> list[Record]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def pointer(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def family(name: str) -> str:
    match = re.search(r"p1[-_](\d{3}[a-z]?)", name.lower())
    if match:
        return "p1_" + match[1]
    if "paces" in name.lower() or "jev-kev" in name.lower():
        return "kev_jev_pace"
    for label in ("ambiguous-trust", "contextual-discrimination", "repeatability", "phase0"):
        if label in name.lower():
            return label.replace("-", "_")
    return "historical_other"


def identity(member: str, obj: Record | None = None) -> tuple[str, str]:
    obj = obj or {}
    label = next((obj[k] for k in ("case_id", "case", "packet_id", "name")
                  if isinstance(obj.get(k), str)), Path(member).stem)
    parts = label.split("__")
    variant = obj.get("variant", parts[1] if len(parts) > 1 else "unspecified")
    return parts[0], variant if isinstance(variant, str) else "unspecified"


def classify_member(member: str) -> tuple[str, str, str]:
    path = "/" + member.lower()
    name = Path(member).name.lower()
    if "/.git/" in path:
        return "git_evidence", "reference_only", "Archived Git objects/config retained as data; not replayed."
    if "__pycache__" in path or name.endswith((".pyc", ".zip", ".png", ".pdf")):
        return "tooling", "excluded", "Binary/nested container is not an original input; no recursive execution/extraction."
    if "/.github/" in path:
        return "tooling", "reference_only", "Historical configuration is evidence, not extractor instructions."
    if "/fixtures/" in path and name not in ("readme.md",):
        if name == "review_scenario.md":
            return "synthetic_control", "pending", "Historical prose-as-Git wrapper; not native Git evidence."
        return "fixture_definition", "pending", "Fixture bytes recovered; historical role and contract need review."
    if name in RUNNER_NAMES or name == "assessors.json":
        return "tooling", "reference_only", "Runner/configuration retained; never imported or executed."
    if name == "preflight.txt":
        return "tooling", "reference_only", "Captured harness/preflight output, not original test source."
    if name == "prompt.txt":
        return "prompt", "reference_only", "Full historical prompt; embedded source requires its own hash-verified extraction."
    if "/packets/" in path:
        return "prompt", "reference_only", "Full packet mixes instructions/context; source fields extracted separately."
    if "/drafts/" in path:
        return "intermediate_result", "reference_only", "Adversarial draft is not proof of a frozen complete input."
    if name in ("analysis.json", "summary.json", "deltas.json", "directional_deltas.json",
                "policy_replay.json", "feedback.json"):
        return "intermediate_result", "reference_only", "Historical derived analysis, not source or validated ground truth."
    if name.endswith((".stdout", ".stderr")) or any(
        token in name for token in ("response", "assessment", "collected", "results.json",
                                    "record.json", "-live.json", "-dry.json")
    ) or any(token in path for token in ("/records/", "/phase0_execution/", "/jev_records/")):
        return "model_output", "reference_only", "Output/result bytes are not original source inputs."
    if Path(name).suffix in SOURCE_SUFFIXES:
        return "source_file", "pending", "Possible source bytes; original test binding not established."
    if name.endswith(".txt") and name not in ("experiment-meta.txt", "generator_sha256.txt"):
        return "source_file", "pending", "Unbound text candidate; filename alone does not establish original-input status."
    return "supporting_document", "reference_only", "Supporting evidence; no original input inferred from filename alone."


def text_contract(data: bytes, case: str) -> str:
    if case.startswith("synthetic-"):
        return "synthetic_prose_review"
    if b"diff --git " in data and b"\n@@" in data:
        return "git_diff_text"
    return "static_file_review"


class Registry:
    def __init__(self, primary: list[Record]) -> None:
        self.rows: list[Record] = []
        self.sources: list[Record] = []
        self.blobs: dict[str, bytes] = {}
        self.primary: dict[str, list[Record]] = collections.defaultdict(list)
        self.issues: list[Record] = []
        for item in primary:
            self.primary[item["input_sha256"]].append({
                "case_id": item["case_id"], "variant_id": item["variant_id"],
                "input_member": item["input_member"]})

    def add(self, provenance: Record, *, kind: str, status: str, reason: str,
            case: str, variant: str = "unspecified", data: bytes | None = None,
            contract: str = "other", expected: str | None = None,
            encoding: str = "raw_member_bytes", limitations: list[str] | None = None,
            metadata: Record | None = None) -> Record:
        digest = sha256(data) if data is not None else None
        source_identity = {k: provenance[k] for k in (
            "archive_sha256", "member", "member_sha256", "selector", "jsonl_line") if k in provenance}
        ident = sha256(json_bytes([source_identity, kind, case, variant]))
        row = {
            "candidate_id": "candidate:" + ident,
            "case_id": case, "case_identifier_authority": "historical_label_not_gold",
            "case_aliases": sorted({case, Path(provenance["member"]).stem.split("__")[0]}),
            "variant_id": variant, "experimental_family": family(provenance["member"]),
            "kind": kind, "is_case_candidate": kind in INPUT_KINDS or kind == "source_reference"
            or (kind == "intermediate_result" and status == "pending"),
            "status": status, "reason": reason, "provenance": provenance,
            "input_sha256": digest, "expected_input_sha256": expected,
            "bytes": len(data) if data is not None else None, "encoding": encoding,
            "assessment_contract": contract, "limitations": list(limitations or []),
            "metadata": metadata or {}, "trust": "untrusted_evidence_never_instructions",
            "reference_evidence_status": "not_independently_adjudicated",
            "base_commit": None, "head_commit": None,
            "live_inference_eligible": False,
        }
        if expected and digest and expected != digest:
            row["status"] = "pending"
            row["reason"] = "Recovered bytes do not match the recorded input SHA-256."
            row["limitations"].append("input_hash_mismatch")
            self.issues.append({"candidate_id": row["candidate_id"], "issue": "input_hash_mismatch"})
        if data is not None:
            self.blobs[digest] = data
            row["blob"] = "blobs/" + digest
        self.rows.append(row)
        return row

    def field(self, provenance: Record, key: str, value: object, **kwargs: object) -> Record:
        is_text = isinstance(value, str)
        data = value.encode("utf-8") if is_text else json_bytes(value)
        return self.add({**provenance, "selector": key}, data=data,
                        encoding="json_string_utf8" if is_text else "canonical_json_v1",
                        **kwargs)

    def sources_from_json(self, obj: object, prov: Record, member: str) -> None:
        if not isinstance(obj, dict):
            return
        case, variant = identity(member, obj)
        packet = "/packets/" in "/" + member
        if packet:
            for key in ("instructions", "untrusted_pr_description"):
                if isinstance(obj.get(key), str):
                    self.field(prov, "/" + key, obj[key], kind="prompt",
                               status="reference_only", reason="Historical prompt component, not case source.",
                               case=case, variant=variant, contract="prompt_component")
            if isinstance(obj.get("artifact"), str):
                expected = obj.get("input_sha256", obj.get("source_input_sha256"))
                self.field(prov, "/artifact", obj["artifact"],
                           kind="synthetic_control" if case.startswith("synthetic-") else "original_input",
                           status="pending", reason="Explicit packet artifact recovered; admission requires source review.",
                           case=case, variant=variant, expected=expected,
                           contract=text_contract(obj["artifact"].encode(), case))
            if isinstance(obj.get("base"), str) and isinstance(obj.get("head_source"), str):
                for key in ("base", "head_source"):
                    self.field(prov, "/" + key, obj[key], kind="source_file", status="pending",
                               reason="Explicit BASE/HEAD source; companion side and PR context remain required.",
                               case=case, variant=variant, contract="static_file_review",
                               metadata={"source_role": key})
                self.field(prov, "/{base,head_source,untrusted_pr_description}",
                           {k: obj[k] for k in ("base", "head_source", "untrusted_pr_description") if k in obj},
                           kind="fixture_definition", status="pending",
                           reason="Paired source snapshot recovered; not an authenticated Git diff.",
                           case=case, variant=variant, contract="source_pair_review",
                           limitations=["git_base_head_not_authenticated", "case_reference_review_required"])
            if isinstance(obj.get("incident"), dict):
                self.field(prov, "/incident", obj["incident"], kind="synthetic_control", status="pending",
                           reason="Incident component recovered; evidence envelopes are separate required context.",
                           case=case, variant=variant, contract="structured_incident_review",
                           limitations=["incident_component_not_complete_experiment"])
                keys = ("incident", "untrusted_envelope", "evidence_envelopes", "signed_evidence")
                self.field(prov, "/{incident,evidence}", {k: obj[k] for k in keys if k in obj},
                           kind="fixture_definition", status="pending",
                           reason="Incident and supplied evidence recovered; claimed verifier/model outputs excluded.",
                           case=case, variant=variant, contract="structured_incident_review",
                           limitations=["attestations_not_reverified", "case_reference_review_required"])
        if Path(member).name == "source_bindings.json":
            for label, binding in obj.items():
                if isinstance(binding, dict) and isinstance(binding.get("text"), str):
                    parts = label.rsplit("/", 1)
                    self.field(prov, "/" + pointer(label) + "/text", binding["text"],
                               kind="synthetic_control" if parts[0].startswith("synthetic-") else "original_input",
                               status="pending",
                               reason="Explicit historical source binding recovered.",
                               case=parts[0], variant=parts[1] if len(parts) == 2 else "unspecified",
                               expected=binding.get("input_sha256"),
                               contract=text_contract(binding["text"].encode(), parts[0]))
        if "/fixtures/" in "/" + member and isinstance(obj.get("fixture"), dict):
            self.field(prov, "/fixture", obj["fixture"], kind="fixture_definition", status="pending",
                       reason="Fixture definition isolated from historical verification/gate results.",
                       case=identity(member, obj["fixture"])[0], contract="structured_incident_review",
                       limitations=["attestations_not_reverified", "case_reference_review_required"])
        if Path(member).name == "frozen_inputs.json":
            for label, binding in obj.items():
                if isinstance(binding, dict) and isinstance(binding.get("draft"), dict):
                    self.field(prov, "/" + pointer(label) + "/draft", binding["draft"],
                               kind="intermediate_result", status="pending",
                               reason="Frozen adversarial draft recovered; complete policy input is not embedded.",
                               case=label, variant=Path(member).parent.name, contract="prompt_component",
                               limitations=["missing_policy_source", "historical_hash_serialization_unspecified"],
                               metadata={"recorded_draft_sha256": binding.get("sha256"),
                                         "recorded_policy_sha256": binding.get("policy_sha256")})
                    digest = binding.get("policy_sha256")
                    if isinstance(digest, str) and HASH.fullmatch(digest):
                        self.add({**prov, "selector": "/" + pointer(label) + "/policy_sha256"},
                                 kind="source_reference", status="pending",
                                 reason="Frozen draft depends on policy source identified only by hash.",
                                 case=label, variant=Path(member).parent.name, expected=digest,
                                 contract="source_pair_review",
                                 limitations=["missing_policy_source"])
        if Path(member).name in ("soc_questions.json", "questions.json"):
            self.field(prov, "", obj, kind="prompt", status="reference_only",
                       reason="Question-set definition; no inference or adapter validation performed.",
                       case=case, contract="systemone_question_set")
        self.references(obj, prov, member)

    def references(self, obj: object, prov: Record, member: str, path: str = "",
                   inherited: Record | None = None, depth: int = 0) -> None:
        if depth > 40:
            self.issues.append({"provenance": prov, "issue": "json_reference_depth_limit"})
            return
        if isinstance(obj, list):
            for i, child in enumerate(obj):
                self.references(child, prov, member, f"{path}/{i}", inherited, depth + 1)
            return
        if not isinstance(obj, dict):
            return
        context = dict(inherited or {})
        for key in ("case_id", "case", "packet_id", "name", "variant"):
            if isinstance(obj.get(key), str):
                context[key] = obj[key]
        if not context and isinstance(obj.get("source_path"), str):
            context["case"] = obj["source_path"]
        case, variant = identity(member, context)
        keys = list(SOURCE_KEYS)
        if context:
            keys.append("source_sha256")
        if "case_id" in obj and "source" in obj:
            keys.append("sha256")
        for key in keys:
            digest = obj.get(key)
            if digest is None:
                continue
            if not isinstance(digest, str) or not HASH.fullmatch(digest):
                self.issues.append({"provenance": prov, "selector": path + "/" + key,
                                    "issue": "invalid_recorded_source_hash"})
                continue
            row = self.add({**prov, "selector": path + "/" + key}, kind="source_reference",
                           status="pending", reason="Original input hash recorded; source bytes not yet resolved.",
                           case=case, variant=variant, expected=digest,
                           contract="git_diff_text" if "diff" in key else "other",
                           limitations=["source_reference_is_not_source_bytes"],
                           metadata={k: obj[k] for k in ("repo", "source", "paths") if k in obj})
            for side in ("base", "head"):
                commit = obj.get(side)
                if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40,64}", commit):
                    row[side + "_commit"] = commit
            if "014_stage2b" in member:
                row["limitations"].append("historical_git_diff_prose_adapter_not_native_git")
        for key, child in obj.items():
            if key not in OUTPUT_KEYS and isinstance(child, (dict, list)):
                self.references(child, prov, member, path + "/" + pointer(key), context, depth + 1)

    def literal_evidence(self, raw: bytes, prov: Record, member: str) -> None:
        """Recover literal prompt/fixture declarations, not computed values or imports."""
        if len(raw) > 1024 * 1024:
            self.issues.append({"provenance": prov, "issue": "python_static_parse_size_limit"})
            return
        try:
            tree = ast.parse(raw)
        except (SyntaxError, ValueError, UnicodeError, RecursionError):
            self.issues.append({"provenance": prov, "issue": "python_static_parse_failed"})
            return
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name) or not re.search(
                    r"(^Q$|CASE|FIXTURE|PROMPT|QUESTION|INSTRUCTION|SCHEMA)", target.id, re.I
                ):
                    continue
                try:
                    value = ast.literal_eval(node.value)
                    data = value.encode("utf-8") if isinstance(value, str) else json_bytes(value)
                except (ValueError, TypeError, SyntaxError, RecursionError):
                    self.issues.append({"provenance": prov, "line": node.lineno,
                                        "issue": "computed_declaration_not_executed"})
                    continue
                self.add({**prov, "selector": f"ast:{target.id}:{node.lineno}-{node.end_lineno}"},
                         kind="tooling", status="reference_only",
                         reason="Literal declaration recovered statically; not assumed to be an executed test input.",
                         case=Path(member).stem + ":" + target.id, data=data,
                         encoding="python_literal_utf8_or_canonical_json",
                         contract="fixture_or_prompt_definition")

    def bounded_prompt(self, prov: Record, raw: bytes, binding_member: str,
                       binding_raw: bytes) -> None:
        """Recover the Phase-0 source span only under both archived hash bindings."""
        try:
            binding = strict_json(binding_raw)
        except (ValueError, UnicodeError, RecursionError):
            self.issues.append({"provenance": prov, "issue": "prompt_binding_malformed"})
            return
        if not isinstance(binding, dict) or not isinstance(binding.get("source_sha256"), str):
            self.issues.append({"provenance": prov, "issue": "prompt_binding_incomplete"})
            return
        marker = b"--- BEGIN UNTRUSTED TERRAFORM SOURCE ---\n"
        end_marker = b"\n--- END UNTRUSTED TERRAFORM SOURCE ---\n"
        size = binding.get("source_bytes")
        if (binding.get("prompt_sha256") != sha256(raw) or raw.count(marker) != 1
                or not raw.endswith(end_marker) or type(size) is not int or size < 0):
            self.issues.append({"provenance": prov, "issue": "prompt_hash_or_delimiter_mismatch"})
            return
        start = raw.index(marker) + len(marker)
        end = start + size
        if raw[end:] != end_marker or sha256(raw[start:end]) != binding["source_sha256"]:
            self.issues.append({"provenance": prov, "issue": "embedded_source_hash_or_size_mismatch"})
            return
        row = self.add({**prov, "selector": f"bytes:{start}:{end}"},
                       data=raw[start:end], expected=binding["source_sha256"],
                       kind="original_input", status="pending",
                       reason="Original source span recovered from archived prompt; prompt and source hash/size verified.",
                       case=binding.get("source_path", "main.tf"), contract="static_file_review",
                       encoding="raw_byte_span",
                       metadata={"binding_member": binding_member, "binding_sha256": sha256(binding_raw),
                                 "historical_git_commit": binding.get("git_commit")},
                       limitations=["case_reference_review_required", "historical_git_commit_not_authenticated"])
        row["case_identifier_authority"] = "archived_experiment_source_path"

    def member(self, archive: Record, member: str, raw: bytes,
               primary_item: Record | None = None) -> None:
        prov = {"archive_sha256": archive["expected_sha256"],
                "archive_inventory_name": archive["inventory_name"],
                "archive_inventory_aliases": archive.get("inventory_aliases", [archive["inventory_name"]]),
                "archive_paths": archive["matched_paths"], "member": member,
                "member_sha256": sha256(raw), "selector": ""}
        kind, status, reason = classify_member(member)
        if member.endswith(".json"):
            try:
                obj = strict_json(raw)
            except (ValueError, UnicodeError, RecursionError):
                obj = None  # The parsing pass below records the failure with provenance.
            if isinstance(obj, dict) and kind == "supporting_document":
                if any(key in obj for key in ("raw", "parsed", "native_response", "answers")) or (
                    isinstance(obj.get("result"), dict) and
                    any(key in obj["result"] for key in ("signals", "findings", "decision"))
                ):
                    kind, status, reason = "model_output", "reference_only", "Result schema contains historical model/tool output, not source."
        case, variant = identity(member)
        contract = "other"
        if primary_item:
            kind, status, reason = "original_input", "eligible", "Previously admitted frozen P1-014 input, reverified unchanged."
            case, variant = primary_item["case_id"], primary_item["variant_id"]
            if case.startswith("synthetic-"):
                kind = "synthetic_control"
            contract = text_contract(raw, case)
        elif kind in INPUT_KINDS:
            contract = text_contract(raw, case)
            if "review_scenario.md" in member:
                contract = "historical_git_diff_prose_wrapper"
            elif "/fixtures/" in "/" + member and member.endswith(".json"):
                kind, status, reason = "supporting_document", "reference_only", "Fixture envelope; original definition isolated below."
                contract = "structured_incident_review"
        row = self.add(prov, kind=kind, status=status, reason=reason, case=case,
                       variant=variant, data=raw, contract=contract,
                       limitations=[] if primary_item else ["historical_role_requires_source_review"] if kind in INPUT_KINDS else [])
        if primary_item:
            row["experimental_family"] = "p1_014_frozen"
            row["case_identifier_authority"] = "frozen_primary_manifest"
            row["reference_evidence_status"] = "existing_primary_admission_preserved"
        self.sources.append({"source_id": row["candidate_id"], **prov, "bytes": len(raw),
                             "kind": kind, "blob": row["blob"]})
        if member.endswith((".json", ".jsonl", ".stdout")):
            lines = raw.splitlines() if member.endswith(".jsonl") else [raw]
            for number, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                line_prov = {**prov, "jsonl_line": number} if member.endswith(".jsonl") else prov
                try:
                    obj = strict_json(line)
                except (ValueError, UnicodeError, RecursionError):
                    self.issues.append({"provenance": line_prov, "issue": "malformed_json_evidence"})
                    row["limitations"].append("malformed_json_evidence")
                    row["status"] = "pending"
                    row["reason"] = "Malformed structured evidence; cannot safely determine source fields or role."
                    continue
                self.sources_from_json(obj, line_prov, member)
        elif member.endswith(".py"):
            self.literal_evidence(raw, prov, member)

    def reconcile(self) -> None:
        originals: dict[str, list[Record]] = collections.defaultdict(list)
        for row in self.rows:
            if row["kind"] in INPUT_KINDS and row["input_sha256"] and "input_hash_mismatch" not in row["limitations"]:
                if "malformed_json_evidence" in row["limitations"]:
                    continue
                originals[row["input_sha256"]].append(row)
        for digest, rows in originals.items():
            rows.sort(key=lambda r: (r["status"] != "eligible", r["candidate_id"]))
            canonical = rows[0]
            for row in rows:
                row["exact_content_group"] = "sha256:" + digest
                row["canonical_candidate_id"] = canonical["candidate_id"]
                if row["status"] == "eligible":
                    continue
                if digest in self.primary:
                    row["status"] = "duplicate"
                    row["reason"] = "Exact source bytes already in frozen P1-014 corpus; no new admission."
                    row["primary_matches"] = self.primary[digest]
                elif row is not canonical:
                    row["status"] = "duplicate"
                    row["reason"] = "Exact recovered content duplicate; canonical candidate remains separately classified."
                else:
                    row["status"] = "pending"
                    row["reason"] += " Case-specific reference/contract review required before admission."
        for row in self.rows:
            if row["kind"] != "source_reference":
                continue
            digest = row["expected_input_sha256"]
            matches = originals.get(digest, [])
            if matches:
                row["status"] = "reference_only"
                row["reason"] = "Recorded source SHA-256 resolves to recovered input bytes; reference is not a new case."
                row["resolved_candidate_ids"] = [r["candidate_id"] for r in matches]
                row["limitations"] = ["hash_match_does_not_prove_identical_experiment"]
                if digest in self.primary:
                    row["primary_matches"] = self.primary[digest]
            else:
                row["reason"] = "Original source bytes missing for recorded SHA-256; outputs cannot reconstruct them."
                row["limitations"].append("missing_source")


def verify_document_manifests(root: Path) -> list[Record]:
    evidence = []
    for folder, filename in (("MMMTAP_Phase2", "MANIFEST_SHA256SUMS.txt"),
                             ("reconciliation_v1", "SHA256SUMS.txt"),
                             ("MMMTAP_Phase2_Eligibility", "SHA256SUMS.txt")):
        base = root / folder
        manifest = base / filename
        evidence.append({"path": str(manifest), "sha256": file_hash(manifest)})
        for line in manifest.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            if not HASH.fullmatch(digest) or Path(name).name != name:
                raise IntegrityError("unsafe_document_manifest")
            path = base / name
            actual = file_hash(path)
            if actual != digest:
                raise IntegrityError("document_hash_mismatch:" + str(path))
            evidence.append({"path": str(path), "sha256": actual})
    return evidence


def discover(root: Path, search_roots: list[Path]) -> tuple[list[Record], list[Record]]:
    known = read_csv(root / "reconciliation_v1/discovered_zips.csv")
    paths = {Path(r["path"]) for r in known}
    issues = []
    for directory in search_roots:
        if not directory.is_dir():
            issues.append({"path": str(directory), "issue": "search_root_missing"})
            continue
        def walk_error(error: OSError) -> None:
            issues.append({"path": str(error.filename), "issue": type(error).__name__})
        for current, dirs, files in os.walk(directory, followlinks=False, onerror=walk_error):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and
                             d not in {"node_modules", "__pycache__", "venv"})
            paths.update(Path(current) / name for name in files if name.lower().endswith(".zip"))
    found = []
    for path in sorted(paths):
        try:
            if path.is_symlink():
                raise IntegrityError("archive_symlink_not_followed")
            if not stat.S_ISREG(path.stat().st_mode):
                raise IntegrityError("archive_not_regular_file")
            digest = file_hash(path)
            found.append({"path": str(path), "filename": path.name, "sha256": digest})
        except (OSError, IntegrityError) as exc:
            issues.append({"path": str(path), "issue": type(exc).__name__})
    return found, issues


def verify_primary(manifest: Record, members: dict[str, bytes]) -> None:
    items = manifest["items"]
    if (manifest["n_inputs"], manifest["n_cases"], manifest["n_variants"]) != (135, 15, 9):
        raise IntegrityError("primary_dimensions_not_135_15_9")
    pairs = {(i["case_id"], i["variant_id"]) for i in items}
    cases = {i["case_id"] for i in items}
    variants = {i["variant_id"] for i in items}
    if (len(items), len(pairs), len(cases), len(variants),
        len({i["input_member"] for i in items})) != (135, 135, 15, 9, 135):
        raise IntegrityError("primary_manifest_dimension_or_identity_mismatch")
    if pairs != {(case, variant) for case in cases for variant in variants}:
        raise IntegrityError("primary_missing_case_variant")
    for item in items:
        data = members.get(item["input_member"])
        if data is None or sha256(data) != item["input_sha256"] or len(data) != item["bytes"]:
            raise IntegrityError("primary_member_missing_or_mismatched:" + item["input_member"])
        if item["source_archive_sha256"] != manifest["archive_sha256"]:
            raise IntegrityError("primary_source_archive_binding_mismatch")


def compatibility(row: Record) -> Record:
    contract = row["assessment_contract"]
    if row["kind"] not in INPUT_KINDS:
        native = carl = "not_applicable_contract"
    else:
        native = "adapter_unvalidated"
        carl = "adapter_unvalidated" if contract in ("git_diff_text", "source_pair_review") else "not_applicable_contract"
    return {
        "candidate_id": row["candidate_id"], "case_id": row["case_id"],
        "assessment_contract": contract, "eligibility": row["status"],
        "native_jev": native, "carl_jev": carl,
        "native_jev_requirements": [
            "Pin endpoint/model/version and explicit case-specific SystemOne question set.",
            "Validate state serialization, token capacity, numerical answer schema, and missing/invalid responses.",
            "Historical KEV baselines and JEV contracts are not interchangeable."],
        "carl_jev_requirements": [
            "Authenticate repository base/head, exact diff, bounded paths and cARL policy/question-set versions.",
            "Non-Git input needs an experimentally validated explicit adapter; never fabricate a prose Git diff.",
            "Validate boolean/noul threshold mapping and structured signal IDs; deterministic policy is not a second model."],
        "structured_security_signals": (
            "historical_output_only_not_source" if row["kind"] == "model_output" else
            "requires_explicit_schema_and_provenance_adapter"),
        "validated": False,
    }


def relationships(registry: Registry) -> Record:
    groups: dict[str, set[str]] = collections.defaultdict(set)
    labels: dict[str, list[str]] = collections.defaultdict(list)
    for row in registry.rows:
        if row["kind"] not in INPUT_KINDS or not row["input_sha256"]:
            continue
        digest = row["input_sha256"]
        labels[row["experimental_family"] + ":" + row["case_id"]].append(row["candidate_id"])
        try:
            text = registry.blobs[digest].decode("utf-8")
        except UnicodeError:
            continue
        normalized = " ".join(text.split())
        groups[sha256(normalized.encode())].add(digest)
    return {
        "method": "whitespace_normalized_utf8_sha256_and_historical_case_labels_v1",
        "limitations": ["Lexical similarity leads only, not semantic equivalence or a comprehensive similarity search.",
                        "No embeddings or model calls. Byte-distinct inputs are never discarded."],
        "similarity_groups": [{"normalized_sha256": digest, "input_sha256s": sorted(values)}
                              for digest, values in sorted(groups.items()) if len(values) > 1],
        "variant_relationships": [{"historical_case_label": label, "candidate_ids": sorted(set(ids)),
                                   "authority": "label_inferred_requires_review"}
                                  for label, ids in sorted(labels.items()) if len(set(ids)) > 1],
    }


def build(root: Path, search_roots: list[Path] | None = None) -> tuple[Record, dict[str, bytes]]:
    documents = verify_document_manifests(root)
    manifest = strict_json((root / "MMMTAP_Phase2/corpus_manifest.json").read_bytes())
    inventory = strict_json((root / "MMMTAP_Phase2/legacy_inventory.json").read_bytes())
    prior = read_csv(root / "MMMTAP_Phase2_Eligibility/historical_archive_eligibility.csv")
    prior_by_hash = {r["expected_sha256"]: r for r in prior}
    found, scan_issues = discover(root, search_roots or [])
    by_hash: dict[str, list[str]] = collections.defaultdict(list)
    by_name: dict[str, list[Record]] = collections.defaultdict(list)
    for item in found:
        by_hash[item["sha256"]].append(item["path"])
        by_name[item["filename"]].append(item)
    archives = []
    verified: dict[str, dict[str, bytes]] = {}
    for entry in inventory["archives"]:
        digest = entry["sha256"]
        matches = by_hash.get(digest, [])
        same_name = [r for r in by_name.get(entry["archive"], []) if r["sha256"] != digest]
        status = "exact_sha_match" if matches else "same_name_different_sha" if same_name else "not_located"
        record = {"inventory_name": entry["archive"], "expected_sha256": digest,
                  "matched_paths": matches, "same_name_different_hash_files": same_name,
                  "status": status, "prior_eligibility": prior_by_hash.get(digest),
                  "limitations": []}
        if matches:
            try:
                verified[digest] = read_verified_zip(Path(matches[0]), digest)
            except (OSError, IntegrityError) as exc:
                record["status"] = "invalid_archive"
                record["limitations"].append(str(exc) if isinstance(exc, IntegrityError) else type(exc).__name__)
        else:
            record["limitations"].append("Original inventory hash unresolved; same-name files are never substituted.")
        archives.append(record)
    primary_members = verified.get(manifest["archive_sha256"])
    if primary_members is None:
        raise IntegrityError("frozen_primary_archive_unavailable_or_invalid")
    verify_primary(manifest, primary_members)
    registry = Registry(manifest["items"])
    primary_by_member = {i["input_member"]: i for i in manifest["items"]}
    processed: set[str] = set()
    for archive in archives:
        if archive["status"] != "exact_sha_match":
            continue
        if archive["expected_sha256"] in processed:
            continue
        processed.add(archive["expected_sha256"])
        archive["inventory_aliases"] = sorted(r["inventory_name"] for r in archives
                                             if r["expected_sha256"] == archive["expected_sha256"])
        for member, raw in sorted(verified[archive["expected_sha256"]].items()):
            primary = primary_by_member.get(member) if archive["expected_sha256"] == manifest["archive_sha256"] else None
            registry.member(archive, member, raw, primary)
            if member.endswith("/phase0-results/prompt.txt"):
                binding_member = str(Path(member).with_name("experiment.json"))
                binding_raw = verified[archive["expected_sha256"]].get(binding_member)
                prov = registry.sources[-1]
                if binding_raw is None:
                    registry.issues.append({"provenance": prov, "issue": "prompt_binding_missing"})
                else:
                    registry.bounded_prompt(
                        {k: prov[k] for k in ("archive_sha256", "archive_inventory_name", "archive_paths",
                                             "archive_inventory_aliases", "member", "member_sha256", "selector")},
                        raw, binding_member, binding_raw)
    registry.reconcile()
    registry.rows.sort(key=lambda r: r["candidate_id"])
    ids = [r["candidate_id"] for r in registry.rows]
    if len(ids) != len(set(ids)):
        raise IntegrityError("candidate_identity_collision")
    leads = []
    for lead in read_csv(root / "MMMTAP_Phase2_Eligibility/historical_case_name_leads.csv"):
        matches = [r["candidate_id"] for r in registry.rows
                   if r["kind"] in INPUT_KINDS and lead["candidate_case_label"] in r["case_aliases"]
                   and r["provenance"]["archive_sha256"] == lead["archive_sha256"]]
        leads.append({**lead, "matched_candidate_ids": matches,
                      "resolution": "candidate_links_not_admission" if matches else "pending_unresolved_name_lead"})
    overlaps = []
    for row in registry.rows:
        if row["experimental_family"] == "p1_014_frozen":
            continue
        digest = row["input_sha256"] if row["kind"] in INPUT_KINDS else row["expected_input_sha256"]
        if digest in registry.primary:
            overlaps.append({"candidate_id": row["candidate_id"], "sha256": digest,
                             "evidence": "recovered_source_bytes" if row["kind"] in INPUT_KINDS else "hash_reference_only",
                             "primary_matches": registry.primary[digest]})
    unresolved = [r for r in registry.rows if r["status"] == "pending"]
    decisions = [{k: r[k] for k in ("candidate_id", "case_id", "variant_id", "kind", "is_case_candidate",
                                    "status", "reason", "limitations")} for r in registry.rows]
    source_cases = [r for r in registry.rows if r["kind"] in INPUT_KINDS]
    historical = [r for r in source_cases if r["experimental_family"] != "p1_014_frozen"]
    content_index: dict[str, list[str]] = collections.defaultdict(list)
    for row in registry.rows:
        if row["input_sha256"]:
            content_index[row["input_sha256"]].append(row["candidate_id"])
    by_case: dict[tuple[str, str], list[Record]] = collections.defaultdict(list)
    for row in registry.rows:
        if row["is_case_candidate"]:
            by_case[(row["experimental_family"], row["case_id"])].append(row)
    case_groups = []
    for (experiment, case), rows in sorted(by_case.items()):
        recovered = [r for r in rows if r["kind"] in INPUT_KINDS]
        admitted = experiment == "p1_014_frozen"
        case_groups.append({
            "case_group_id": sha256(json_bytes([experiment, case])),
            "experimental_family": experiment, "historical_case_label": case,
            "grouping_authority": "historical_label_not_semantic_equivalence",
            "admitted": admitted, "status": "eligible" if admitted else "pending",
            "reason": "Frozen primary admission preserved." if admitted else
                      "Historical label group only; source/variant completeness and reference evidence require review.",
            "candidate_ids": [r["candidate_id"] for r in rows],
            "recovered_input_sha256s": sorted({r["input_sha256"] for r in recovered}),
            "variants": sorted({r["variant_id"] for r in rows}),
            "assessment_contracts": sorted({r["assessment_contract"] for r in rows}),
            "missing_source_hashes": sorted({r["expected_input_sha256"] for r in rows
                                             if r["kind"] == "source_reference" and r["status"] == "pending"}),
        })
    summary = {
        "protocol": "MMMTAP-P2-historical-extraction-v1",
        "execution": "offline_no_inference_no_untrusted_code_execution",
        "primary_inputs_verified": 135, "primary_cases_preserved": 15,
        "primary_archive_sha256": manifest["archive_sha256"],
        "archive_inventory_records": len(archives),
        "archive_status_counts": dict(collections.Counter(r["status"] for r in archives)),
        "archive_member_count": len(registry.sources),
        "candidate_registry_rows": len(registry.rows),
        "all_evidence_status_counts": {s: sum(r["status"] == s for r in registry.rows) for s in STATUSES},
        "historical_recovered_source_occurrences": len(historical),
        "historical_recovered_unique_hashes": len({r["input_sha256"] for r in historical}),
        "historical_source_status_counts": {s: sum(r["status"] == s for r in historical) for s in STATUSES},
        "additional_historical_cases_admitted": 0,
        "historical_label_groups_not_admitted_cases": sum(not c["admitted"] for c in case_groups),
        "unresolved_source_hashes": len({r["expected_input_sha256"] for r in unresolved if r["kind"] == "source_reference"}),
        "pending_registry_rows": len(unresolved),
        "unresolved_name_leads": sum(not r["matched_candidate_ids"] for r in leads),
        "primary_overlap_recovered_unique_hashes": len({r["sha256"] for r in overlaps if r["evidence"] == "recovered_source_bytes"}),
        "extraction_issue_count": len(registry.issues),
        "discovery_issue_count": len(scan_issues),
        "limitations": [
            "Source occurrences, variants, labels and content hashes are not counts of independently admitted cases.",
            "No new historical admission without case-specific reference and assessment-contract review.",
            "JSON subobjects use declared canonical serialization; raw parent member bytes are preserved.",
            "Git objects retained without checkout, hooks, diff generation or commit authentication.",
            "Computed fixture generators and missing mutable repository sources are not executed or substituted.",
            "Signatures, ground truth, historical model claims and adapter compatibility are not independently validated.",
            "Only inventory SHA-matched ZIPs are examined; nested containers are indexed, not recursively expanded.",
            "Default discovery rechecks reconciliation paths, not the whole host; use --search-root for additional local archives.",
        ],
    }
    report = {
        "SUMMARY.json": summary, "candidate_cases.json": registry.rows,
        "case_level_eligibility.json": case_groups,
        "source_provenance_index.json": {"documents": documents, "archives": archives,
                                       "sources": registry.sources, "discovery": found,
                                       "discovery_issues": scan_issues,
                                       "content_sha256_index": dict(sorted(content_index.items())),
                                       "extractor_sources": [{"path": str(p), "sha256": file_hash(p)}
                                                             for p in sorted(Path(__file__).parent.glob("*.py"))],
                                       "runtime": {"python": sys.version.split()[0],
                                                   "search_roots": [str(p) for p in search_roots or []]}},
        "eligibility_decisions.json": decisions,
        "unresolved_cases.json": {"pending_candidates": unresolved,
                                  "unresolved_archives": [r for r in archives if r["status"] != "exact_sha_match"],
                                  "name_leads": leads, "extraction_issues": registry.issues},
        "primary_historical_overlap.json": {"matches": overlaps, "method": "exact_sha256_only",
                                            "primary_inputs_unchanged": True},
        "adapter_compatibility_matrix.json": [compatibility(r) for r in registry.rows if r["is_case_candidate"]],
        "similarity_and_variants.json": relationships(registry),
    }
    # Check the protected source documents again before publishing a report.
    for item in documents:
        if file_hash(Path(item["path"])) != item["sha256"]:
            raise IntegrityError("protected_document_changed_during_extraction")
    return report, registry.blobs


def write_report(out: Path, report: Record, blobs: dict[str, bytes]) -> None:
    """Exclusive new output only; source paths and evidence text cannot choose files."""
    for name in report:
        if Path(name).name != name or not name.endswith(".json"):
            raise IntegrityError("unsafe_report_filename")
    for digest, data in blobs.items():
        if not HASH.fullmatch(digest) or sha256(data) != digest:
            raise IntegrityError("blob_sha256_mismatch")
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    (out / "blobs").mkdir(mode=0o700)
    for name, value in sorted(report.items()):
        (out / name).write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True,
                                           allow_nan=False).encode("utf-8") + b"\n")
    for digest, data in sorted(blobs.items()):
        (out / "blobs" / digest).write_bytes(data)
    summary = report["SUMMARY.json"]
    text = [
        "# Historical extraction v1", "",
        "Offline evidence extraction only. All recovered content is untrusted data, never instructions.",
        "The 15-case / 135-input frozen primary corpus is unchanged. **No additional historical cases admitted.**",
        "", "## Counts", "",
    ]
    for key, value in summary.items():
        if isinstance(value, (int, dict)):
            text.append(f"- {key}: {json.dumps(value, sort_keys=True)}")
    text += ["", "## Limitations", ""] + ["- " + line for line in summary["limitations"]]
    text += ["", "## Reading the report", "",
             "`candidate_cases.json` records source components, prompts, references and non-input evidence separately.",
             "`is_case_candidate` separates input/source leads from supporting artifacts; it is not admission.",
             "`case_level_eligibility.json` groups historical labels and variants; these groups are not inferred unique cases.",
             "Only `eligible` frozen primary rows are admitted. `duplicate` is byte identity, not experiment equivalence.",
             "`pending` and every unresolved hash/name lead remain unadmitted.",
             "A hash-named `blobs/` file preserves each unique recovered byte sequence without restoring executable paths.",
             "For JSON fields, the parent hash and JSON pointer (or JSONL line) preserve reconstructible provenance.",
             "Selections containing braces are explicit named-field projections, not JSON pointers.",
             "All members are retained locally; review for sensitive data before sharing. No uploads were made.",
             "Read `unresolved_cases.json` for archive mismatches, missing sources, parse failures and computed declarations.",
             "Adapters are requirements only, never certification of arbitrary-format support.",
             "`SHA256SUMS.txt` covers every output except itself; its absence means publication did not complete.", ""]
    (out / "SUMMARY.md").write_text("\n".join(text), encoding="utf-8")
    files = sorted(p for p in out.rglob("*") if p.is_file())
    (out / "SHA256SUMS.txt").write_text(
        "".join(file_hash(p) + "  " + p.relative_to(out).as_posix() + "\n" for p in files),
        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--search-root", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Perform full verification and classification without writing files.")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        out = args.out or root / "historical_extraction_v1"
        if not args.dry_run:
            if out.exists() or out.is_symlink():
                raise IntegrityError("output_exists_refusing_overwrite")
            if out.parent.resolve(strict=True) != root:
                raise IntegrityError("output_must_be_new_direct_child_of_phase2_root")
        report, blobs = build(root, args.search_root)
        if not args.dry_run:
            write_report(out, report, blobs)
        print(json.dumps({"dry_run": args.dry_run, **report["SUMMARY.json"]}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Extraction failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
