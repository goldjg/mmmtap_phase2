"""Explicitly authorised v2 transports; offline import never invokes a provider."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .adapters import Response, NativeJEVAdapter
from .core import IntegrityError, json_bytes, load
from historical_extractor.extract import strict_json
from .isolation import (Staging, bwrap_argv, sandbox_env, stream_run, verify_binary,
                        CopilotWatchdog, CodexWatchdog, CODEX_TOOL_MARKERS,
                        DATETIME_PREFIX, redact, stage_codex_auth)

EXCLUDED = ("bash,read_bash,stop_bash,list_bash,view,create,edit,web_fetch,"
            "fetch_copilot_cli_documentation,search_code_subagent,skill,run_dynamic_workflow,"
            "dynamic_workflows_manage,sql,session_store_sql,read_agent,list_agents,write_agent,"
            "grep,glob,task,ask_user")
DISABLED = (
    "shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "hooks", "plugins", "remote_plugin",
    "apps", "computer_use", "browser_use", "browser_use_external", "in_app_local_automation",
    "image_generation", "code_mode_host", "skill_search", "skill_mcp_dependency_install",
    "workspace_dependencies", "memories", "shell_snapshot", "daemon_auto_start",
    "unbounded_connection_retries", "step_model_switching", "goals", "realtime_conversation",
    "enable_request_compression", "sleep_tool", "tool_suggest", "view_image", "write_stdin_approval",
    "unified_exec_tty", "guardian_approval", "worktrees", "plugin_sharing", "tool_call_mcp_elicitation",
    "auth_elicitation", "mentions_v2", "content_item_kinds", "fast_mode", "ultrafast_mode",
    "in_app_browser", "in_app_chat", "browser_annotation_api", "browser_use_full_cdp_access")
CODEX_WARNING = ("Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; "
                 "enable `features.code_mode_host` and install `codex-code-mode-host`.")


def copilot_argv(model: str) -> list[str]:
    return ["/opt/bin/copilot", "--model", model, "--reasoning-effort", "low", "--output-format", "json",
            "--stream", "off", "--disable-builtin-mcps", "--no-auto-update", "--no-ask-user",
            "--no-experimental", "--no-remote-export", "--no-bash-env", "--max-autopilot-continues", "0",
            "--no-custom-instructions", "--available-tools=mmmtap_no_tool_placeholder",
            "--excluded-tools=" + EXCLUDED]


def codex_argv(*, mock: bool = False) -> list[str]:
    provider = ('name="mmmtap-loopback",base_url="{BASE}/v1",env_key="MMMTAP_PROVIDER_KEY"' if mock else
                'name="mmmtap-chatgpt",base_url="https://chatgpt.com/backend-api/codex",requires_openai_auth=true')
    settings = [f"features.{n}=false" for n in DISABLED] + [
        "project_doc_max_bytes=0", 'web_search="disabled"', 'model_provider="mmmtap_explicit"',
        'model_providers.mmmtap_explicit={' + provider +
        ',wire_api="responses",request_max_retries=0,stream_max_retries=0,'
        'stream_idle_timeout_ms=60000,supports_websockets=false}']
    return ["/opt/codex-release/bin/codex", "-a", "never", "exec", "--strict-config",
            "--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "read-only", "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="low"',
            "--json", "--color", "never"] + [p for s in settings for p in ("-c", s)] + ["-"]


def parse_events(raw: bytes, stderr: bytes, *, model: str, provider: str, prompt: str,
                 mock: bool = False) -> tuple[bytes, dict | None, dict]:
    events = [strict_json(line) for line in raw.splitlines() if line.strip()]
    if not all(isinstance(e, dict) and isinstance(e.get("type"), str) for e in events):
        raise ValueError("invalid_event_shape")
    messages, usage = [], None
    observed = []
    if provider == "codex_cli":
        if any(marker in stderr for marker in CODEX_TOOL_MARKERS):
            raise ValueError("codex_tool_routing")
        allowed = {"thread.started", "turn.started", "item.started", "item.completed", "turn.completed"}
        for e in events:
            if e["type"] not in allowed:
                raise ValueError("codex_unknown_or_failure_event")
            item = e.get("item", {})
            if item:
                if item.get("type") == "error":
                    if item.get("message", item.get("text")) != CODEX_WARNING:
                        raise ValueError("codex_warning_not_allowlisted")
                elif item.get("type") not in ("reasoning", "agent_message"):
                    raise ValueError("codex_non_assessment_item")
                elif e["type"] == "item.completed" and item["type"] == "agent_message":
                    messages.append(item["text"])
            if e["type"] == "turn.completed":
                usage = e.get("usage")
        for kind in ("thread.started", "turn.started", "turn.completed"):
            if sum(e["type"] == kind for e in events) != 1:
                raise ValueError("codex_turn_count")
        # These fields describe client configuration, never a provider identity.
        for marker in (b"Configuring session: model=gpt-6.1-sol", b"request_max_retries: Some(0)",
                       b"stream_max_retries: Some(0)", b"codex.turn.reasoning_effort=low",
                       b'name: "mmmtap-loopback"' if mock else b'name: "mmmtap-chatgpt"'):
            if marker not in stderr:
                raise ValueError("codex_effective_config_unobserved")
        basis = "requested_model_and_client_debug_configuration_not_provider_attestation"
    else:
        allowed = {"session.mcp_servers_loaded", "session.tools_updated", "session.info", "session.skills_loaded",
                   "user.message", "assistant.turn_start", "model.call_start", "model.call_finished",
                   "assistant.message", "assistant.reasoning", "model.call_final_result", "assistant.turn_end",
                   "session.usage_checkpoint", "assistant.idle", "result"}
        for e in events:
            if e["type"] not in allowed:
                raise ValueError("copilot_unknown_or_failure_event")
            d, kind = e.get("data", {}), e["type"]
            if not isinstance(d, dict):
                raise ValueError("copilot_invalid_data")
            if kind == "assistant.message":
                if d.get("toolRequests"):
                    raise ValueError("copilot_tool_request")
                messages.append(d.get("content"))
            if kind == "session.tools_updated" and d.get("tools"):
                raise ValueError("copilot_tools_advertised")
            if kind == "session.mcp_servers_loaded":
                servers = d.get("servers")
                if not isinstance(servers, list) or any(s.get("status") != "disabled" for s in servers):
                    raise ValueError("copilot_mcp_server_not_disabled")
            if kind == "model.call_start":
                observed.append(d.get("model"))
            if kind == "model.call_finished" and d.get("outcome") != "success":
                raise ValueError("copilot_call_not_successful")
            if kind == "model.call_final_result" and (d.get("result") != "success"
                    or d.get("model") != model or d.get("isByok") is not mock):
                raise ValueError("copilot_route_or_model_changed")
            if kind == "session.usage_checkpoint":
                counts = [details.get("tool_count") for conversation in d.get("promptCacheBreakState", [])
                          for details in conversation.get("models", {}).values()]
                if not counts or any(type(n) is not int or n != 0 for n in counts):
                    raise ValueError("copilot_telemetry_tool_exposure_or_missing")
                metrics = d.get("accountingSnapshot", {}).get("modelMetrics", {})
                if set(metrics) != {model} or metrics[model].get("requests", {}).get("count") != 1:
                    raise ValueError("copilot_accounted_request_or_model_mismatch")
                tokens = metrics[model].get("usage", {})
                usage = {"input_tokens": tokens.get("inputTokens"), "output_tokens": tokens.get("outputTokens"),
                         "cached_input_tokens": tokens.get("cacheReadTokens"), "raw_telemetry": d}
            if kind == "user.message":
                if d.get("content") != prompt:
                    raise ValueError("copilot_prompt_changed")
                transformed = d.get("transformedContent", prompt)
                if transformed != prompt and not (transformed.endswith(prompt) and
                        DATETIME_PREFIX.fullmatch(transformed[:-len(prompt)])):
                    raise ValueError("copilot_inherited_prompt")
            if kind == "result" and e.get("exitCode", d.get("exitCode")) != 0:
                raise ValueError("copilot_result_failed")
        for kind in ("user.message", "model.call_start", "model.call_finished", "model.call_final_result", "result"):
            if sum(e["type"] == kind for e in events) != 1:
                raise ValueError("copilot_event_count:" + kind)
        if observed != [model]:
            raise ValueError("copilot_client_model_mismatch")
        if not mock and usage is None:
            raise ValueError("copilot_live_telemetry_missing")
        basis = "CLI_model_event_not_provider_attestation"
    if len(messages) != 1 or not isinstance(messages[0], str) or not messages[0].strip():
        raise ValueError("one_complete_assessment_required")
    return messages[0].encode(), usage, {
        "observed_model": model if provider != "codex_cli" else None,
        "requested_model": model, "provider_confirmed_model": None, "identity_basis": basis,
        "event_types": [e["type"] for e in events], "observed_tool_use": 0,
        "provider_internal_retries": "unobservable", "evidence_mode": "loopback_mock" if mock else "live_unqualified"}


class GeneratorAdapter:
    def __init__(self, spec: dict, cfg: dict):
        self.spec, self.cfg = spec, cfg

    def invoke(self, prompt: str, *, authorised: bool = False) -> Response:
        if not authorised:
            return Response(error="live_authorisation_required")
        spec = self.spec
        verify_binary(Path(self.cfg["isolation_runtime"]["binary"]), self.cfg["isolation_runtime"]["sha256"])
        binary = Path(spec["binary"]).expanduser().resolve()
        verify_binary(binary, spec["binary_sha256"])
        secrets = []
        with Staging() as stage:
            if spec["provider"] == "codex_cli":
                home = stage.path("home") / ".codex"
                home.mkdir()
                auth = Path.home() / ".codex/auth.json"
                if not auth.is_file():
                    return Response(error="credentials_unavailable")
                auth_info = stage_codex_auth(auth, home)
                secrets = auth_info["secrets"]
                env = sandbox_env({"CODEX_HOME": "/home/assessor/.codex",
                    "PATH": "/opt/codex-release/codex-path:/opt/codex-release/bin:/usr/bin:/bin",
                    "RUST_LOG": "warn,codex_core=debug"})
                binds = [(binary.parent.parent, "/opt/codex-release")]
                command, watchdog = codex_argv(), CodexWatchdog()
            else:
                token = next((os.environ[k] for k in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
                              if os.environ.get(k)), None)
                if not token:
                    return Response(error="credentials_unavailable")
                secrets = [token]
                env = sandbox_env({"COPILOT_HOME": "/home/assessor/.copilot", "COPILOT_GITHUB_TOKEN": token})
                binds = [(binary, "/opt/bin/copilot")]
                command, watchdog = copilot_argv(spec["model_id"]), CopilotWatchdog()
            if command != spec["argv"]:
                raise IntegrityError("Generator invocation differs from frozen instrument")
            argv = bwrap_argv(command, ro_binds=binds + [(stage.path("work"), "/work")],
                              rw_binds=[(stage.path("home"), "/home/assessor")], network="host")
            run = stream_run(argv, stdin=prompt.encode(), env=env, timeout=self.cfg["timeout_seconds"],
                             limit=self.cfg["max_response_bytes"], watchdog=watchdog)
            out, red1 = redact(run.stdout, secrets)
            err, red2 = redact(run.stderr, secrets)
            response = Response(stdout=out, stderr=err, exit_status=run.exit_status,
                                latency_seconds=run.latency_seconds,
                                error=run.error or run.watchdog_reason,
                                provenance={"transport_attempts": 1, "argv": command,
                                            "binary_sha256": verify_binary(binary, spec["binary_sha256"]),
                                            "isolation": "fresh_mount_pid_home_readonly_work_namespace",
                                            "network": "host_for_authorised_provider_transport",
                                            "credential_redacted": red1 or red2,
                                            "home_file_names": stage.inventory("home"),
                                            "auth_writeback": "never_writes_host_auth"})
            if not response.error and run.exit_status == 0:
                try:
                    response.message, response.usage, evidence = parse_events(out, err, model=spec["model_id"],
                        provider=spec["provider"], prompt=prompt)
                    response.provenance.update(evidence)
                except (ValueError, TypeError, KeyError) as exc:
                    response.error = "strict_parser:" + str(exc)
            elif not response.error:
                response.error = "nonzero_exit"
        response.provenance["staging_removed"] = stage.removed
        return response


class PathBAdapter:
    def __init__(self, spec: dict, cfg: dict):
        self.spec, self.cfg = spec, cfg

    def invoke(self, request: dict, *, authorised: bool = False, mock_response: dict | None = None) -> Response:
        if mock_response is None and not authorised:
            return Response(error="live_authorisation_required")
        spec = self.spec
        binary = Path(spec["binary"]).resolve()
        verify_binary(binary, spec["binary_sha256"])
        from .isolation import sha256_file
        for name, expected in spec["policy_files"].items():
            if sha256_file(Path(spec["policy_root"]) / name) != expected:
                raise IntegrityError("Path B policy changed after freeze")
        with tempfile.TemporaryDirectory(prefix="mmmtap-path-b-") as tmp:
            root = Path(tmp)
            (root / "request.json").write_bytes(json_bytes(request))
            logs = []

            def call(args, *, live=False):
                env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
                if live and os.environ.get("JEVKEY"):
                    env["JEVKEY"] = os.environ["JEVKEY"]
                r = stream_run([str(binary), *args], stdin=b"", env=env,
                               timeout=self.cfg["timeout_seconds"] + 10, limit=32 << 20)
                logs.append({"args": args, "exit_status": r.exit_status, "error": r.error,
                             "stdout": base64.b64encode(r.stdout).decode(), "stderr": base64.b64encode(r.stderr).decode()})
                return r

            first = call(["prepare", "--request", str(root / "request.json"), "--policy-root",
                          spec["policy_root"], "--out", str(root / "prepared")])
            if first.exit_status != 0 or first.error:
                return Response(error="unsupported_contract_or_preparation_failed", provenance={"processes": logs})
            prepared = root / "prepared/prepared.json"
            args = ["--prepared", str(prepared), "--prepared-sha256", sha256_file(prepared),
                    "--out", str(root / "result")]
            if mock_response is not None:
                (root / "answer.json").write_bytes(json_bytes(mock_response))
                args = ["evaluate-offline", *args, "--response", str(root / "answer.json"), "--mode", "mock"]
                name = "receipt.json"
            else:
                args = ["evaluate-live", *args, "--authorize-live", "--timeout-seconds", str(self.cfg["timeout_seconds"])]
                name = "live_receipt.json"
            result = call(args, live=mock_response is None)
            path = root / "result" / name
            raw = path.read_bytes() if path.exists() else b""
            response = Response(stdout=raw, stderr=result.stderr, exit_status=result.exit_status,
                latency_seconds=result.latency_seconds, error=result.error,
                provenance={"transport_attempts": int(mock_response is None), "processes": logs,
                            "receipt_kind": "local_integrity_not_provider_signature",
                            "evidence_mode": "mock" if mock_response is not None else "live"})
            # Preserve failure artifacts even when there was no serializable receipt.
            response.provenance["artifacts"] = {str(p.relative_to(root)): base64.b64encode(p.read_bytes()).decode()
                for p in root.rglob("*") if p.is_file()}
            if not raw:
                response.error = response.error or "missing_receipt"
                return response
            replay = call(["replay", "--receipt", str(path), "--receipt-sha256", sha256_file(path)])
            receipt = strict_json(raw)
            response.provenance["receipt_sha256"] = sha256_file(path)
            response.provenance["replay_exit_status"] = replay.exit_status
            if result.exit_status != 0 or replay.exit_status != 0 or receipt["status"] not in ("ok", "mock_ok"):
                response.error = response.error or receipt.get("failure_class", "evaluation_or_replay_failed")
            else:
                response.message = json_bytes({"mechanism": "carl_jev_path_b",
                    "evidence_mode": response.provenance["evidence_mode"], "provenance": "supplied_not_authenticated_git",
                    "receipt_sha256": sha256_file(path), **receipt["result"]})
                response.provenance["observed_model"] = receipt["result"]["reported_model"]
            verify_binary(binary, spec["binary_sha256"])
            return response
