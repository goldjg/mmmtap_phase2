"""Versioned subscription CLI containment; never the strict Q1 worker profile.

Current CLI binaries are inspected/started only for help in a networkless,
credential-free sandbox during qualification. Fixture executions substitute a
pinned event producer under the same mounts/guard. No inference occurs here.
"""
import os
from pathlib import Path
import shutil

from ..model import raw_hash, encode, decode
from ..contracts import ROOT

HERE = Path(__file__).resolve().parent
PROFILE = "q1-subscription-cli-containment-v1"


def metadata():
    from phase2.adapters_v2 import copilot_argv, codex_argv
    from phase2.software import tree_identity
    result = {}
    for key, provider, model, name in (
        ("gemini", "github_copilot_cli", "gemini-3.8-flash", "copilot"),
        ("haiku", "github_copilot_cli", "claude-haiku-5.5", "copilot"),
        ("sol", "codex_cli", "gpt-6.1-sol", "codex")):
        path = Path(shutil.which(name) or "/missing/" + name).resolve(strict=True)
        item = {"provider": provider, "model": model, "binary": str(path),
            "binary_sha256": raw_hash(path.read_bytes()), "profile": PROFILE,
            "argv": codex_argv() if key == "sol" else copilot_argv(model),
            "credential_source": "owner_only_ChatGPT_auth_file" if key == "sol" else "COPILOT_GITHUB_TOKEN",
            "transport": "subscription_CLI_events_not_provider_HTTP", "provider_HTTP_attempts": None,
            "provider_internal_retries": "UNKNOWN", "serving_identity_attestation": None}
        if key != "sol":
            index = item["argv"].index("--no-remote-export")
            item["argv"][index:index+1] = ["--sync-session", "off"]
            item["historical_flag_adaptation"] = {"--no-remote-export": "--sync-session off",
                "basis": "current_binary_help_rejects_old_flag_and_names_replacement"}
        if key == "sol":
            release = path.parent.parent
            # This is the installed immutable runtime, not CODEX_HOME. Refuse
            # credential filenames before any recursive byte inspection.
            if any(p.name in {"auth.json", "credentials.json"} for p in release.rglob("*")):
                raise ValueError("runtime_tree_contains_auth_filename_not_inspected")
            item.update(release_root=str(release), release_tree=tree_identity(release))
        result[key] = item
    return result


def verify_binding(binding):
    from phase2.software import tree_identity
    if raw_hash(Path(binding["binary"]).read_bytes()) != binding["binary_sha256"]:
        raise ValueError("current_CLI_binary_changed")
    if "release_root" in binding and tree_identity(Path(binding["release_root"])) != binding["release_tree"]:
        raise ValueError("current_CLI_runtime_closure_changed")


def environment(binding):
    from phase2.isolation import sandbox_env
    if binding["provider"] == "codex_cli":
        return sandbox_env({"CODEX_HOME": "/home/assessor/.codex", "PATH": "/opt/codex-release/codex-path:/opt/codex-release/bin:/usr/bin:/bin",
                            "RUST_LOG": "warn,codex_core=debug", "PYTHONDONTWRITEBYTECODE": "1"})
    return sandbox_env({"COPILOT_HOME": "/home/assessor/.copilot", "PYTHONDONTWRITEBYTECODE": "1"})


def argv(binding, workspace, *, fixture=False, help_only=False):
    from phase2.isolation import bwrap_argv
    work = str(Path(workspace).absolute())
    binds = [(work + "/work", "/work"), (work + "/guard.py", "/opt/q1-cli-guard.py")]
    if binding["provider"] == "codex_cli":
        binds.append((binding["release_root"], "/opt/codex-release"))
    else:
        binds.append((binding["binary"], "/opt/bin/copilot"))
    command = list(binding["argv"])
    if help_only:
        # Exact production option parsing, with help terminating before a task.
        command = command[:-1] + ["--help"] if command[-1] == "-" else command + ["--help"]
    if fixture:
        binds += [(work + "/event_fixture.py", "/opt/event-fixture.py"), (work + "/request.json", "/inputs/request.json"),
                  (work + "/fixture.stdout", "/inputs/fixture.stdout"), (work + "/fixture.stderr", "/inputs/fixture.stderr")]
        binds.append((work + "/scenario", "/inputs/scenario"))
        command = ["/usr/bin/python3", "-I", "-S", "-B", "/opt/event-fixture.py"]
    command = ["/usr/bin/python3", "-I", "-S", "-B", "/opt/q1-cli-guard.py", *command]
    result = bwrap_argv(command, ro_binds=binds, rw_binds=[(work + "/home", "/home/assessor")],
                        network="none" if fixture or help_only else "host")
    # No ambient Linux capabilities, even in this explicitly broader profile.
    result[2:2] = ["--cap-drop", "ALL"]
    return result


def initialise(workspace, binding):
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("home", "work"):
        (workspace / name).mkdir(mode=0o700)
    (workspace / "home" / (".codex" if binding["provider"] == "codex_cli" else ".copilot")).mkdir(mode=0o700)
    (workspace / "guard.py").write_bytes((HERE / "guard.py").read_bytes())


LIMITATIONS = {
    "network": "production_host_namespace_not_endpoint_filtered; fixtures/help_have_no_network",
    "processes": "internal_children_allowed_inside_private_PID_namespace; one_top_level_CLI_launch_per_reservation",
    "tools": "client_config_restrictions_and_streaming_watchdog; no_universal_pre_dispatch_tool_interlock",
    "filesystem": "fresh_private_home_and_tmp; readonly_work_and_usr_runtime; host_home_repo_and_other_auth_hidden",
    "credentials": "only_selected_subscription_credential_in_CLI_context; CLI_can_access_its_own_credential",
    "credential_inspection": "CLI_environment_or_staged_auth_not_fully_isolated_from_other_same_UID_processes; not_the_SystemOne_broker_FD_guarantee",
    "remote_context": "fresh_local_context_requested; complete_remote_isolation_unavailable",
    "identity": "client_report_or_requested_configuration_only; independently_attested_serving_identity_unavailable",
    "remote_attempts": "UNKNOWN; no_harness_retry_or_fallback",
}
