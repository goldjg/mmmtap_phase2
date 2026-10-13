"""Operator-only stage gates; all commands other than smoke/pilot/full are offline."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from phase2.core import IntegrityError, load
from phase2.engine import locked
from .checks import preflight, run_controls, verify_preservation, verify_seal
from .planning import FILENAMES, PACKAGE, RUNS, STAGES, base_plan, estimate, publish_manifests, validate_manifest
from .runtime import execute, immutable, safe_runs_root


def print_result(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build-manifests", help="Offline, exclusive publication; refuses to replace an existing release.")
    sub.add_parser("verify", help="Verify operator seal and all preserved pre-existing workspace files.")
    control = sub.add_parser("controls", help="Real CLIs with dummy loopback providers and no external network.")
    control.add_argument("--out", type=Path, required=True)
    for name in ("preflight", "estimate", "mock", *STAGES):
        command = sub.add_parser(name)
        if name not in STAGES:
            command.add_argument("--stage", choices=STAGES, default="smoke" if name == "preflight" else "pilot")
        command.add_argument("--manifest", type=Path)
        if name in ("preflight", "mock", *STAGES):
            command.add_argument("--runs-root", type=Path, default=RUNS if name != "mock" else None,
                                 required=name == "mock")
        if name in ("estimate", "mock", *STAGES):
            command.add_argument("--max-calls", type=int, required=True,
                                 help="Persisted adapter-attempt ceiling, NOT a provider billing or HTTP-request ceiling.")
        if name == "estimate":
            command.add_argument("--input-tokens-per-call", type=int, default=4000)
            command.add_argument("--output-tokens-per-call", type=int, default=1000)
            command.add_argument("--rates", type=Path, help="Explicit account-specific billing unit and token rates.")
        if name in ("mock", *STAGES):
            command.add_argument("--stop-after", type=int, help="Pause after this many new adapter invocations.")
        if name in STAGES:
            command.add_argument("--authorize-live-stage", choices=STAGES)
            command.add_argument("--accept-lower-assurance", action="store_true")
            command.add_argument("--approve-frozen-instruments", action="store_true")
            command.add_argument("--review-prior-stage", help="Required for pilot/full; records the operator's review.")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        if args.command == "build-manifests":
            print_result(publish_manifests())
            return 0
        if args.command == "verify":
            from forensic_remediation_v1.verify_package import files, verify_references
            print_result({"operator": verify_seal(), "v5": verify_references(files()),
                          "preservation": verify_preservation(load(PACKAGE / "evidence/PRESERVATION_BASELINE.json")),
                          "real_provider_calls": 0})
            return 0
        if args.command == "controls":
            result = run_controls(args.out, base_plan()["config"])
            print_result({"controls": len(result["controls"]), "strict_qualification": result["strict_qualification"],
                          "real_provider_calls": 0, "output": str(args.out)})
            return 0
        stage = args.command if args.command in STAGES else args.stage
        manifest = args.manifest or PACKAGE / FILENAMES[stage]
        plan = load(manifest)
        if plan["operator_execution"]["stage"] != stage:
            raise IntegrityError("The manifest belongs to a different stage")
        if args.command == "preflight":
            runs_root = safe_runs_root(args.runs_root)
            result = preflight(plan, runs_root=runs_root)
            runs_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            with locked(runs_root / "preflight"):
                directory = runs_root / "preflight"
                number = 1 + max((int(p.stem.rsplit("-", 1)[-1]) for p in directory.glob("report-*.json")), default=0)
                target = directory / f"report-{number:06d}.json"
                immutable(target, result)
            print_result({"report": str(target), "stage": stage, "manifest_sha256": plan["manifest_sha256"],
                          "credentials": result["credentials"], "storage": result["storage"],
                          "blocking_infrastructure": result["blocking_infrastructure"], "real_provider_calls": 0})
            return 2 if result["blocking_infrastructure"] else 0
        if args.command == "estimate":
            validate_manifest(plan)
            print_result(estimate(plan, args.max_calls, input_tokens=args.input_tokens_per_call,
                                  output_tokens=args.output_tokens_per_call,
                                  rates=load(args.rates) if args.rates else None))
            return 0
        if args.command == "mock":
            result = execute(plan, args.runs_root, mode="mock", max_calls=args.max_calls,
                             stop_after=args.stop_after)
        else:
            result = execute(plan, args.runs_root, mode="live", max_calls=args.max_calls,
                             authorised_stage=args.authorize_live_stage,
                             accept_lower_assurance=args.accept_lower_assurance,
                             approve_instruments=args.approve_frozen_instruments,
                             review_note=args.review_prior_stage, stop_after=args.stop_after)
        print_result({key: result[key] for key in (
            "stage", "mode", "manifest_sha256", "output_directory", "status_counts", "new_checkpoints",
            "preserved_checkpoints", "adapter_attempt_reservations", "maximum_call_budget",
            "complete", "stopped_reason", "evidence_quality", "satisfies_strict_isolation", "automatic_next_stage")})
        if result["stopped_reason"] == "operator_interrupt":
            return 130
        return 0 if result["complete"] and set(result["status_counts"]) <= {"ok", "mock_ok"} else 2
    except KeyboardInterrupt:
        print("Operator interrupted. Existing reservations are permanent; repeat only the same stage command to resume.",
              file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print("Operator execution stopped: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
