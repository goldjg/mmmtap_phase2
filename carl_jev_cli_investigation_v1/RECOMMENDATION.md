# Recommendation

**Use an explicitly approved, versioned assessment-challenge interface
(Path B) for the 135 frozen source-text cases. Preserve the installed Git-review
CLI (Path A) for a separately admitted authentic-Git partition. Neither path is
currently live-ready for the primary cARL arms.**

The important correction is not that cARL can only ever process diffs:
the installed command builds Git-review state, but its underlying evaluator
accepts a typed state/question interface and optional caller text already
exists. What is absent is a public, typed, provenance-honest mode for challenging
an existing assessment of frozen non-Git source under an explicit cARL policy.
Putting JSON in `--task` transports it; it does not implement that mode.

The separate local `cARL-semantic-eval` worktree provides inspectable source
for the semantic-review path, supported by binary debug paths and offline
behavior. Its eight boolean questions and one score produce model signals
which cARL maps to deterministic Git-review findings. The CLI itself does not
cryptographically authenticate history and cannot emit the Phase 2-required
SystemOne execution receipt. Both inspected repositories lack active semantic
configuration. Hosted SystemOne also uses a different wire schema from the
CLI's HTTP adapter.

## Current decision

Keep all 135 primary cases `unsupported_contract` for the installed cARL
Git-review path. The existing 1,215 unsupported cARL jobs and 2,025 blocked
descendants remain unchanged. Do not manufacture repositories/diffs, waive
provenance, accept a fail-open `pass`, infer live identity from config, or
convert the historical bridge into a qualified result.

Path A still needs genuine evidence admission, a verified hosted translation/
receipt path, actual config/policy binding, and repairs to the Phase 2 binding/
task-file integration. It can provide assessment-conditioned **Git policy
feedback**, not arbitrary typed claim verification.

## Exact next decision

Approve or reject the **design and implementation scope** of
`carl-assessment-challenge-v1` described in `INTEGRATION_OPTIONS.md`, including
the question catalog, deterministic policy, evidence labels, model-version
binding and receipt format. Such approval would authorize a separate scoped
implementation task only, not live calls.

After implementation and offline contract validation, separately authorize
fresh live qualification attempts. Only then consider a newly frozen execution
plan and separate pilot authorization, also subject to the existing generator
blockers. This investigation is not permission for either the 81-call pilot
or the full experiment.

## Evidence and preservation

Seven read-only dry-run probes confirmed transport behavior and expected
contract failures. There were **zero live SystemOne calls**, zero experimental
calls and zero source or installed-binary changes. The 135 input hashes and
108 distinct-byte count were reverified. Existing integration tests were
inspected, not run; no mocked result was promoted to live evidence.

Reports and exact command/source evidence live only in this versioned
investigation directory. The previous sealed qualification remains intact;
no earlier report was rewritten to hide narrower or corrected conclusions.
No cARL governance-file update was made because this task explicitly forbids
cARL repository modifications. Any accepted interface/policy change will need
its own approved cARL documentation/governance update.

Residual uncertainties are explicit: source-to-binary build attestation,
hosted bridge compatibility, live model identity, zero-wire-retry guarantees,
strict response validation, evidence size/redaction behavior, and the proposed
assessment policy. None is resolved merely by successful help or dry-run exit.
