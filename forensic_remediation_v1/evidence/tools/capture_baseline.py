"""Read-only target inventory; writes only a new owner-only session evidence folder."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

WORKSPACE = Path("/home/prometheus/git/mmmtap_phase2")
CARL = Path("/home/prometheus/git/cARL-semantic-eval")
OUT = Path(__file__).parent / "preservation_baseline"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root):
    result = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(names + [d for d in dirs if (Path(directory) / d).is_symlink()]):
            path = Path(directory) / name
            info = path.lstat()
            record = {"mode": stat.S_IMODE(info.st_mode), "size": info.st_size}
            if path.is_symlink():
                record.update(type="symlink", target=os.readlink(path))
            elif path.is_file():
                record.update(type="file", sha256=sha(path))
            else:
                record.update(type="other")
            result[str(path.relative_to(root))] = record
    return result


def write(name, value):
    raw = json.dumps(value, sort_keys=True, indent=2).encode() + b"\n"
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


def git_record(root):
    records = {}
    for key, args in {
        "status": ["status", "--porcelain=v1", "--branch"],
        "head": ["rev-parse", "HEAD"],
        "diff": ["diff", "--binary", "--no-ext-diff"],
        "staged_diff": ["diff", "--cached", "--binary", "--no-ext-diff"],
        "tracked": ["ls-files", "-z"],
    }.items():
        proc = subprocess.run(["git", "--no-pager", "-C", str(root), *args],
                              capture_output=True, check=False)
        records[key] = {"exit_status": proc.returncode,
                        "stdout": proc.stdout.decode(), "stderr": proc.stderr.decode()}
    return records


def main():
    os.umask(0o077)
    OUT.mkdir(mode=0o700)
    inventories = {"workspace": inventory(WORKSPACE), "carl": inventory(CARL)}
    manifest = {
        "schema": "mmmtap-remediation-preservation-baseline-v1",
        "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": {"workspace": str(WORKSPACE), "carl": str(CARL)},
        "before_target_modifications": True,
        "git": {"workspace": git_record(WORKSPACE), "carl": git_record(CARL)},
        "installed_path_a": {
            "path": "/home/prometheus/bin/carl-jev",
            "sha256": sha(Path("/home/prometheus/bin/carl-jev")),
        },
        "inventories": {},
    }
    for label, inv in inventories.items():
        manifest["inventories"][label] = {
            "path": label + "_inventory.json",
            "sha256": write(label + "_inventory.json", inv), "entries": len(inv),
        }
    for label, root, patterns in (
        ("workspace", WORKSPACE, ("phase2/*.py", "phase2/*.json",
                                  "historical_extractor/*.py", "tests/*.py")),
        ("carl", CARL, ("internal/assessment/*.go", "cmd/carl-assessment-challenge/*.go",
                       "internal/pack/snapshot.go", ".github/carl/current-pr-contract.md",
                       "ASSESSMENT.md", "ARCHITECTURE.md", "CLI.md", "ROADMAP.md", "go.mod")),
    ):
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                target = OUT / "source" / label / path.relative_to(root)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                if sha(target) != inventories[label][str(path.relative_to(root))]["sha256"]:
                    raise RuntimeError("Concurrent source change: " + str(path))
    baseline_sha = write("baseline.json", manifest)
    print(json.dumps({"baseline_sha256": baseline_sha,
                      "inventories": manifest["inventories"],
                      "installed_path_a": manifest["installed_path_a"]}, indent=2))


if __name__ == "__main__":
    main()
