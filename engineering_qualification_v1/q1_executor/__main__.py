"""Durable synthetic demo. No live mode, adapters, credentials or release path."""
import argparse
import json
import os
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
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True)
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
    for name in ("resume", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--campaign", type=Path, required=True)
        if name == "resume":
            command.add_argument("--interrupt-after-reservation", help="Simulation fault injection only; exits 75.")
        else:
            command.add_argument("--history", action="store_true", help="Include reconstructed journal and exact receipts.")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            output = demo(args.output)
        elif args.command == "resume":
            output = resume(args.campaign, interrupt_after_reservation=args.interrupt_after_reservation)
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
