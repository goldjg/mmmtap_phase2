"""Retain offline command evidence with a kernel-enforced external-network block."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

from phase2.core import ROOT, digest, write_new
from phase2.isolation import sha256_file
from phase2.software import source_hashes
from .planning import PACKAGE, software


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.label or Path(args.label).name != args.label:
        parser.error("label must be a single directory name")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("command required")
    os.umask(0o077)
    output = PACKAGE / "evidence" / args.label
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    before, original = software(), source_hashes()
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
        "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "JEVKEY": "",
        "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local", "GOTELEMETRY": "off",
        "GOCACHE": "/tmp/mmmtap-go-cache", "GOMODCACHE": "/tmp/mmmtap-go-mod",
        "GOFLAGS": "-buildvcs=false", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }
    argv = ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--bind", str(output), str(output),
            "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--unshare-net",
            "--die-with-parent", "--", *command]
    started, error = time.monotonic(), None
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                    timeout=args.timeout, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code, error = 124, "offline_validation_timeout"
    record = {
        "schema": "mmmtap-operator-offline-command-v1", "argv": argv, "cwd": str(ROOT), "environment": env,
        "completed_at": datetime.now(timezone.utc).isoformat(), "exit_status": code, "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "operator_software_sha256": digest(before), "operator_sources": before,
        "v5_source_hashes": original, "sources_unchanged": before == software() and original == source_hashes(),
        "external_network": "kernel_network_namespace_disabled", "real_provider_calls": 0,
        "stdout_sha256": sha256_file(output / "stdout.txt"), "stderr_sha256": sha256_file(output / "stderr.txt"),
    }
    write_new(output / "command.json", record)
    print(json.dumps({k: record[k] for k in ("exit_status", "error", "elapsed_seconds", "sources_unchanged",
                                            "operator_software_sha256", "real_provider_calls")}, indent=2))
    print(str(output))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
