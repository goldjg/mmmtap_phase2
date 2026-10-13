# Path B offline validation v1

## Outcome and scope

Implemented `carl-assessment-challenge-v1` as a separate offline sibling
executable and MMMTAP request adapter. **Zero live SystemOne calls, zero
generator calls, zero pilot calls, zero historical admissions.**

The executable supports `prepare`, `evaluate-offline` and `replay`; it has no
live transport, credential lookup or live-success status. This report does
not qualify a live adapter or unblock the old execution plan's E2/E3 jobs.
Path A remains unchanged.

## Implementation and actual reuse

The Go implementation is in `../cARL-semantic-eval/internal/assessment` and
`../cARL-semantic-eval/cmd/carl-assessment-challenge` relative to the Phase 2
workspace. `phase2/path_b.py` reuses the original native request constructor
and reads existing immutable checkpoints only as lineage evidence.

The additive `internal/pack/snapshot.go` API invokes real cARL discovery,
profile/role/task activation, required dependencies, precedence, explicit
overrides, conflict detection and policy trace construction. It does not
reimplement that machinery. A new explicitly versioned typed-rule block
provides assessment-specific policy; ordinary pack prose is not interpreted.
Only effective, non-overridden pack rules apply.

`path_b_policy_v1` demonstrates custom packs, dependencies and reviewer/cautious
roles. Its thresholds are offline fixtures, not approved experimental policy.
The distinct cARL mechanism is deterministic policy arbitration over a matched
SystemOne question set, not a separate underlying adversarial model.

Receipts preserve exact request/response bytes, source/manifest/parent hashes,
the native request, frozen policy definitions, cARL trace, compiled policy,
implementation hash, parser result and evidence mode. Replay reconstructs the
frozen policy independently of the current policy directory. Externally held
hashes verify integrity, **not provider authentication or correctness**.

## Validation results

| Check | Actual result |
|---|---|
| Full Go suite, uncached | 232 top-level tests passed; 297 including subtests; 16 packages passed; no skipped tests |
| New Go assessment package | 16 top-level tests passed |
| Full Python suite | 100 tests passed, including 7 new Path B tests |
| `go vet ./...` | Passed |
| Separate Path B and original Path A builds | Passed; installed binary not overwritten |
| Original/rebuilt Path A help | Exact stdout/stderr equality |
| Compiled Path B corpus coverage | 135 case/variant identities; 108 distinct source hashes |
| Preparation, mock evaluation, offline replay | 137 successful sets; no failed corpus attempts |
| Native request parity | Exact full request bytes for every covered branch |
| Extra sequential coverage | One independent parent-lineage example for each E3 order, in addition to unit tests |
| Source archive | SHA-256 verified against the existing frozen manifest |
| Live model invocations | 0 |

The 137 sets are 135 E2 reference positions plus two E3 examples, all using
Haiku-labelled **existing mocked** checkpoints. No Haiku execution occurred.
Every provider response used here is an explicitly generated numerical mock
fixture with model field `offline-fixture-not-provider`. The examples do not
represent provider judgments, experimental findings or live branch feasibility.

All historical mock assessments used in this corpus coverage have **zero
claims**, leaving the two assessment-level questions. Nonempty claims,
quote preservation and exact claim-question construction are separately
covered by benign Go fixtures; Python tests verify the reused native builder.
The entire E3 corpus matrix and all generator transports were not run.

Tests cover strict/duplicate/malformed JSON, source and parent tampering,
unsupported Git/deployment assertions, exact matched questions, missing
policy/dependencies/roles, conflicts, overrides, inactive rules, threshold
boundaries, failed first-attempt immutability, oversized receipt failure
persistence, raw response preservation, anchored replay/tampering, policy
changes after capture, source-instruction isolation, stripped adapter
credentials/environment, timeout without retry, and both branch histories.

Exact test commands, stdout, stderr and exit statuses are retained in the
adjacent JSON/text logs. Per-case directories retain request bytes,
preparations, mock responses, receipts and each subprocess outcome.
`receipt_anchors.json` independently lists the recorded receipt digests.

## Preserved failures and original evidence

An initial formatting check failed because new test declarations were
accidentally nested. After correcting this, the first full Go suite found
embedded-mirror drift caused by new paragraphs in shared cARL memory and
trust-boundary documents. Those Path B-only paragraphs were removed from
the shared defaults and recorded in dedicated documentation instead; changing
embedded defaults would have unnecessarily affected Path A.

These failed development checks remain in `gofmt.*` and `go_tests.*`.
The successful corrected run is `go_tests_final.*`. They are not inference
attempts; no provider was called or retried. All compiled corpus attempts
succeeded on their first invocation.

The original harness checksum inventory checked **29,185 files**:
29,184 matched, with one pre-existing mismatch in `phase2/adapters.py`.
That file was already amended during earlier adapter qualification. Its
current hash matches the sealed investigation's source index and the
pre-Path-B snapshot; Path B did not edit it. The old checksum manifest was
not rewritten to conceal this mismatch.

Original plans, checkpoint results, adjudication packets, frozen inputs,
historical extraction, qualification and investigation evidence are preserved.
`protected_before.json`, `preservation.json`, original-manifest checks and
`original_harness_integrity.json` record the verification boundaries.
The installed Path A binary remains:

```text
b34696d54d0b9c910d48c9adbe0155f825617d8e4c8981e58a2f50b5d0868428
```

Original `cmd/carl`, `internal/review`, `internal/semantic`, embedded assets,
shared policy defaults and dependency manifests match the source revision.
Build metadata, revision, tested implementation snapshots and binary hashes
are retained. No dependency installation or release configuration changes
were required.

## Remaining qualification requirements

1. Approve and freeze the experimental role, custom-pack definitions, typed
   policy semantics and thresholds. These examples are not production policy.
2. Implement and review a separately authorized single-attempt live transport
   with trustworthy request-bound receipt capture. Offline digest receipts
   cannot attest provider invocation; imported data stays unverified.
3. Verify actual SystemOne identity/version, endpoint and authentication,
   redirect/retry restrictions, timeouts, raw response/usage capture, source
   data-release requirements and full-corpus capacity. Match native JEV's
   underlying model and questions while making independent provider calls;
   never reuse native outputs as cARL experimental evidence.
4. Integrate global attempt-ID uniqueness, append-only ledger handling and
   software/policy-bound planning without altering existing plans or results.
   Exclusive output directories currently prevent overwrite/retry but do not
   enforce global ID uniqueness across directories.
5. Obtain separate authorization for live adapter smoke tests, resolve the
   existing generator qualification blockers, then freeze a new experimental
   plan and obtain explicit pilot authorization.

Standalone cARL verifies supplied archive-member/manifest/parent bindings; it
does not independently reopen or authenticate the archive. The MMMTAP builder
does verify the real frozen archive. Neither layer asserts authenticated Git
history, deployed state, correctness or an operational gate bypass.

The next approval should cover production policy selection and the bounded
live-transport/qualification work, **not the 81-call pilot yet**.
