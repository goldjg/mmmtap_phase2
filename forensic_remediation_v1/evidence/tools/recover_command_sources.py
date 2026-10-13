"""Recover exact earlier edited bytes, accepting only contemporaneously recorded hashes."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import subprocess

BASE = Path(__file__).parent
SESSION = BASE.parent
ROOTS = {
    "workspace": Path("/home/prometheus/git/mmmtap_phase2"),
    "carl": Path("/home/prometheus/git/cARL-semantic-eval"),
}
OBJECTS = BASE / "source_objects"
state = {}


def retain(raw):
    ident = hashlib.sha256(raw).hexdigest()
    target = OBJECTS / ident
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(raw)
    elif target.read_bytes() != raw:
        raise RuntimeError("Source object collision")
    return ident


def key_for(path):
    path = Path(path)
    for label, root in ROOTS.items():
        if path.is_relative_to(root):
            return label + "/" + str(path.relative_to(root))
    if path.parent == BASE and path.name in ("offline_run.py", "capture_baseline.py"):
        return "session/" + path.name
    return None


def apply_update(text, chunks):
    lines = text.splitlines()
    cursor = 0
    for chunk in chunks:
        old = [line[1:] for line in chunk if line.startswith((" ", "-"))]
        new = [line[1:] for line in chunk if line.startswith((" ", "+"))]
        positions = [i for i in range(cursor, len(lines) - len(old) + 1) if lines[i:i+len(old)] == old]
        if not positions:
            compact = lambda values: [" ".join(line.split()) for line in values]
            positions = [i for i in range(cursor, len(lines) - len(old) + 1)
                         if compact(lines[i:i+len(old)]) == compact(old)]
        if not positions:
            raise ValueError("Recorded edit context not found")
        position = positions[0]
        lines[position:position+len(old)] = new
        cursor = position + len(new)
    return "\n".join(lines) + "\n"


def replay_patch(patch):
    lines = patch.splitlines()
    edits = []
    for line in lines:
        if line.startswith(("*** Add File: ", "*** Update File: ", "*** Delete File: ")):
            kind, path = line[4:].split(" File: ", 1)
            edits.append((kind, path, []))
        elif edits and line not in ("*** Begin Patch", "*** End Patch"):
            edits[-1][2].append(line)
    changes = {}
    for kind, path, body in edits:
        key = key_for(path)
        if key is None:
            continue
        if kind == "Add":
            raw = ("\n".join(line[1:] for line in body if line.startswith("+")) + "\n").encode()
        elif kind == "Delete":
            changes[key] = None
            continue
        else:
            if key not in state:
                continue
            chunks = []
            for line in body:
                if line.startswith("@@"):
                    chunks.append([])
                elif line.startswith((" ", "+", "-")):
                    if not chunks:
                        chunks.append([])
                    chunks[-1].append(line)
            raw = apply_update(state[key].decode(), chunks).encode()
        changes[key] = raw
    for key, raw in changes.items():
        if raw is None:
            state.pop(key, None)
        else:
            state[key] = raw
            retain(raw)
            if key.endswith(".go"):
                formatted = subprocess.run(["gofmt"], input=raw, capture_output=True, check=False)
                if formatted.returncode == 0:
                    retain(formatted.stdout)


def main():
    os.umask(0o077)
    OBJECTS.mkdir(mode=0o700, exist_ok=True)
    for label in ROOTS:
        root = BASE / "preservation_baseline/source" / label
        for path in root.rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                state[label + "/" + str(path.relative_to(root))] = raw
                retain(raw)
    events = [json.loads(line) for line in (SESSION / "events.jsonl").read_text().splitlines()]
    failures, runners = [], []
    for event in events:
        if event.get("type") != "tool.execution_start":
            continue
        data = event.get("data", {})
        if "apply_patch" not in data.get("toolName", "") or not isinstance(data.get("arguments"), str):
            continue
        try:
            replay_patch(data["arguments"])
            if "session/offline_run.py" in state:
                runners.append((datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")),
                                retain(state["session/offline_run.py"])))
        except (ValueError, UnicodeError) as exc:
            failures.append({"event_id": event["id"], "reason": str(exc)})
    for label, root in ROOTS.items():
        for path in root.rglob("*.go" if label == "carl" else "*.py"):
            if label == "workspace" and not any(path.is_relative_to(root / part)
                                                for part in ("phase2", "historical_extractor", "tests")):
                continue
            if path.is_file():
                retain(path.read_bytes())
        for pattern in (("go.mod", "go.sum", "internal/assessment/testdata/*.json", "embedded/assets/**/*")
                        if label == "carl" else ("phase2/*.json", "tests/fixtures/*.json")):
            for path in root.glob(pattern):
                if path.is_file():
                    retain(path.read_bytes())
    records = {}
    for path in sorted((BASE / "command_evidence").glob("*/command.json")):
        command = json.loads(path.read_bytes())
        missing = {name: ident for name, ident in command["source_sha256"].items()
                   if not (OBJECTS / ident).is_file()}
        records[path.parent.name] = {"source_files": len(command["source_sha256"]), "missing": missing,
                                    "all_exact_recorded_source_hashes_recovered": not missing}
        applicable = [ident for at, ident in runners
                      if at <= datetime.fromisoformat(command["started_at_utc"])]
        if applicable:
            records[path.parent.name]["runner_source_from_recorded_edit_timing"] = applicable[-1]
    report = {"schema": "mmmtap-source-byte-recovery-v1",
              "method": "baseline bytes plus recorded own-session edits; gofmt candidates; SHA256 equality to original command records",
              "classification": "derived recovery, not a new or retroactively executed test",
              "commands": records, "unapplied_edit_events": failures}
    output = BASE / "source_recovery.json"
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"commands": len(records), "missing_files": sum(len(r["missing"]) for r in records.values()),
                      "unapplied_edit_events": len(failures)}))


if __name__ == "__main__":
    main()
