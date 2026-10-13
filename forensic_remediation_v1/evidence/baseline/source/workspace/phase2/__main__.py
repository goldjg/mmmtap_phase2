from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from historical_extractor.archive import IntegrityError, file_hash
from .adapters import probe
from .adjudication import blind_export, freeze_reviews, score
from .core import ROOT, corpus, experiment_plan, load, read_config, validate_plan, write_new
from .engine import approve_smoke, execute, live_smoke


def new_workspace_child(path: Path, root: Path) -> Path:
    path = path.absolute()
    if path.is_symlink() or path.parent.resolve() != root.resolve():
        raise IntegrityError("Output must be a direct child of the Phase 2 workspace")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MMMTAP Phase 2: offline first, immutable evidence, no automatic inference.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("readiness", help="Offline versions and auth-presence report; never an inference probe.")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("plan")
    p.add_argument("--readiness", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--retry-of", help="Prior experimental manifest path, required for attempt > 1", type=Path)
    p.add_argument("--retry-reason")
    for name in ("validate", "dry-run", "pilot", "run", "smoke", "approve-smoke"):
        p = sub.add_parser(name)
        p.add_argument("--manifest", type=Path, required=True)
        if name not in ("validate", "approve-smoke"):
            p.add_argument("--out", type=Path, required=True)
        if name in ("pilot", "run", "smoke"):
            p.add_argument("--authorize-live", action="store_true")
        if name in ("pilot", "run"):
            p.add_argument("--max-live-calls", type=int, required=True)
            p.add_argument("--smoke-dir", type=Path, required=True)
        if name in ("smoke", "approve-smoke"):
            p.add_argument("--adapter", choices=("haiku", "gemini", "sol", "native_jev", "carl_jev"), required=True)
        if name == "approve-smoke":
            p.add_argument("--smoke-dir", type=Path, required=True)
            p.add_argument("--confirm-isolation", action="store_true")
            p.add_argument("--confirm-no-hidden-retries", action="store_true")
            p.add_argument("--review-note", required=True)
    p = sub.add_parser("export")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--key-file", type=Path, required=True)
    p = sub.add_parser("freeze-adjudication")
    p.add_argument("--export-dir", type=Path, required=True)
    p.add_argument("--reviews", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("score")
    p.add_argument("--export-dir", type=Path, required=True)
    p.add_argument("--frozen-reviews", type=Path, required=True)
    p.add_argument("--key-file", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        cfg = read_config(args.config) if args.config else read_config()
        out = new_workspace_child(args.out, root) if hasattr(args, "out") else None
        if args.command == "readiness":
            result = probe(cfg)
            write_new(out, result)
            print(json.dumps({"report": str(out), "live_capable_adapters": 0}, indent=2))
            return 0
        source, members = corpus(root)
        if args.command == "plan":
            previous = load(args.retry_of) if args.retry_of else None
            if previous and args.attempt != previous["experimental_attempt"] + 1:
                raise IntegrityError("Experimental retry attempt must increment prior attempt")
            plan = experiment_plan(cfg, source, load(args.readiness), attempt=args.attempt,
                                   retry_of=previous["manifest_sha256"] if previous else None,
                                   retry_reason=args.retry_reason)
            validate_plan(plan, source, cfg)
            write_new(out, plan)
            print(json.dumps({"manifest": str(out), "manifest_sha256": plan["manifest_sha256"], **plan["counts"]}, indent=2))
            return 0
        if args.command in ("validate", "dry-run", "pilot", "run", "smoke", "approve-smoke"):
            plan = load(args.manifest)
            validate_plan(plan, source, cfg)
            if args.command == "validate":
                result = {"validated": True, "manifest_sha256": plan["manifest_sha256"], **plan["counts"]}
            elif args.command == "approve-smoke":
                smoke_dir = new_workspace_child(args.smoke_dir, root)
                result = approve_smoke(plan, smoke_dir, args.adapter, isolation=args.confirm_isolation,
                                       retries=args.confirm_no_hidden_retries, note=args.review_note)
            elif args.command == "smoke":
                result = live_smoke(plan, members, out, args.adapter, authorised=args.authorize_live)
            else:
                selected = None
                if args.command == "pilot":
                    if not 1 <= args.max_live_calls <= 100:
                        raise IntegrityError("Pilot ceiling must be 1..100 live call reservations")
                    pilot = cfg["pilot"]
                    selected = {(c, pilot["variant"]) for c in pilot["cases"].values()}
                    if len(selected) != 3 or not selected <= {(i["case_id"], i["variant_id"]) for i in source["items"]}:
                        raise IntegrityError("Pilot must select three distinct frozen case/variant pairs")
                result = execute(plan, members, out, mode="mock" if args.command == "dry-run" else "live",
                                 authorised=getattr(args, "authorize_live", False),
                                 max_live_calls=getattr(args, "max_live_calls", None),
                                 smoke_directory=getattr(args, "smoke_dir", None), selected_inputs=selected)
            print(json.dumps(result, indent=2))
            failed = any(result.get("status_counts", {}).get(s, 0) for s in
                         ("execution_failed", "schema_invalid", "adapter_unverified", "incomplete_attempt"))
            return 0 if not failed and result.get("complete", True) and result.get("status", "ok") == "ok" else 2
        if args.command == "export":
            validate_plan(load(args.run_dir / "manifest.json"), source, cfg)
            key = new_workspace_child(args.key_file, root)
            result = blind_export(args.run_dir, members, out, key)
        elif args.command == "freeze-adjudication":
            result = freeze_reviews(args.export_dir, args.reviews, out)
        else:
            result = score(args.export_dir, args.frozen_reviews, args.key_file)
            write_new(out, result)
            result = {"score_file": str(out), "adjudicated_pairs": len(result["rows"]), "automatic_research_conclusions": False}
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Phase 2 stopped: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
