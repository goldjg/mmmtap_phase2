# Separately authorised limited live qualification

**NOT EXECUTED. This file is a procedure, not permission.** The implementation
and offline package authorise no provider/model call and no 81-call pilot.

## Preconditions and stop rules

Review `REMEDIATION_REPORT.md`, the nine paired loopback controls, frozen
instrument hashes and full test results. Reverify the package checksum and
v3 plan with `python -m phase2.readiness validate`. Any binary, Python, Go,
configuration, template or policy change requires a new frozen version.

Approve the proposed role/thresholds for qualification only. The primary
reviewer uses 0.5 cutoffs; the inactive cautious role is an explicit alternate,
not pooled with the reviewer. No security-benefit claim supports these choices.
Confirm source-data release permission and intended GitHub/ChatGPT/SystemOne
accounts without recording credentials. Copilot needs an explicit environment
token; Codex needs an existing valid local login. Stage no user instructions.

Remaining engineering/qualification gates are explicit:

- Codex still advertises ten internal tools. The mount boundary prevents access
  to the host research workspace; it does not prove zero internal tool execution.
  Strict tool-free qualification needs an upstream fix or a separately reviewed
  pre-execution interlock. Do not approve experimental use based on the watchdog.
- Copilot cannot disable all internal retries by a documented CLI flag.
  A first-failure watchdog was tested, but does not prove no racing wire retry.
  Inspect actual transport evidence; reject ambiguous or multiple-call attempts.
- Host network in the isolated live command is not a provider-only firewall.
  Use a separately reviewed restricted host/network if that is required for
  the qualification boundary. Do not deploy or modify one under this task.
- Prior authenticated catalog evidence confirms advertised Haiku/Gemini IDs at
  that time, not current upstream served versions. Revalidate metadata when
  separately authorised; never replace a missing served identity with a request.

An authorisation must name the adapter, fixture, account, maximum one invocation,
output directory and allowed metadata/network operations. A failed or incomplete
first attempt is retained. Stop after failure; any further attempt needs new
explicit authorisation and a new directory. No fallback model or rerun is allowed.

## Bounded diagnostic sequence

The commands below use `synthetic-token-logging/baseline`, a frozen descriptive
input, never executed as code. The maximum proposed sequence is five adapter
invocations: three generators, then native JEV and Path B. They are qualification
calls only. Authorise adapters individually after their preconditions are met;
if Haiku fails, do not fabricate a parent for the adversary checks.

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m phase2.readiness qualify --adapter haiku \
  --out qualification_haiku_attempt1 --authorize-live
python -m phase2.readiness qualify --adapter gemini \
  --out qualification_gemini_attempt1 --authorize-live
python -m phase2.readiness qualify --adapter sol \
  --out qualification_sol_attempt1 --authorize-live
python -m phase2.readiness qualify --adapter native_jev \
  --parent-run qualification_haiku_attempt1 \
  --out qualification_native_attempt1 --authorize-live
python -m phase2.readiness qualify --adapter carl_jev \
  --parent-run qualification_haiku_attempt1 \
  --out qualification_path_b_attempt1 --authorize-live
```

Do not execute this as an unattended five-command batch. Each adversary receives
the same actual nonempty B0 claims/source and identical typed questions but
makes its own evaluation; no provider response reuse. Path B applies the frozen
role/policy after evaluation. Actual outputs are not ground truth.

Each command reserves its directory before invocation. On interruption,
preserve intent/raw artifacts and do not retry. Credential failures are outcomes.
The local attempt counter describes wrapper calls, not unknowable provider
internals. Inspect SystemOne request-written/TLS/status/raw headers/model fields,
policy replay and all failure classifications. Missing request-written evidence
does not prove the remote service saw nothing.

## Acceptance evidence before any pilot request

Inspect raw CLI JSONL and stderr, not process exit alone. Require one assessment,
correct source/identity/schema, no inherited conversation, verified source
quotes, no observed tool action, no unexpected model call, and reviewed retry
accounting. Distinguish advertised tools, rejected calls and executed actions.
Capture exact requested reasoning/model, client-observed metadata, catalog
evidence and whatever provider identity is actually exposed.

For Path B, verify request bytes equal native JEV's bytes, independent evaluation
receipts, unchanged supplied-not-Git provenance, exact active profile/policy,
raw response/parser status and deterministic replay. TLS and local SHA hashes
are not provider signatures. Any lack of provider-authenticated receipts remains
an explicit limitation rather than fabricated attestation.

`qualification_result.json` deliberately never sets `live_qualified: true`.
After independent evidence review, publish a separately versioned qualification
report, freeze the chosen policy/model aliases or exact served-version policy,
and review full-corpus capacity and scoring/adjudication readiness. Three fixture
inputs do not qualify every real source size. Only then request approval for a
new gated experimental plan and the 81-call pilot. The current v3 plan keeps live
experiment execution disabled and cannot be unlocked by these commands.
