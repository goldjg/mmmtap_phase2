import hashlib
import json
from pathlib import Path
import subprocess

E = Path(__file__).resolve().parent
R = Path("/home/prometheus/git/cARL-semantic-eval")
M = Path("/home/prometheus/git/mmmtap_phase2")
env = json.loads((E / "validation_v2.json").read_text())["environment"]
overlay = {"Replace": {str(R / "internal/assessment/forensic_test.go"): str(E / "forensic_test.go")}}
(E / "overlay.json").write_text(json.dumps(overlay))
prefix = ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--bind", str(E), str(E),
          "--dev", "/dev", "--proc", "/proc", "--unshare-net", "--die-with-parent", "--"]
runs = []
def run(name, args):
    with (E / (name + ".stdout")).open("wb") as out, (E / (name + ".stderr")).open("wb") as err:
        p = subprocess.run(prefix + args, cwd=R, env=env, stdout=out, stderr=err)
    runs.append({"name": name, "args": args, "exit_code": p.returncode})
    print(name, p.returncode, flush=True)

run("forensic", ["go", "test", "-overlay", str(E / "overlay.json"), "-count=1", "-json",
                 "-run", "^TestForensic", "./internal/assessment"])
for version, path in {
    "v1": M / "path_b_validation_v1/bin/carl-assessment-challenge-v1",
    "draft": M / "integration_readiness_v1/bin/carl-assessment-challenge-v1-live",
    "v2": M / "integration_readiness_v1/bin/carl-assessment-challenge-v2",
}.items():
    run(version + "_help", [str(path), "--help"])
    runs[-1]["binary_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
v2 = str(M / "integration_readiness_v1/bin/carl-assessment-challenge-v2")
for name, path in {
    "v2_replay_historical": M / "path_b_validation_v1/cases/021-E2/evaluated/receipt.json",
    "v2_replay_missing_credential": M / "integration_readiness_v1/go_validation/binary_missing_credential/live_receipt.json",
}.items():
    run(name, [v2, "replay", "--receipt", str(path),
               "--receipt-sha256", hashlib.sha256(path.read_bytes()).hexdigest()])
(E / "reproductions.json").write_text(json.dumps(runs, indent=2))
