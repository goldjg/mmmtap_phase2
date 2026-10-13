"""Serial, immutable stage execution with separately authorised live entry points."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import collections
import os
from pathlib import Path
import shutil
import signal

from historical_extractor.archive import sha256
from historical_extractor.extract import strict_json
from phase2.adapters import Response
from phase2.adjudication import checked_records
from phase2.core import (IntegrityError, SUCCESS, assessment, challenge_request, corpus, digest,
                         json_bytes, load, render_prompt, write_new)
from phase2.engine import Ledger, histories, locked, now, usage_metrics
from phase2.integration import ScriptedAdapters
from phase2.isolation import sha256_file
from phase2.path_b import build_request
from . import VERSION
from .checks import preflight
from .planning import PACKAGE, ROOT, REGISTRY, STAGES, adapter, make_manifest, validate_manifest
from .profiles import authorise
from .transports import credentials, invoke, systemone

MIN_FREE_DURING_RUN = 128 * 1024 * 1024


def immutable(path: Path, value) -> None:
    write_new(path, value)
    path.chmod(0o400)


def safe_runs_root(path: Path) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise IntegrityError("Symlink in output path")
    if path in (Path("/"), Path.home(), ROOT, PACKAGE):
        raise IntegrityError("Output must be a dedicated operator run directory")
    if path.is_relative_to(ROOT) and path != ROOT / "operator_runs_v1":
        raise IntegrityError("Inside the workspace, only operator_runs_v1 is writable for live stages")
    return path


@contextmanager
def interrupt_handlers():
    previous = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    for number in (signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.signal(number, interrupt)
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


class OperatorMock(ScriptedAdapters):
    """Use v5 challenge-sensitive fixtures and the actual contained Path B worker."""
    identity = "operator-v1-labelled_mock_with_contained_Path_B"

    def invoke(self, job: dict, payload, previous: dict | None) -> Response:
        if job["mechanism"] != "carl_jev":
            return super().invoke(job, payload, previous)
        self.calls.append(job["job_id"])
        native = strict_json(base64.b64decode(payload["native_request"], validate=True))
        answer = {"model": "MOCK_SYSTEMONE_NOT_PROVIDER", "answers": {
            key: {"type": "noul", "noul": 0.1 if key == "authority_promoted"
                  else 0.2 if key == "claim_0000_supported" else 0.8}
            for key in native["questions"]}, "usage": {"input_tokens": 11, "output_tokens": 7}}
        response = systemone(self.plan, job, payload, mock_response=answer)
        if not response.error:
            parsed = strict_json(response.message)
            parsed["mock_fixture_binding"] = {
                "adversary_job_id": job["job_id"], "assessment_sha256": digest(previous)}
            response.message = json_bytes(parsed)
        return response


def stage_records(directory: Path, expected: dict) -> dict:
    if directory.is_symlink():
        raise IntegrityError("Predecessor directory is a symlink")
    if load(directory / "manifest.json") != expected:
        raise IntegrityError("Predecessor must have the exact same profile and software lineage")
    plan, records = checked_records(directory)
    scope = load(directory / "run.json")
    if scope["mode"] != "live" or scope.get("stage") != expected["operator_execution"]["stage"]:
        raise IntegrityError("Mocks or a different stage cannot authorise a live stage")
    completion = load(directory / "completion.json")
    ledger = Ledger(directory / "ledger.jsonl")
    starts = {event["job_id"]: event["intent_sha256"] for event in ledger.events if event["event"] == "started"}
    events = [e for e in ledger.events if e["event"] == "stage_completion"]
    if not events or events[-1]["sha256"] != sha256_file(directory / "completion.json"):
        raise IntegrityError("Unanchored stage completion")
    if completion["manifest_sha256"] != plan["manifest_sha256"]:
        raise IntegrityError("Stage completion identity changed")
    if set(completion["outcomes"]) != {j["job_id"] for j in plan["jobs"]}:
        raise IntegrityError("Predecessor has unfinished matrix positions")
    for ident, row in completion["outcomes"].items():
        if ident in records:
            path = directory / "checkpoints" / ident / "result.json"
            if row != {"status": records[ident]["status"], "result_sha256": sha256_file(path)}:
                raise IntegrityError("Predecessor completion result changed")
        else:
            intent = directory / "checkpoints" / ident / "intent.json"
            if row != {"status": "incomplete_attempt", "result_sha256": None} or not intent.is_file():
                raise IntegrityError("Missing predecessor attempt evidence")
            value = load(intent)
            job = next(j for j in expected["jobs"] if j["job_id"] == ident)
            if (value["job"] != job or value["manifest_sha256"] != expected["manifest_sha256"]
                    or value["mode"] != "live" or starts.get(ident) != sha256_file(intent)):
                raise IntegrityError("Incomplete predecessor intent changed")
    return records


def prerequisites(plan: dict, runs_root: Path) -> tuple[dict, str | None, dict]:
    stage = plan["operator_execution"]["stage"]
    names = plan["counts"]["by_adapter"]
    if stage == "smoke":
        return {name: None for name in names}, None, {}
    previous_stage = STAGES[STAGES.index(stage) - 1]
    selected_profile = plan["operator_execution"]["profile"]["name"]
    expected = make_manifest(previous_stage, selected_profile)
    records = stage_records(runs_root / previous_stage, expected)
    reasons = {}
    for name in names:
        jobs = [j for j in expected["jobs"] if adapter(j) == name]
        failed = [j["job_id"] for j in jobs if records.get(j["job_id"], {}).get("status") != "ok"]
        reasons[name] = "preceding_stage_adapter_not_successful:" + str(len(failed)) if failed else None
    smoke_plan = make_manifest("smoke", selected_profile)
    smoke = stage_records(runs_root / "smoke", smoke_plan)
    observed = {row["model_identity"]["observed_model"]
                for job in smoke_plan["jobs"] if job["kind"] == "adversary"
                for row in [smoke.get(job["job_id"], {})]
                if row.get("status") == "ok" and row.get("model_identity", {}).get("observed_model")}
    if len(observed) > 1:
        raise IntegrityError("Matched SystemOne smoke mechanisms reported different model identities")
    anchors = {previous_stage: sha256_file(runs_root / previous_stage / "completion.json"),
               "smoke": sha256_file(runs_root / "smoke" / "completion.json")}
    return reasons, next(iter(observed), None), anchors


def _existing(folder: Path, job: dict, plan: dict, ledger: Ledger,
              starts: dict, finishes: dict) -> dict | None:
    if not folder.exists():
        return None
    if folder.is_symlink() or any(p.is_symlink() for p in folder.iterdir()):
        raise IntegrityError("Checkpoint symlink refused")
    intent = load(folder / "intent.json")
    ident = job["job_id"]
    if (intent["job"] != job or intent["manifest_sha256"] != plan["manifest_sha256"]
            or starts.get(ident) != sha256_file(folder / "intent.json")):
        raise IntegrityError("Checkpoint reservation/ledger changed")
    if not (folder / "result.json").exists():
        return {"job_id": ident, "status": "incomplete_attempt", "parsed": None,
                "checkpoint_sha256": None, "reason": "Reserved attempt; never reissued."}
    result = load(folder / "result.json")
    if (result["job_id"] != ident or result["manifest_sha256"] != plan["manifest_sha256"]
            or result["input_sha256"] != job["input_sha256"] or result["mode"] != intent["mode"]
            or result["implementation_sha256"] != plan["implementation_sha256"]
            or result["instruments_sha256"] != plan["instruments_sha256"]
            or result["execution_profile"] != plan["operator_execution"]["profile"]
            or set(result["artifact_sha256"]) != {"intent.json", "payload.json", "raw.json"}):
        raise IntegrityError("Checkpoint result identity/profile changed")
    for name, expected in result["artifact_sha256"].items():
        if sha256_file(folder / name) != expected:
            raise IntegrityError("Checkpoint artifact changed")
    actual = sha256_file(folder / "result.json")
    if ident in finishes and finishes[ident] != actual:
        raise IntegrityError("Checkpoint completion changed")
    if ident not in finishes:
        ledger.append({"event": "recovered_completion", "job_id": ident, "result_sha256": actual})
        finishes[ident] = actual
    return {**result, "checkpoint_sha256": actual}


def _identity(plan: dict, job: dict, response: Response) -> dict:
    spec = {**plan["config"]["generators"], **plan["config"]["adversaries"]}[adapter(job)]
    return {
        "provider": spec["provider"], "requested_model": spec["model_id"],
        "observed_model": response.provenance.get("observed_model"),
        "provider_confirmed_model": response.provenance.get("provider_confirmed_model"),
        "basis": response.provenance.get("identity_basis",
                                        response.provenance.get("provider_identity_basis", "not_observed")),
        "binary_sha256": spec.get("binary_sha256"), "configuration_sha256": digest(spec),
        "cli_version": response.provenance.get("cli_version"),
    }


def execute(plan: dict, runs_root: Path, *, mode: str, max_calls: int,
            authorised_stage: str | None = None, accept_lower_assurance: bool = False,
            approve_instruments: bool = False, review_note: str | None = None,
            stop_after: int | None = None, mock: ScriptedAdapters | None = None) -> dict:
    if mode not in ("mock", "live"):
        raise IntegrityError("Unknown execution mode")
    stage = plan["operator_execution"]["stage"]
    if mode == "live":
        authorise(plan, stage, authorised_stage=authorised_stage,
                  accept_lower_assurance=accept_lower_assurance, approve_instruments=approve_instruments,
                  review_note=review_note)
        if mock is not None:
            raise IntegrityError("Mock adapters cannot enter live execution")
        runs_root = safe_runs_root(runs_root)
    validate_manifest(plan)
    if type(max_calls) is not int or not 1 <= max_calls <= len(plan["jobs"]):
        raise IntegrityError("An explicit positive stage-bounded call budget is required")
    if stop_after is not None and (type(stop_after) is not int or stop_after < 1):
        raise IntegrityError("stop-after must be a positive invocation-local bound")
    reasons, jev_pin, predecessor = (prerequisites(plan, runs_root) if mode == "live" else
                                    ({name: None for name in plan["counts"]["by_adapter"]}, None, {}))
    report = preflight(plan, runs_root=runs_root) if mode == "live" else None
    if report and report["blocking_infrastructure"]:
        raise IntegrityError("Preflight blocked: " + ";".join(report["blocking_infrastructure"]))
    present = report["credentials"] if report else {}
    scope = {
        "schema": VERSION + "-run", "manifest_sha256": plan["manifest_sha256"], "mode": mode,
        "stage": stage, "selected_job_ids": [j["job_id"] for j in plan["jobs"]],
        "max_live_calls": max_calls, "max_concurrency": 1, "execution_profile": plan["operator_execution"]["profile"],
        "predecessor_completion_sha256": predecessor,
        "mock_fixture": getattr(mock, "identity", OperatorMock.identity) if mode == "mock" else None,
    }
    runs_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = runs_root / stage
    registry = REGISTRY if mode == "live" else runs_root / ".mock_registry"
    if registry.is_symlink():
        raise IntegrityError("Reservation registry symlink")
    with locked(registry), locked(directory), interrupt_handlers():
        reservation = {"scope": scope, "output": str(directory.absolute())}
        reservation_file = registry / (plan["manifest_sha256"] + ".json")
        if reservation_file.exists():
            if load(reservation_file) != reservation:
                raise IntegrityError("Stage identity already reserved at another output or with another budget")
        else:
            immutable(reservation_file, reservation)
        if (directory / "run.json").exists():
            if load(directory / "run.json") != scope or load(directory / "manifest.json") != plan:
                raise IntegrityError("Run scope, budget, profile or manifest changed")
        else:
            immutable(directory / "run.json", scope)
            immutable(directory / "manifest.json", plan)
            immutable(directory / "authorisation.json", {
                "stage": stage, "mode": mode, "at": now(), "authorised_stage": authorised_stage,
                "lower_assurance_accepted": accept_lower_assurance, "instruments_approved": approve_instruments,
                "review_note": review_note, "instruments_sha256": plan["instruments_sha256"],
                "manifest_sha256": plan["manifest_sha256"], "automatic_stage_transition": False,
            })
        checkpoint_root = directory / "checkpoints"
        checkpoint_root.mkdir(mode=0o700, exist_ok=True)
        if checkpoint_root.is_symlink():
            raise IntegrityError("Checkpoint root symlink")
        ledger = Ledger(directory / "ledger.jsonl")
        if report:
            number = 1 + max((int(p.stem.rsplit("-", 1)[-1]) for p in directory.glob("preflight-*.json")), default=0)
            immutable(directory / f"preflight-{number:06d}.json", report)
        starts = {e["job_id"]: e["intent_sha256"] for e in ledger.events if e["event"] == "started"}
        finishes = {e["job_id"]: e["result_sha256"] for e in ledger.events
                    if e["event"] in ("completed", "recovered_completion")}
        used = sum(e.get("budget_reservation", 0) for e in ledger.events)
        source_manifest, members = corpus()
        if source_manifest != plan["source_manifest"]:
            raise IntegrityError("Frozen source manifest changed")
        jobs = {j["job_id"]: j for j in plan["jobs"]}
        results = {}
        new = reused = invocations = 0
        stopped = None
        mock = mock or (OperatorMock(plan) if mode == "mock" else None)
        for job in plan["jobs"]:
            ident, name = job["job_id"], adapter(job)
            folder = checkpoint_root / ident
            existing = _existing(folder, job, plan, ledger, starts, finishes)
            if existing is not None:
                expected_parents = {p: results[p]["checkpoint_sha256"] for p in job["dependencies"]}
                if (existing["status"] != "incomplete_attempt"
                        and existing["parent_checkpoint_sha256"] != expected_parents):
                    raise IntegrityError("Parent checkpoint lineage changed")
                results[ident] = existing
                reused += 1
                if job["kind"] == "adversary" and existing["status"] in SUCCESS:
                    identity = existing["model_identity"]["observed_model"]
                    if mode == "live" and identity:
                        if jev_pin and jev_pin != identity:
                            raise IntegrityError("Existing SystemOne identity drift")
                        jev_pin = identity
                continue
            parents = {p: results[p]["checkpoint_sha256"] for p in job["dependencies"]}
            blocked = any(results[p]["status"] not in SUCCESS for p in job["dependencies"])
            unsupported = (job["kind"] == "adversary" and job.get("adversary_contract", job["evidence_contract"])
                           not in plan["config"]["adversaries"][name]["evidence_contracts"])
            unavailable = reasons[name]
            if mode == "live" and not present[name]["present"]:
                unavailable = "missing_or_unsupported_scoped_credential"
            will_call = not (blocked or unsupported or unavailable)
            if will_call and (used >= max_calls or stop_after is not None and invocations >= stop_after):
                stopped = "budget_exhausted" if used >= max_calls else "operator_chunk_limit"
                break
            if shutil.disk_usage(directory).free < MIN_FREE_DURING_RUN:
                stopped = "low_storage_before_next_reservation"
                break
            folder.mkdir(mode=0o700, exist_ok=False)
            intent = {"schema": VERSION + "-intent", "job": job, "mode": mode,
                      "manifest_sha256": plan["manifest_sha256"], "parent_checkpoint_sha256": parents,
                      "execution_profile": plan["operator_execution"]["profile"],
                      "budget_reservation": int(will_call), "payload_state": "not_prepared",
                      "started_at": now()}
            immutable(folder / "intent.json", intent)
            ledger.append({"event": "started", "job_id": ident, "intent_sha256": sha256_file(folder / "intent.json"),
                           "budget_reservation": int(will_call)})
            starts[ident] = sha256_file(folder / "intent.json")
            used += int(will_call)
            response = Response(provenance={"transport_attempts": 0, "cli_invocations": 0})
            payload = parsed = challenge = previous = None
            attempt_launched = False
            source = members[job["input_member"]]
            schema_valid = None
            status, reason = "execution_failed", None
            try:
                if sha256(source) != job["input_sha256"]:
                    raise IntegrityError("Source bytes changed before preparation")
                if blocked:
                    status, reason = "blocked_parent", "Required immutable first attempt is unsuccessful or incomplete."
                elif unsupported:
                    status, reason = "unsupported_contract", "No supported frozen evidence contract; no substitute."
                elif unavailable:
                    status, reason = "adapter_unavailable", unavailable
                else:
                    parent = job["assessment_parent"]
                    previous = results[parent]["parsed"] if parent else None
                    challenge = results[job["challenge_parent"]]["parsed"] if job["challenge_parent"] else None
                    if job["kind"] == "generator":
                        payload = render_prompt(plan, job, source, previous, histories(job, results, jobs), challenge)
                    else:
                        if not previous["claims"]:
                            status, reason = "unsupported_contract", "Nonempty assessment claims required for a genuine challenge."
                        elif name == "carl_jev":
                            payload = build_request(plan, job, directory, members,
                                                    json_bytes(plan["source_manifest"]), "operator-" + ident)
                        else:
                            payload = challenge_request(plan, job, source, previous)
                immutable(folder / "payload.json", {"payload": payload})
                if payload is not None and reason is None:
                    invocations += 1
                    attempt_launched = True
                    response = mock.invoke(job, payload, previous) if mode == "mock" else invoke(
                        plan, job, payload, authorised=True)
                    if response.error:
                        status, reason = "execution_failed", response.error
                    elif job["kind"] == "generator":
                        observed = response.provenance.get("observed_model")
                        if mode == "live" and observed is not None and observed != job["generator_spec"]["model_id"]:
                            status, reason = "model_identity_mismatch", "No model substitution is permitted."
                        else:
                            parsed, reason = assessment(response.message.decode("utf-8"), job, previous)
                            schema_valid = parsed is not None
                            status = ("mock_ok" if mode == "mock" else "ok") if parsed is not None else "schema_invalid"
                    else:
                        parsed = strict_json(response.message)
                        if not isinstance(parsed, dict):
                            raise ValueError("Adversary must return an object")
                        observed = response.provenance.get("observed_model")
                        if mode == "live" and (not observed or jev_pin and observed != jev_pin):
                            parsed = None
                            status, reason = "model_identity_mismatch", "Missing or drifted SystemOne identity; no fallback."
                        else:
                            if mode == "live":
                                jev_pin = observed
                            schema_valid = True
                            status = "mock_ok" if mode == "mock" else "ok"
            except KeyboardInterrupt:
                response = Response(error="operator_interrupted_execution_unknown_no_retry",
                                    provenance={"transport_attempts": None, "partial_response": "not_available"})
                status, reason = "interrupted_attempt", response.error
                stopped = "operator_interrupt"
            except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
                status, reason = "execution_failed", "preparation_or_adapter_failure:" + type(exc).__name__
                response.error = response.error or reason
                if attempt_launched:
                    response.provenance.update(transport_attempts=None, execution_outcome="unknown_no_retry")
            if not (folder / "payload.json").exists():
                immutable(folder / "payload.json", {"payload": payload})
            if response.error and "operator_interrupted" in response.error:
                stopped = "operator_interrupt"
                status = "interrupted_attempt"
            immutable(folder / "raw.json", response.record())
            quotes = ([{"claim_id": claim["claim_id"], "quote": quote,
                        "exact_source_substring": quote in source.decode("utf-8")}
                       for claim in parsed["claims"] for quote in claim["evidence_quotes"]]
                      if parsed and job["kind"] == "generator" else [])
            record = {
                "schema": "mmmtap-checkpoint-v1", "job_id": ident, "mode": mode, "stage": stage,
                "manifest_sha256": plan["manifest_sha256"], "input_sha256": job["input_sha256"],
                "implementation_sha256": plan["implementation_sha256"], "instruments_sha256": plan["instruments_sha256"],
                "execution_profile": plan["operator_execution"]["profile"],
                "evidence_quality": ("mock_not_research" if mode == "mock" else
                                     plan["operator_execution"]["profile"]["evidence_quality"]),
                "satisfies_strict_isolation": False, "status": status, "reason": reason,
                "parsed": parsed, "schema_valid": schema_valid, "quote_audit": quotes,
                "parent_checkpoint_sha256": parents, "payload_sha256": digest(payload),
                "challenge_used": challenge, "model_identity": _identity(plan, job, response),
                "metrics": usage_metrics(response, mode, plan["config"]),
                "correctness": "not_adjudicated", "completed_at": now(),
                "artifact_sha256": {n: sha256_file(folder / n) for n in ("intent.json", "payload.json", "raw.json")},
            }
            immutable(folder / "result.json", record)
            result_hash = sha256_file(folder / "result.json")
            ledger.append({"event": "completed", "job_id": ident, "result_sha256": result_hash, "status": status})
            finishes[ident] = result_hash
            folder.chmod(0o500)
            results[ident] = {**record, "checkpoint_sha256": result_hash}
            new += 1
            if stopped or mode == "live" and status in ("execution_failed", "schema_invalid", "model_identity_mismatch"):
                stopped = stopped or "first_attempt_failure_requires_deliberate_resume"
                break
        counts = dict(collections.Counter(r["status"] for r in results.values()))
        if len(results) < len(plan["jobs"]):
            counts["not_attempted"] = len(plan["jobs"]) - len(results)
        summary = {
            "schema": VERSION + "-summary", "stage": stage, "mode": mode,
            "manifest_sha256": plan["manifest_sha256"], "execution_profile": plan["operator_execution"]["profile"],
            "evidence_quality": "mock_not_research" if mode == "mock" else "lower_assurance_operator_supervised_research",
            "satisfies_strict_isolation": False, "selected_jobs": len(plan["jobs"]), "new_checkpoints": new,
            "preserved_checkpoints": reused, "adapter_attempt_reservations": used, "maximum_call_budget": max_calls,
            "invocations_this_session": invocations, "status_counts": counts, "stopped_reason": stopped,
            "complete": len(results) == len(plan["jobs"]), "automatic_next_stage": False,
            "output_directory": str(directory), "provider_calls": 0 if mode == "mock" else "see_individual_receipts",
        }
        ledger.append({"event": "session_summary", "summary": summary})
        immutable(directory / f"summary-{len(ledger.events):06d}.json", summary)
        if summary["complete"]:
            completion = {
                "manifest_sha256": plan["manifest_sha256"], "mode": mode,
                "execution_profile": plan["operator_execution"]["profile"],
                "outcomes": {ident: {"status": row["status"], "result_sha256": row["checkpoint_sha256"]}
                             for ident, row in results.items()},
                "adapter_attempt_reservations": used,
            }
            path = directory / "completion.json"
            if path.exists():
                if load(path) != completion:
                    raise IntegrityError("Completed stage changed")
            else:
                immutable(path, completion)
            anchors = [e["sha256"] for e in ledger.events if e["event"] == "stage_completion"]
            if anchors and anchors != [sha256_file(path)]:
                raise IntegrityError("Stage completion anchor changed")
            if not anchors:
                ledger.append({"event": "stage_completion", "sha256": sha256_file(path)})
        return summary
