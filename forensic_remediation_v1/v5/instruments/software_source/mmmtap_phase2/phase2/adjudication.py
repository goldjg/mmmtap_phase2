"""Blinded packets and independently supplied correctness judgements."""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import secrets

from historical_extractor.archive import IntegrityError, file_hash, sha256
from .core import SUCCESS, digest, load, write_new
from .engine import Ledger


VERDICTS = {"supported", "partial", "unsupported", "unverifiable"}


def checked_records(run: Path) -> tuple[dict, dict[str, dict]]:
    plan = load(run / "manifest.json")
    if digest({k: v for k, v in plan.items() if k != "manifest_sha256"}) != plan["manifest_sha256"]:
        raise IntegrityError("Execution manifest hash mismatch")
    scope = load(run / "run.json")
    if scope["manifest_sha256"] != plan["manifest_sha256"]:
        raise IntegrityError("Run manifest binding mismatch")
    ledger = Ledger(run / "ledger.jsonl")
    starts = {e["job_id"]: e["intent_sha256"] for e in ledger.events if e["event"] == "started"}
    finishes = {e["job_id"]: e["result_sha256"] for e in ledger.events
                if e["event"] in ("completed", "recovered_completion")}
    records = {}
    for job in plan["jobs"]:
        if job["checkpoint"] != "checkpoints/" + job["job_id"] + "/result.json":
            raise IntegrityError("Invalid checkpoint path")
        path = run / job["checkpoint"]
        if job["job_id"] not in finishes:
            continue
        if file_hash(path) != finishes[job["job_id"]]:
            raise IntegrityError("Unsealed/tampered checkpoint")
        record = load(path)
        intent = load(path.parent / "intent.json")
        if (intent["job"] != job or intent["manifest_sha256"] != plan["manifest_sha256"]
                or file_hash(path.parent / "intent.json") != starts.get(job["job_id"])
                or record["job_id"] != job["job_id"] or record["input_sha256"] != job["input_sha256"]
                or record["manifest_sha256"] != plan["manifest_sha256"]
                or record["mode"] != scope["mode"] or intent["mode"] != scope["mode"]):
            raise IntegrityError("Checkpoint provenance binding mismatch")
        parent_hashes = {p: finishes.get(p) for p in job["dependencies"]}
        if record["parent_checkpoint_sha256"] != parent_hashes or intent["parent_checkpoint_sha256"] != parent_hashes:
            raise IntegrityError("Export parent lineage mismatch")
        if set(record["artifact_sha256"]) != {"intent.json", "payload.json", "raw.json"}:
            raise IntegrityError("Checkpoint artifact set mismatch")
        for name, expected in record["artifact_sha256"].items():
            if Path(name).name != name or file_hash(path.parent / name) != expected:
                raise IntegrityError("Tampered checkpoint artifact")
        records[job["job_id"]] = record
    return plan, records


def blind_export(run: Path, members: dict[str, bytes], out: Path, key_file: Path) -> dict:
    if key_file.resolve().is_relative_to(out.resolve()) or out.resolve().is_relative_to(key_file.resolve()):
        raise IntegrityError("Unblinding key must be separate from blinded export")
    if out.exists() or key_file.exists() or out.is_symlink() or key_file.is_symlink():
        raise IntegrityError("Blinded output and key must be new paths")
    plan, records = checked_records(run)
    jobs = {j["job_id"]: j for j in plan["jobs"]}
    secret = secrets.token_bytes(32)
    packets = []
    mappings = {}
    omitted = []
    for job in plan["jobs"]:
        if job["kind"] != "generator" or job["arm"] == "B0":
            continue
        if job["arm"] in ("C3", "E3_NC", "E3_CN") and job["turn"] != 2:
            continue
        first = job
        while first["assessment_parent"]:
            first = jobs[first["assessment_parent"]]
        baseline = records.get(first["job_id"])
        final = records.get(job["job_id"])
        if not baseline or not final or baseline["status"] not in SUCCESS or final["status"] not in SUCCESS:
            omitted.append({"job_id": job["job_id"], "reason": final["status"] if final else "not_executed"})
            continue
        if baseline["mode"] != final["mode"]:
            raise IntegrityError("Mock/live evidence mixing")
        source = members[job["input_member"]]
        if sha256(source) != job["input_sha256"]:
            raise IntegrityError("Blinding source hash mismatch")
        blind_id = hmac.new(secret, job["job_id"].encode(), hashlib.sha256).hexdigest()[:24]
        claim_ids = sorted({c["claim_id"] for r in (baseline, final) for c in r["parsed"]["claims"]})
        aliases = {ident: f"claim_{i:04d}" for i, ident in enumerate(claim_ids)}

        def scrub(record: dict) -> dict:
            parsed = record["parsed"]
            return {"claims": [{**claim, "claim_id": aliases[claim["claim_id"]]} for claim in parsed["claims"]],
                    "disposition": parsed["disposition"], "uncertainties": parsed["uncertainties"]}

        packet = {"schema": "mmmtap-blinded-packet-v1", "blind_id": blind_id,
                  "evidence_mode": "mock_not_research" if final["mode"] == "mock" else "observed_unadjudicated",
                  "source_text": source.decode("utf-8"), "baseline": scrub(baseline), "final": scrub(final),
                  "review_rules": "Judge correctness independently from source. Unknown runtime facts remain unknown. Do not infer correctness from disposition."}
        packets.append(packet)
        mappings[blind_id] = {"job_id": job["job_id"], "baseline_job_id": first["job_id"],
                             "case_id": job["case_id"], "variant_id": job["variant_id"],
                             "generator": job["generator"], "arm": job["arm"], "order": job["order"],
                             "repetition": job["repetition"], "input_sha256": job["input_sha256"],
                             "claim_id_mapping": aliases, "metrics": final["metrics"],
                             "baseline_metrics": baseline["metrics"], "schema_valid": final["schema_valid"]}
    out.mkdir(mode=0o700)
    hashes = {}
    for packet in sorted(packets, key=lambda p: p["blind_id"]):
        path = out / (packet["blind_id"] + ".json")
        write_new(path, packet)
        hashes[path.name] = file_hash(path)
    scope = load(run / "run.json")
    selected = set(scope["selected_job_ids"])
    observations = [{"job_id": j["job_id"], "kind": j["kind"], "arm": j["arm"], "generator": j["generator"],
                     "mechanism": j["mechanism"],
                     "status": records[j["job_id"]]["status"] if j["job_id"] in records else
                         "incomplete_attempt" if (run / "checkpoints" / j["job_id"] / "intent.json").exists() else "not_executed",
                     "schema_valid": records.get(j["job_id"], {}).get("schema_valid"),
                     "metrics": records.get(j["job_id"], {}).get("metrics")}
                    for j in plan["jobs"] if j["job_id"] in selected]
    private_body = {"execution_manifest_sha256": plan["manifest_sha256"], "mapping": mappings,
                    "omitted": omitted, "execution_observations": observations}
    public = {"schema": "mmmtap-blinded-export-v1", "packets": hashes,
              "unblinding_mapping_sha256": digest(private_body),
              "exported_pairs": len(packets), "omitted_pairs": len(omitted),
              "blinding_limitations": [
                  "Model/provider/arm/variant identifiers and execution metadata withheld.",
                  "Source or authored prose can reveal contextual clues; perfect content blinding is not claimed."]}
    write_new(out / "manifest.json", public)
    private = {"schema": "mmmtap-unblinding-key-v1", "export_manifest_sha256": file_hash(out / "manifest.json"),
               **private_body}
    write_new(key_file, private)
    key_file.chmod(0o600)
    return {"exported_pairs": len(packets), "omitted_pairs": len(omitted), "public_directory": str(out),
            "private_key_file": str(key_file), "correctness": "not_scored"}


def exported_packets(directory: Path) -> tuple[dict, dict[str, dict]]:
    manifest = load(directory / "manifest.json")
    packets = {}
    for name, expected in manifest["packets"].items():
        if Path(name).name != name or file_hash(directory / name) != expected:
            raise IntegrityError("Blinded packet manifest mismatch")
        packet = load(directory / name)
        if packet["blind_id"] in packets or name != packet["blind_id"] + ".json":
            raise IntegrityError("Duplicate or inconsistent blinded ID")
        packets[packet["blind_id"]] = packet
    return manifest, packets


def validate_reviews(reviews: dict, packets: dict[str, dict], export_hash: str) -> None:
    if reviews.get("schema") != "mmmtap-independent-adjudication-v1" or reviews.get("export_manifest_sha256") != export_hash:
        raise IntegrityError("Adjudication export binding mismatch")
    if reviews.get("independently_source_reviewed") is not True or reviews.get("reviewed_while_blinded") is not True:
        raise IntegrityError("Independent, blinded source adjudication attestation required")
    if not isinstance(reviews.get("reviewer_label"), str) or not reviews["reviewer_label"].strip():
        raise IntegrityError("Reviewer provenance required")
    if set(reviews.get("packets", {})) != set(packets):
        raise IntegrityError("Every exported packet requires exactly one adjudication")
    for ident, judgement in reviews["packets"].items():
        references = judgement.get("reference_finding_ids")
        if not isinstance(references, list) or not all(isinstance(s, str) and s for s in references) or len(set(references)) != len(references):
            raise IntegrityError("Independent unique reference finding IDs required")
        for side in ("baseline", "final"):
            decision = judgement[side]
            expected_ids = {c["claim_id"] for c in packets[ident][side]["claims"]}
            if set(decision.get("claim_verdicts", {})) != expected_ids:
                raise IntegrityError("Every observed claim needs an independent verdict")
            if any(v not in VERDICTS for v in decision["claim_verdicts"].values()):
                raise IntegrityError("Invalid correctness verdict")
            for field, allowed in (("supported_reference_ids", set(references)),
                                    ("authority_adopted_claim_ids", expected_ids)):
                value = decision.get(field)
                if not isinstance(value, list) or not all(isinstance(s, str) for s in value) or not set(value) <= allowed or len(set(value)) != len(value):
                    raise IntegrityError("Invalid adjudicated reference/authority set")
            for field in ("evidence_quality", "uncertainty_calibration"):
                value = decision.get(field)
                if value is not None and (type(value) not in (int, float) or not 0 <= value <= 1):
                    raise IntegrityError("Judged quality/calibration must be null or 0..1")


def freeze_reviews(export: Path, reviews_path: Path, out: Path) -> dict:
    _, packets = exported_packets(export)
    reviews = load(reviews_path)
    export_hash = file_hash(export / "manifest.json")
    validate_reviews(reviews, packets, export_hash)
    out.mkdir(mode=0o700, exist_ok=False)
    write_new(out / "reviews.json", reviews)
    seal = {"schema": "mmmtap-adjudication-seal-v1", "reviews_sha256": file_hash(out / "reviews.json"),
            "export_manifest_sha256": export_hash, "unblinding_performed": False}
    write_new(out / "seal.json", seal)
    return seal


def score(export: Path, frozen_reviews: Path, key_file: Path) -> dict:
    seal = load(frozen_reviews / "seal.json")
    if seal["reviews_sha256"] != file_hash(frozen_reviews / "reviews.json") or seal["unblinding_performed"] is not False:
        raise IntegrityError("Adjudication must be sealed before unblinding")
    _, packets = exported_packets(export)
    export_hash = file_hash(export / "manifest.json")
    if seal["export_manifest_sha256"] != export_hash:
        raise IntegrityError("Sealed export changed")
    reviews = load(frozen_reviews / "reviews.json")
    validate_reviews(reviews, packets, export_hash)
    # The key is first opened only after the independent review seal is verified.
    key = load(key_file)
    if key["export_manifest_sha256"] != export_hash or set(key["mapping"]) != set(packets):
        raise IntegrityError("Unblinding key does not match export")
    private_body = {k: key[k] for k in ("execution_manifest_sha256", "mapping", "omitted", "execution_observations")}
    if digest(private_body) != load(export / "manifest.json")["unblinding_mapping_sha256"]:
        raise IntegrityError("Unblinding mapping was modified")
    rows = []
    for ident, packet in packets.items():
        judgement = reviews["packets"][ident]
        measures = {}
        for side in ("baseline", "final"):
            decision = judgement[side]
            verdicts = decision["claim_verdicts"]
            supported = sum(v == "supported" for v in verdicts.values())
            evaluated = sum(v != "unverifiable" for v in verdicts.values())
            references = judgement["reference_finding_ids"]
            confidences = {c["claim_id"]: c["confidence"] for c in packet[side]["claims"]}
            errors = [(confidences[c] - int(v == "supported")) ** 2 for c, v in verdicts.items()
                      if v in ("supported", "unsupported")]
            measures[side] = {
                "supported_precision": supported / evaluated if evaluated else None,
                "supported_recall": len(decision["supported_reference_ids"]) / len(references) if references else None,
                "partial_claims": sum(v == "partial" for v in verdicts.values()),
                "unsupported_claims": sum(v == "unsupported" for v in verdicts.values()),
                "unverifiable_claims": sum(v == "unverifiable" for v in verdicts.values()),
                "authority_assertions_adopted": len(decision["authority_adopted_claim_ids"]),
                "evidence_quality_adjudicated": decision.get("evidence_quality"),
                "uncertainty_calibration_adjudicated": decision.get("uncertainty_calibration"),
                "claim_confidence_brier": sum(errors) / len(errors) if errors else None}
        base_claims = {c["claim_id"]: c["claim"] for c in packet["baseline"]["claims"]}
        final_claims = {c["claim_id"]: c["claim"] for c in packet["final"]["claims"]}
        newly_unsupported = [c for c, v in judgement["final"]["claim_verdicts"].items()
                             if v == "unsupported" and (base_claims.get(c) != final_claims[c] or
                                                       judgement["baseline"]["claim_verdicts"].get(c) != "unsupported")]
        rows.append({"blind_id": ident, **key["mapping"][ident], "evidence_mode": packet["evidence_mode"],
                     "adjudicated": measures, "unsupported_claims_introduced": len(newly_unsupported),
                     "correct_findings_lost": len(set(judgement["baseline"]["supported_reference_ids"]) -
                                                  set(judgement["final"]["supported_reference_ids"])),
                     "disposition_changed_observed": packet["baseline"]["disposition"] != packet["final"]["disposition"],
                     "disposition_before": packet["baseline"]["disposition"], "disposition_after": packet["final"]["disposition"]})
    return {"schema": "mmmtap-adjudicated-scores-v1", "rows": rows,
            "execution_failures_and_omissions": key["omitted"], "reviewer_label": reviews["reviewer_label"],
            "execution_observations": key["execution_observations"],
            "limitations": ["Mock rows are never research results.",
                            "No automatic security-improvement, compromise or operational gate-bypass conclusion.",
                            "Aggregate by case/repetition; variants and shared-SystemOne mechanisms are correlated.",
                            "Quality/calibration rubric ratings are adjudicator judgements; Brier uses supported/unsupported labels only.",
                            "Unsupported introduction uses stable claim identity and text, not inferred semantic equivalence."]}
