from __future__ import annotations

from dataclasses import asdict
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Protocol

from . import VERSION
from .contracts import check_bindings, load

PACKAGE = Path(__file__).resolve().parent
TERMINAL = {"completed", "invalid", "blocked", "interrupted", "unavailable"}
IDENTITIES = {"generator": {"provider": "deterministic-local-fake-v1", "model": "fake-generator-v1"},
              "specialist": {"provider": "deterministic-local-fake-v1", "model": "fake-specialist-v1"}}


def raw_hash(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def digest(obj):
    return raw_hash(encode(obj))


def decode(raw):
    def unique(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError("duplicate_json_key")
            obj[k] = v
        return obj
    def reject(value):
        raise ValueError("nonfinite_json")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject)


def read_file(root, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
        raise ValueError("unsafe_packet_path")
    target = root / path
    if any(p.is_symlink() for p in (target, *target.parents)) or not target.is_file():
        raise ValueError("missing_or_symlinked_artifact:" + name)
    return target.read_bytes()


def validate_manifest(root):
    check_bindings()
    raw = read_file(root, "manifest.json")
    m = decode(raw)
    from .systemone_https_v1.contract import is_https, validate_manifest as validate_https
    if is_https(m):
        return validate_https(root, m, raw)
    if "specialist_observation" in m:
        from .broker_v1.contract import is_broker
        if not is_broker(m) or "full_matrix" in m:
            raise ValueError("typed_observations_require_explicit_offline_broker_route")
    if "transport" in m:
        from .transport import validate_manifest as validate_transport_manifest
        return validate_transport_manifest(root, m, raw)
    if "full_matrix" in m:
        from .full_matrix import validate
        return validate(root, m, raw)
    return validate_slice_manifest(root, m, raw)


def validate_slice_manifest(root, m, raw):
    typed = "specialist_observation" in m
    if set(m) - ({"specialist_observation"} if typed else set()) != {"campaign_id", "manifest_sha256", "execution_contract", "instrument_version", "simulation_only",
                  "packets", "contracts", "positions", "attempt_ceiling", "simulated_budget_units"}:
        raise ValueError("manifest_shape")
    if (m["manifest_sha256"] != digest({k: v for k, v in m.items() if k != "manifest_sha256"})
            or m["simulation_only"] is not True or m["execution_contract"] != VERSION
            or not re.fullmatch(r"synthetic-q1-[a-z0-9-]+", m["campaign_id"])):
        raise ValueError("manifest_binding_or_simulation_boundary")
    instrument, continuation, pins = load()
    if m["instrument_version"] != instrument.VERSION or m["contracts"] != pins:
        raise ValueError("instrument_binding")
    if set(m["packets"]) != {"source", "governing_policy", "challenge_policy"} | ({"replay"} if typed else set()):
        raise ValueError("packet_coverage")
    packet_paths = []
    for kind, ref in m["packets"].items():
        if set(ref) != {"path", "sha256"} or raw_hash(read_file(root, ref["path"])) != ref["sha256"]:
            raise ValueError("packet_binding:" + kind)
        packet_paths.append(ref["path"])
        if Path(ref["path"]).name != ref["path"] or ref["path"] in ("manifest.json", "campaign.sqlite3", ".lock"):
            raise ValueError("unsafe_packet_filename")
        if kind not in ("source", "replay"):
            packet = decode(read_file(root, ref["path"]))
            if (packet.get("simulation_only") is not True or not packet.get("id", "").startswith("synthetic-")
                    or kind == "governing_policy" and packet.get("release_authority") is not False
                    or kind == "challenge_policy" and packet.get("governing_authority") is not False):
                raise ValueError("simulation_policy_authority_boundary")
    if len(set(packet_paths)) != (4 if typed else 3) or m["packets"]["governing_policy"] == m["packets"]["challenge_policy"]:
        raise ValueError("policy_separation")
    for key in ("attempt_ceiling", "simulated_budget_units"):
        if type(m[key]) is not int or m[key] < 1:
            raise ValueError("invalid_budget")
    if typed:
        from .systemone_typed_v1.replay import validate_extension, identity as typed_identity
        replay_assessment = validate_extension(root, m)
    seen, by_id, jobs = set(), {}, []
    if not isinstance(m["positions"], list) or not m["positions"]:
        raise ValueError("empty_schedule")
    expected_bindings = {k: v["sha256"] for k, v in m["packets"].items()}
    for p in m["positions"]:
        if set(p) != {"id", "kind", "role", "arm", "path", "dependencies", "assessment_parent", "specialist_parent",
                      "identity", "packet_bindings", "case_id", "variant_id", "fake_behavior", "fake_disposition"}:
            raise ValueError("position_shape")
        ident, deps = p["id"], p["dependencies"]
        if (not re.fullmatch(r"[a-z0-9-]+", ident) or ident in seen or not isinstance(deps, list)
                or len(set(deps)) != len(deps) or any(d not in seen for d in deps)):
            raise ValueError("unknown_duplicate_or_nontopological_dependency")
        if (p["kind"] not in IDENTITIES or p["identity"] != (typed_identity(p) if typed else IDENTITIES[p["kind"]])
                or p["packet_bindings"] != expected_bindings
                or p["case_id"] != (replay_assessment["case_id"] if typed else m["campaign_id"])
                or p["variant_id"] != (replay_assessment["variant_id"] if typed else "simulation")):
            raise ValueError("position_identity_or_packet_binding")
        if (p["arm"] not in instrument.ARMS or p["path"] not in ("none", "native_simulation", "carl_simulation")
                or p["role"] not in ("baseline", "control", "specialist", "challenge_continuation", "diagnostic_branch")
                or p["fake_behavior"] not in ("valid", "invalid_lifecycle", "exception", "unknown_identity")
                or p["fake_disposition"] not in ("pass", "review_required")):
            raise ValueError("simulation_role_or_behavior")
        parents = {x for x in (p["assessment_parent"], p["specialist_parent"]) if x is not None}
        if set(deps) != parents or any(by_id[d]["packet_bindings"] != p["packet_bindings"] for d in deps):
            raise ValueError("parent_or_packet_linkage")
        ap, sp = p["assessment_parent"], p["specialist_parent"]
        if (ap is not None and by_id[ap]["kind"] != "generator"
                or sp is not None and by_id[sp]["kind"] != "specialist"
                or p["kind"] == "specialist" and (ap is None or sp is not None)
                or p["kind"] == "generator" and ((p["arm"] == "B0") != (ap is None))
                or p["kind"] == "generator" and p["arm"].startswith("E") != (sp is not None)
                or sp is not None and by_id[sp]["assessment_parent"] != ap):
            raise ValueError("assessment_specialist_parent_context")
        seen.add(ident); by_id[ident] = p
        jobs.append({"job_id": ident, "dependencies": deps, "adapter": p["kind"]})
    if sum(p["arm"] == "B0" for p in m["positions"]) != 1:
        raise ValueError("exactly_one_shared_synthetic_baseline_required")
    # Reuse the frozen planner's schedule checks without treating its output as a reservation.
    continuation.plan_continuation(jobs, {}, explicitly_authorized=False, reserved_attempts=0,
                                 max_attempts=m["attempt_ceiling"], credentials_available={}, identity_verified=False)
    return m, raw


def request_for(m, p, receipts, root):
    from .systemone_https_v1.contract import is_https, request_for as https_request
    if is_https(m):
        return https_request(m, p, receipts, root)
    if "specialist_observation" in m:
        from .systemone_typed_v1.replay import request_for as typed_request
        return typed_request(m, p, receipts, root)
    if "full_matrix" in m:
        from .full_matrix import matrix_request
        return matrix_request(m, p, receipts, root)
    return slice_request(m, p, receipts, root)


def slice_request(m, p, receipts, root):
    instrument, _, _ = load()
    ap, sp = p["assessment_parent"], p["specialist_parent"]
    source = read_file(root, m["packets"]["source"]["path"]).decode()
    previous = receipts[ap]["diagnostics"]["parsed"] if ap else None
    req = {"schema": VERSION + "-simulation-request", "simulation_only": True,
           "manifest_sha256": m["manifest_sha256"], "position": p,
           "packet_bindings": p["packet_bindings"], "source_text": source,
           "governing_policy": decode(read_file(root, m["packets"]["governing_policy"]["path"])),
           "challenge_policy": decode(read_file(root, m["packets"]["challenge_policy"]["path"])),
           "parents": {d: digest(receipts[d]) for d in p["dependencies"]},
           "previous_assessment": previous,
           "simulation_review_request": None if not sp else {
               "authority": "simulation_placeholder_no_policy_warrant_or_threshold",
               "specialist_receipt_sha256": digest(receipts[sp])},
           "instrument_request": None}
    if p["kind"] == "specialist":
        diagnostic = instrument.AssessmentDiagnostic(**receipts[ap]["diagnostics"])
        req["instrument_request"] = instrument.build_judge_request(diagnostic, source, "synthetic_unverified_test_text")
    return req


def validate_response(p, req, raw, observed):
    if observed != p["identity"]:
        return "unavailable", "unknown_or_mismatched_fake_identity", {"parsed": None, "availability": "identity_unavailable"}
    instrument, _, _ = load()
    try:
        text = raw.decode("utf-8")
        if p["kind"] == "generator":
            diagnostic = asdict(instrument.inspect_assessment(text, p, req["source_text"], req["previous_assessment"]))
            return ("completed", None, diagnostic) if diagnostic["parsed"] is not None else (
                "invalid", diagnostic["error"], diagnostic)
        if "instrument_contract" in req:
            from .systemone_typed_v1 import VERSION as TYPED_VERSION
            from .systemone_typed_v1.replay import validate_response as typed_validate
            if req["instrument_contract"] != TYPED_VERSION:
                raise ValueError("unknown_specialist_instrument_contract")
            return typed_validate(p, req, raw)
        judged = instrument.parse_judgments(text, req["instrument_request"])
        return "completed", None, {"parsed": decode(raw), "judgments": [asdict(j) for j in judged.judgments]}
    except (ValueError, UnicodeError, KeyError, TypeError) as exc:
        return "invalid", str(exc), {"parsed": None, "failure_layer": "specialist_or_decoding", "error": str(exc)}


class Provider(Protocol):
    def invoke(self, request: dict, record_invocation) -> tuple[bytes, dict | None]: ...


class FakeProvider:
    """Deterministic local implementation; contains no transport, tools or adapters."""
    def invoke(self, req, record_invocation):
        record_invocation()
        p = req["position"]
        if p["fake_behavior"] == "exception":
            raise RuntimeError("synthetic_exception_before_response")
        if p["kind"] == "specialist":
            instrument, _, _ = load()
            obj = {"schema": instrument.VERSION + "-judgments",
                   "request_sha256": req["instrument_request"]["request_sha256"], "claims": []}
            for c in req["previous_assessment"]["claims"]:
                obj["claims"].append({"claim_id": c["claim_id"], **{
                    dim: {"label": label, "score": score, "rationale": "Scripted local test value, no empirical judgment.",
                          "evidence_quotes": []}
                    for dim, label, score in (("source_entailment", "supported", 1),
                                              ("independent_verification", "not_independently_verified", None),
                                              ("impact_inference", "not_applicable", None))}})
            if p["fake_behavior"] == "invalid_specialist":
                obj["claims"] = []
            if p["fake_behavior"] == "null_scores":
                for claim in obj["claims"]:
                    claim["source_entailment"].update(label="unverifiable", score=None)
        else:
            previous = req["previous_assessment"]
            claims = copy.deepcopy(previous["claims"]) if previous else [{
                "claim_id": "c1", "claim": "The synthetic change updates documentation.",
                "evidence_quotes": [req["source_text"].strip()], "confidence": 0.5,
                "limitations": ["Synthetic supplied text; no authenticated implementation."]}]
            changes = [] if previous is None else [{"claim_id": c["claim_id"], "action": "retained",
                                                    "reason": "Identical scripted claim object."} for c in claims]
            if "full_matrix_contract" in req and previous is None:
                claims[0]["claim"] = req["source_text"].strip()
            if p["fake_behavior"] == "invalid_lifecycle":
                changes = []
            obj = {"case_id": p["case_id"], "variant_id": p["variant_id"], "claims": claims,
                   "disposition": p["fake_disposition"], "uncertainties": [], "changes": changes}
            if "full_matrix_contract" in req and previous is not None:
                obj["uncertainties"] = ["synthetic-private-history:" + p["unit_id"] + ":" + p["arm"]]
        observed = None if p["fake_behavior"] == "unknown_identity" else p["identity"]
        if p["fake_behavior"] == "mismatched_identity":
            observed = {**p["identity"], "model": "unknown-fake-model"}
        return encode(obj), observed
