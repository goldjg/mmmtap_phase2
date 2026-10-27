"""Read-only reconstruction for the explicit HTTPS broker event version."""
from . import VERSION, DESTINATION, MODEL
from .contract import native_request, identity, POSITION
from .. import transport
from ..model import decode, encode, raw_hash

TRANSITIONS = {
    None: {"authorised"}, "authorised": {"dispatch_intent", "interrupted"},
    "dispatch_intent": {"https_connected", "terminal_failure", "interrupted"},
    "https_connected": {"request_write_intent", "terminal_failure", "interrupted"},
    "request_write_intent": {"request_delivered", "terminal_failure", "interrupted"},
    "request_delivered": {"response_headers", "terminal_failure", "interrupted"},
    "response_headers": {"partial_response", "complete_response", "terminal_failure", "interrupted"},
    "partial_response": {"partial_response", "complete_response", "terminal_failure", "interrupted"},
    "complete_response": set(), "terminal_failure": set(), "interrupted": set(),
}


def verify_transport(rec, envelope, spec, root, previous):
    def base(value):
        from ..live_campaign_v1 import VERSION as CAMPAIGN
        if "https" not in value or value["contract"] not in (VERSION, CAMPAIGN):
            raise ValueError("https_transport_record_shape")
        has_binding = "credential_binding" in envelope
        if has_binding:
            handoff = value.get("credential_handoff")
            if (not handoff or handoff["contract"] != envelope["credential_binding"]["version"]
                    or handoff["launcher_protection"] != {"dumpable": False, "core_soft": 0, "core_hard": 0}
                    or set(handoff) != {"contract", "source_configured", "launcher_protection", "broker_ready_before_release", "broker_sender_PID_authenticated", "delivery", "broker_pid"}
                    or handoff["delivery"] not in {"not_released", "single_use_pipe_written_and_closed"}
                    or handoff["delivery"] == "single_use_pipe_written_and_closed" and not (handoff["broker_ready_before_release"] and handoff["broker_sender_PID_authenticated"])):
                raise ValueError("JEVKEY_transport_handoff_changed")
        elif "credential_handoff" in value:
            raise ValueError("JEVKEY_handoff_without_binding")
        return {**{k: v for k, v in value.items() if k not in {"https", "credential_handoff"}}, "contract": transport.VERSION}
    transport.base_verify_record(base(rec), envelope, spec, root, base(previous) if previous else None)
    if rec["status"] == "completed" and (not rec["https"] or not rec["https"]["response_complete"]
                                        or rec["https"]["http_status"] != 200):
        raise ValueError("https_false_transport_completion")


def metadata(meta, env, raw, stage, request=None, simulation=True):
    if meta is None:
        if stage not in {"authorised", "interrupted"} or raw:
            raise ValueError("https_missing_metadata")
        return
    fields = {"contract", "destination", "request_entity_sha256", "requested_model", "returned_model", "identity_state",
              "identity_assurance", "http_status", "safe_response_headers", "provider_request_ids", "usage",
              "response_complete", "response_entity_bytes", "tls", "egress", "client_POSTs", "retries",
              "request_delivery", "remote_execution_assurance", "credential_source", "started_at"}
    jevkey = "credential_binding" in env
    if jevkey:
        fields.add("credential")
        credential = meta.get("credential", {})
        expected = {"contract", "broker_protection", "broker_JEVKEY_environment_absent", "broker_environment_minimal", "received_once", "descriptor_closed"}
        if (set(credential) not in (expected, expected | {"child_environment_and_descriptors_clean"})
                or credential["contract"] != env["credential_binding"]["version"]
                or credential["broker_protection"] != {"dumpable": False, "core_soft": 0, "core_hard": 0}
                or not credential["broker_JEVKEY_environment_absent"] or not credential["broker_environment_minimal"]
                or meta["client_POSTs"] and (not credential["received_once"] or not credential["descriptor_closed"])):
            raise ValueError("JEVKEY_broker_protection_changed")
    expected_request = native_request() if request is None else encode(request["instrument_request"])
    model_expected = env["requested_identity"]["model"]
    assurance = "local_TLS_fixture_only_not_genuine_SystemOne" if simulation else "TLS_provider_model_self_report_not_serving_attestation"
    if (set(meta) != fields or meta["contract"] != env["broker_contract"] or meta["destination"] != env["destination"]
            or meta["request_entity_sha256"] != raw_hash(expected_request) or meta["requested_model"] != model_expected
            or meta["client_POSTs"] not in (0, 1) or meta["retries"] != 0
            or meta["response_entity_bytes"] != len(raw)
            or meta["identity_assurance"] != assurance
            or meta["remote_execution_assurance"] != "UNKNOWN"
            or meta["credential_source"] != ("JEVKEY_via_single_use_broker_pipe" if jevkey else "explicit_broker_fixture_interface")):
        raise ValueError("https_metadata_or_request_binding")
    from .https import SAFE_HEADERS
    headers = meta["safe_response_headers"]
    if (any(type(h) is not list or len(h) != 2 or h[0] not in SAFE_HEADERS or not isinstance(h[1], str) for h in headers)
            or meta["provider_request_ids"] != [h for h in headers if h[0] in {"x-request-id", "request-id", "x-correlation-id"}]):
        raise ValueError("https_safe_headers_or_correlation_changed")
    if meta["response_complete"]:
        try:
            entity = decode(raw)
            model = entity.get("model")
            model = model if isinstance(model, str) and model else None
            usage = entity.get("usage")
        except (ValueError, UnicodeError, AttributeError):
            model, usage = None, None
        state = "unknown" if model is None else "matched" if model == model_expected else "mismatch"
        if (meta["returned_model"], meta["identity_state"], meta["usage"]) != (model, state, usage):
            raise ValueError("https_returned_identity_or_usage_changed")
    if meta["client_POSTs"]:
        if (not meta["tls"] or meta["tls"]["certificate_verified"] is not True
                or meta["tls"]["hostname_verified"] is not True
                or meta["tls"]["server_hostname"] != env["destination"]["host"]
                or not meta["egress"] or meta["egress"].get("secondary_socket_denied") is not True):
            raise ValueError("https_unqualified_network_or_TLS")
    if stage == "complete_response" and (meta["http_status"] != 200 or not meta["response_complete"]):
        raise ValueError("https_false_response_completion")


def audit(db, m):
    from ..broker_v1.broker import binding, REJECTIONS
    from ..broker_v1.contract import envelope_for
    histories, rejections = {}, 0
    from ..live_campaign_v1.contract import is_campaign
    campaign = is_campaign(m)
    positions = {p["id"]: p for p in m["positions"]}
    for (body,) in db.execute("SELECT body FROM events ORDER BY seq"):
        event = decode(body); ident, rec = event["position"], event["data"]
        if event["kind"] == "broker_rejected":
            if set(rec) != {"reason", "message_sha256"} or rec["reason"] not in REJECTIONS or len(rec["message_sha256"]) != 64:
                raise ValueError("https_rejection_changed")
            rejections += 1
        if event["kind"] != "broker_event":
            continue
        if ident not in positions or not campaign and ident != POSITION:
            raise ValueError("https_unscheduled_dispatch")
        request = db.execute("SELECT request FROM attempts WHERE id=?", (ident,)).fetchone()[0]
        env = envelope_for(m, positions[ident], request)
        expected = binding(env)
        if (set(rec) != set(expected) | {"stage", "raw_b64", "observed_identity", "uncertain_completion", "reason", "frame_integrity", "https"}
                or any(rec[k] != v for k, v in expected.items())):
            raise ValueError("https_authorisation_binding_changed")
        hist = histories.setdefault(ident, [])
        prev = hist[-1] if hist else None
        if rec["stage"] not in TRANSITIONS[prev["stage"] if prev else None]:
            raise ValueError("https_duplicate_or_nonmonotonic_dispatch")
        raw = transport.unb64(rec["raw_b64"])
        if (len(raw) > env["response_byte_limit"] or transport.b64(raw) != rec["raw_b64"]
                or prev and not raw.startswith(transport.unb64(prev["raw_b64"]))):
            raise ValueError("https_raw_prefix_changed")
        if raw and rec["stage"] in {"authorised", "dispatch_intent", "https_connected", "request_write_intent", "request_delivered", "response_headers"}:
            raise ValueError("https_bytes_before_response")
        metadata(rec["https"], env, raw, rec["stage"], decode(request) if campaign else None, m["simulation_only"])
        if rec["stage"] == "complete_response":
            model = rec["https"]["returned_model"]
            observed = dict(env["requested_identity"], model=model) if model else None
            if rec["uncertain_completion"] or rec["observed_identity"] != observed or not rec["frame_integrity"]:
                raise ValueError("https_false_completion_or_identity")
        elif rec["observed_identity"] is not None:
            raise ValueError("https_identity_without_complete_response")
        hist.append(rec)
    for ident, raw, observed in db.execute("SELECT id,raw,observed FROM responses"):
        hist = histories.get(ident, [])
        if hist and (raw != transport.unb64(hist[-1]["raw_b64"]) or decode(observed) != hist[-1]["observed_identity"]):
            raise ValueError("https_response_custody_changed")
        if not hist and raw:
            raise ValueError("https_response_without_dispatch")
    for ident, _, record in db.execute("SELECT id,envelope,record FROM transports"):
        if record:
            rec = decode(record)
            hist = histories.get(ident, [])
            if rec["status"] not in {"launch_intent", "running"} and hist and rec["https"] != hist[-1]["https"]:
                raise ValueError("https_transport_and_broker_metadata_differ")
    count = lambda stage: sum(any(r["stage"] == stage for r in h) for h in histories.values())
    return {"broker_authorised_requests": count("authorised"), "broker_rejected_requests": rejections,
            "broker_dispatch_intents": count("dispatch_intent"), "https_connections": count("https_connected"),
            "client_POST_intents": count("request_write_intent"), "client_POST_writes_completed": count("request_delivered"),
            "broker_complete_responses": count("complete_response"), "broker_partial_responses": count("partial_response"),
            "broker_terminal_failures": count("terminal_failure"),
            "broker_uncertain_completions": sum(h[-1]["uncertain_completion"] for h in histories.values()),
            "remote_exactly_once_claimed": False, "genuine_SystemOne_response_established": False}
