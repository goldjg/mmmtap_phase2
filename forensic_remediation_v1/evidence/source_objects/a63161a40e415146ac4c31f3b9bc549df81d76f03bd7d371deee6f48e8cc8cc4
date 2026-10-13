"""Explicit transports. Importing this module never authenticates or performs inference."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import selectors
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

from historical_extractor.archive import IntegrityError, file_hash
from historical_extractor.extract import strict_json
from .core import ROOT, digest, json_bytes


CODEX_DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "hooks",
    "plugins", "remote_plugin", "apps", "computer_use", "browser_use",
    "browser_use_external", "in_app_local_automation", "image_generation",
    "code_mode_host", "skill_search", "skill_mcp_dependency_install",
    "workspace_dependencies", "memories", "shell_snapshot", "daemon_auto_start",
    "unbounded_connection_retries", "step_model_switching", "goals",
    "realtime_conversation",
)


def codex_overrides() -> list[str]:
    settings = [f"features.{name}=false" for name in CODEX_DISABLED_FEATURES]
    settings += ["features.skip_host_skill_discovery=true", "project_doc_max_bytes=0",
                 'web_search="disabled"', "model_providers.openai.request_max_retries=0",
                 "model_providers.openai.stream_max_retries=0"]
    return [part for setting in settings for part in ("-c", setting)]


def redact_bytes(value: bytes, secrets: list[str]) -> tuple[bytes, bool]:
    original = value
    for secret in secrets:
        if len(secret) > 5:
            value = value.replace(secret.encode(), b"[CREDENTIAL REDACTED]")
    return value, value != original


@dataclass
class Response:
    stdout: bytes = b""
    stderr: bytes = b""
    message: bytes = b""
    exit_status: int | None = None
    latency_seconds: float = 0.0
    usage: dict | None = None
    error: str | None = None
    provenance: dict = field(default_factory=dict)

    def record(self) -> dict:
        return {**self.__dict__, "stdout": base64.b64encode(self.stdout).decode(),
                "stderr": base64.b64encode(self.stderr).decode(),
                "message": base64.b64encode(self.message).decode(), "raw_encoding": "base64"}


def executable(spec: dict) -> str | None:
    name = os.path.expanduser(spec.get("binary", ""))
    return shutil.which(name) if name else None


def probe(cfg: dict) -> dict:
    """Offline entry-point/version and credential-presence checks, not live readiness."""
    adapters = {}
    for name, spec in {**cfg["generators"], **cfg["adversaries"]}.items():
        binary = executable(spec)
        row = {"provider": spec["provider"], "requested_model": spec["model_id"],
               "resolved_model": None, "live_capable": False, "smoke_test": "not_authorised_not_run",
               "authentication": "unverified", "binary": binary, "binary_sha256": None,
               "cli_version": None, "limitations": []}
        if binary:
            row["binary_sha256"] = file_hash(Path(binary))
            command = [binary, "version"] if name == "carl_jev" else [binary, "--version"]
            try:
                result = subprocess.run(command, capture_output=True, timeout=20, check=False)
                row["version_exit_status"] = result.returncode
                row["cli_version"] = result.stdout.decode("utf-8", "replace").strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                row["limitations"].append("version_probe:" + type(exc).__name__)
        elif name != "native_jev":
            row["limitations"].append("executable_missing")
        if name in ("haiku", "gemini"):
            row["credential_present"] = any(bool(os.environ.get(k)) for k in
                                            ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"))
            row["limitations"] += [
                "Isolated Copilot requires an explicit credential environment variable; cached user config is not loaded.",
                "Model availability, served model version, empty tool allowlist and internal retry visibility need live smoke review."]
        elif name == "sol":
            row["credential_present"] = bool(os.environ.get("OPENAI_API_KEY")) or (Path.home() / ".codex/auth.json").is_file()
            if binary:
                try:
                    result = subprocess.run([binary, "login", "status"], capture_output=True, timeout=20, check=False)
                    row["authentication"] = "local_login_status_ok_not_remote_validated" if result.returncode == 0 else "local_login_unverified"
                except (OSError, subprocess.TimeoutExpired) as exc:
                    row["limitations"].append("auth_status:" + type(exc).__name__)
            row["limitations"].append("Tool disabling, requested model routing and internal retries need live smoke review.")
        else:
            row["credential_present"] = bool(os.environ.get(spec["key_env"]))
            row["evidence_contracts"] = spec["evidence_contracts"]
        if name == "native_jev":
            row["endpoint"] = spec["endpoint"]
            row["limitations"].append("Endpoint authentication, state capacity and actual resolved JEV version are unverified.")
        if name == "carl_jev":
            row["limitations"] += [
                "No authenticated BASE/HEAD repository binding for any frozen primary text input.",
                "Real cARL output must include verifiable SystemOne execution provenance, not signals alone.",
                "Git-diff-prose fixture generation is intentionally absent."]
        adapters[name] = row
    prior = ROOT.parent / "mmmtap_p1_014_phase0_adapter/assessors.json"
    return {"schema": "mmmtap-adapter-readiness-v1", "mode": "offline_probe",
            "adapters": adapters, "mock_success_is_live_evidence": False,
            "gemini_discovery": {"model_id": cfg["generators"]["gemini"]["model_id"],
                                 "interface": "copilot --model",
                                 "evidence": str(prior), "evidence_sha256": file_hash(prior) if prior.is_file() else None,
                                 "status": "historical_exact_id_current_availability_unverified"}}


def run_process(argv: list[str], prompt: str, cwd: Path, env: dict[str, str],
                timeout: int, limit: int) -> Response:
    start = time.monotonic()
    response = Response(provenance={"argv": ["[PROMPT:" + digest(prompt) + "]" if s == prompt else s for s in argv],
                                    "cwd_policy": "isolated_temporary_directory", "transport_attempts": 1})
    try:
        with tempfile.TemporaryFile() as stdin, selectors.DefaultSelector() as selector:
            stdin.write(prompt.encode("utf-8"))
            stdin.seek(0)
            child = subprocess.Popen(argv, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     cwd=cwd, env=env, start_new_session=True)
            buffers = {"stdout": bytearray(), "stderr": bytearray()}
            selector.register(child.stdout, selectors.EVENT_READ, "stdout")
            selector.register(child.stderr, selectors.EVENT_READ, "stderr")
            try:
                while selector.get_map():
                    remaining = timeout - (time.monotonic() - start)
                    if remaining <= 0:
                        response.error = "timeout_execution_outcome_uncertain_no_retry"
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        buffer = buffers[key.data]
                        space = limit - len(buffer)
                        buffer.extend(data[:space])
                        if len(data) > space:
                            response.error = "output_size_limit"
                            break
                    if response.error:
                        break
                if response.error:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=max(0.01, timeout - (time.monotonic() - start)))
                response.exit_status = child.returncode
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                response.error = "timeout_execution_outcome_uncertain_no_retry"
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                child.stdout.close()
                child.stderr.close()
                response.stdout = bytes(buffers["stdout"])
                response.stderr = bytes(buffers["stderr"])
    except OSError as exc:
        response.error = "process_error:" + type(exc).__name__
    response.latency_seconds = round(time.monotonic() - start, 6)
    return response


def parse_cli_events(raw: bytes, provider: str) -> tuple[bytes, dict | None, dict]:
    messages = []
    usage = None
    model = None
    calls = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        event = strict_json(line)
        if not isinstance(event, dict):
            raise ValueError("CLI event is not an object")
        kind = event.get("type", "")
        if not isinstance(kind, str):
            raise ValueError("invalid_event_type")
        if ("tool" in kind and kind != "session.tools_updated") or "retry" in kind or kind in ("error", "turn.failed"):
            raise ValueError("tool_retry_or_error_event")
        if kind == "model.call_start":
            calls += 1
            if calls > 1:
                raise ValueError("multiple_model_calls_for_one_assessment")
        if provider == "codex_cli":
            item = event.get("item", {})
            if isinstance(item, dict) and kind.startswith("item."):
                if item.get("type") not in ("agent_message", "reasoning"):
                    raise ValueError("non_assessment_codex_item")
                if kind == "item.completed" and item.get("type") == "agent_message":
                    messages.append(item.get("text"))
            if kind == "turn.completed":
                usage = event.get("usage")
        else:
            data = event.get("data", {})
            if kind == "assistant.message" and isinstance(data, dict):
                if data.get("toolRequests"):
                    raise ValueError("assistant_tool_requests_forbidden")
                messages.append(data.get("content"))
            if kind in ("assistant.message", "model.call_final_result") and isinstance(data, dict):
                reported = data.get("model")
                if isinstance(reported, str):
                    if model and model != reported:
                        raise ValueError("CLI_model_changed")
                    model = reported
            if kind == "session.usage_info" and isinstance(data, dict):
                usage = data
            if kind == "session.usage_checkpoint" and isinstance(data, dict):
                for conversation in data.get("promptCacheBreakState", []):
                    for details in conversation.get("models", {}).values():
                        if details.get("tool_count", 0) > 0:
                            raise ValueError("model_tool_exposure_detected:" + str(details["tool_count"]))
                metrics = data.get("accountingSnapshot", {}).get("modelMetrics", {})
                if model in metrics:
                    recorded = metrics[model]
                    if recorded.get("requests", {}).get("count", 0) > 1:
                        raise ValueError("multiple_accounted_model_requests")
                    tokens = recorded.get("usage", {})
                    usage = {"input_tokens": tokens.get("inputTokens"), "output_tokens": tokens.get("outputTokens"),
                             "cached_input_tokens": tokens.get("cacheReadTokens"),
                             "cache_write_tokens": tokens.get("cacheWriteTokens")}
        if isinstance(event.get("model"), str):
            model = event["model"]
    if len(messages) != 1 or not isinstance(messages[0], str):
        raise ValueError("expected_exactly_one_final_assistant_message")
    return messages[0].encode("utf-8"), usage, {"observed_model": model, "event_parser": "cli-events-v1"}


class GeneratorAdapter:
    def __init__(self, spec: dict, cfg: dict) -> None:
        self.spec, self.cfg = spec, cfg

    def invoke(self, prompt: str, *, authorised: bool) -> Response:
        if not authorised:
            raise IntegrityError("Live inference not authorised")
        binary = executable(self.spec)
        if not binary:
            return Response(error="executable_missing")
        provider = self.spec["provider"]
        secrets = []
        with tempfile.TemporaryDirectory(prefix="mmmtap-p2-generator-") as directory:
            tmp = Path(directory)
            env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
                   if k in os.environ}
            env.update({"HOME": str(tmp), "TMPDIR": str(tmp), "NO_COLOR": "1",
                        "XDG_CONFIG_HOME": str(tmp / "xdg-config"), "XDG_DATA_HOME": str(tmp / "xdg-data"),
                        "XDG_CACHE_HOME": str(tmp / "xdg-cache")})
            if provider == "github_copilot_cli":
                credential = next((os.environ[k] for k in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
                                   if os.environ.get(k)), None)
                if not credential:
                    return Response(error="isolated_copilot_credential_missing")
                secrets.append(credential)
                env.update({"COPILOT_HOME": str(tmp / "copilot"), "COPILOT_GITHUB_TOKEN": credential})
                argv = [binary, "--model", self.spec["model_id"], "--reasoning-effort", self.spec["reasoning_effort"],
                        "--output-format", "json", "--stream", "off", "--available-tools=",
                        "--deny-tool=shell", "--deny-tool=write", "--deny-tool=url",
                        "--disable-builtin-mcps", "--no-custom-instructions", "--no-auto-update",
                        "--no-ask-user", "--no-experimental", "--no-remote-export", "--no-bash-env",
                        "--max-autopilot-continues", "0",
                        "--usage-output-file", str(tmp / "usage.json"), "-p", prompt]
            elif provider == "codex_cli":
                home = tmp / "codex"
                home.mkdir(mode=0o700)
                env["CODEX_HOME"] = str(home)
                auth = Path.home() / ".codex/auth.json"
                if os.environ.get("OPENAI_API_KEY"):
                    env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
                    secrets.append(env["OPENAI_API_KEY"])
                elif auth.is_file():
                    auth_data = auth.read_bytes()
                    (home / "auth.json").write_bytes(auth_data)
                    os.chmod(home / "auth.json", 0o600)
                    parsed = strict_json(auth_data)
                    if isinstance(parsed, dict):
                        secrets += [v for v in parsed.values() if isinstance(v, str)]
                        if isinstance(parsed.get("tokens"), dict):
                            secrets += [v for v in parsed["tokens"].values() if isinstance(v, str)]
                else:
                    return Response(error="codex_credential_missing")
                argv = [binary, "-a", "never", "exec", "--strict-config", "--ignore-user-config", "--ignore-rules",
                        "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only",
                        "--model", self.spec["model_id"], "-c", 'model_reasoning_effort="' + self.spec["reasoning_effort"] + '"',
                        *codex_overrides(),
                        "--json", "--color", "never", "-"]
            else:
                return Response(error="unsupported_generator_provider")
            response = run_process(argv, prompt, tmp, env, self.cfg["timeout_seconds"], self.cfg["max_response_bytes"])
            for attr in ("stdout", "stderr"):
                value, changed = redact_bytes(getattr(response, attr), secrets)
                setattr(response, attr, value)
                if changed:
                    response.provenance["credential_redaction"] = True
            if not response.error and response.exit_status == 0:
                try:
                    usage_path = tmp / "usage.json"
                    if usage_path.is_file():
                        with usage_path.open("rb") as stream:
                            raw = stream.read(self.cfg["max_response_bytes"] + 1)
                        if len(raw) > self.cfg["max_response_bytes"]:
                            raise ValueError("usage_output_size_limit")
                        raw, redacted = redact_bytes(raw, secrets)
                        if redacted:
                            response.provenance["credential_redaction"] = True
                        response.provenance["raw_usage"] = strict_json(raw)
                    response.message, response.usage, parsed_provenance = parse_cli_events(response.stdout, provider)
                    response.provenance.update(parsed_provenance)
                except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
                    response.error = "cli_contract:" + str(exc)
            elif response.exit_status not in (0, None):
                response.error = response.error or "nonzero_exit"
            response.provenance.update({"requested_model": self.spec["model_id"],
                                        "reasoning_effort": self.spec["reasoning_effort"],
                                        "identity_basis": "CLI_event_not_independent_provider_attestation",
                                        "provider_confirmed_model": None,
                                        "isolation": {"fresh_home": True, "fresh_cwd": True, "xdg_isolated": True,
                                                      "resume_requested": False, "environment_keys": sorted(env)},
                                        "binary_sha256": file_hash(Path(binary))})
            return response


class HaikuAdapter(GeneratorAdapter):
    pass


class GeminiAdapter(GeneratorAdapter):
    pass


class SolAdapter(GeneratorAdapter):
    pass


def parse_systemone(raw: bytes, request: dict) -> dict:
    obj = strict_json(raw)
    if not isinstance(obj, dict) or not isinstance(obj.get("model"), str) or not obj["model"]:
        raise ValueError("SystemOne resolved model missing")
    answers = obj.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(request["questions"]):
        raise ValueError("SystemOne answer IDs mismatch")
    for name, question in request["questions"].items():
        answer = answers[name]
        if not isinstance(answer, dict):
            raise ValueError("SystemOne answer shape")
        if question["type"] == "noul":
            number = answer.get("noul")
            if type(number) not in (int, float) or not 0 <= number <= 1:
                raise ValueError("SystemOne invalid noul")
        elif question["type"] == "choice":
            if answer.get("choice") not in question["criteria"]:
                raise ValueError("SystemOne invalid choice")
            probabilities = answer.get("probabilities")
            if probabilities is not None:
                if (not isinstance(probabilities, dict) or set(probabilities) != set(question["criteria"])
                        or any(type(p) not in (int, float) or not 0 <= p <= 1 for p in probabilities.values())
                        or abs(sum(probabilities.values()) - 1) > 0.001):
                    raise ValueError("SystemOne invalid choice probabilities")
        else:
            raise ValueError("Unsupported SystemOne question type")
    return {"mechanism": "native_jev", "answers": answers, "resolved_model": obj["model"],
            "usage": obj.get("usage"), "authority": "untrusted_model_judgements"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class NativeJEVAdapter:
    def __init__(self, spec: dict, cfg: dict) -> None:
        self.spec, self.cfg = spec, cfg

    def supports(self, contract: str) -> bool:
        return contract in self.spec["evidence_contracts"]

    def invoke(self, request: dict, contract: str, *, authorised: bool) -> Response:
        if not self.supports(contract):
            return Response(error="unsupported_contract")
        if not authorised:
            raise IntegrityError("Live SystemOne not authorised")
        key = os.environ.get(self.spec["key_env"])
        if not key:
            return Response(error="systemone_credential_missing")
        if self.spec["endpoint"] != "https://api.typesafe.ai/v1/systemone":
            raise IntegrityError("Unapproved endpoint")
        body = json_bytes(request)
        response = Response(provenance={"endpoint": self.spec["endpoint"], "request_sha256": digest(request),
                                        "transport_attempts": 1})
        start = time.monotonic()
        req = urllib.request.Request(self.spec["endpoint"], data=body, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=self.cfg["timeout_seconds"]) as stream:
                response.stdout = stream.read(self.cfg["max_response_bytes"] + 1)
                response.exit_status = stream.status
        except urllib.error.HTTPError as exc:
            response.exit_status = exc.code
            response.stdout = exc.read(self.cfg["max_response_bytes"] + 1)
            response.error = "systemone_http_error"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            response.error = "systemone_transport:" + type(exc).__name__
        response.latency_seconds = round(time.monotonic() - start, 6)
        if key.encode() in response.stdout:
            response.stdout = response.stdout.replace(key.encode(), b"[CREDENTIAL REDACTED]")
            response.provenance["credential_redaction"] = True
        if len(response.stdout) > self.cfg["max_response_bytes"]:
            response.stdout = response.stdout[:self.cfg["max_response_bytes"]]
            response.error = "output_size_limit"
        if not response.error:
            try:
                parsed = parse_systemone(response.stdout, request)
                response.message = json_bytes(parsed)
                response.usage = parsed["usage"]
                response.provenance["observed_model"] = parsed["resolved_model"]
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
                response.error = "systemone_contract:" + str(exc)
        return response


class CarlJEVAdapter:
    def __init__(self, spec: dict, cfg: dict) -> None:
        self.spec, self.cfg = spec, cfg

    def supports(self, contract: str) -> bool:
        return contract == "authenticated_git_diff_v1"

    @staticmethod
    def parse(raw: bytes) -> dict:
        obj = strict_json(raw)
        result = obj.get("result") if isinstance(obj, dict) else None
        if not isinstance(result, dict) or obj.get("dryRun") or obj.get("schemaVersion") != 1:
            raise ValueError("cARL result schema or dry-run output")
        if result.get("decision") not in ("pass", "warn", "review_required", "fail"):
            raise ValueError("cARL deterministic decision missing")
        signals = result.get("signals")
        if not isinstance(signals, list) or not signals or result.get("diagnostics"):
            raise ValueError("cARL signals missing or diagnostic failure")
        for signal_value in signals:
            if not isinstance(signal_value, dict) or not isinstance(signal_value.get("id"), str) or "value" not in signal_value:
                raise ValueError("cARL signal schema")
        # Historical cARL signals alone do not establish a new live SystemOne call.
        receipt = result.get("systemone_execution")
        if not isinstance(receipt, dict) or not receipt.get("model") or not receipt.get("request_sha256"):
            raise ValueError("cARL live SystemOne provenance unavailable")
        return {"mechanism": "carl_jev", "signals": signals, "decision": result["decision"],
                "systemone_execution": receipt, "authority": "untrusted_signals_plus_deterministic_policy"}

    def invoke(self, task: str, contract: str, evidence: dict | None = None, *, authorised: bool) -> Response:
        if not self.supports(contract) or not evidence:
            return Response(error="unsupported_contract")
        if not authorised:
            raise IntegrityError("Live cARL-JEV not authorised")
        # An operator-supplied authenticated binding is never synthesized from primary text.
        required = {"repository", "base", "head", "diff_sha256", "policy_path", "policy_sha256"}
        if set(evidence) != required:
            return Response(error="invalid_git_evidence_binding")
        import re
        if not all(re.fullmatch(r"[0-9a-f]{40}", evidence[s]) for s in ("base", "head")):
            return Response(error="git_commit_not_pinned")
        repo = Path(evidence["repository"]).resolve(strict=True)
        policy = (repo / evidence["policy_path"]).resolve(strict=True)
        if not policy.is_relative_to(repo) or file_hash(policy) != evidence["policy_sha256"]:
            return Response(error="policy_binding_mismatch")
        binary = executable(self.spec)
        if not binary:
            return Response(error="executable_missing")
        check = subprocess.run(["git", "--no-replace-objects", "-c", "core.fsmonitor=false",
                                "-c", "core.hooksPath=/dev/null", "diff", "--no-ext-diff", "--no-textconv",
                                "--no-renames", evidence["base"], evidence["head"], "--"],
                               cwd=repo, capture_output=True, timeout=30, check=False)
        from historical_extractor.archive import sha256
        if check.returncode or sha256(check.stdout) != evidence["diff_sha256"]:
            return Response(error="git_diff_binding_mismatch")
        with tempfile.TemporaryDirectory(prefix="mmmtap-p2-carl-") as directory:
            taskfile = Path(directory) / "task.json"
            taskfile.write_text(task, encoding="utf-8")
            argv = [binary, "review", "--base", evidence["base"], "--head", evidence["head"],
                    "--format", "json", "--task-file", str(taskfile)]
            env = {k: os.environ[k] for k in ("PATH", "HOME", self.spec["key_env"]) if k in os.environ}
            response = run_process(argv, "", repo, env, self.cfg["timeout_seconds"], self.cfg["max_response_bytes"])
        response.provenance.update({"cwd_policy": "operator_bound_git_repository", "evidence": evidence,
                                    "binary_sha256": file_hash(Path(binary))})
        if not response.error and response.exit_status in (0, 2):
            try:
                response.message = json_bytes(self.parse(response.stdout))
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
                response.error = "carl_contract:" + str(exc)
        else:
            response.error = response.error or "carl_nonzero_exit"
        return response


class MockAdapters:
    """Never live evidence. Full cARL support is test-only, not a production capability claim."""
    def __init__(self, *, test_carl_supported: bool = False) -> None:
        self.test_carl_supported = test_carl_supported
        self.calls: list[dict] = []

    def invoke(self, job: dict, payload: object, previous: dict | None) -> Response:
        self.calls.append({"job_id": job["job_id"], "mechanism": job["mechanism"], "payload": payload})
        if job["mechanism"] == "carl_jev" and not self.test_carl_supported:
            return Response(error="unsupported_contract", provenance={"mode": "mock"})
        if job["kind"] == "adversary":
            value = {"mechanism": job["mechanism"], "mock": True, "authority": "test_fixture_not_research",
                     "answers": {k: {"noul": 0.5} for k in payload["questions"]}}
        else:
            value = {"case_id": job["case_id"], "variant_id": job["variant_id"],
                     "claims": [], "disposition": "insufficient_evidence",
                     "uncertainties": ["MOCK: no security assessment performed."], "changes": []}
        raw = json_bytes(value)
        return Response(stdout=raw, message=raw, exit_status=0, usage={"input_tokens": 0, "output_tokens": 0},
                        provenance={"mode": "mock", "mock": True, "transport_attempts": 0})
