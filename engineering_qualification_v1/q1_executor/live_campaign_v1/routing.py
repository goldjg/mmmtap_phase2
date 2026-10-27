"""Existing subscription event contracts, not a certification of opaque CLIs."""
import base64

from ..model import decode, encode


def parse_cli_entity(raw, req):
    from phase2.adapters_v2 import parse_events
    obj = decode(raw)
    if set(obj) != {"model", "stdout_b64", "stderr_b64", "exit_status", "usage"} or obj["exit_status"] != 0:
        raise ValueError("CLI_transport_entity")
    route = req["provider_route"]
    if obj["model"] != route["model"]:
        raise ValueError("CLI_requested_model_substitution")
    message, usage, provenance = parse_events(base64.b64decode(obj["stdout_b64"], validate=True),
        base64.b64decode(obj["stderr_b64"], validate=True), model=route["model"], provider=route["provider"],
        prompt=req["instrument_request"]["prompt"], mock=False)
    provenance.update(evidence_mode="injected_local_CLI_event_fixture" if req["simulation_only"] else "live_unqualified",
        provider_serving_identity=None, local_envelope_identity_is_not_CLI_served_identity=True)
    if obj["usage"] != usage:
        raise ValueError("CLI_usage_mismatch")
    return message, usage, provenance


def fixture_cli_entity(body, scenario):
    """Generate local *event* fixtures using the real adapter parser contracts.

    Never invokes a configured generator CLI, reads credentials, or establishes
    what that CLI would send remotely. This is explicit fixture injection.
    """
    model, prompt = body["model"], body["prompt"]
    envelope = decode(prompt.split("\n", 1)[1])
    evidence = envelope["untrusted_evidence"]
    previous = evidence["preceding_assessment"]
    claims = previous["claims"] if previous else [{"claim_id": "c1",
        "claim": "The supplied document states: " + evidence["source_text"],
        "evidence_quotes": [evidence["source_text"]], "confidence": 0.5,
        "limitations": ["Authored historical engineering stimulus; no independent verification."]}]
    assessment = {**envelope["identity"], "claims": claims,
        "disposition": "review_required" if envelope["arm"].startswith("E") else "pass",
        "uncertainties": ["Local injected output; no model inference or research result."],
        "changes": [{"claim_id": c["claim_id"], "action": "retained", "reason": "Exact claim object retained in local fixture."}
                    for c in claims] if previous else []}
    if scenario == "invalid_assessment":
        assessment["changes"] = []
    if scenario == "empty_claims":
        assessment["claims"] = []
        assessment["changes"] = [{"claim_id": c["claim_id"], "action": "withdrawn",
            "reason": "Local fixture withdraws its claim; no substitute is manufactured."} for c in previous["claims"]]
    if scenario == "bad_quote":
        import copy
        assessment["claims"] = copy.deepcopy(claims)
        assessment["claims"][0]["evidence_quotes"] = ["INJECTED QUOTATION ABSENT FROM SOURCE"]
        assessment["changes"] = [{"claim_id": c["claim_id"], "action": "revised",
            "reason": "Deliberate invalid quotation fixture."} for c in claims]
    message = encode(assessment).decode()
    if model == "gpt-6.1-sol":
        usage = {"input_tokens": 101, "output_tokens": 37, "cached_input_tokens": 0}
        events = [{"type": "thread.started", "thread_id": "local-fresh-context"}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": message}},
            {"type": "turn.completed", "usage": usage}]
        stderr = b'Configuring session: model=gpt-6.1-sol\nrequest_max_retries: Some(0)\nstream_max_retries: Some(0)\ncodex.turn.reasoning_effort=low\nname: "mmmtap-chatgpt"\n'
    else:
        telemetry = {"promptCacheBreakState": [{"models": {model: {"tool_count": 0}}}],
            "accountingSnapshot": {"modelMetrics": {model: {"requests": {"count": 1},
                "usage": {"inputTokens": 101, "outputTokens": 37, "cacheReadTokens": 0}}}}}
        usage = {"input_tokens": 101, "output_tokens": 37, "cached_input_tokens": 0, "raw_telemetry": telemetry}
        events = [{"type": "user.message", "data": {"content": prompt}},
            {"type": "model.call_start", "data": {"model": model}},
            {"type": "assistant.message", "data": {"content": message}},
            {"type": "model.call_finished", "data": {"outcome": "success"}},
            {"type": "model.call_final_result", "data": {"model": model, "result": "success", "isByok": False}},
            {"type": "session.usage_checkpoint", "data": telemetry}, {"type": "result", "exitCode": 0}]
        stderr = b""
    return {"model": model, "stdout_b64": base64.b64encode(b"\n".join(encode(e) for e in events)).decode(),
            "stderr_b64": base64.b64encode(stderr).decode(), "exit_status": 0, "usage": usage}
