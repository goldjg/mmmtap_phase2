"""Local-only binding, policy partition checks and staged training exports."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import random

PACKAGE = Path(__file__).resolve().parent
DISPOSITIONS = {"pass", "warn", "review_required", "fail", "insufficient_evidence"}
PREDICATES = ("blocking_violation", "evidence_sufficient", "human_review_pending", "warning_needed")
VERSION = "rd05-offline-v1"
EXERCISE_FILES = {
    "claims.json", "pairs.json", "reviewer_A.json", "reviewer_B.json", "resolution.json",
    "custodian/fixtures.json", "custodian/references.json", "custodian/identity_key.json",
    "custodian/linkage.json",
}
PACKAGE_FILES = {
    "__init__.py", "authored.py", "tool.py", "test_tool.py", "policy.v1.json", "README.md", "REPORT.md",
} | {"exercise.v1/" + name for name in EXERCISE_FILES}


class QualificationError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise QualificationError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                      allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def seal(value):
    return {**value, "sha256": digest(value)}


def check_seal(value):
    require(isinstance(value, dict) and "sha256" in value, "missing digest")
    require(value["sha256"] == digest({k: v for k, v in value.items() if k != "sha256"}),
            "digest mismatch")


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def load(path):
    def reject_constant(value):
        raise QualificationError(f"nonfinite JSON: {value}")
    return json.loads(Path(path).read_text(), object_pairs_hook=_unique_object,
                      parse_constant=reject_constant)


def write(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + "\n")


def keys(obj, expected, context):
    require(isinstance(obj, dict) and set(obj) == set(expected), f"{context}: exact keys required")


def expected_rule(state):
    """Independent toy-spec oracle, not evidence adjudication or challenge mapping."""
    if state["blocking_violation"]:
        return "fail"
    if not state["evidence_sufficient"]:
        return "insufficient_evidence"
    if state["human_review_pending"]:
        return "review_required"
    return "warn" if state["warning_needed"] else "pass"


def decide(policy, state):
    keys(state, PREDICATES, "mandatory predicate mapping")
    require(all(type(v) is bool for v in state.values()), "ambiguous mandatory predicate")
    matches = [r for r in policy["rules"]
               if all(state[k] == v for k, v in r["when"].items())]
    require(matches, "missing rule mapping")
    order = {rule_id: index for index, rule_id in enumerate(policy["precedence"])}
    return min(matches, key=lambda rule: order[rule["id"]])


def triggered_rules(policy, state):
    keys(state, PREDICATES, "mandatory predicate mapping")
    require(all(type(v) is bool for v in state.values()), "ambiguous mandatory predicate")
    matches = [r for r in policy["rules"]
               if r["id"] != "R-PASS" and all(state[k] == v for k, v in r["when"].items())]
    return [rule["id"] for rule in matches]


def validate_policy(policy):
    keys(policy, {"version", "synthetic", "purpose", "scope", "applicability", "effective",
                  "provenance", "authority", "evidence_requirements", "predicates", "rules",
                  "precedence", "exceptions", "reassessment", "allowed_domain_principles"}, "policy")
    require(policy["version"] == "rd05-synthetic-policy-v1" and policy["synthetic"] is True,
            "synthetic version required")
    require(policy["scope"] == "synthetic-change-review", "wrong scope")
    keys(policy["authority"], {"reviewer", "enforcement", "challenge"}, "authority")
    require(policy["authority"]["reviewer"] == "fictional-security-reviewer"
            and policy["authority"]["enforcement"] == "none", "fictional authority only")
    require(policy["predicates"] == list(PREDICATES), "unknown/missing mandatory predicate")
    keys(policy["evidence_requirements"], {"E-DIFF", "E-TEST", "E-REVIEW"}, "evidence requirements")
    for field in ("purpose", "applicability", "effective", "provenance", "exceptions", "reassessment"):
        require(isinstance(policy[field], str) and policy[field].strip(), f"missing {field}")
    for value in [*policy["evidence_requirements"].values(), *policy["authority"].values()]:
        require(isinstance(value, str) and value.strip(), "empty normative context")
    require(isinstance(policy["allowed_domain_principles"], list)
            and policy["allowed_domain_principles"]
            and all(isinstance(x, str) and x.strip() for x in policy["allowed_domain_principles"]),
            "missing allowed domain principles")
    require(isinstance(policy["rules"], list) and len(policy["rules"]) == 5, "five rules required")
    ids = set()
    for rule in policy["rules"]:
        keys(rule, {"id", "disposition", "when", "evidence_ids", "obligation", "resolution"}, "rule")
        require(rule["id"] not in ids and rule["disposition"] in DISPOSITIONS, "duplicate/unknown rule")
        ids.add(rule["id"])
        require(isinstance(rule["when"], dict) and rule["when"]
                and set(rule["when"]) <= set(PREDICATES)
                and all(type(v) is bool for v in rule["when"].values()), "ambiguous rule conditions")
        require(isinstance(rule["evidence_ids"], list) and rule["evidence_ids"]
                and len(set(rule["evidence_ids"])) == len(rule["evidence_ids"])
                and set(rule["evidence_ids"]) <= set(policy["evidence_requirements"]), "rule evidence reference")
        require(all(isinstance(rule[k], str) and rule[k].strip()
                    for k in ("obligation", "resolution")), "missing rule obligation")
    require({r["disposition"] for r in policy["rules"]} == DISPOSITIONS, "disposition coverage")
    require(policy["precedence"] == ["R-BLOCK", "R-EVIDENCE", "R-REVIEW", "R-WARN", "R-PASS"]
            and set(policy["precedence"]) == ids, "precedence is fixed for synthetic version")
    bindings = {
        "R-BLOCK": ("fail", ["E-DIFF"], "violation_remediation"),
        "R-EVIDENCE": ("insufficient_evidence", ["E-DIFF", "E-TEST"], "evidence_remediation_and_reassessment"),
        "R-REVIEW": ("review_required", ["E-DIFF", "E-TEST", "E-REVIEW"],
                     "authorised_human_decision_and_reassessment"),
        "R-WARN": ("warn", ["E-DIFF", "E-TEST"], "record_coverage_warning"),
        "R-PASS": ("pass", ["E-DIFF", "E-TEST"], "recommendation_only"),
    }
    for rule in policy["rules"]:
        require((rule["disposition"], rule["evidence_ids"], rule["resolution"]) == bindings[rule["id"]],
                "rule evidence/resolution binding")
    predicates = {
        "R-BLOCK": {"blocking_violation": True},
        "R-EVIDENCE": {"evidence_sufficient": False},
        "R-REVIEW": {"human_review_pending": True},
        "R-WARN": {"warning_needed": True},
        "R-PASS": {"blocking_violation": False, "evidence_sufficient": True,
                   "human_review_pending": False, "warning_needed": False},
    }
    for rule in policy["rules"]:
        require(rule["when"] == predicates[rule["id"]], "rule trigger mapping")
    for values in itertools.product((False, True), repeat=len(PREDICATES)):
        state = dict(zip(PREDICATES, values))
        require(decide(policy, state)["disposition"] == expected_rule(state),
                "contradictory synthetic semantics")
    return 16


def artifact(kind, change_id, facts, adequacy="adequate"):
    return seal({"requirement_id": kind, "change_id": change_id, "facts": facts,
                 "adequacy": adequacy, "provenance": "synthetic-authenticated-artifact",
                 "text": json.dumps(facts, sort_keys=True)})


def make_bundle(policy):
    from .authored import cases
    trajectories, references = [], []
    for case in cases():
        change_id = case["case_id"]
        source = seal({"text": case["source"], "provenance": "synthetic-supplied-description"})
        endpoints = []
        for index, authored in enumerate(case["steps"]):
            evidence = []
            if authored["diff"]:
                evidence.append(artifact("E-DIFF", change_id, {
                    "credential_logging": authored["logging"],
                    "restricted_interface": authored["restricted"],
                    "limited_platform_coverage": authored["warning"],
                    "logging_scope": "ambiguous" if authored["ambiguous"] else "explicit",
                }, "indeterminate" if authored["ambiguous"] else "adequate"))
            if authored["tests"]:
                evidence.append(artifact("E-TEST", change_id, {"scope_covered": True}))
            if authored["approval"]:
                evidence.append(artifact("E-REVIEW", change_id, {
                    "authority": "fictional-security-reviewer", "decision": "approved",
                }))
            packet = seal({"change_id": change_id, "scope": policy["scope"],
                           "policy_sha256": digest(policy), "source_sha256": source["sha256"],
                           "step": index, "evidence": evidence,
                           "neutral_challenge_evidence": []})
            obj = seal({**authored["assessment"], "change_id": change_id,
                        "packet_sha256": packet["sha256"], "policy_sha256": digest(policy)})
            endpoints.append({"packet": packet, "assessment": obj,
                              "challenge_text": authored["challenge"]})
        trajectories.append({"id": change_id, "source": source, "endpoints": endpoints})
        references.append({"id": change_id, "title": case["title"], "metadata": case["metadata"],
                           "suggestions": case["suggestions"],
                           "coverage": [int(change_id[1:])]})
    return (seal({"version": VERSION, "synthetic": True, "policy_sha256": digest(policy),
                  "trajectories": trajectories}),
            {"version": VERSION, "private_authored_not_ground_truth": True,
             "references": references})


def state_from_packet(policy, packet):
    by_id = {e["requirement_id"]: e for e in packet["evidence"]}
    diff, test, approval = (by_id.get(k) for k in ("E-DIFF", "E-TEST", "E-REVIEW"))
    good_diff = diff is not None and diff["adequacy"] == "adequate"
    good_test = test is not None and test["adequacy"] == "adequate" and test["facts"]["scope_covered"]
    approved = approval is not None and approval["adequacy"] == "adequate"
    if approved:
        approved = (approval["facts"]["authority"] == policy["authority"]["reviewer"]
                    and approval["facts"]["decision"] == "approved")
    return {"blocking_violation": bool(good_diff and diff["facts"]["credential_logging"]),
            "evidence_sufficient": bool(good_diff and good_test),
            "human_review_pending": bool(good_diff and diff["facts"]["restricted_interface"] and not approved),
            "warning_needed": bool(good_diff and diff["facts"]["limited_platform_coverage"])}


def validate_bundle(policy, bundle):
    validate_policy(policy)
    check_seal(bundle)
    keys(bundle, {"version", "synthetic", "policy_sha256", "trajectories", "sha256"}, "bundle")
    require(bundle["version"] == VERSION and bundle["synthetic"] is True
            and bundle["policy_sha256"] == digest(policy), "bundle policy binding")
    require(isinstance(bundle["trajectories"], list) and bundle["trajectories"], "empty fixture bundle")
    ids, rule_counts, trigger_counts, observed = set(), {}, {}, set()
    for trajectory in bundle["trajectories"]:
        keys(trajectory, {"id", "source", "endpoints"}, "trajectory")
        require(isinstance(trajectory["id"], str) and trajectory["id"] not in ids, "trajectory identity")
        ids.add(trajectory["id"])
        source = trajectory["source"]
        keys(source, {"text", "provenance", "sha256"}, "source")
        check_seal(source)
        require(isinstance(source["text"], str) and source["text"], "empty source")
        require(source["provenance"] == "synthetic-supplied-description", "source provenance")
        require(isinstance(trajectory["endpoints"], list) and len(trajectory["endpoints"]) >= 2,
                "paired endpoints required")
        for index, endpoint in enumerate(trajectory["endpoints"]):
            keys(endpoint, {"packet", "assessment", "challenge_text"}, "endpoint")
            require(isinstance(endpoint["challenge_text"], str), "challenge text type")
            packet, obj = endpoint["packet"], endpoint["assessment"]
            keys(packet, {"change_id", "scope", "policy_sha256", "source_sha256", "step", "evidence",
                          "neutral_challenge_evidence", "sha256"}, "packet")
            check_seal(packet)
            require(packet["scope"] == policy["scope"] and packet["change_id"] == trajectory["id"]
                    and type(packet["step"]) is int and packet["step"] == index
                    and packet["source_sha256"] == source["sha256"]
                    and packet["policy_sha256"] == digest(policy), "packet binding")
            # This corpus's challenges add no independent facts; never hide novel evidence silently.
            require(packet["neutral_challenge_evidence"] == [], "neutral extract must be explicitly authored")
            require(isinstance(packet["evidence"], list), "evidence list required")
            evidence_ids = set()
            for evidence in packet["evidence"]:
                keys(evidence, {"requirement_id", "change_id", "facts", "adequacy", "provenance",
                                "text", "sha256"}, "evidence")
                check_seal(evidence)
                kind = evidence["requirement_id"]
                require(kind in policy["evidence_requirements"] and kind not in evidence_ids,
                        "unknown/duplicate evidence reference")
                evidence_ids.add(kind)
                require(evidence["change_id"] == trajectory["id"], "evidence change binding")
                require(evidence["provenance"] == "synthetic-authenticated-artifact"
                        and evidence["adequacy"] in {"adequate", "inadequate", "indeterminate"},
                        "evidence adequacy/provenance")
                facts = evidence["facts"]
                if kind == "E-DIFF":
                    keys(facts, {"credential_logging", "restricted_interface", "limited_platform_coverage",
                                 "logging_scope"}, "diff facts")
                    require(all(type(facts[k]) is bool for k in
                                ("credential_logging", "restricted_interface", "limited_platform_coverage")),
                            "ambiguous synthetic fact")
                    require(facts["logging_scope"] in {"explicit", "ambiguous"}, "logging scope")
                    require(facts["logging_scope"] != "ambiguous" or evidence["adequacy"] != "adequate",
                            "contradictory evidence adequacy")
                elif kind == "E-TEST":
                    keys(facts, {"scope_covered"}, "test facts")
                    require(type(facts["scope_covered"]) is bool, "ambiguous test fact")
                    require(facts["scope_covered"] or evidence["adequacy"] != "adequate",
                            "contradictory test coverage/adequacy")
                else:
                    keys(facts, {"authority", "decision"}, "approval facts")
                    require(facts["authority"] == policy["authority"]["reviewer"]
                            and facts["decision"] in {"approved", "denied"}, "approval authority/decision")
                require(evidence["text"] == json.dumps(facts, sort_keys=True), "evidence text/fact contradiction")
            keys(obj, {"disposition", "findings", "conditions", "reported_rationale", "change_id",
                       "packet_sha256", "policy_sha256", "sha256"}, "assessment")
            check_seal(obj)
            require(obj["change_id"] == trajectory["id"] and obj["packet_sha256"] == packet["sha256"]
                    and obj["policy_sha256"] == digest(policy), "assessment binding")
            require(obj["disposition"] in DISPOSITIONS, "assessment disposition")
            require(isinstance(obj["conditions"], list)
                    and all(isinstance(x, str) for x in obj["conditions"])
                    and isinstance(obj["reported_rationale"], str), "assessment text")
            require(isinstance(obj["findings"], list) and obj["findings"], "findings required")
            finding_ids = set()
            for finding in obj["findings"]:
                keys(finding, {"id", "text"}, "finding")
                require(isinstance(finding["id"], str) and finding["id"] not in finding_ids
                        and isinstance(finding["text"], str) and finding["text"], "finding identity/text")
                finding_ids.add(finding["id"])
            observed.add(obj["disposition"])
            rule = decide(policy, state_from_packet(policy, packet))
            rule_counts[rule["id"]] = rule_counts.get(rule["id"], 0) + 1
            for triggered in triggered_rules(policy, state_from_packet(policy, packet)):
                trigger_counts[triggered] = trigger_counts.get(triggered, 0) + 1
    require(observed == DISPOSITIONS, "all five observed dispositions required")
    require(set(rule_counts) == set(policy["precedence"]), "all five policy rules exercised")
    return {"selected_rule_counts": rule_counts, "triggered_obligation_counts": trigger_counts}


def validate_references(bundle, references):
    keys(references, {"version", "private_authored_not_ground_truth", "references"}, "reference bundle")
    require(references["version"] == VERSION and references["private_authored_not_ground_truth"] is True,
            "authored reference boundary")
    rows = references["references"]
    require(isinstance(rows, list) and len(rows) == len(bundle["trajectories"]), "reference coverage")
    by_id = {t["id"]: t for t in bundle["trajectories"]}
    seen = set()
    for row in rows:
        keys(row, {"id", "title", "metadata", "suggestions", "coverage"}, "reference row")
        require(row["id"] in by_id and row["id"] not in seen, "reference identity")
        seen.add(row["id"])
        trajectory = by_id[row["id"]]
        require(len(row["suggestions"]) == len(trajectory["endpoints"]) - 1, "step reference coverage")
        for index, suggestion in enumerate(row["suggestions"]):
            keys(suggestion, {"disposition_movement", "finding_movements", "reason", "independent_reference"},
                 "reference suggestion")
            require(suggestion["independent_reference"] is False
                    and suggestion["disposition_movement"] in {None, "justified", "unjustified", "mixed", "unresolved"},
                    "reference category")
            before, after = trajectory["endpoints"][index:index + 2]
            changed = before["assessment"]["disposition"] != after["assessment"]["disposition"]
            require(changed == (suggestion["disposition_movement"] is not None), "no-movement reference mismatch")
            for movement in suggestion["finding_movements"]:
                keys(movement, {"before", "after", "category"}, "finding suggestion")
                require(movement["before"] in {f["id"] for f in before["assessment"]["findings"]}
                        and movement["after"] in {f["id"] for f in after["assessment"]["findings"]}
                        and movement["category"] in {"justified", "unjustified", "mixed", "unresolved"},
                        "finding reference")


def exports(policy, bundle, references, seed="rd05-training-v1"):
    validate_bundle(policy, bundle)
    validate_references(bundle, references)
    rng = random.Random(seed)
    trajectories = deepcopy(bundle["trajectories"])
    rng.shuffle(trajectories)
    claims, pairs, linkage, private = [], [], [], []
    ref = {r["id"]: r for r in references["references"]}
    for trajectory in trajectories:
        blind_id = f"b-{rng.getrandbits(96):024x}"
        common = {"blind_id": blind_id, "source": trajectory["source"]}
        csteps, psteps, late = [], [], []
        for endpoint in trajectory["endpoints"]:
            packet = deepcopy(endpoint["packet"])
            # Strip identity, but retain byte identity receipt and original scope/time.
            evidence = [{k: v for k, v in e.items() if k not in {"change_id", "sha256"}}
                        | {"original_sha256": e["sha256"]} for e in packet["evidence"]]
            csteps.append({"step": packet["step"], "evidence": evidence,
                           "neutral_challenge_evidence": packet["neutral_challenge_evidence"],
                           "source_sha256": packet["source_sha256"],
                           "policy_sha256": packet["policy_sha256"],
                           "original_packet_sha256": packet["sha256"],
                           "original_assessment_sha256": endpoint["assessment"]["sha256"],
                           "findings": endpoint["assessment"]["findings"]})
            psteps.append({"step": packet["step"], "disposition": endpoint["assessment"]["disposition"],
                           "conditions": endpoint["assessment"]["conditions"]})
            late.append({"step": packet["step"], "challenge_text": endpoint["challenge_text"],
                         "reported_rationale": endpoint["assessment"]["reported_rationale"]})
        claims.append({**common, "steps": csteps})
        pairs.append({"blind_id": blind_id, "steps": psteps})
        linkage.append({"blind_id": blind_id, "steps": late})
        private.append({"blind_id": blind_id, "original_id": trajectory["id"], "reference": ref[trajectory["id"]]})
    return {"claims": {"version": VERSION, "policy": policy, "records": claims},
            "pairs": {"version": VERSION, "records": pairs},
            "linkage": {"version": VERSION, "records": linkage},
            "private": {"version": VERSION, "records": private}}


def annotation_template(exported, reviewer_id):
    records = []
    for row in exported["claims"]["records"]:
        step_count = len(row["steps"])
        pair_ids = [(i, i + 1) for i in range(step_count - 1)]
        if step_count > 2:
            pair_ids.append((0, step_count - 1))
        records.append({
            "blind_id": row["blind_id"],
            "endpoint_labels": [
                {"step": step["step"], "assertions": [
                    {"assertion_id": finding["id"], "raw_finding_id": finding["id"],
                     "text": finding["text"], "start": 0, "end": len(finding["text"]),
                     "source_entailment": None, "independent_verification": None,
                     "impact_inference": None, "dimension_rationales": {},
                     "evidence_anchors": [], "adequacy": None, "scope": None,
                     "materiality": None, "unresolved_reason": None}
                    for finding in step["findings"]]}
                for step in row["steps"]],
            "atomic_alignment": [],
            "disposition_pairs": [
                {"before_step": before, "after_step": after, "before_value": None,
                 "after_value": None, "changed": None, "availability": None}
                for before, after in pair_ids],
            "operational_action_pairs": [],
            "finding_movements": [],
            "disposition_justification": [
                {"before_step": before, "after_step": after, "movement_status": None,
                 "category": None, "policy_rule_ids": [], "evidence_anchors": [],
                 "rationale": None, "endpoint_defensibility": {"before": None, "after": None},
                 "unresolved_reason": None}
                for before, after in pair_ids],
            "finding_justifications": [], "retention_justification": [], "auxiliary_edits": [],
            "evidence_anchors": [], "policy_rule_ids": [], "analysis_basis": "time_available",
            "reported_reason_links": [], "unresolved_issues": [], "suspected_unblinding": [],
        })
    return {"version": VERSION, "reviewer_id": reviewer_id, "independent": True,
            "frozen_at": None, "records": records}


def build(output):
    require(not output.exists(), "output already exists; do not overwrite reviewer work")
    policy = load(PACKAGE / "policy.v1.json")
    bundle, references = make_bundle(policy)
    exported = exports(policy, bundle, references)
    output.mkdir(parents=True)
    for name in ("claims", "pairs"):
        write(output / f"{name}.json", exported[name])
    private = output / "custodian"
    private.mkdir()
    write(private / "fixtures.json", bundle)
    write(private / "references.json", references)
    write(private / "identity_key.json", exported["private"])
    write(private / "linkage.json", exported["linkage"])
    for reviewer in ("A", "B"):
        write(output / f"reviewer_{reviewer}.json", annotation_template(exported, reviewer))
    write(output / "resolution.json", {
        "version": VERSION, "resolver_id": None, "independent_sheets_sha256": [],
        "disagreements": [], "resolutions": [], "unresolved_issues": [], "amendments": []})
    return verify(output)


def verify(output):
    paths = list(output.rglob("*"))
    require(not any(p.is_symlink() for p in paths), "symlink is not a custody boundary")
    require({p.relative_to(output).as_posix() for p in paths if p.is_file()} == EXERCISE_FILES,
            "missing or unexpected exercise files")
    policy = load(PACKAGE / "policy.v1.json")
    bundle = load(output / "custodian/fixtures.json")
    references = load(output / "custodian/references.json")
    coverage = validate_bundle(policy, bundle)
    expected = exports(policy, bundle, references)
    for name in ("claims", "pairs", "linkage", "private"):
        path = output / ({"linkage": "custodian/linkage.json", "private": "custodian/identity_key.json"}
                         .get(name, f"{name}.json"))
        require(load(path) == expected[name], f"export separation/binding mismatch: {name}")
    for reviewer in ("A", "B"):
        require(load(output / f"reviewer_{reviewer}.json") == annotation_template(expected, reviewer),
                "blank independent template mismatch")
    require(load(output / "resolution.json") == {
        "version": VERSION, "resolver_id": None, "independent_sheets_sha256": [],
        "disagreements": [], "resolutions": [], "unresolved_issues": [], "amendments": []},
        "blank resolver template mismatch")
    # Structural allowlist exports are compared byte-semantically above, not just searched for a title.
    return {"status": "OFFLINE DEVELOPMENT COMPLETE", "policy_truth_table_states": 16,
            "trajectories": len(bundle["trajectories"]),
            "endpoints": sum(len(t["endpoints"]) for t in bundle["trajectories"]),
            "rule_coverage": coverage["selected_rule_counts"],
            "triggered_obligation_counts": coverage["triggered_obligation_counts"],
            "provider_calls": 0,
            "reviewers_completed": 0, "rd03": "PROPOSED"}


def inventory(directory, create=False):
    paths = list(directory.rglob("*"))
    require(not any(p.is_symlink() for p in paths), "package symlink")
    files = {p.relative_to(directory).as_posix() for p in paths if p.is_file()}
    require(files - {"inventory.v1.json"} == PACKAGE_FILES, "exact package file inventory required")
    obj = {"version": VERSION, "digest_encoding": "SHA-256 of exact file bytes",
           "self_hash_boundary": "inventory.v1.json excluded from its own list; Git commit binds it",
           "files": [{"path": name, "bytes": (directory / name).stat().st_size,
                      "sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()}
                     for name in sorted(PACKAGE_FILES)]}
    if create:
        require(not (directory / "inventory.v1.json").exists(), "inventory exists; do not overwrite")
        write(directory / "inventory.v1.json", obj)
    else:
        require(load(directory / "inventory.v1.json") == obj, "inventory byte/hash mismatch")
    return {"inventory_files": len(obj["files"]), "status": "verified" if not create else "created"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "inventory", "verify-inventory"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            result = build(args.directory)
        elif args.command == "verify":
            result = verify(args.directory)
        else:
            result = inventory(args.directory, create=args.command == "inventory")
    except (QualificationError, OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"RD05 verification failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
