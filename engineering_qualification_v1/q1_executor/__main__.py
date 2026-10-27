"""Durable Q1 executor. Live dispatch disabled; JEVKEY is broker-only."""
import os

# Protect the source process as early as Python permits, before importing the
# engine or reading any value. The existing operator parent environment is
# outside this process boundary and is never copied/inspected by this guard.
if "JEVKEY" in os.environ:
    from .systemone_https_v1.credential import harden
    harden()

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from .engine import create, resume, verify
from .model import raw_hash


def demo(root):
    create(root)
    # A real child process exits immediately after its durable reservation.
    child = subprocess.run([sys.executable, "-m", "engineering_qualification_v1.q1_executor", "resume",
                            "--campaign", str(root.absolute()), "--interrupt-after-reservation", "interruption"],
                           env={"LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True)
    if child.returncode != 75:
        raise ValueError("expected_simulated_crash_exit_75:" + child.stderr.decode("utf-8", "replace"))
    interrupted = verify(root)["summary"]
    first_resume = resume(root)
    before = raw_hash((root / "campaign.sqlite3").read_bytes())
    second_resume = resume(root)
    after = raw_hash((root / "campaign.sqlite3").read_bytes())
    if before != after or first_resume != second_resume:
        raise ValueError("repeated_resume_not_idempotent")
    return {"interruption_exit_status": child.returncode, "after_interruption": interrupted,
            "first_resume": first_resume, "second_resume": second_resume,
            "second_resume_database_unchanged": True, "verification": verify(root)["summary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("demo")
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("matrix-demo", help="Two synthetic 153-position campaigns; no live providers.")
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("matrix-build", help="Reproduce a frozen full-matrix fixture.")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--scenario", choices=("normal", "adverse"), required=True)
    for name in ("transport-demo", "transport-probes"):
        command = sub.add_parser(name, help="Offline-only pinned subprocess fixture.")
        command.add_argument("--output", type=Path, required=True)
    for name in ("resume", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--campaign", type=Path, required=True)
        if name == "resume":
            command.add_argument("--interrupt-after-reservation", help="Simulation fault injection only; exits 75.")
            command.add_argument("--offline-subprocess", action="store_true", help="Pinned local fixture only; network denied.")
            command.add_argument("--interrupt-after-transport-start", help="Offline fault injection: abrupt executor exit 75.")
        else:
            command.add_argument("--history", action="store_true", help="Include reconstructed journal and exact receipts.")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            output = demo(args.output)
        elif args.command == "matrix-demo":
            from .full_matrix import demo as matrix_demo
            output = matrix_demo(args.output)
        elif args.command == "matrix-build":
            from .full_matrix import build
            output = build(args.output, args.scenario)
        elif args.command in ("transport-demo", "transport-probes"):
            from .transport_qualification import demo as transport_demo, probes
            output = (transport_demo if args.command == "transport-demo" else probes)(args.output)
        elif args.command == "resume":
            output = resume(args.campaign, interrupt_after_reservation=args.interrupt_after_reservation,
                            offline_subprocess=args.offline_subprocess,
                            interrupt_after_transport_start=args.interrupt_after_transport_start)
        else:
            report = verify(args.campaign)
            output = report if args.history else report["summary"]
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(json.dumps({"verification": "FAIL", "error": str(exc), "live_execution_authorized": False}), file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
