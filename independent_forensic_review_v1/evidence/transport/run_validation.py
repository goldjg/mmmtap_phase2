import hashlib
import json
import os
from pathlib import Path
import subprocess

E = Path(__file__).resolve().parent
R = Path("/home/prometheus/git/cARL-semantic-eval")
M = Path("/home/prometheus/git/mmmtap_phase2")
for n in ("work", "cache", "modcache", "home"):
    (E / n).mkdir(exist_ok=True)
env = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": str(E / "home"), "LANG": "C.UTF-8",
    "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local",
    "GOFLAGS": "-buildvcs=false", "GOCACHE": str(E / "cache"),
    "GOMODCACHE": str(E / "modcache"), "TMPDIR": str(E / "work"),
    "GOTMPDIR": str(E / "work"), "JEVKEY": "",
    "GOTELEMETRY": "off",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
}
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(name, argv, isolated=False):
    name = "v2_" + name
    if isolated:
        argv = ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--bind", str(E), str(E),
                "--dev", "/dev", "--proc", "/proc", "--unshare-net", "--die-with-parent", "--", *argv]
    with (E / (name + ".stdout")).open("wb") as out, (E / (name + ".stderr")).open("wb") as err:
        p = subprocess.run(argv, cwd=R, env=env, stdout=out, stderr=err)
    print(name, p.returncode, flush=True)
    return {"argv": argv, "exit_code": p.returncode}

tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=R).decode().split("\0")
tracked = [p for p in tracked if p]
head_diff = []
for name in tracked:
    original = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=R)
    if original != (R / name).read_bytes():
        head_diff.append(name)
baseline = json.loads((M / "integration_readiness_v1/go_validation/baseline.json").read_text())
protected = {n: sha(Path(n)) == h for n, h in baseline["protected_sha256"].items()}
meta = json.loads((M / "integration_readiness_v1/go_validation/build_metadata.json").read_text())
sources = {n: sha(R / n) == h for n, h in meta["source_go_sha256"].items()}
cfg = json.loads((M / "integration_readiness_v1/instruments/config.v2.json").read_text())
spec = cfg["adversaries"]["carl_jev"]
report = {
    "environment": env,
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=R).decode().strip(),
    "tracked_count": len(tracked), "tracked_differences_from_HEAD": head_diff,
    "protected_hash_matches": protected, "source_build_metadata_matches": sources,
    "frozen_binary": spec["binary"], "frozen_binary_expected": spec["binary_sha256"],
    "frozen_binary_actual": sha(Path(spec["binary"])), "runs": []
}
before = {str(p.relative_to(R)): sha(p) for p in R.rglob("*") if p.is_file() and ".git" not in p.parts}
(E / "before.json").write_text(json.dumps(before, indent=2))
probe = run("namespace", ["/usr/bin/true"], isolated=True)
report["runs"].append(probe)
if probe["exit_code"] != 0:
    (E / "validation.json").write_text(json.dumps(report, indent=2))
    raise SystemExit("Network isolation unavailable; do not run tests")
report["runs"].append(run("full_test", ["go", "test", "-count=1", "-json", "./..."], isolated=True))
report["runs"].append(run("vet", ["go", "vet", "./..."], isolated=True))
report["runs"].append(run("gofmt", ["gofmt", "-l", "internal/assessment", "cmd/carl-assessment-challenge", "internal/pack/snapshot.go"], isolated=True))
report["runs"].append(run("diff_check", ["git", "--no-pager", "diff", "--check"], isolated=True))
report["runs"].append(run("binary_build_info", ["go", "version", "-m", spec["binary"]], isolated=True))
after = {str(p.relative_to(R)): sha(p) for p in R.rglob("*") if p.is_file() and ".git" not in p.parts}
report["repository_files_unchanged"] = before == after
events = [json.loads(line) for line in (E / "v2_full_test.stdout").read_text().splitlines() if line.startswith("{")]
report["counts"] = {
    "top_level_pass": sum(e.get("Action") == "pass" and "Test" in e and "/" not in e["Test"] for e in events),
    "including_subtests_pass": sum(e.get("Action") == "pass" and "Test" in e for e in events),
    "test_packages_pass": sum(e.get("Action") == "pass" and "Test" not in e for e in events),
    "fail_events": sum(e.get("Action") == "fail" for e in events),
    "test_skips": sum(e.get("Action") == "skip" and "Test" in e for e in events),
}
(E / "validation_v2.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report["counts"]), flush=True)
