# Assessment challenge v1 (offline only)

`cmd/carl-assessment-challenge` is a separately versioned sibling executable.
It does not register a new command in `cmd/carl`, replace `~/bin/carl-jev`,
or change `internal/review`, `internal/semantic`, pack/profile semantics or
Path A's Git-evidence contract.

This implementation has **no live command, provider transport or credential
lookup**. It prepares matched SystemOne requests, consumes explicitly mock or
unverified imported responses, and replays cARL-owned assessment policy.
It is not a qualified live integration.

## Build and commands

Build to a new operator-selected path, never over the installed Path A binary:

```sh
GOPROXY=off GOSUMDB=off go build -o /tmp/carl-assessment-challenge-v1 ./cmd/carl-assessment-challenge
```

```text
carl-assessment-challenge prepare --request FILE --policy-root DIR --out NEW_DIR
carl-assessment-challenge evaluate-offline --prepared FILE --prepared-sha256 HASH --response FILE --mode mock|imported_unverified --out NEW_DIR
carl-assessment-challenge replay --receipt FILE --receipt-sha256 HASH
```

`NEW_DIR` must not exist. Each operation reserves an independent attempt,
persists intent and inputs with exclusive writes, and writes a preparation or
receipt plus its SHA-256. Invalid responses produce a failed receipt and
nonzero exit, never `no_challenge`. Invalid preparation produces an explicit
failure record. Serialization/capacity and later write errors also attempt to
persist a failure record; persistence failures are reported explicitly.
Repeating an output path fails; it does not resume, overwrite
or retry. An intentionally new attempt requires a new request attempt ID and
output directory; operators must keep the original attempt.

`replay` needs an independently retained receipt digest. It recomputes the
prepared request bindings, calls the same cARL pack/profile evaluator on the
frozen snapshot, recompiles assessment rules and recomputes the policy result.
Current repository configuration, responses from other branches and network
services are not consulted.

## Actual reuse of cARL

The additive `pack.PolicyTraceInDir` API delegates to existing discovery,
profile/role/task activation, required dependencies, precedence, explicit
overrides, conflict detection and provenance explanation. It changes no
existing command semantics. Path B captures repository-local selection,
profiles, optional registry-install provenance and instruction definitions.
It evaluates that snapshot with no ambient bundled-pack fallback.

V1 requires explicit `packs.json`, `profiles.json`, active profile and role,
and locally materialized dependencies. Invalid or unresolved composition
fails closed. Effective overridden packs stay visible in the trace but their
assessment rules are not applied. Definitions of selected-but-inactive packs
are retained for reproducibility but never become applied policy.

Ordinary pack prose is **not** converted into executable policy. This explicit
extension recognizes one narrowly typed fenced block in each effective pack:

````text
```carl-assessment-policy-v1
{"rules":[{"id":"support","signal":"claim_supported","operator":"lt","threshold":0.5,"action":"challenge_required"}]}
```
````

Supported signals are `claim_supported` (expanded per indexed claim),
`authority_promoted` and `uncertainty_adequate`. Operators are `lt` and `ge`;
finite thresholds must be explicitly supplied in [0,1]. Actions are
`challenge_required` or `insufficient_evidence`. Rule IDs are unique per pack.
Unknown fields, missing thresholds and conflicting pack composition fail.
Applied packs compose additively: insufficient evidence dominates a challenge,
which dominates no challenge. Rule order is stable within cARL pack order.

Thresholds and role selection are operator policy, not provider output or
source instructions. The MMMTAP `path_b_policy_v1` directory is an **offline
fixture**, not an approved research policy. No production threshold is chosen
implicitly. It demonstrates existing custom packs, an evidence dependency,
reviewer/cautious role overlays and an explicit override.

## Request and matched native questions

The input schema is `carl-assessment-challenge-v1-request`; exact fields and
types are in `internal/assessment/request.go`. It carries:

- explicit attempt ID, branch, turn and parent job;
- exact UTF-8 source, SHA-256, archive/member/manifest provenance, mandatory
  `authenticated_git: false` and `deployment_state: "not_asserted"`;
- the existing MMMTAP assessment object;
- base64 raw manifest, raw parent checkpoint and raw native request bytes;
- the raw parent-checkpoint digest.

Source/manifest case/member/hash binding and parent job/input/assessment/status
binding are verified. Assessment quote substrings must occur in the source.
No code is executed or source transformed/redacted. V1 supports supplied
archive-member text only; arbitrary non-archive input is explicitly unsupported.
The cARL command does not reopen the archive: its guarantee is correspondence
to the supplied manifest and bytes, not independent archive authentication.
The MMMTAP builder additionally verifies the actual frozen archive.

The entire native request byte string is retained unchanged, including model,
state and questions. Validation requires the native task and the source/
assessment state to match, and exactly the existing native JEV question set:
one noul question per indexed claim, `authority_promoted`, and
`uncertainty_adequate`, with identical instructions. No cARL-only questions or
pack prose are injected into that request. Native and cARL calls must remain
separate independent evaluations in any future live study.

The distinct cARL mechanism is **post-evaluation deterministic policy
arbitration** from the actual effective packs/role, not an independent model.
Raw noul values remain model judgments. Rules emit claim/question/pack/rule
references and source quotes, not fabricated model explanations or correctness.

Limits: 8 MiB JSON/file/artifact, 64 JSON nesting levels, 1 MiB source,
128 claims, 2 MiB total policy definitions, 256 policy files/rules. Oversized,
malformed, duplicate-key, unknown request fields, missing provenance,
unmatched questions and incomplete/non-numeric/out-of-range answers fail.
These are offline interface limits, not provider capacity qualification.

## Receipts and epistemic boundary

Preparation embeds exact request and policy bytes, complete cARL trace,
compiled rules, binary digest and hashes for source, assessment, parent,
manifest, native request, policy snapshot and compiled policy.

Receipt schema `carl-assessment-challenge-v1-receipt` embeds the preparation,
raw response, their hashes, deterministic result, parser failure when present,
execution binary hash and mode. Base64 byte fields preserve original JSON
formatting independently of canonical derived objects. Return statuses are
`mock_ok`, `imported_unverified`, or `failed`; `live_calls` is always zero.
Returned model text is labelled unverified even when it resembles a real model.
Raw usage metadata remains in the response artifact rather than being invented.

Hashes with an external trusted digest detect alteration and allow offline
replay. They are **not signatures**, publisher authentication, provider
receipts or evidence of a SystemOne invocation. An attacker who replaces both
receipt and trusted digest can invent a consistent offline record. Keep the
digest in independently controlled evidence storage. Missing/live receipt
authentication cannot be fixed by relabelling an imported response.

Replay records the historical implementation digest; operators must also
pin the replay binary/source version externally. The same v1 semantics are
recomputed, not arbitrary code embedded in a receipt.

## Qualification still required

Before live use, approve and freeze the policy/role/thresholds and the new
experimental mechanism/plan. Implement/review an explicitly authorized
single-attempt transport and request-bound receipt capture, using the same
underlying SystemOne model policy as native JEV. Validate actual served identity,
credentials, endpoint/redirect/retry controls, provider capacity, raw response/
usage capture and data-release handling. Do not execute extracted code.

Obtain separately authorized smoke tests and distinguish provider evidence
from local hashes and imported data. Generator qualification blockers and the
separate pilot authorization remain. Path A, old plans, existing qualification
attempts and frozen research evidence must not be rewritten.

## Offline validation evidence

`../mmmtap_phase2/path_b_validation_v1/VALIDATION_REPORT.md` records the full
Go/Python suites, compiled-binary corpus coverage, receipt anchors, exact
commands and preserved development failures. All 135 frozen identities were
prepared, mock-evaluated and replayed, with two additional E3-order examples.
Those existing mocked assessments have no claims; nonempty claim rules,
thresholds, role overrides and malformed responses are exercised separately
by unit fixtures. This is interface evidence, not model or hypothesis evidence.

Shared cARL memory/trust-boundary documents and their embedded mirrors remain
unchanged to preserve Path A's bundled defaults. This document, the active
contract, architecture, CLI guide and roadmap carry Path B-specific governance.
