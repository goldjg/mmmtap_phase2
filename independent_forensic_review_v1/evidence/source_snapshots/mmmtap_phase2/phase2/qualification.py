"""Bounded qualification only: no experimental execution or automatic retries."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from historical_extractor.archive import IntegrityError, file_hash, sha256
from .adapters import (
    GeminiAdapter, HaikuAdapter, NativeJEVAdapter, Response, SolAdapter,
    codex_overrides, executable,
)
from .core import ROOT, assessment, challenge_request, corpus, digest, load, render_prompt, write_new
from .engine import Ledger, locked, now


ADAPTERS = ("haiku", "gemini", "sol", "native_jev", "carl_jev")
SOURCE = b'def greeting(name: str) -> str:\n    return "Hello, " + name\n'


def audit_plan(plan: dict, source: dict) -> dict:
    if plan["manifest_sha256"] != digest({k: v for k, v in plan.items() if k != "manifest_sha256"}):
        raise IntegrityError("Original plan hash mismatch")
    expected = {(i["case_id"], i["variant_id"]): i for i in source["items"]}
    jobs = {}
    groups = {}
    consumers = Counter()
    statuses = {}
    arm_counts = {}
    for job in plan["jobs"]:
        ident = job["job_id"]
        identity_fields = {k: v for k, v in job.items() if k not in
                           ("job_id", "checkpoint", "parent_checkpoint")}
        if digest(identity_fields) != ident or ident in jobs:
            raise IntegrityError("Invalid or duplicate job identity")
        item = expected[(job["case_id"], job["variant_id"])]
        if job["input_sha256"] != item["input_sha256"] or job["input_member"] != item["input_member"]:
            raise IntegrityError("Frozen input mismatch")
        group_id = (job["case_id"], job["variant_id"], job["generator"], job["repetition"])
        groups.setdefault(group_id, []).append(job)
        for parent in job["dependencies"]:
            other = jobs[parent]
            if any(other[k] != job[k] for k in ("case_id", "variant_id", "generator", "repetition")):
                raise IntegrityError("Cross-group lineage")
            if other["arm"] not in ("B0", job["arm"]):
                raise IntegrityError("Cross-arm lineage")
        if job["challenge_parent"]:
            parent = jobs[job["challenge_parent"]]
            if parent["kind"] != "adversary" or parent["assessment_parent"] != job["assessment_parent"]:
                raise IntegrityError("Challenge attached to wrong assessment")
            consumers[parent["job_id"]] += 1
        status = "unsupported_contract" if job["mechanism"] == "carl_jev" else (
            "blocked_parent" if any(statuses[p] != "contract_executable" for p in job["dependencies"])
            else "contract_executable")
        statuses[ident] = status
        counts = arm_counts.setdefault(job["arm"], Counter())
        counts[job["kind"] + "_jobs"] += 1
        counts[status] += 1
        jobs[ident] = job
    for group in groups.values():
        b0 = [j for j in group if j["arm"] == "B0"]
        if len(b0) != 1 or b0[0]["dependencies"] or len(group) != 17:
            raise IntegrityError("B0/group shape mismatch")
        for job in group:
            if job["turn"] == 1 and job["assessment_parent"] != b0[0]["job_id"]:
                raise IntegrityError("First follow-up not from B0")
        for arm, sequence in (("E1", ["native_jev"]), ("E2", ["carl_jev"]),
                              ("E3_NC", ["native_jev", "carl_jev"]),
                              ("E3_CN", ["carl_jev", "native_jev"])):
            branch = [j for j in group if j["arm"] == arm]
            if [j["mechanism"] for j in branch if j["kind"] == "adversary"] != sequence:
                raise IntegrityError("Challenge ordering mismatch")
            generated = [j for j in branch if j["kind"] == "generator"]
            if len(generated) == 2 and generated[1]["assessment_parent"] != generated[0]["job_id"]:
                raise IntegrityError("Sequential branch parent mismatch")
        c3 = [j for j in group if j["arm"] == "C3"]
        if (len(c3) != 2 or [j["turn"] for j in c3] != [1, 2]
                or c3[1]["assessment_parent"] != c3[0]["job_id"]
                or any(j["challenge_parent"] or j["mechanism"] for j in c3)):
            raise IntegrityError("Matched-turn control mismatch")
    if any(consumers[j["job_id"]] != 1 for j in jobs.values() if j["kind"] == "adversary"):
        raise IntegrityError("Adversarial output reused or orphaned")
    counts = Counter(statuses.values())
    if len(groups) != 405 or len(jobs) != 6885 or counts != {
        "contract_executable": 3645, "unsupported_contract": 1215, "blocked_parent": 2025
    }:
        raise IntegrityError("Full experimental matrix mismatch")
    return {"manifest_sha256": plan["manifest_sha256"], "inputs": len(expected),
            "distinct_input_hashes": len({i["input_sha256"] for i in expected.values()}),
            "jobs": len(jobs), "b0_groups": len(groups), "generator_jobs": 4455,
            "adversary_jobs": 2430, "statuses_if_all_compatible_adapters_qualify": dict(counts),
            "by_arm": {k: dict(v) for k, v in arm_counts.items()},
            "adversarial_results_reused_across_branches": 0,
            "note": "Contract feasibility only; not live readiness. Original schedule is not time-randomised."}


def capture_command(out: Path, name: str, argv: list[str], **kwargs) -> dict:
    result = subprocess.run(argv, capture_output=True, timeout=40, check=False, **kwargs)
    row = {"argv": argv, "exit_status": result.returncode,
           "stdout": result.stdout.decode("utf-8", "replace"),
           "stderr": result.stderr.decode("utf-8", "replace"), "inference_calls": 0}
    write_new(out / (name + ".json"), row)
    return row


def offline_extra(directory: Path) -> None:
    out = directory / "offline"
    for name, argv in {
        "codex_prompt_input_help": ["codex", "debug", "prompt-input", "--help"],
        "codex_models_help": ["codex", "debug", "models", "--help"],
        "copilot_permissions_help": ["copilot", "help", "permissions"],
    }.items():
        capture_command(out, name, argv)
    with tempfile.TemporaryDirectory(prefix="mmmtap-sandbox-check-") as tmp:
        env = {"PATH": os.environ["PATH"], "HOME": tmp, "CODEX_HOME": tmp + "/codex"}
        script = (
            "from pathlib import Path; import errno\n"
            "denied=False\n"
            "try:Path('sandbox-write-check').write_text('trusted qualification probe')\n"
            "except OSError as e:denied=e.errno in (errno.EPERM,errno.EACCES,errno.EROFS)\n"
            "print('write_denied='+str(denied)); raise SystemExit(0 if denied else 3)"
        )
        capture_command(out, "codex_read_only_enforcement",
                        ["codex", "sandbox", "-c", 'sandbox_mode="read-only"', "--", sys.executable, "-c", script],
                        cwd=tmp, env=env)
        capture_command(out, "codex_strict_feature_validation",
                        ["codex", "--strict-config", *codex_overrides(), "features", "list"], cwd=tmp, env=env)
    source, _ = corpus()
    write_new(out / "comparability_audit.json", audit_plan(load(ROOT / "execution_plan_v2.json"), source))


def offline_runtime(directory: Path) -> None:
    out = directory / "offline"
    with tempfile.TemporaryDirectory(prefix="mmmtap-runtime-check-") as tmp:
        home = Path(tmp) / "home"
        cwd = Path(tmp) / "work"
        home.mkdir()
        cwd.mkdir()
        (home / "codex").mkdir()
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(home / "codex")}
        script = (
            "from pathlib import Path; import errno\n"
            "denied=False\n"
            "try:Path('sandbox-write-check').write_text('trusted qualification probe')\n"
            "except OSError as e:denied=e.errno in (errno.EPERM,errno.EACCES,errno.EROFS)\n"
            "print('write_denied='+str(denied)); raise SystemExit(0 if denied else 3)"
        )
        capture_command(out, "codex_read_only_enforcement_v2",
                        ["codex", "sandbox", "-c", 'sandbox_mode="read-only"', "--", sys.executable, "-c", script],
                        cwd=cwd, env=env)
        capture_command(out, "codex_feature_validation_v2",
                        ["codex", *codex_overrides(), "features", "list"], cwd=cwd, env=env)
        sentinel = "MMMTAP_INHERITED_INSTRUCTION_SENTINEL_DO_NOT_LOAD"
        (home / "AGENTS.md").write_text(sentinel)
        (home / "codex/AGENTS.md").write_text(sentinel)
        (cwd / "AGENTS.md").write_text(sentinel)
        capture_command(out, "codex_prompt_isolation",
                        ["codex", *codex_overrides(), "-c", 'model="gpt-6.1-sol"',
                         "-c", 'model_reasoning_effort="low"', "-c", 'sandbox_mode="read-only"',
                         "debug", "prompt-input", "Benign qualification metadata. Do not run tools."],
                        cwd=cwd, env=env)


def offline_diagnostics(directory: Path) -> None:
    out = directory / "offline"
    # Diagnostic subset only: omitting unsupported retry overrides does not authorise live Sol.
    flags = codex_overrides()
    diagnostic = [part for index in range(0, len(flags), 2)
                  if not flags[index + 1].startswith("model_providers.")
                  for part in flags[index:index + 2]]
    with tempfile.TemporaryDirectory(prefix=".qualification-runtime-", dir=ROOT) as tmp:
        home, cwd = Path(tmp) / "home", Path(tmp) / "work"
        home.mkdir()
        cwd.mkdir()
        (home / "codex").mkdir()
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(home / "codex")}
        script = ("from pathlib import Path; import errno\n"
                  "try:Path('write-probe').write_text('trusted qualification probe')\n"
                  "except OSError as e:print('write_denied',e.errno);raise SystemExit(0 if e.errno in (1,13,30) else 2)\n"
                  "raise SystemExit(3)")
        capture_command(out, "codex_read_only_enforcement_v3",
                        ["codex", "sandbox", "-c", 'sandbox_mode="read-only"', "--", sys.executable, "-c", script],
                        cwd=cwd, env=env)
        capture_command(out, "codex_features_without_retry_overrides",
                        ["codex", *diagnostic, "features", "list"], cwd=cwd, env=env)
        sentinel = "MMMTAP_INHERITED_INSTRUCTION_SENTINEL_DO_NOT_LOAD"
        (home / "codex/AGENTS.md").write_text(sentinel)
        (cwd / "AGENTS.md").write_text(sentinel)
        capture_command(out, "codex_prompt_isolation_without_retry_overrides",
                        ["codex", *diagnostic, "-c", 'model="gpt-6.1-sol"',
                        "-c", 'model_reasoning_effort="low"', "-c", 'sandbox_mode="read-only"',
                        "debug", "prompt-input", "Benign qualification metadata. Do not run tools."],
                        cwd=cwd, env=env)
    capture_command(out, "carl_authentic_git_dry_run",
                    [str(Path.home() / "bin/carl-jev"), "review", "--dry-run", "--format", "json",
                     "--base", "e725f6f5e89a0225b79a033dbc8b21219179f361",
                     "--head", "8938d62d77e8c0d68eaa824bf35dfb577e0e757c"],
                    cwd=ROOT.parent / "cARL")


def fixture(plan: dict, name: str) -> tuple[dict, object]:
    job = {"partition": "adapter_qualification_only", "case_id": "qualification-benign-greeting-v1",
           "variant_id": "baseline", "input_sha256": sha256(SOURCE),
           "input_member": "inline:qualification-source", "template_key": "B0",
           "kind": "generator", "generator": name}
    if name == "native_jev":
        job.update(kind="adversary", mechanism=name)
        previous = {"case_id": job["case_id"], "variant_id": "baseline",
                    "claims": [{"claim_id": "return_value", "claim": "The function returns a greeting string.",
                                "evidence_quotes": ['return "Hello, " + name'], "confidence": 1.0,
                                "limitations": ["Qualification fixture claim, not a historical/model result."]}],
                    "disposition": "pass", "changes": [], "uncertainties": ["Only supplied static source is known."]}
        payload = challenge_request(plan, job, SOURCE, previous)
        payload["questions"]["side_effect_choice"] = {
            "type": "choice", "instructions": "Which side effect is explicitly implemented in the supplied source?",
            "criteria": {"none": "No file or network operation", "file_write": "Writes a file", "network": "Sends a network request"}}
        return job, payload
    return job, render_prompt(plan, job, SOURCE, None, [], None)


def freeze_manifest(directory: Path, compatible: list[str]) -> dict:
    if any(n not in ADAPTERS or n == "carl_jev" for n in compatible) or len(set(compatible)) != len(compatible):
        raise IntegrityError("No compatible authenticated cARL fixture admitted")
    plan = load(ROOT / "execution_plan_v2.json")
    config = deepcopy(plan["config"])
    config["timeout_seconds"] = 60
    config["max_response_bytes"] = 524288
    entries = {}
    for name in ADAPTERS:
        job, payload = fixture(plan, name)
        spec = {**config["generators"], **config["adversaries"]}[name]
        binary = executable(spec)
        entries[name] = {"compatible": name in compatible, "requested_model": spec["model_id"],
                         "job": job, "payload": payload, "payload_sha256": digest(payload),
                         "binary_sha256": file_hash(Path(binary)) if binary else None}
    manifest = {"schema": "mmmtap-adapter-qualification-smokes-v1", "purpose": "qualification_not_experiment",
                "max_live_invocations": 5, "max_attempts_per_adapter": 1, "automatic_retries": False,
                "original_plan_sha256": plan["manifest_sha256"], "config": config,
                "source_text": SOURCE.decode(), "source_sha256": sha256(SOURCE),
                "software_sha256": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
                "entries": entries, "frozen_at": now()}
    manifest["manifest_sha256"] = digest(manifest)
    write_new(directory / "live_smoke_manifest.json", manifest)
    return manifest


def invoke_once(directory: Path, name: str, *, authorised: bool) -> dict:
    if not authorised:
        raise IntegrityError("Explicit smoke authorisation required")
    manifest = load(directory / "live_smoke_manifest.json")
    if digest({k: v for k, v in manifest.items() if k != "manifest_sha256"}) != manifest["manifest_sha256"]:
        raise IntegrityError("Qualification manifest changed")
    for filename, expected in manifest["software_sha256"].items():
        if file_hash(Path(__file__).parent / filename) != expected:
            raise IntegrityError("Qualification software changed")
    entry = manifest["entries"][name]
    if not entry["compatible"]:
        raise IntegrityError("Adapter blocked by offline qualification; no invocation")
    config = manifest["config"]
    spec = {**config["generators"], **config["adversaries"]}[name]
    binary = executable(spec)
    if binary and file_hash(Path(binary)) != entry["binary_sha256"]:
        raise IntegrityError("Qualified executable changed")
    with locked(directory / "attempts"):
        ledger = Ledger(directory / "attempts/ledger.jsonl")
        if sum(e.get("live_reservation", 0) for e in ledger.events) >= 5:
            raise IntegrityError("Five-call qualification budget exhausted")
        folder = directory / "attempts" / name
        folder.mkdir(mode=0o700, exist_ok=False)
        write_new(folder / "intent.json", {"adapter": name, "manifest_sha256": manifest["manifest_sha256"],
                                          "live_reservation": 1, "payload_sha256": entry["payload_sha256"],
                                          "started_at": now(), "purpose": "qualification_not_experiment"})
        ledger.append({"event": "reserved", "adapter": name, "live_reservation": 1,
                       "intent_sha256": file_hash(folder / "intent.json")})
        credential = None
        previous_token = os.environ.get("COPILOT_GITHUB_TOKEN")
        try:
            if name in ("haiku", "gemini"):
                # Credential material is kept only in memory, never in the output directory.
                proc = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"],
                                      capture_output=True, timeout=20, check=False)
                if proc.returncode or not proc.stdout.strip():
                    raise IntegrityError("Previously discovered GitHub credential unavailable")
                credential = proc.stdout.decode().strip()
                os.environ["COPILOT_GITHUB_TOKEN"] = credential
            if name == "native_jev":
                response = NativeJEVAdapter(spec, config).invoke(entry["payload"], "frozen_text_assessment_v1", authorised=True)
            else:
                cls = {"haiku": HaikuAdapter, "gemini": GeminiAdapter, "sol": SolAdapter}[name]
                response = cls(spec, config).invoke(entry["payload"], authorised=True)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            response = Response(error="qualification_adapter_exception:" + type(exc).__name__)
        finally:
            if credential is not None:
                if previous_token is None:
                    os.environ.pop("COPILOT_GITHUB_TOKEN", None)
                else:
                    os.environ["COPILOT_GITHUB_TOKEN"] = previous_token
        if response.provenance.get("mock") or response.provenance.get("mode") == "mock":
            response.error = "mock_response_forbidden_in_live_qualification"
        write_new(folder / "raw.json", response.record())
        parsed, parser_error = None, response.error
        if not parser_error:
            try:
                if name == "native_jev":
                    from historical_extractor.extract import strict_json
                    parsed = strict_json(response.message)
                else:
                    parsed, parser_error = assessment(response.message.decode("utf-8", "strict"), entry["job"])
            except (ValueError, UnicodeError, TypeError, KeyError) as exc:
                parsed, parser_error = None, "qualification_parser:" + type(exc).__name__
        result = {"schema": "mmmtap-qualification-result-v1", "adapter": name, "mode": "live_smoke",
                  "purpose": "qualification_not_experiment", "status": "ok" if parsed is not None else "failed",
                  "parsed": parsed, "parser_error": parser_error, "exit_status": response.exit_status,
                  "latency_seconds": response.latency_seconds, "usage": response.usage,
                  "requested_model": spec["model_id"], "reasoning_effort": spec.get("reasoning_effort"),
                  "reported_model": response.provenance.get("observed_model"),
                  "provider_confirmed_model": response.provenance.get("observed_model") if name == "native_jev" else None,
                  "identity_basis": "provider_response_model_field" if name == "native_jev" else "CLI_events",
                  "transport_attempts": response.provenance.get("transport_attempts", 0),
                  "manifest_sha256": manifest["manifest_sha256"], "raw_sha256": file_hash(folder / "raw.json"),
                  "completed_at": now()}
        write_new(folder / "result.json", result)
        ledger.append({"event": "completed", "adapter": name, "result_sha256": file_hash(folder / "result.json")})
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("offline-extra", "offline-runtime", "offline-diagnostics", "freeze", "smoke"))
    parser.add_argument("--directory", type=Path, default=ROOT / "adapter_qualification_v1")
    parser.add_argument("--compatible", nargs="*", choices=ADAPTERS, default=[])
    parser.add_argument("--adapter", choices=ADAPTERS)
    parser.add_argument("--authorize-live", action="store_true")
    args = parser.parse_args()
    if args.command == "offline-extra":
        offline_extra(args.directory)
        print("Offline qualification metadata captured; no inference.")
    elif args.command == "offline-runtime":
        offline_runtime(args.directory)
        print("Offline runtime probes recorded; no inference.")
    elif args.command == "offline-diagnostics":
        offline_diagnostics(args.directory)
        print("Additional offline diagnoses recorded; no inference.")
    elif args.command == "freeze":
        result = freeze_manifest(args.directory, args.compatible)
        print("Frozen smoke manifest:", result["manifest_sha256"])
    else:
        if args.adapter is None:
            parser.error("--adapter required")
        result = invoke_once(args.directory, args.adapter, authorised=args.authorize_live)
        print({k: result[k] for k in ("adapter", "status", "parser_error", "exit_status", "latency_seconds",
                                      "requested_model", "reported_model", "provider_confirmed_model", "transport_attempts")})


if __name__ == "__main__":
    main()
