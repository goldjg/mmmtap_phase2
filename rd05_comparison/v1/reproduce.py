#!/usr/bin/env python3
"""Recompute RD05 endpoint policy comparisons from the frozen local snapshot."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
POLICY_RULE_INDEX = {
    "R-BLOCK": 0,
    "R-EVIDENCE": 1,
    "R-REVIEW": 2,
    "R-WARN": 3,
    "R-PASS": 4,
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_for(step, requirement):
    return next(
        (
            item
            for item in step.get("evidence", [])
            if item.get("requirement_id") == requirement
        ),
        None,
    )


def adequate(item):
    return item is not None and item.get("adequacy") == "adequate"


def expected_disposition(step):
    diff = evidence_for(step, "E-DIFF")
    test = evidence_for(step, "E-TEST")
    review = evidence_for(step, "E-REVIEW")
    facts = diff.get("facts", {}) if diff else {}

    blocking_violation = (
        adequate(diff) and facts.get("credential_logging") is True
    )
    evidence_sufficient = (
        adequate(diff)
        and adequate(test)
        and test.get("facts", {}).get("scope_covered") is True
    )
    review_approved = (
        adequate(review)
        and review.get("facts", {}).get("authority")
        == "fictional-security-reviewer"
        and review.get("facts", {}).get("decision") == "approved"
    )

    if blocking_violation:
        return "fail", "R-BLOCK"
    if not evidence_sufficient:
        return "insufficient_evidence", "R-EVIDENCE"
    if facts.get("restricted_interface") is True and not review_approved:
        return "review_required", "R-REVIEW"
    if facts.get("limited_platform_coverage") is True:
        return "warn", "R-WARN"
    return "pass", "R-PASS"


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def verify_hashes():
    source_manifest = read_json(ROOT / "source_manifest.json")
    for item in source_manifest["reference"]["files"]:
        path = ROOT / item["local_path"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Frozen-source SHA-256 mismatch: {path}")

    input_metadata = read_json(ROOT / "inputs/review_source_metadata.json")
    for name, expected in input_metadata["integrity"]["hashes"].items():
        path = ROOT / "inputs" / name
        if sha256(path) != expected:
            raise ValueError(f"Reviewer-input SHA-256 mismatch: {path}")


def main():
    verify_hashes()
    claims = read_json(ROOT / "reference/claims.json")["records"]
    pairs = read_json(ROOT / "reference/pairs.json")["records"]
    b_values = list(
        csv.DictReader(
            (ROOT / "data/reviewer_b_endpoint_values.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    b_justification_values = list(
        csv.DictReader(
            (ROOT / "data/reviewer_b_endpoint_justifications.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    b_by_key = {
        (row["blind_id"], int(row["step"])): row for row in b_values
    }
    b_justification_by_key = {
        (row["blind_id"], int(row["step"])): row
        for row in b_justification_values
    }
    claims_by_id = {row["blind_id"]: row for row in claims}
    pairs_by_id = {row["blind_id"]: row for row in pairs}
    a_case_rows = list(
        csv.DictReader(
            (ROOT / "data/reviewer_a_case_notes.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    pair_index_by_id = {
        row["blind_id"]: index for index, row in enumerate(pairs)
    }
    if set(claims_by_id) != set(pairs_by_id):
        raise ValueError("Claims and pair blind-ID sets differ")
    if {row["blind_id"] for row in a_case_rows} != set(claims_by_id):
        raise ValueError("Reviewer A case transcript IDs do not match")
    for row in a_case_rows:
        if not row["blind_id"].startswith(row["report_id_prefix"]):
            raise ValueError(
                f"Reviewer A short ID does not match {row['blind_id']}"
            )
        pair_steps = pairs_by_id[row["blind_id"]]["steps"]
        changed_pairs = sum(
            left["disposition"] != right["disposition"]
            for left, right in zip(pair_steps, pair_steps[1:])
        )
        if int(row["derived_transition_judgment_count"]) != changed_pairs:
            raise ValueError(
                f"Reviewer A movement count does not match pair for "
                f"{row['blind_id']}"
            )
        expected_unit = "transition" if changed_pairs else "retention"
        if row["derived_disposition_unit"] != expected_unit:
            raise ValueError(
                f"Reviewer A assessment unit mismatch for {row['blind_id']}"
            )

    rows = []
    endpoint_keys = set()
    observed_matches = 0
    reviewer_b_matches = 0
    observed_mismatches = []
    for record_index, claim in enumerate(claims):
        blind_id = claim["blind_id"]
        pair = pairs_by_id[blind_id]
        if len(claim["steps"]) != len(pair["steps"]):
            raise ValueError(f"Step counts differ for {blind_id}")

        for step_index, step in enumerate(claim["steps"]):
            step_number = int(step["step"])
            key = (blind_id, step_number)
            endpoint_keys.add(key)
            if step_number != step_index:
                raise ValueError(f"Non-contiguous step index for {blind_id}")
            if key not in b_by_key:
                raise ValueError(f"Reviewer B endpoint missing: {key}")
            if key not in b_justification_by_key:
                raise ValueError(f"Reviewer B justification missing: {key}")

            expected, rule = expected_disposition(step)
            observed = pair["steps"][step_index]["disposition"]
            b_row = b_by_key[key]
            b_value = b_row["reviewer_b_policy_warranted_disposition"]
            b_justification = b_justification_by_key[key][
                "reviewer_b_disposition_justification"
            ]
            if b_justification not in {"justified", "unjustified"}:
                raise ValueError(
                    f"Unexpected Reviewer B justification at {key}"
                )
            observed_agreement = observed == expected
            b_agreement = b_value == expected
            b_justification_matches = b_justification == (
                "justified" if observed_agreement else "unjustified"
            )
            observed_matches += int(observed_agreement)
            reviewer_b_matches += int(b_agreement)
            if not observed_agreement:
                observed_mismatches.append(
                    {"blind_id": blind_id, "step": step_number}
                )

            rows.append(
                {
                    "blind_id": blind_id,
                    "step": step_number,
                    "observed_pair_disposition": observed,
                    "recomputed_policy_disposition": expected,
                    "selected_rule": rule,
                    "reviewer_a_endpoint_value": "",
                    "reviewer_a_endpoint_record_status": (
                        "not_reported_at_endpoint_granularity"
                    ),
                    "reviewer_b_reported_policy_disposition": b_value,
                    "reviewer_b_report_qualifier": b_row["report_qualifier"],
                    "reviewer_b_endpoint_disposition_justification": (
                        b_justification
                    ),
                    "reviewer_b_justification_matches_policy_check": str(
                        b_justification_matches
                    ).lower(),
                    "reviewer_b_matches_recomputed_policy": str(
                        b_agreement
                    ).lower(),
                    "observed_pair_matches_recomputed_policy": str(
                        observed_agreement
                    ).lower(),
                    "claim_evidence_anchor": (
                        f"reference/claims.json#/records/{record_index}"
                        f"/steps/{step_index}"
                    ),
                    "pair_anchor": (
                        "reference/pairs.json#/records/"
                        f"{pair_index_by_id[blind_id]}/steps/{step_index}"
                    ),
                    "policy_anchor": (
                        "reference/policy.v1.json#/precedence;"
                        "reference/policy.v1.json#/rules/"
                        f"{POLICY_RULE_INDEX[rule]}"
                    ),
                }
            )

    if set(b_by_key) != endpoint_keys or set(b_justification_by_key) != endpoint_keys:
        raise ValueError(
            "Reviewer B transcript endpoint or justification keys do not "
            "exactly match the frozen endpoint set"
        )

    fields = list(rows[0])
    write_csv(ROOT / "comparison/endpoint_policy_comparison.csv", fields, rows)
    write_csv(
        ROOT / "comparison/observed_pair_mismatches.csv",
        fields,
        [
            row
            for row in rows
            if row["observed_pair_matches_recomputed_policy"] == "false"
        ],
    )

    finding_rows = list(
        csv.DictReader(
            (ROOT / "comparison/finding_movement_comparison.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    scored_finding_codes = {
        "unresolved_vs_justified",
        "unjustified_vs_justified",
        "justified_vs_justified",
    }
    scored_finding = [
        row
        for row in finding_rows
        if row["comparison_code"] in scored_finding_codes
    ]
    finding_matches = sum(
        row["comparison_code"] == "justified_vs_justified"
        for row in scored_finding
    )
    b_justification_counts = {
        label: sum(
            row["reviewer_b_disposition_justification"] == label
            for row in b_justification_values
        )
        for label in ("justified", "unjustified")
    }
    b_justification_policy_matches = sum(
        row["reviewer_b_justification_matches_policy_check"] == "true"
        for row in rows
    )
    b_no_movement_labels = sum(
        row["reviewer_b_finding_movement_label_as_reported"].startswith(
            "Justified (no "
        )
        for row in finding_rows
    )

    summary = {
        "status": "COMPARISON COMPLETE / RESOLUTION PENDING",
        "reference_commit": (
            "9af5992ecccc4d0c34f5a62f4767f9053254adf6"
        ),
        "case_count": len(claims),
        "endpoint_count": len(endpoint_keys),
        "adjacent_transition_count": sum(
            max(0, len(record["steps"]) - 1) for record in claims
        ),
        "reviewer_a_case_records": len(a_case_rows),
        "reviewer_a_endpoint_records": 0,
        "reviewer_b_endpoint_records": len(b_by_key),
        "disposition_justification": {
            "reviewer_a_transition_judgments": sum(
                int(row["derived_transition_judgment_count"])
                for row in a_case_rows
            ),
            "reviewer_a_retention_assessments": sum(
                row["derived_disposition_unit"] == "retention"
                for row in a_case_rows
            ),
            "reviewer_b_endpoint_labels": len(b_justification_values),
            "reviewer_b_endpoint_label_counts": b_justification_counts,
            "matched_transition_or_retention_records": 0,
            "fraction": None,
            "exclusion_reason": (
                "Reviewer A's reported judgments are 12 transition-level "
                "labels plus 5 no-movement retention assessments; Reviewer "
                "B's 31 labels assess endpoint defensibility. No common "
                "assessment unit is explicitly provided."
            ),
        },
        "reviewer_b_vs_deterministic_policy": {
            "matches": reviewer_b_matches,
            "denominator": len(endpoint_keys),
            "fraction": reviewer_b_matches / len(endpoint_keys),
            "meaning": (
                "Agreement with a deterministic application of the written "
                "synthetic policy to the frozen permitted evidence; not "
                "independently established ground truth."
            ),
        },
        "reviewer_b_endpoint_justification_vs_policy_check": {
            "matches": b_justification_policy_matches,
            "denominator": len(endpoint_keys),
            "fraction": (
                b_justification_policy_matches / len(endpoint_keys)
            ),
            "meaning": (
                "Reviewer B endpoint defensibility labels match whether the "
                "observed disposition equals this package's deterministic "
                "synthetic-policy result. Not transition-level justification "
                "agreement or independently established ground truth."
            ),
        },
        "observed_pair_vs_deterministic_policy": {
            "matches": observed_matches,
            "mismatches": len(observed_mismatches),
            "denominator": len(endpoint_keys),
            "mismatch_endpoints": observed_mismatches,
        },
        "reviewer_a_vs_reviewer_b_endpoint_agreement": {
            "matched_records": 0,
            "exact_agreement_count": 0,
            "fraction": None,
            "reason": (
                "Reviewer A supplied case-level narrative assessments, "
                "not endpoint-granular policy-warranted disposition values."
            ),
        },
        "finding_movement": {
            "reviewer_a_explicit_case_level_finding_assessments": sum(
                row["reviewer_a_finding_assessment_as_reported"]
                != "NOT_REPORTED"
                and row["comparison_code"]
                != "a_not_finding_judgment_b_no_movement"
                for row in finding_rows
            ),
            "reviewer_b_case_level_finding_assessments": len(finding_rows),
            "post_hoc_case_level_judgment_comparison": {
                "matched_records": len(scored_finding),
                "exact_category_matches": finding_matches,
                "fraction": finding_matches / len(scored_finding),
                "scope_note": (
                    "Qualitative mapping of the four cases in which both "
                    "reports express a finding-transition judgment; the "
                    "b-13d9dacc unresolved wording is mapped to unresolved. "
                    "Not a preregistered reliability statistic."
                ),
            },
            "reviewer_b_no_movement_labels_using_justified_category": (
                b_no_movement_labels
            ),
            "reviewer_a_explicit_unchanged_finding_status_records": 1,
        },
        "reviewer_b_explicit_ambiguous_cases": 3,
        "finding_transition_count_from_frozen_materials": 4,
        "resolver_participation": False,
        "reviewer_b_completed_json_file_supplied": False,
    }
    (ROOT / "comparison/summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{summary['status']}: {len(claims)} cases, "
        f"{len(endpoint_keys)} endpoints, "
        f"Reviewer B/policy {reviewer_b_matches}/{len(endpoint_keys)}, "
        f"observed pair/policy {observed_matches}/{len(endpoint_keys)}, "
        f"A/B matched endpoint records 0."
    )


if __name__ == "__main__":
    main()
