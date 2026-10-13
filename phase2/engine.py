from __future__ import annotations

import collections
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import subprocess

from historical_extractor.archive import IntegrityError, file_hash, sha256
from historical_extractor.extract import strict_json
from .adapters import (
    CarlJEVAdapter, GeminiAdapter, HaikuAdapter, MockAdapters, NativeJEVAdapter,
    Response, SolAdapter, executable,
)
from .core import SUCCESS, assessment, challenge_request, digest, json_bytes, load, render_prompt, write_new


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def locked(directory: Path):
    if directory.is_symlink():
        raise IntegrityError("Run directory must not be a symlink")
    directory.mkdir(mode=0o700, parents=False, exist_ok=True)
    lock_path = directory / ".lock"
    if lock_path.is_symlink():
        raise IntegrityError("Unsafe lock path")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.events: list[dict] = []
        if path.is_symlink():
            raise IntegrityError("Ledger symlink refused")
        if path.exists():
            for line in path.read_bytes().splitlines():
                event = strict_json(line)
                if not isinstance(event, dict):
                    raise IntegrityError("Invalid ledger event")
                expected = digest({k: v for k, v in event.items() if k != "event_sha256"})
                if event.get("event_sha256") != expected or event.get("previous_event_sha256") != self.tip:
                    raise IntegrityError("Ledger hash chain mismatch; no automatic repair")
                if event.get("sequence") != len(self.events):
                    raise IntegrityError("Ledger sequence mismatch")
                self.events.append(event)

    @property
    def tip(self) -> str | None:
        return self.events[-1]["event_sha256"] if self.events else None

    def append(self, event: dict) -> None:
        row = {**event, "sequence": len(self.events), "previous_event_sha256": self.tip, "at": now()}
        row["event_sha256"] = digest(row)
        with self.path.open("ab") as stream:
            stream.write(json_bytes(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.events.append(row)


def sealed_result(folder: Path, ledger: Ledger, job: dict, manifest_hash: str) -> dict | None:
    if not folder.exists():
        return None
    if folder.is_symlink() or any(p.is_symlink() for p in folder.iterdir()):
        raise IntegrityError("Checkpoint symlink refused")
    intent_file = folder / "intent.json"
    if not intent_file.is_file():
        raise IntegrityError("Reserved checkpoint without intent; inspect manually")
    intent = load(intent_file)
    if intent["job"] != job or intent["manifest_sha256"] != manifest_hash:
        raise IntegrityError("Checkpoint intent binding mismatch")
    started = [e for e in ledger.events if e.get("job_id") == job["job_id"] and e["event"] == "started"]
    if not started or started[0]["intent_sha256"] != file_hash(intent_file):
        raise IntegrityError("Checkpoint intent not bound to ledger")
    result_file = folder / "result.json"
    if not result_file.exists():
        return {"status": "incomplete_attempt", "job_id": job["job_id"], "parsed": None,
                "checkpoint_sha256": None, "reason": "Intent exists without result; no inference replay.",
                "schema_valid": None, "mode": intent["mode"]}
    result = load(result_file)
    if result.get("job_id") != job["job_id"] or result.get("manifest_sha256") != manifest_hash:
        raise IntegrityError("Result binding mismatch")
    for name, expected in result["artifact_sha256"].items():
        if Path(name).name != name or file_hash(folder / name) != expected:
            raise IntegrityError("Checkpoint artifact hash mismatch")
    completed = [e for e in ledger.events if e.get("job_id") == job["job_id"] and
                 e["event"] in ("completed", "recovered_completion")]
    actual = file_hash(result_file)
    if completed and completed[-1]["result_sha256"] != actual:
        raise IntegrityError("Checkpoint result hash mismatch")
    if not completed:
        ledger.append({"event": "recovered_completion", "job_id": job["job_id"], "result_sha256": actual,
                       "reason": "Result persisted before ledger completion; no inference replay."})
    return {**result, "checkpoint_sha256": actual}


def histories(job: dict, results: dict[str, dict], jobs: dict[str, dict]) -> list[dict]:
    """Follow only this job's assessment ancestors; never enumerate other branches."""
    chain = []
    parent = job["assessment_parent"]
    while parent:
        previous_job = jobs[parent]
        if previous_job["arm"] not in ("B0", job["arm"]):
            raise IntegrityError("Cross-arm history refused")
        result = results[parent]
        chain.append({"assessment": result["parsed"],
                      "challenge": result.get("challenge_used"),
                      "source_sha256": previous_job["input_sha256"]})
        parent = previous_job["assessment_parent"]
    return list(reversed(chain))


def smoke_ready(name: str, plan: dict, directory: Path | None, *, require_approval: bool = True) -> tuple[bool, str]:
    if directory is None or not (directory / name / "result.json").is_file():
        return False, "missing_live_smoke_receipt"
    receipt = load(directory / name / "result.json")
    if receipt.get("mode") != "live_smoke" or receipt.get("status") != "ok":
        return False, "mock_or_failed_smoke_is_not_live_readiness"
    if receipt.get("config_sha256") != plan["config_sha256"]:
        return False, "smoke_configuration_mismatch"
    if receipt.get("adapter_software_sha256") != plan["software_sha256"].get("adapters.py"):
        return False, "smoke_adapter_software_mismatch"
    if receipt.get("adapter") != name or receipt.get("transport_attempts") != 1:
        return False, "smoke_transport_provenance_missing"
    if file_hash(directory / name / "raw.json") != receipt.get("raw_sha256"):
        return False, "smoke_raw_hash_mismatch"
    spec = {**plan["config"]["generators"], **plan["config"]["adversaries"]}[name]
    observed = receipt.get("observed_model")
    if not isinstance(observed, str) or not observed:
        return False, "served_model_not_observed"
    if name in plan["config"]["generators"] and observed != spec["model_id"]:
        return False, "served_model_mismatch"
    if spec.get("binary"):
        path = executable(spec)
        if not path or file_hash(Path(path)) != receipt.get("binary_sha256"):
            return False, "smoke_binary_changed"
    if require_approval:
        approval_file = directory / name / "approval.json"
        if not approval_file.is_file():
            return False, "operator_isolation_and_retry_review_required"
        approval = load(approval_file)
        if (approval.get("smoke_result_sha256") != file_hash(directory / name / "result.json")
                or approval.get("isolation_reviewed") is not True
                or approval.get("no_hidden_retries_reviewed") is not True
                or not approval.get("review_note")):
            return False, "invalid_operator_smoke_approval"
    return True, "live_smoke_verified"


def approve_smoke(plan: dict, directory: Path, name: str, *, isolation: bool, retries: bool, note: str) -> dict:
    if not isolation or not retries or not note.strip():
        raise IntegrityError("Explicit isolation/retry review and evidence note required")
    ready, reason = smoke_ready(name, plan, directory, require_approval=False)
    if not ready:
        raise IntegrityError("Smoke cannot be approved: " + reason)
    approval = {"schema": "mmmtap-smoke-approval-v1",
                "smoke_result_sha256": file_hash(directory / name / "result.json"),
                "isolation_reviewed": True, "no_hidden_retries_reviewed": True,
                "review_note": note, "at": now(), "basis": "operator_attestation_not_automatic_certification"}
    write_new(directory / name / "approval.json", approval)
    return approval


def live_invoke(plan: dict, job: dict, payload: object) -> Response:
    cfg = plan["config"]
    if job["kind"] == "generator":
        cls = {"haiku": HaikuAdapter, "gemini": GeminiAdapter, "sol": SolAdapter}[job["generator"]]
        return cls(cfg["generators"][job["generator"]], cfg).invoke(payload, authorised=True)
    if job["mechanism"] == "native_jev":
        return NativeJEVAdapter(cfg["adversaries"]["native_jev"], cfg).invoke(
            payload, job["evidence_contract"], authorised=True)
    return CarlJEVAdapter(cfg["adversaries"]["carl_jev"], cfg).invoke(
        json_bytes(payload).decode(), job["evidence_contract"], authorised=True)


def usage_metrics(response: Response, mode: str, cfg: dict) -> dict:
    usage = response.usage if isinstance(response.usage, dict) else {}
    counts = {}
    for field in ("input_tokens", "output_tokens", "cached_input_tokens"):
        value = usage.get(field)
        counts[field] = value if type(value) is int and value >= 0 else None
    return {**counts, "latency_seconds": response.latency_seconds, "exit_status": response.exit_status,
            "cost_usd": None, "cost_status": "not_priced" if mode == "live" else "mock_not_billable",
            "usage_raw": response.usage}


def execute(plan: dict, members: dict[str, bytes], directory: Path, *, mode: str,
            authorised: bool = False, max_live_calls: int | None = None,
            selected_inputs: set[tuple[str, str]] | None = None, smoke_directory: Path | None = None,
            mock: MockAdapters | None = None) -> dict:
    if mode not in ("mock", "live") or (mode == "live" and not authorised):
        raise IntegrityError("Explicit live authorisation required")
    integration = plan.get("integration_version") is not None
    if integration:
        from .integration import validate_v4
        validate_v4(plan)
        if mode == "live":
            raise IntegrityError("Proposed v4 instruments need separately qualified adapters and a newly approved plan")
    if mode == "live" and (type(max_live_calls) is not int or max_live_calls < 1):
        raise IntegrityError("Live execution requires an explicit positive call ceiling")
    if mode == "live" and mock is not None:
        raise IntegrityError("Mock adapter cannot be used in live mode")
    if digest({k: v for k, v in plan.items() if k != "manifest_sha256"}) != plan["manifest_sha256"]:
        raise IntegrityError("Execution manifest hash mismatch")
    mock = mock or MockAdapters()
    selected = [j for j in plan["jobs"] if selected_inputs is None or (j["case_id"], j["variant_id"]) in selected_inputs]
    if not selected:
        raise IntegrityError("Empty execution selection")
    if selected_inputs is not None and selected_inputs != {(j["case_id"], j["variant_id"]) for j in selected}:
        raise IntegrityError("Selection contains unknown frozen input identities")
    scope = {"manifest_sha256": plan["manifest_sha256"], "mode": mode,
             "selected_job_ids": [j["job_id"] for j in selected], "max_live_calls": max_live_calls,
             "mock_carl_supported": mock.test_carl_supported if mode == "mock" else False}
    if integration:
        scope["mock_fixture"] = getattr(mock, "identity", "default_empty_claims")
    jobs = {j["job_id"]: j for j in plan["jobs"]}
    with locked(directory):
        if (directory / "run.json").exists():
            if load(directory / "run.json") != scope or load(directory / "manifest.json") != plan:
                raise IntegrityError("Run scope, mode, budget or manifest changed; choose a new run")
        else:
            write_new(directory / "run.json", scope)
            write_new(directory / "manifest.json", plan)
        (directory / "checkpoints").mkdir(mode=0o700, exist_ok=True)
        if (directory / "checkpoints").is_symlink():
            raise IntegrityError("Checkpoint root symlink refused")
        ledger = Ledger(directory / "ledger.jsonl")
        used = sum(e.get("budget_reservation", 0) for e in ledger.events)
        results: dict[str, dict] = {}
        executed = 0
        reused = 0
        for job in selected:
            ident = job["job_id"]
            folder = directory / "checkpoints" / ident
            previous_result = sealed_result(folder, ledger, job, plan["manifest_sha256"])
            if previous_result is not None:
                # Verify persisted lineage against the immutable first-attempt parents.
                if previous_result["status"] != "incomplete_attempt":
                    expected_parents = {p: results[p]["checkpoint_sha256"] for p in job["dependencies"]}
                    if previous_result["parent_checkpoint_sha256"] != expected_parents:
                        raise IntegrityError("Parent checkpoint lineage changed")
                results[ident] = previous_result
                reused += 1
                continue
            missing = [dep for dep in job["dependencies"] if dep not in results]
            if missing:
                raise IntegrityError("Selection omits required parent")
            blocked = any(results[p]["status"] not in SUCCESS for p in job["dependencies"])
            unsupported = job["mechanism"] == "carl_jev" and job["evidence_contract"] != "authenticated_git_diff_v1"
            if integration:
                unsupported = (job["kind"] == "adversary" and job["adversary_contract"] not in
                               plan["config"]["adversaries"][job["mechanism"]]["evidence_contracts"])
            elif mode == "mock" and mock.test_carl_supported:
                unsupported = False
            response = Response()
            name = job["generator"] if job["kind"] == "generator" else job["mechanism"]
            ready, readiness_reason = (True, "mock_only") if mode == "mock" else smoke_ready(name, plan, smoke_directory)
            will_call = not blocked and not unsupported and ready
            if mode == "live" and will_call and used >= max_live_calls:
                break
            source = members[job["input_member"]]
            if sha256(source) != job["input_sha256"]:
                raise IntegrityError("Frozen source integrity failure")
            parent_id = job["assessment_parent"]
            previous = results[parent_id]["parsed"] if parent_id and results[parent_id]["status"] in SUCCESS else None
            challenge = results[job["challenge_parent"]]["parsed"] if job["challenge_parent"] and not blocked else None
            parent_hashes = {p: results[p]["checkpoint_sha256"] for p in job["dependencies"]}
            reservation = int(mode == "live" and will_call)
            folder.mkdir(mode=0o700, exist_ok=False)
            intent = {"job": job, "manifest_sha256": plan["manifest_sha256"], "mode": mode,
                      "parent_checkpoint_sha256": parent_hashes, "payload_state": "not_prepared",
                      "budget_reservation": reservation, "started_at": now()}
            write_new(folder / "intent.json", intent)
            ledger.append({"event": "started", "job_id": ident, "intent_sha256": file_hash(folder / "intent.json"),
                           "budget_reservation": reservation})
            used += reservation
            payload, preparation_error = None, None
            if not blocked:
                try:
                    if job["kind"] == "generator":
                        payload = render_prompt(plan, job, source, previous, histories(job, results, jobs), challenge)
                    elif integration and job["mechanism"] == "carl_jev":
                        from .path_b import build_request
                        payload = build_request(plan, job, directory, members,
                            json_bytes(plan["source_manifest"]), "integration-" + ident)
                    else:
                        payload = challenge_request(plan, job, source, previous)
                except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
                    preparation_error = "preparation_failed:" + type(exc).__name__
                    response = Response(error=preparation_error, provenance={
                        "preparation_status": "failed_before_adapter_invocation",
                        "transport_attempts": 0, "cli_invocations": 0})
            write_new(folder / "payload.json", {"payload": payload})
            parsed = None
            schema_valid = None
            parse_error = None
            if blocked:
                status, reason = "blocked_parent", "Required first-attempt parent failed, is incomplete or unsupported."
            elif preparation_error:
                status, reason = "execution_failed", preparation_error
            elif unsupported:
                status, reason = "unsupported_contract", "Frozen primary text has no authenticated cARL Git-diff binding."
            elif not ready:
                status, reason = "adapter_unverified", readiness_reason
            else:
                try:
                    response = mock.invoke(job, payload, previous) if mode == "mock" else live_invoke(plan, job, payload)
                except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
                    response = Response(error="adapter_exception:" + type(exc).__name__)
                if response.error:
                    status = "unsupported_contract" if response.error == "unsupported_contract" else "execution_failed"
                    reason = response.error
                elif job["kind"] == "generator":
                    observed = response.provenance.get("observed_model")
                    model_error = mode == "live" and observed != job["generator_spec"]["model_id"]
                    parsed, parse_error = (None, "served_model_missing_or_changed") if model_error else assessment(
                        response.message.decode("utf-8", "replace"), job, previous)
                    schema_valid = parsed is not None
                    status, reason = ("mock_ok" if mode == "mock" else "ok", "Parsed assessment; correctness unadjudicated.") if parsed else (
                        "schema_invalid", parse_error)
                else:
                    try:
                        parsed = strict_json(response.message)
                        if not isinstance(parsed, dict):
                            raise ValueError("adversary response not object")
                        status, reason = ("mock_ok" if mode == "mock" else "ok"), "Untrusted challenge, not source truth."
                        schema_valid = True
                    except (ValueError, UnicodeError, RecursionError) as exc:
                        status, reason, parse_error = "schema_invalid", str(exc), str(exc)
                        schema_valid = False
            write_new(folder / "raw.json", response.record())
            quote_audit = []
            if parsed and job["kind"] == "generator":
                text = source.decode("utf-8")
                quote_audit = [{"claim_id": c["claim_id"], "quote": q, "exact_source_substring": q in text}
                               for c in parsed["claims"] for q in c["evidence_quotes"]]
            record = {"schema": "mmmtap-checkpoint-v1", "job_id": ident, "mode": mode,
                      "manifest_sha256": plan["manifest_sha256"], "input_sha256": job["input_sha256"],
                      "status": status, "reason": reason, "parsed": parsed, "schema_valid": schema_valid,
                      "parse_error": parse_error, "quote_audit": quote_audit,
                      "parent_checkpoint_sha256": parent_hashes, "payload_sha256": digest(payload),
                      "challenge_used": challenge, "metrics": usage_metrics(response, mode, plan["config"]),
                      "correctness": "not_adjudicated", "completed_at": now(),
                      "artifact_sha256": {name: file_hash(folder / name) for name in ("intent.json", "payload.json", "raw.json")}}
            write_new(folder / "result.json", record)
            result_hash = file_hash(folder / "result.json")
            ledger.append({"event": "completed", "job_id": ident, "result_sha256": result_hash, "status": status})
            results[ident] = {**record, "checkpoint_sha256": result_hash}
            executed += 1
            if mode == "live" and status in ("execution_failed", "schema_invalid", "adapter_unverified"):
                break
        summary = {"mode": mode, "selected_jobs": len(selected), "completed_or_preserved_jobs": len(results),
                   "new_checkpoints": executed, "preserved_checkpoints": reused,
                   "live_call_reservations": used, "status_counts": dict(collections.Counter(r["status"] for r in results.values())),
                   "complete": len(results) == len(selected), "research_conclusions": "none",
                   "independent_adjudication": "not_performed"}
        ledger.append({"event": "session_summary", "summary": summary})
        # Every invocation gets a new summary; prior summaries are never overwritten.
        write_new(directory / f"summary-{len(ledger.events):06d}.json", summary)
        return summary


def live_smoke(plan: dict, members: dict[str, bytes], directory: Path, name: str, *, authorised: bool) -> dict:
    if not authorised:
        raise IntegrityError("A live smoke test needs separate explicit authorisation")
    specs = {**plan["config"]["generators"], **plan["config"]["adversaries"]}
    if name not in specs:
        raise IntegrityError("Unknown adapter")
    # Reserve before even an authentication failure; failed smoke never retries itself.
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink():
        raise IntegrityError("Smoke directory symlink refused")
    folder = directory / name
    folder.mkdir(mode=0o700, exist_ok=False)
    base = next(j for j in plan["jobs"] if j["arm"] == "B0" and j["case_id"] == "synthetic-benign-docs"
                and j["variant_id"] == "baseline" and j["generator"] == (name if name in plan["config"]["generators"] else "haiku"))
    job = dict(base)
    source = members[job["input_member"]]
    if name in plan["config"]["adversaries"]:
        job.update({"kind": "adversary", "mechanism": name})
        previous = {"case_id": job["case_id"], "variant_id": job["variant_id"], "claims": [],
                    "disposition": "insufficient_evidence", "uncertainties": ["Smoke contract probe, not an assessment."], "changes": []}
        payload = challenge_request(plan, job, source, previous)
    else:
        payload = render_prompt(plan, job, source, None, [], None)
    write_new(folder / "intent.json", {"purpose": "live_smoke_not_experiment", "adapter": name,
                                      "config_sha256": plan["config_sha256"], "max_calls": 1, "payload": payload})
    try:
        response = live_invoke(plan, job, payload)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        response = Response(error="adapter_exception:" + type(exc).__name__)
    parsed, error = (None, None)
    if not response.error and job["kind"] == "generator":
        parsed, error = assessment(response.message.decode("utf-8", "replace"), job)
    elif not response.error:
        try:
            parsed = strict_json(response.message)
            if not isinstance(parsed, dict):
                raise ValueError("adversary_response_not_object")
        except (ValueError, UnicodeError, RecursionError) as exc:
            parsed, error = None, str(exc)
    write_new(folder / "raw.json", response.record())
    spec = specs[name]
    binary = executable(spec)
    result = {"schema": "mmmtap-live-smoke-v1", "mode": "live_smoke", "purpose": "not_research",
              "adapter": name, "status": "ok" if parsed is not None and not error else response.error or error or "invalid",
              "parsed": parsed, "config_sha256": plan["config_sha256"],
              "adapter_software_sha256": plan["software_sha256"]["adapters.py"],
              "binary_sha256": file_hash(Path(binary)) if binary else None,
              "requested_model": spec["model_id"], "observed_model": response.provenance.get("observed_model"),
              "raw_sha256": file_hash(folder / "raw.json"), "transport_attempts": response.provenance.get("transport_attempts", 0),
              "limitations": ["CLI requested model is pinned; served version may not be exposed.",
                              "Client/provider-internal retry behaviour requires operator review of raw events."]}
    write_new(folder / "result.json", result)
    return result
