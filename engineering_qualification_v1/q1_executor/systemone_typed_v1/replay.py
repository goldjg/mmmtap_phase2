"""Pinned historical evidence injection into the EXISTING Q1/broker machinery.

No new scheduler, provider transport, inference or scientific reclassification.
"""
import base64
import copy
from decimal import Decimal
from pathlib import Path

from . import VERSION
from .contract import bindings, derive_carl, parse
from ..model import PACKAGE, IDENTITIES, decode, digest, encode, raw_hash, read_file

ROOT = PACKAGE.parents[1]
RESOLUTION = ROOT / "engineering_qualification_v1/systemone_contract_resolution_v1"
SELECTION_SHA256 = "4153a4cdb9c7923f30b0f43a70ba28633c08f2110a90e5e487ea4628bc29969a"
NEGATIVES = {"missing", "extra", "duplicate", "wrong_type"}


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


def unb64(value):
    return base64.b64decode(value, validate=True)


def checked(root, path, expected):
    raw = read_file(root, path)
    if raw_hash(raw) != expected:
        raise ValueError("historical_artifact_binding:" + path)
    return raw


def selection():
    return decode(checked(RESOLUTION, "evidence/selection.json", SELECTION_SHA256))


def load_record(ident):
    selected = selection()
    manifest_ref = selected["pilot_manifest"]
    pilot = decode(checked(ROOT, manifest_ref["path"], manifest_ref["sha256"]))
    if pilot["manifest_sha256"] != digest({k: v for k, v in pilot.items() if k != "manifest_sha256"}):
        raise ValueError("historical_pilot_manifest_binding")
    sample = next(s for s in selected["samples"] if s["id"] == ident)
    originals = {e["path"]: checked(ROOT, e["path"], e["sha256"]) for e in sample["record_files"]}
    wrapper = decode(originals[sample["record_files"][0]["path"]])
    stdout = unb64(wrapper["stdout"])
    receipt = decode(stdout) if sample["mechanism"] == "carl_jev" else None
    if ident == "smoke-choice":
        manifest = decode(originals["adapter_qualification_v1/live_smoke_manifest.json"])
        request = manifest["entries"]["native_jev"]["payload"]
        request_raw = encode(request)
        intent = decode(originals["adapter_qualification_v1/attempts/native_jev/intent.json"])
        if intent["payload_sha256"] != raw_hash(request_raw) or manifest["entries"]["native_jev"]["payload_sha256"] != raw_hash(request_raw):
            raise ValueError("qualification_request_binding")
    else:
        payload = decode(originals[sample["record_files"][1]["path"]])["payload"]
        request_raw = unb64(payload["native_request"]) if receipt else encode(payload)
        request = decode(request_raw)
        result = decode(originals[sample["record_files"][3]["path"]])
        if result["job_id"] != sample["job_id"] or result["mode"] != "live":
            raise ValueError("pilot_origin_binding")
        parent = Path(sample["record_files"][0]["path"]).parent
        for name, expected in result["artifact_sha256"].items():
            checked(ROOT, (parent / name).as_posix(), expected)
        if not receipt and wrapper["provenance"]["request_sha256"] != raw_hash(request_raw):
            raise ValueError("native_request_custody_binding")
    raw = unb64(receipt["raw_response"]) if receipt else stdout
    if raw != checked(RESOLUTION, sample["response_file"], sample["response_sha256"]):
        raise ValueError("historical_entity_bytes_mismatch")
    prepared = None
    metadata = {"historical_kind": sample["kind"], "artifacts": sample["record_files"],
                "selection_sha256": SELECTION_SHA256,
                "request_bytes_basis": "captured_carl_request_body" if receipt else "original_canonical_payload_custody_not_wire_attestation"}
    if receipt:
        prepared = unb64(receipt["prepared"])
        if (receipt["request_body"] != b64(request_raw) or receipt["request_sha256"] != raw_hash(request_raw)
                or receipt["response_sha256"] != raw_hash(raw) or receipt["prepared_sha256"] != raw_hash(prepared)
                or receipt["response_capture"] != "complete" or receipt["provider_authenticated"] is not False):
            raise ValueError("historical_carl_custody_binding")
        metadata["available_transport_metadata"] = {k: receipt[k] for k in (
            "http_status", "response_headers", "response_capture", "response_bytes_observed", "response_observed_sha256",
            "tls", "started_at", "completed_at", "latency_ms", "timeout_ms", "receipt_kind", "identity_evidence", "provider_authenticated")}
    state = decode(request["state"])
    source = state["untrusted_source"].encode()
    if "assessment_parent" in sample:
        parent_dir = "operator_runs_v1/pilot/checkpoints/" + sample["assessment_parent"]
        parent_result = decode(read_file(ROOT, parent_dir + "/result.json"))
        if (parent_result["job_id"] != sample["assessment_parent"]
                or parent_result["manifest_sha256"] != pilot["manifest_sha256"]
                or encode(parent_result["parsed"]) != encode(state["assessment"])):
            raise ValueError("original_generator_parent_binding")
        # The child seals its complete original parent result through the
        # checkpoint digest; do not rely on a current unbound parent filename.
        if result["parent_checkpoint_sha256"].get(sample["assessment_parent"]) != raw_hash(read_file(ROOT, parent_dir + "/result.json")):
            raise ValueError("original_parent_checkpoint_digest")
        for name, expected in parent_result["artifact_sha256"].items():
            checked(ROOT, parent_dir + "/" + name, expected)
    bindings(request_raw, source, state["assessment"], sample["claim_ids"], qualification_choice=ident == "smoke-choice")
    context = {"sample_id": ident, "mechanism": sample["mechanism"], "request_b64": b64(request_raw),
               "request_sha256": raw_hash(request_raw), "response_b64": b64(raw), "response_sha256": raw_hash(raw),
               "source_sha256": raw_hash(source), "assessment": state["assessment"], "assessment_sha256": digest(state["assessment"]),
               "claim_ids": sample["claim_ids"], "qualification_choice": ident == "smoke-choice",
               "prepared_b64": b64(prepared) if prepared else None,
               "historical_result": receipt["result"] if receipt else None, "response_metadata": metadata}
    return context


def observe(context, raw):
    request_raw = unb64(context["request_b64"])
    request = decode(request_raw)
    state = decode(request["state"])
    result = parse(request_raw, raw, source_raw=state["untrusted_source"].encode(), assessment=context["assessment"],
                   claim_ids=context["claim_ids"], request_sha256=context["request_sha256"],
                   response_sha256=raw_hash(raw), qualification_choice=context["qualification_choice"],
                   response_metadata=context["response_metadata"])
    if context["mechanism"] == "carl_jev":
        result["derived_carl"] = derive_carl(result, unb64(context["prepared_b64"]), context["assessment"])
        old, derived = context["historical_result"], result["derived_carl"]
        if (old["disposition"] != derived["disposition"] or encode(old["challenges"]) != encode(derived["challenges"])
                or {k: Decimal(str(v)) for k, v in old["signals"].items()} != {k: Decimal(v) for k, v in derived["signals_decimal"].items()}
                or old["reported_model"] != result["direct_systemone"]["returned_model"]["value"]):
            raise ValueError("historical_policy_replay_mismatch")
    elif context["prepared_b64"] is not None:
        raise ValueError("native_must_not_apply_carl_policy")
    return result


def identity(p):
    if p["kind"] == "generator":
        return IDENTITIES["generator"]
    return {"provider": "historical-local-replay-v1", "model": "preserved-systemone-entity",
            "specialist_role": "carl" if p["path"] == "carl_simulation" else "native",
            "instrument_contract": VERSION, "underlying_judge": "SystemOne"}


def corrupt(raw, negative):
    """Explicit negative-input derivatives, NEVER overwritten historical bodies."""
    if negative is None:
        return raw
    obj = decode(raw)
    if negative == "missing":
        del obj["answers"]["claim_0000_supported"]
    elif negative == "extra":
        obj["answers"]["invented"] = {"type": "noul", "noul": 0.5}
    elif negative == "wrong_type":
        obj["answers"]["claim_0000_supported"]["type"] = "choice"
    elif negative == "duplicate":
        # Inject a real duplicate JSON key; a dict cannot represent it.
        return raw.replace(b'"answers":{', b'"answers":{"claim_0000_supported":{"type":"noul","noul":0.5},', 1)
    else:
        raise ValueError("unknown_negative_input")
    return encode(obj)


def validate_extension(root, m):
    ext = m["specialist_observation"]
    if (set(ext) != {"version", "replay_only", "samples", "negative_inputs"} or ext["version"] != VERSION
            or ext["replay_only"] is not True or type(ext["samples"]) is not dict
            or type(ext["negative_inputs"]) is not dict or set(ext["negative_inputs"]) - set(ext["samples"])
            or any(v not in NEGATIVES for v in ext["negative_inputs"].values())):
        raise ValueError("typed_replay_extension")
    packet = decode(read_file(root, m["packets"]["replay"]["path"]))
    if set(packet) != {"version", "records"} or packet["version"] != VERSION or set(packet["records"]) != set(ext["samples"].values()):
        raise ValueError("typed_replay_packet")
    records = packet["records"]
    for ident, context in records.items():
        if encode(context) != encode(load_record(ident)):
            raise ValueError("replay_record_not_original:" + ident)
    first = next(iter(records.values()))
    state = decode(decode(unb64(first["request_b64"]))["state"])
    if read_file(root, m["packets"]["source"]["path"]) != state["untrusted_source"].encode():
        raise ValueError("typed_source_binding")
    if any(c["assessment_sha256"] != first["assessment_sha256"] or c["source_sha256"] != first["source_sha256"] for c in records.values()):
        raise ValueError("unmatched_replay_parents")
    specialists = {p["id"]: p for p in m["positions"] if p["kind"] == "specialist"}
    if set(specialists) != set(ext["samples"]):
        raise ValueError("replay_specialist_coverage")
    for pid, p in specialists.items():
        expected = "carl_simulation" if records[ext["samples"][pid]]["mechanism"] == "carl_jev" else "native_simulation"
        if p["path"] != expected:
            raise ValueError("native_carl_role_binding")
    return first["assessment"]


def request_for(m, p, receipts, root):
    ext = m["specialist_observation"]
    contexts = decode(read_file(root, m["packets"]["replay"]["path"]))["records"]
    context = next(iter(contexts.values()))
    assessment = context["assessment"]
    ap, sp = p["assessment_parent"], p["specialist_parent"]
    previous = receipts[ap]["diagnostics"]["parsed"] if ap else None
    req = {"schema": VERSION + "-offline-request", "simulation_only": True, "replay_only": True,
           "manifest_sha256": m["manifest_sha256"], "position": p, "packet_bindings": p["packet_bindings"],
           "source_text": read_file(root, m["packets"]["source"]["path"]).decode(),
           "governing_policy": decode(read_file(root, m["packets"]["governing_policy"]["path"])),
           "challenge_policy": decode(read_file(root, m["packets"]["challenge_policy"]["path"])),
           "parents": {d: digest(receipts[d]) for d in p["dependencies"]},
           "previous_assessment": previous, "instrument_contract": VERSION,
           "specialist_observations": receipts[sp]["diagnostics"]["parsed"] if sp else None,
           "continuation_authority": "untrusted_observations_only_no_operational_or_policy_authority",
           "instrument_request": None, "typed_context": None}
    if p["kind"] == "specialist":
        context = contexts[ext["samples"][p["id"]]]
        if digest(previous) != context["assessment_sha256"]:
            raise ValueError("replay_assessment_parent_mismatch")
        req["typed_context"] = context
        req["instrument_request"] = decode(unb64(context["request_b64"]))
        response = corrupt(unb64(context["response_b64"]), ext["negative_inputs"].get(p["id"]))
        origin = "negative_input_derivative" if p["id"] in ext["negative_inputs"] else "exact_historical_provider_entity"
    else:
        # Replay the assessment AS SUPPLIED TO the historical judge. This is not
        # a new generator inference or a claim to replay its original wire body.
        obj = copy.deepcopy(assessment)
        if previous:
            obj = {**copy.deepcopy(previous), "changes": [
                {"claim_id": c["claim_id"], "action": "retained", "reason": "Offline scripted continuation; no model inference."}
                for c in previous["claims"]]}
        response, origin = encode(obj), "preserved_assessment_input" if not previous else "scripted_continuation"
    req["offline_replay"] = {"version": VERSION, "raw_b64": b64(response), "raw_sha256": raw_hash(response), "origin": origin}
    return req


def validate_response(p, req, raw):
    if req["instrument_contract"] != VERSION:
        raise ValueError("typed_instrument_version")
    if raw_hash(raw) != req["offline_replay"]["raw_sha256"]:
        raise ValueError("replay_response_bytes_changed")
    if req["previous_assessment"] != req["typed_context"]["assessment"]:
        raise ValueError("typed_parent_assessment_changed")
    observation = observe(req["typed_context"], raw)
    observation["replay_provenance"] = {"sample_id": req["typed_context"]["sample_id"],
        "historical_outcomes_reclassified": False, "new_experimental_observation": False,
        "broker_request_sha256": digest(req), "origin": req["offline_replay"]["origin"]}
    return "completed", None, {"parsed": observation, "instrument_contract": VERSION}
