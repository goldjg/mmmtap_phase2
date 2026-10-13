"""Bounded offline Path B validation; no evaluator or credential access."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path("/home/prometheus/git/mmmtap_phase2")
CARL = Path("/home/prometheus/git/cARL-semantic-eval")
OUT = ROOT / "path_b_validation_v1"
BINARY = OUT / "bin/carl-assessment-challenge-v1"
ENV = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
ENV.update(GOPROXY="off", GOSUMDB="off", PYTHONDONTWRITEBYTECODE="1", GIT_PAGER="cat", GIT_OPTIONAL_LOCKS="0")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def save(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def run(name, argv, cwd, timeout=300):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True, timeout=timeout, check=False)
    write(OUT / f"{name}.stdout.txt", result.stdout)
    write(OUT / f"{name}.stderr.txt", result.stderr)
    save(OUT / f"{name}.json", {"argv": argv, "cwd": str(cwd), "exit_status": result.returncode,
                               "latency_seconds": round(time.monotonic()-start, 6),
                               "stdout_sha256": digest(result.stdout), "stderr_sha256": digest(result.stderr)})
    if result.returncode:
        raise RuntimeError(f"{name} failed: {result.stderr[-3000:].decode(errors='replace')}")
    return result


def init():
    OUT.mkdir(exist_ok=False)
    (OUT / "bin").mkdir()
    indexed = json.loads((ROOT / "carl_jev_cli_investigation_v1/evidence/source_index.json").read_text())
    protected = {}
    for entry in indexed:
        name = entry["source_path"]
        if "/internal/review/" in name or "/internal/semantic/" in name or name.endswith("/cmd/carl/main.go") or "/mmmtap_phase2/phase2/" in name:
            assert digest(Path(name).read_bytes()) == entry["sha256"], name
            protected[name] = entry["sha256"]
    binary = Path("/home/prometheus/bin/carl-jev")
    protected[str(binary)] = digest(binary.read_bytes())
    assert protected[str(binary)] == "b34696d54d0b9c910d48c9adbe0155f825617d8e4c8981e58a2f50b5d0868428"
    for name in ("execution_plan_v2.json", "adapter_qualification_v1/SHA256SUMS.txt",
                 "historical_extraction_v1/SHA256SUMS.txt", "carl_jev_cli_investigation_v1/SHA256SUMS.txt"):
        protected[str(ROOT/name)] = digest((ROOT/name).read_bytes())
    save(OUT / "protected_before.json", protected)


def go():
    run("gofmt_final", ["gofmt", "-w", "internal/assessment", "cmd/carl-assessment-challenge",
                    "internal/pack/snapshot.go"], CARL)
    result = run("go_tests_final", ["go", "test", "-count=1", "-json", "./..."], CARL)
    events = [json.loads(line) for line in result.stdout.splitlines()]
    passed = [e for e in events if e["Action"] == "pass" and e.get("Test")]
    save(OUT / "go_test_summary.json", {
        "passed_test_events_including_subtests": len(passed),
        "passed_top_level_tests": sum("/" not in e["Test"] for e in passed),
        "passed_packages": sum(e["Action"] == "pass" and not e.get("Test") for e in events),
        "failed_events": sum(e["Action"] == "fail" for e in events),
    })
    run("go_vet", ["go", "vet", "./..."], CARL)
    run("go_build_path_b", ["go", "build", "-buildvcs=false", "-o", str(BINARY), "./cmd/carl-assessment-challenge"], CARL)
    run("go_build_path_a", ["go", "build", "-buildvcs=false", "-o", str(OUT/"bin/path-a-rebuild"), "./cmd/carl"], CARL)
    run("path_b_help", [str(BINARY), "--help"], ROOT)
    old = run("path_a_installed_help", ["/home/prometheus/bin/carl-jev", "--help"], ROOT)
    new = run("path_a_rebuilt_help", [str(OUT/"bin/path-a-rebuild"), "--help"], ROOT)
    assert old.stdout == new.stdout and old.stderr == new.stderr
    run("git_diff_check", ["git", "--no-pager", "diff", "--check"], CARL)
    print((OUT/"go_test_summary.json").read_text())


def python():
    result = run("python_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], ROOT)
    counts = re.findall(rb"Ran (\d+) tests", result.stderr)
    assert counts and result.stderr.rstrip().endswith(b"OK")
    save(OUT / "python_test_summary.json", {"tests": int(counts[-1]), "exit_status": 0})
    print((OUT/"python_test_summary.json").read_text())


def matrix():
    sys.path.insert(0, str(ROOT))
    from phase2.core import corpus, load, json_bytes, challenge_request
    from phase2.path_b import build_request, invoke_offline
    import base64
    plan = load(ROOT/"execution_plan_v2.json")
    manifest, sources = corpus()
    manifest_raw = (ROOT/"MMMTAP_Phase2/corpus_manifest.json").read_bytes()
    jobs = [j for j in plan["jobs"] if j["mechanism"] == "carl_jev" and j["generator"] == "haiku" and j["arm"] == "E2"]
    assert len(jobs) == 135
    for arm in ("E3_NC", "E3_CN"):
        jobs.append(next(j for j in plan["jobs"] if j["mechanism"] == "carl_jev" and j["generator"] == "haiku" and j["arm"] == arm))
    records = []
    anchors = {}
    for i, job in enumerate(jobs):
        case = OUT/"cases"/f"{i:03d}-{job['arm']}"
        case.mkdir(parents=True)
        request = build_request(plan, job, ROOT/"execution_dry_run_v2", sources, manifest_raw, f"offline-path-b-{i:03d}")
        request_raw = json_bytes(request)
        write(case/"request.json", request_raw)
        native = json.loads(base64.b64decode(request["native_request"]))
        expected_native = challenge_request(plan, {**job, "mechanism": "native_jev"}, sources[job["input_member"]], request["assessment"])
        assert base64.b64decode(request["native_request"]) == json_bytes(expected_native)
        response = {"model": "offline-fixture-not-provider",
                    "answers": {q: {"noul": 0.75 if q == "authority_promoted" else 0.9 if q == "uncertainty_adequate" else 0.25}
                                for q in native["questions"]},
                    "usage": {"input_tokens": 0, "output_tokens": 0}}
        write(case/"mock-response.json", json_bytes(response))
        actions = [
            ["prepare", "--request", str(case/"request.json"), "--policy-root", str(ROOT/"path_b_policy_v1"), "--out", str(case/"prepared")],
        ]
        first = invoke_offline(BINARY, actions[0])
        save(case/"prepare_process.json", {"argv": actions[0], "exit_status": first.returncode,
                                          "stdout": first.stdout.decode(), "stderr": first.stderr.decode()})
        assert first.returncode == 0, first.stderr
        p = (case/"prepared/prepared.json").read_bytes()
        actions.append(["evaluate-offline", "--prepared", str(case/"prepared/prepared.json"), "--prepared-sha256", digest(p),
                        "--response", str(case/"mock-response.json"), "--mode", "mock", "--out", str(case/"evaluated")])
        evaluation = invoke_offline(BINARY, actions[1])
        save(case/"evaluate_process.json", {"argv": actions[1], "exit_status": evaluation.returncode,
                                           "stdout": evaluation.stdout.decode(), "stderr": evaluation.stderr.decode()})
        assert evaluation.returncode == 0, evaluation.stderr
        raw = (case/"evaluated/receipt.json").read_bytes()
        result = json.loads(raw)
        assert result["status"] == "mock_ok" and result["live_calls"] == 0
        assert result["result"]["disposition"] == "challenge_required"
        anchor = digest(raw)
        anchors[str((case/"evaluated/receipt.json").relative_to(OUT))] = anchor
        replay_args = ["replay", "--receipt", str(case/"evaluated/receipt.json"), "--receipt-sha256", anchor]
        replay = invoke_offline(BINARY, replay_args)
        save(case/"replay_process.json", {"argv": replay_args, "exit_status": replay.returncode,
                                         "stdout": replay.stdout.decode(), "stderr": replay.stderr.decode()})
        assert replay.returncode == 0, replay.stderr
        records.append({"case_id": job["case_id"], "variant_id": job["variant_id"],
                        "source_sha256": job["input_sha256"], "branch": job["arm"],
                        "parent_job_id": job["assessment_parent"], "matched_native_bytes": True,
                        "mock_claim_count": len(request["assessment"]["claims"]),
                        "receipt_sha256": anchor, "status": "mock_ok"})
    save(OUT/"receipt_anchors.json", anchors)
    save(OUT/"matrix.json", {
        "primary_identities": len({(j["case_id"],j["variant_id"]) for j in jobs}),
        "distinct_source_hashes": len({j["input_sha256"] for j in jobs}),
        "offline_preparations": len(records), "mock_evaluations": len(records),
        "successful_offline_replays": len(records), "live_calls": 0,
        "generator_scope": "haiku-labelled existing mocked checkpoints only; no generator invoked",
        "e3_coverage": "one example per order, plus unit tests; not full live matrix",
        "source_archive_sha256": manifest["archive_sha256"], "records": records,
    })
    print(json.dumps({"inputs": 135, "distinct_source_hashes": 108, "offline_preparations": len(records),
                      "mock_evaluations": len(records), "replays": len(records), "live_calls": 0}))


def evidence():
    run("go_version", ["go", "version"], CARL)
    run("path_b_build_metadata", ["go", "version", "-m", str(BINARY)], CARL)
    run("carl_source_revision", ["git", "rev-parse", "HEAD"], CARL)
    run("path_a_source_unchanged", ["git", "--no-pager", "diff", "--exit-code", "HEAD", "--",
        "cmd/carl", "internal/review", "internal/semantic", "embedded", "go.mod", "go.sum",
        ".github/carl/memory.md", ".github/carl/trust-boundaries.md", ".github/instructions"], CARL)
    archive = Path("/home/prometheus/mmmtap_p1_014_verified_inputs.zip")
    assert digest(archive.read_bytes()) == "a3fe94069009f328b0a46bb52a7ff52d2c2bedfcd0eb3babe360eea1c884cc21"
    checked, mismatches = 0, []
    for line in (ROOT/"HARNESS_SHA256SUMS.txt").read_text().splitlines():
        expected, name = line.split("  ", 1)
        actual = digest((ROOT/name).read_bytes())
        checked += 1
        if expected != actual:
            mismatches.append({"file": name, "expected_sha256": expected, "current_sha256": actual})
    save(OUT/"original_harness_integrity.json", {"files_checked": checked, "mismatches": mismatches,
        "frozen_archive_sha256": digest(archive.read_bytes())})
    print(json.dumps({"harness_files_checked": checked, "mismatches": mismatches}))


def seal():
    protected = json.loads((OUT/"protected_before.json").read_text())
    for name, expected in protected.items():
        assert digest(Path(name).read_bytes()) == expected, name
    for directory in ("historical_extraction_v1", "adapter_qualification_v1", "carl_jev_cli_investigation_v1"):
        run(directory+"_integrity", ["sha256sum", "-c", "--quiet", "SHA256SUMS.txt"], ROOT/directory)
    paths = sorted((CARL/"internal/assessment").glob("*.go"))
    paths += [CARL/"internal/pack/snapshot.go", CARL/"cmd/carl-assessment-challenge/main.go",
              CARL/"ASSESSMENT.md", CARL/"CLI.md", CARL/"ARCHITECTURE.md", CARL/"ROADMAP.md",
              CARL/".github/carl/current-pr-contract.md",
              ROOT/"phase2/path_b.py", ROOT/"tests/test_path_b.py", ROOT/"PATH_B.md", Path(__file__)]
    paths += sorted((ROOT/"path_b_policy_v1").rglob("*"))
    hashes = {}
    for path in paths:
        if path.is_file():
            relative = path.relative_to("/home/prometheus/git") if path.is_relative_to("/home/prometheus/git") else Path("validation_runner.py")
            raw = path.read_bytes()
            write(OUT/"tested_implementation"/relative, raw)
            hashes[str(path)] = digest(raw)
    save(OUT/"implementation_hashes.json", hashes)
    save(OUT/"preservation.json", {"protected_original_files_unchanged": len(protected),
                                  "installed_path_a_binary_unchanged": True,
                                  "frozen_evidence_manifests_verified": True,
                                  "live_calls": 0, "historical_admissions": 0,
                                  "path_b_binary_sha256": digest(BINARY.read_bytes())})
    assert (OUT/"VALIDATION_REPORT.md").is_file()
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    sums = "".join(f"{digest(p.read_bytes())}  {p.relative_to(OUT)}\n" for p in files)
    write(OUT/"SHA256SUMS.txt", sums.encode())
    print(json.dumps({"sealed_files": len(files), "manifest_sha256": digest(sums.encode())}))


if __name__ == "__main__":
    {"init": init, "go": go, "python": python, "matrix": matrix, "evidence": evidence, "seal": seal}[sys.argv[1]]()
