"""Loopback supervisor inside an external-network-disabled test namespace."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from phase2.loopback_provider import Recorder, serve
from .transports import Watchdog, run_once


def main() -> int:
    spec = json.loads(Path(sys.argv[1]).read_bytes())
    output = Path("/capture")
    recorder = Recorder(output / "requests.jsonl", spec["scenario"], spec["text"],
                        spec["tool_target"], spec["write_target"], spec.get("forced_tool"))
    server = serve(recorder)
    base = "http://127.0.0.1:" + str(server.server_address[1])
    argv = [arg.replace("{BASE}", base) for arg in spec["argv"]]
    env = {key: value.replace("{BASE}", base) for key, value in spec["env"].items()}
    watch = Watchdog("codex_cli" if spec["provider"] == "codex" else "github_copilot_cli",
                     spec["model"]) if spec["watchdog"] else None
    try:
        result = run_once(argv, stdin=spec["stdin"].encode(), env=env, timeout=spec["timeout"],
                          limit=8 * 1024 * 1024, watchdog=watch, cwd="/work")
    finally:
        server.shutdown()
        server.server_close()
    (output / "stdout.bin").write_bytes(result.stdout)
    (output / "stderr.bin").write_bytes(result.stderr)
    outcome = {key: value for key, value in result.__dict__.items() if key not in ("stdout", "stderr")}
    outcome.update(read_target_visible_in_sandbox=Path(spec["tool_target"]).exists(),
                   write_target_exists_in_sandbox=Path(spec["write_target"]).exists(),
                   home_files=sorted(str(p.relative_to("/home/assessor"))
                                     for p in Path("/home/assessor").rglob("*") if p.is_file()),
                   live_calls=0)
    (output / "outcome.json").write_text(json.dumps(outcome, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
