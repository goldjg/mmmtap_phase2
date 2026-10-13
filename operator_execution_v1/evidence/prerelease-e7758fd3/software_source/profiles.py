"""Assurance labels are part of experiment identity, never approval overrides."""
from __future__ import annotations

import copy

from phase2.core import IntegrityError

PROFILES = {
    "strict_isolation": {
        "name": "strict_isolation",
        "version": "frozen-v5-unchanged",
        "evidence_quality": "strict_isolation_required_not_qualified",
        "satisfies_strict_isolation": False,
        "live_generators": "blocked",
        "preventive": [
            "All v5 preventive qualification criteria remain mandatory.",
            "Unqualified generators are rejected before credentials or process launch.",
        ],
        "detective": ["Unmodified v5 source-bound qualification evidence."],
        "unenforced": [
            "No new strict qualification is supplied by this operator package.",
        ],
    },
    "research_controlled": {
        "name": "research_controlled",
        "version": "research-controlled-v1",
        "evidence_quality": "lower_assurance_operator_supervised_research",
        "satisfies_strict_isolation": False,
        "live_generators": "separate_stage_authorisation_required",
        "preventive": [
            "Fresh process and private home for every generator turn and arm.",
            "Bubblewrap hides host homes, research repositories and run checkpoints.",
            "Source and prompts are stdin data; /work and mounted inputs are read-only.",
            "Only the selected adapter credential is staged; no ambient environment.",
            "Generator seccomp denies non-thread process creation and namespace changes.",
            "No corpus code is restored to executable paths or intentionally executed.",
            "No tool permissions, user instructions, plugins or previous sessions are imported.",
            "Exact pinned model/CLI/configuration; no harness retry or model fallback.",
            "Exclusive, fsynced first-attempt reservations and checkpoint creation.",
            "Serial execution and a persisted maximum adapter-attempt budget.",
        ],
        "detective": [
            "Streaming watchdog kills on observed tools, subagents, retries or model switching.",
            "Strict v5 event/parser validation rejects unexpected output and tool telemetry.",
            "Raw evidence, requested/client/provider identity and configuration hashes are retained.",
            "Source, executable, policy, checkpoint and own-branch lineage hashes are checked.",
            "Known credential echoes are withheld and the attempt fails explicitly.",
        ],
        "unenforced": [
            "Authenticated CLI egress uses host networking; no provider-only allowlist.",
            "CLI/provider internal retries may race or evade the watchdog.",
            "Codex internal tools remain advertised; no universal pre-dispatch tool interlock.",
            "Seccomp denies child processes, not all code running inside the existing CLI process.",
            "Staged credentials are visible to their CLI; token scopes and server validity are not proven offline.",
            "Codex served-model identity is unavailable; client configuration is not provider attestation.",
            "Copilot model events and SystemOne model strings are not signed provider attestations.",
            "Read-only /usr and the host kernel are not a hermetic runtime image.",
            "Operator/root mutation, storage rollback and cross-host exactly-once execution are not prevented.",
        ],
    },
}


def profile(name: str) -> dict:
    if name not in PROFILES:
        raise IntegrityError("Unknown execution profile")
    return copy.deepcopy(PROFILES[name])


def authorise(plan: dict, stage: str, *, authorised_stage: str | None,
              accept_lower_assurance: bool, approve_instruments: bool,
              review_note: str | None = None) -> None:
    execution = plan["operator_execution"]
    if stage != execution["stage"] or authorised_stage != stage:
        raise IntegrityError("Separate explicit authorisation for this exact live stage is required")
    if execution["profile"] != profile(execution["profile"]["name"]):
        raise IntegrityError("Execution profile was altered")
    if execution["profile"]["name"] == "strict_isolation":
        raise IntegrityError("strict_generator_isolation_blocked; v5 qualification is unchanged")
    if not accept_lower_assurance or not approve_instruments:
        raise IntegrityError("Explicit lower-assurance acceptance and frozen-instrument approval are required")
    if stage != "smoke" and (not isinstance(review_note, str) or not review_note.strip()):
        raise IntegrityError("A deliberate review note for the preceding stage is required")
