from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from . import VERSION

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPLAY_STATUSES = {"ok", "schema_invalid", "blocked_parent"}
STOP_STATUSES = {
    "adapter_unavailable",
    "credential_error",
    "credential_failure",
    "credentials_unavailable",
    "execution_failed",
    "incomplete_attempt",
    "interrupted_attempt",
    "model_identity_mismatch",
    "unknown_execution",
    "provider_execution_unknown",
    "unsupported_contract",
}
SUCCESS = {"ok"}


class ContinuationError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ContinuationError("nonfinite_json_number")


def _unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ContinuationError("duplicate_json_key")
        result[key] = value
    return result


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ContinuationError("missing_or_symlinked_evidence:" + str(path))
    try:
        return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuationError("invalid_json_evidence:" + str(path)) from exc


def _tree_digest(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise ContinuationError("invalid_evidence_root")
    records = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ContinuationError("symlinked_evidence:" + str(path))
        if path.is_file():
            records[path.relative_to(root).as_posix()] = _file_digest(path)
        elif not path.is_dir():
            raise ContinuationError("special_evidence_file:" + str(path))
    return records


def audit_completed_stage(run_dir: Path, expected_manifest_sha256: str) -> dict[str, Any]:
    """Read-only audit/replay of a fully checkpointed live stage; never invokes a provider."""
    if not SHA256.fullmatch(expected_manifest_sha256):
        raise ContinuationError("invalid_expected_manifest_identity")
    before = _tree_digest(run_dir)
    manifest = _read_json(run_dir / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("manifest_sha256") != expected_manifest_sha256:
        raise ContinuationError("manifest_identity_mismatch")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if _digest(unsigned) != expected_manifest_sha256:
        raise ContinuationError("manifest_digest_mismatch")

    run = _read_json(run_dir / "run.json")
    completion = _read_json(run_dir / "completion.json")
    authorisation = _read_json(run_dir / "authorisation.json")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ContinuationError("invalid_manifest_jobs")
    job_ids = [job.get("job_id") for job in jobs if isinstance(job, dict)]
    if len(job_ids) != len(jobs) or len(set(job_ids)) != len(job_ids):
        raise ContinuationError("duplicate_or_invalid_job_identity")
    if (run.get("manifest_sha256") != expected_manifest_sha256 or run.get("mode") != "live"
            or run.get("stage") != "pilot" or run.get("selected_job_ids") != job_ids
            or run.get("execution_profile") != manifest.get("operator_execution", {}).get("profile")
            or type(run.get("max_live_calls")) is not int or run["max_live_calls"] < 1
            or authorisation.get("automatic_stage_transition") is not False):
        raise ContinuationError("run_scope_mismatch")
    if (completion.get("manifest_sha256") != expected_manifest_sha256 or completion.get("mode") != "live"
            or completion.get("execution_profile") != run["execution_profile"]
            or set(completion.get("outcomes", {})) != set(job_ids)):
        raise ContinuationError("incomplete_or_mismatched_completion")

    ledger_path = run_dir / "ledger.jsonl"
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise ContinuationError("missing_or_symlinked_ledger")
    starts: dict[str, dict[str, Any]] = {}
    finishes: dict[str, dict[str, Any]] = {}
    completion_anchors: list[str] = []
    tip = None
    try:
        lines = ledger_path.read_bytes().splitlines()
        for sequence, line in enumerate(lines):
            event = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object,
                               parse_constant=_reject_constant)
            if not isinstance(event, dict):
                raise ContinuationError("invalid_ledger_event")
            if (event.get("sequence") != sequence
                    or event.get("previous_event_sha256") != tip
                    or event.get("event_sha256") != _digest(
                        {key: value for key, value in event.items() if key != "event_sha256"})):
                raise ContinuationError("ledger_hash_chain_mismatch")
            tip = event["event_sha256"]
            ident = event.get("job_id")
            if event.get("event") == "started":
                if ident in starts:
                    raise ContinuationError("duplicate_attempt_reservation")
                starts[ident] = event
            elif event.get("event") in ("completed", "recovered_completion"):
                if ident in finishes:
                    raise ContinuationError("duplicate_terminal_checkpoint")
                finishes[ident] = event
            elif event.get("event") == "stage_completion":
                completion_anchors.append(event.get("sha256"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuationError("invalid_ledger_json") from exc
    if set(starts) != set(job_ids) or set(finishes) != set(job_ids):
        raise ContinuationError("ledger_job_set_mismatch")
    if completion_anchors != [_file_digest(run_dir / "completion.json")]:
        raise ContinuationError("stage_completion_anchor_mismatch")
    checkpoint_root = run_dir / "checkpoints"
    if checkpoint_root.is_symlink() or not checkpoint_root.is_dir() or {
            path.name for path in checkpoint_root.iterdir()} != set(job_ids):
        raise ContinuationError("checkpoint_directory_set_mismatch")

    results: dict[str, dict[str, Any]] = {}
    result_hashes: dict[str, str] = {}
    status_counts: collections.Counter[str] = collections.Counter()
    schema_errors: collections.Counter[str] = collections.Counter()
    reservations = 0
    for job in jobs:
        ident = job["job_id"]
        if not SHA256.fullmatch(ident):
            raise ContinuationError("invalid_job_id")
        job_identity = {key: value for key, value in job.items()
                        if key not in {"job_id", "checkpoint", "parent_checkpoint"}}
        if _digest(job_identity) != ident:
            raise ContinuationError("job_identity_mismatch:" + ident)
        folder = run_dir / "checkpoints" / ident
        intent = _read_json(folder / "intent.json")
        payload_path, raw_path = folder / "payload.json", folder / "raw.json"
        result_path = folder / "result.json"
        payload, raw, result = (_read_json(payload_path), _read_json(raw_path), _read_json(result_path))
        reservation = intent.get("budget_reservation")
        if (intent.get("job") != job or intent.get("manifest_sha256") != expected_manifest_sha256
                or intent.get("mode") != "live" or type(reservation) is not int or reservation not in (0, 1)
                or starts[ident].get("intent_sha256") != _file_digest(folder / "intent.json")
                or starts[ident].get("budget_reservation") != reservation):
            raise ContinuationError("attempt_intent_mismatch:" + ident)
        if not isinstance(payload, dict) or not isinstance(raw, dict):
            raise ContinuationError("invalid_attempt_artifact:" + ident)
        if (result.get("job_id") != ident or result.get("manifest_sha256") != expected_manifest_sha256
                or result.get("mode") != "live" or result.get("input_sha256") != job.get("input_sha256")
                or result.get("implementation_sha256") != manifest.get("implementation_sha256")
                or result.get("instruments_sha256") != manifest.get("instruments_sha256")
                or result.get("execution_profile") != run["execution_profile"]
                or result.get("payload_sha256") != _digest(payload.get("payload"))
                or result.get("artifact_sha256") != {
                    "intent.json": _file_digest(folder / "intent.json"),
                    "payload.json": _file_digest(payload_path),
                    "raw.json": _file_digest(raw_path),
                }):
            raise ContinuationError("checkpoint_integrity_mismatch:" + ident)
        result_hash = _file_digest(result_path)
        finish = finishes[ident]
        if (finish.get("result_sha256") != result_hash or finish.get("status") != result.get("status")
                or completion["outcomes"].get(ident) != {
                    "status": result.get("status"), "result_sha256": result_hash}):
            raise ContinuationError("checkpoint_completion_mismatch:" + ident)
        status = result.get("status")
        if status not in REPLAY_STATUSES:
            raise ContinuationError("unknown_or_nonterminal_status:" + str(status))
        if status == "schema_invalid":
            if (job.get("kind") != "generator" or result.get("schema_valid") is not False
                    or result.get("parsed") is not None or not result.get("reason")):
                raise ContinuationError("schema_failure_was_reinterpreted:" + ident)
            schema_errors[result["reason"]] += 1
        if (status in ("ok", "schema_invalid") and reservation != 1) or (
                status == "blocked_parent" and reservation != 0):
            raise ContinuationError("status_reservation_mismatch:" + ident)
        dependencies = job.get("dependencies")
        if not isinstance(dependencies, list) or any(parent not in results for parent in dependencies):
            raise ContinuationError("non_topological_or_unknown_parent:" + ident)
        parent_hashes = {parent: result_hashes[parent] for parent in dependencies}
        if result.get("parent_checkpoint_sha256") != parent_hashes:
            raise ContinuationError("parent_checkpoint_binding_mismatch:" + ident)
        has_failed_parent = any(results[parent]["status"] != "ok" for parent in dependencies)
        if (status == "blocked_parent") != has_failed_parent:
            raise ContinuationError("parent_blocking_semantics_mismatch:" + ident)
        results[ident] = result
        result_hashes[ident] = result_hash
        reservations += reservation
        status_counts[status] += 1

    if (reservations != completion.get("adapter_attempt_reservations")
            or reservations > run["max_live_calls"]):
        raise ContinuationError("attempt_budget_reconciliation_mismatch")
    latest_summary_path = max(run_dir.glob("summary-*.json"),
                              key=lambda path: int(path.stem.rsplit("-", 1)[1]), default=None)
    if latest_summary_path is None:
        raise ContinuationError("missing_final_summary")
    summary = _read_json(latest_summary_path)
    if (summary.get("manifest_sha256") != expected_manifest_sha256
            or summary.get("selected_jobs") != len(jobs) or summary.get("complete") is not True
            or summary.get("status_counts") != dict(status_counts)
            or summary.get("adapter_attempt_reservations") != reservations
            or summary.get("automatic_next_stage") is not False
            or summary.get("stopped_reason") is not None):
        raise ContinuationError("final_summary_mismatch")
    after = _tree_digest(run_dir)
    if before != after:
        raise ContinuationError("read_only_replay_modified_evidence")
    return {
        "schema": VERSION + "-replay",
        "manifest_sha256": expected_manifest_sha256,
        "manifest_file_sha256": _file_digest(run_dir / "manifest.json"),
        "terminal_checkpoints": len(results),
        "status_counts": dict(status_counts),
        "schema_error_counts": dict(schema_errors),
        "adapter_attempt_reservations": reservations,
        "provider_calls_during_replay": 0,
        "frozen_evidence_modified": False,
    }


def plan_continuation(
    jobs: Sequence[Mapping[str, Any]],
    outcomes: Mapping[str, str],
    *,
    explicitly_authorized: bool,
    reserved_attempts: int,
    max_attempts: int,
    credentials_available: Mapping[str, bool],
    identity_verified: bool,
    verified_outcome_job_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Plan from caller-verified checkpoint outcomes without performing any invocation."""
    if type(explicitly_authorized) is not bool or type(identity_verified) is not bool:
        raise ContinuationError("authorization_and_identity_must_be_explicit_booleans")
    if (type(reserved_attempts) is not int or type(max_attempts) is not int
            or reserved_attempts < 0 or max_attempts < 1 or reserved_attempts > max_attempts):
        raise ContinuationError("invalid_attempt_budget")
    seen: set[str] = set()
    for job in jobs:
        ident = job.get("job_id")
        dependencies = job.get("dependencies")
        if not isinstance(ident, str) or ident in seen or not isinstance(dependencies, list):
            raise ContinuationError("invalid_or_duplicate_job")
        if any(not isinstance(parent, str) or parent not in seen for parent in dependencies):
            raise ContinuationError("non_topological_dependency")
        seen.add(ident)
    if set(outcomes) - seen:
        raise ContinuationError("outcome_for_unknown_job")
    if verified_outcome_job_ids - set(outcomes):
        raise ContinuationError("verification_for_missing_outcome")
    for ident, status in outcomes.items():
        if ident not in verified_outcome_job_ids:
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "checkpoint_outcome_unverified", "at_job_id": ident,
                    "ready_job_ids": [], "deferred_job_ids": [],
                    "reserved_attempts": reserved_attempts, "provider_calls": 0}
        if status in STOP_STATUSES or status not in REPLAY_STATUSES:
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "credential_or_ambiguous_execution_failure" if status in STOP_STATUSES
                    else "unknown_status", "at_job_id": ident, "ready_job_ids": [],
                    "deferred_job_ids": [], "reserved_attempts": reserved_attempts, "provider_calls": 0}

    pending = [job for job in jobs if job["job_id"] not in outcomes]
    resolved: dict[str, str] = {}
    for job in jobs:
        ident = job["job_id"]
        if ident not in outcomes:
            continue
        parents = [resolved.get(parent) for parent in job["dependencies"]]
        if any(status is None for status in parents):
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "terminal_checkpoint_missing_parent_outcome",
                    "at_job_id": ident, "ready_job_ids": [],
                    "deferred_job_ids": [], "reserved_attempts": reserved_attempts, "provider_calls": 0}
        failed_parent = any(status not in SUCCESS for status in parents)
        if (outcomes[ident] == "blocked_parent") != failed_parent:
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "parent_blocking_semantics_mismatch",
                    "at_job_id": ident, "ready_job_ids": [],
                    "deferred_job_ids": [], "reserved_attempts": reserved_attempts, "provider_calls": 0}
        resolved[ident] = outcomes[ident]
    if not pending:
        return {"schema": VERSION + "-plan", "decision": "complete", "reason": None,
                "ready_job_ids": [], "blocked_parent_job_ids": [],
                "deferred_job_ids": [],
                "preserved_schema_invalid_job_ids": sorted(
                    ident for ident, status in outcomes.items() if status == "schema_invalid"),
                "reserved_attempts": reserved_attempts, "provider_calls": 0}
    if not explicitly_authorized:
        return {"schema": VERSION + "-plan", "decision": "stop",
                "reason": "explicit_continuation_authorization_required", "ready_job_ids": [],
                "deferred_job_ids": sorted(job["job_id"] for job in pending),
                "reserved_attempts": reserved_attempts, "provider_calls": 0}
    if not identity_verified:
        return {"schema": VERSION + "-plan", "decision": "stop",
                "reason": "identity_unverified", "ready_job_ids": [],
                "deferred_job_ids": sorted(job["job_id"] for job in pending),
                "reserved_attempts": reserved_attempts, "provider_calls": 0}

    next_status = dict(outcomes)
    ready: list[str] = []
    blocked: list[str] = []
    deferred: list[str] = []
    new_reservations = reserved_attempts
    for job in jobs:
        ident = job["job_id"]
        if ident in outcomes:
            continue
        parents = [next_status.get(parent) for parent in job["dependencies"]]
        if any(status is None for status in parents):
            deferred.append(ident)
            continue
        if any(status not in SUCCESS for status in parents):
            next_status[ident] = "blocked_parent"
            blocked.append(ident)
            continue
        adapter = job.get("adapter")
        if not isinstance(adapter, str) or credentials_available.get(adapter) is not True:
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "credential_unavailable", "at_job_id": ident,
                    "ready_job_ids": [], "deferred_job_ids": deferred,
                    "reserved_attempts": reserved_attempts,
                    "provider_calls": 0}
        if new_reservations >= max_attempts:
            return {"schema": VERSION + "-plan", "decision": "stop",
                    "reason": "attempt_budget_exhausted", "at_job_id": ident,
                    "ready_job_ids": [], "deferred_job_ids": deferred,
                    "reserved_attempts": reserved_attempts,
                    "provider_calls": 0}
        ready.append(ident)
        new_reservations += 1
    return {"schema": VERSION + "-plan", "decision": "continue" if ready else "complete",
            "reason": None, "ready_job_ids": ready, "blocked_parent_job_ids": blocked,
            "deferred_job_ids": deferred,
            "preserved_schema_invalid_job_ids": sorted(
                ident for ident, status in outcomes.items() if status == "schema_invalid"),
            "reserved_attempts": new_reservations, "provider_calls": 0}
