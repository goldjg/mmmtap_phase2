"""Recover a rejected-candidate reporter by its contemporaneously recorded byte hash."""
import hashlib
import json
import os
from pathlib import Path

import recover_command_sources as recovery

BASE = Path(__file__).parent
REPORT = Path("/home/prometheus/git/mmmtap_phase2/forensic_remediation_v1/CANDIDATE_V4_PRESERVATION_CHECKS.json")
TARGET = BASE / "publish_evidence.py"


def main():
    os.umask(0o077)
    expected = json.loads(REPORT.read_bytes())["producer_sha256"]
    recovery.key_for = lambda path: "publisher" if Path(path) == TARGET else None
    edits = []
    with (BASE.parent / "events.jsonl").open() as events:
        for line in events:
            event = json.loads(line)
            data = event.get("data", {})
            patch = data.get("arguments")
            if (event.get("type") != "tool.execution_start"
                    or "apply_patch" not in data.get("toolName", "")
                    or not isinstance(patch, str) or str(TARGET) not in patch):
                continue
            recovery.replay_patch(patch)
            raw = recovery.state.get("publisher")
            if raw is None:
                continue
            ident = hashlib.sha256(raw).hexdigest()
            edits.append({"event_id": event["id"], "timestamp": event["timestamp"],
                          "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
                          "result_sha256": ident})
            if ident == expected:
                result = {"schema": "mmmtap-evidence-producer-recovery-v1",
                          "classification": "derived exact bytes, not retrospective execution",
                          "method": "own-session recorded file edits matched to the original report producer hash",
                          "report": REPORT.name, "report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
                          "producer_sha256": expected, "edits": edits}
                with (BASE / "producer_recovery.json").open("x") as stream:
                    json.dump(result, stream, indent=2, sort_keys=True)
                    stream.write("\n")
                print(json.dumps({"recovered_sha256": ident, "recorded_edits": len(edits)}))
                return
    raise RuntimeError("Exact original evidence producer was not recovered")


if __name__ == "__main__":
    main()
