# Phase 2 continuation controller review

## Existing v1 behavior

`operator_execution_v1/runtime.py:199-432` reserves an attempt before
preparation/invocation, binds outputs to immutable jobs and parent
checkpoints, reuses verified existing outcomes on deliberate resume, and
never issues a second attempt for a terminal failed job. In live mode a
schema, execution, or model-identity failure stops the current invocation;
resuming requires the same manifest, output root, profile, and persisted
budget. Descendants of unsuccessful parents become `blocked_parent`, while
independent unattempted jobs may continue after deliberate resume. Stage
completion never advances automatically.

Known unavailable credentials are recorded as `adapter_unavailable`; the
v1 runner can continue processing unrelated positions. That behavior is
accountable, but a future controller that must stop on credential problems
should preflight and fail closed before exposing any continuation plan.
Unknown, interrupted, and potentially executed attempts remain failures,
not invitations to retry. The recovery policy is detailed in
`operator_execution_v1/STOP_RESUME_RECOVERY.md`.

## Separate v2 component

`phase2_v2/continuation.py` declares
`mmmtap-phase2-continuation-v2`. It is deliberately not wired to a provider,
adapter, stage executor, or live command.

- `audit_completed_stage` is read-only. It checks manifest and job
  identities, run/authorization scope, ledger sequence/hash chain, intent
  reservations, payload/raw/result artifact hashes, terminal completion
  anchors, parent checkpoint binding/blocking semantics, status totals,
  budget, and final summary. It inventories evidence before and after and
  rejects missing, symlinked, malformed, unknown, or inconsistent evidence.
- `plan_continuation` is pure. It preserves terminal schema failures, requires
  explicit authorization before planning pending jobs, enforces verified
  identity and attempt budgets, stops for credential/identity/unknown or
  ambiguous execution states, and never makes a provider call.
- A pending child is runnable only when **every required parent has a
  verified `ok` outcome**. Terminality or checkpoint existence alone is not
  sufficient. Missing parents defer the child; verified `schema_invalid`
  or `blocked_parent` outcomes block it; other failure or unknown states
  stop planning. Planned-but-unexecuted parents are never assumed successful.
- The planner is a decision function, not a durable executor. It does not
  write checkpoints, reserve budgets in a live ledger, or itself prove that
  its input outcomes came from verified checkpoints. The caller must explicitly
  supply `verified_outcome_job_ids` after checking checkpoint integrity and
  lineage; omitted verification fails closed even for an `ok` status. This
  caller attestation is not itself a cryptographic verifier. A future executor must
  consume only audited evidence, reserve each invocation atomically, run
  jobs serially in dependency order, and replan from newly committed
  checkpoints. No live integration is approved by this review.

## Offline replay acceptance

The deterministic test audits the existing pilot using the expected
manifest identity `3062def66204e79ec8bcc3b7565f3de681b5dcb411bee06a6817fb04152ddfc1`.
It verifies:

| Replay result | Required and observed |
|---|---:|
| `ok` | 114 |
| `schema_invalid` | 28 |
| `blocked_parent` | 11 |
| Attempt reservations | 142 |
| Terminal checkpoints | 153 |
| Schema-invalid reasons: retained / incomplete / top-level | 15 / 12 / 1 |
| Provider calls during replay | 0 |
| Frozen pilot evidence modified | No |

The replay reads `operator_runs_v1/pilot/` only; a complete SHA-256 inventory
is compared before and after. The auditor also checks the ledger-to-checkpoint
and checkpoint-to-summary bindings rather than trusting only the reported
totals.

Tests: `PYTHONDONTWRITEBYTECODE=1 python -m unittest phase2_v2.test_continuation -v`.
The suite covers exact pilot replay, tampered manifest rejection, explicit
authorization, no retry of schema failures, parent blocking, deferred
children, multi-parent acceptable-outcome and explicit-verification gates,
credential/identity/unknown-status/budget fail-closed behavior, and
completion with no new calls. The separate package check is
`PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify`.

## Status and limits

The replay/planner is implemented as an isolated v2 component and does not
alter v1. Its offline acceptance target is met. It is not an execution
authorization, research-grade run controller, cross-host exactly-once
mechanism, or strict-isolation certificate. Before any live use, a human must
approve a versioned executor integration and stage scope; the executor must
reconstruct state only from integrity-checked immutable checkpoints, reserve
attempt budgets before every invocation, stop on integrity/identity/
credential/unknown/ambiguous outcomes, preserve parent semantics, and never
retry, repair, replace, or silently advance. The full experiment remains
unauthorized.
