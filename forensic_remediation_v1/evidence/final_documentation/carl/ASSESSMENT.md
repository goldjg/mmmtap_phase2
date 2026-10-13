# Assessment challenge: canonical evidence and source-bound integration

`cmd/carl-assessment-challenge` is a separately versioned sibling executable.
It does not register a new command in `cmd/carl`, replace `~/bin/carl-jev`,
or change `internal/review`, `internal/semantic`, pack/profile semantics or
Path A's Git-evidence contract.

The v1 preparation, mock/import and offline-replay command signatures are unchanged.
The separate v2 transport adds an explicitly authorized `evaluate-live`
command and environment-only credential lookup. Its implementation has been
tested **offline with localhost HTTP fixtures only**; no provider/model calls
are authorized by the implementation contract. It is not a qualified live
integration, experimental-policy approval or permission to release source data.

## Build and commands

For the MMMTAP v5 plan (source-bound format v4), build through the helper from the Phase 2 workspace,
to a new operator-selected path, never over a historical or installed binary:

```sh
cd ../mmmtap_phase2
PYTHONDONTWRITEBYTECODE=1 python -c \
  'from pathlib import Path; from phase2.software import build_path_b; build_path_b(Path("NEW_BUILD_DIR/carl-assessment-challenge-v5"))'
```

The helper records local Go/embedded source, compiler input and toolchain hashes,
the actual build command, and the resulting binary hash in an exclusive adjacent
`.build.json` receipt. Frozen instruments reject an unbound historical executable
claimed against current source. This remains local build provenance, not signed
attestation; an independent rebuild can check the pinned bytes. The validation
runner separately prevents external networking.

```text
carl-assessment-challenge prepare --request FILE --policy-root DIR --out NEW_DIR
carl-assessment-challenge evaluate-offline --prepared FILE --prepared-sha256 HASH --response FILE --mode mock|imported_unverified --out NEW_DIR
carl-assessment-challenge evaluate-live --prepared FILE --prepared-sha256 HASH --authorize-live --timeout-seconds N --out NEW_DIR
carl-assessment-challenge replay --receipt FILE --receipt-sha256 HASH
```

The live command signature documents capability, not authorization to invoke
it. It requires separate operator approval plus `--authorize-live` and a
whole-call timeout of 1–600 seconds. It sends exactly the frozen native request
bytes to `https://api.typesafe.ai/v1/systemone`, using `Bearer` authentication
from `JEVKEY`. Missing/blank or malformed bearer credentials fail before a
transport attempt; values are never printed or stored. Known credential
material in the supplied preparation is rejected before copying or sending it,
not redacted into a different native request.

The HTTP client has no proxies, redirects, automatic retries, connection
reuse, fallback model or automatic decompression. It requests identity content
encoding. Redirect bodies and non-200 failures are captured without following
`Location` or `Retry-After`. Malformed answers, timeouts, disconnected bodies,
and oversized responses remain explicit failures, never policy success.

`NEW_DIR` must not exist. Each operation reserves an independent attempt,
persists intent and inputs with exclusive writes, and writes a preparation or
receipt plus its SHA-256. Invalid responses produce a failed receipt and
nonzero exit, never `no_challenge`. Invalid preparation produces an explicit
failure record. Serialization/capacity and later write errors also attempt to
persist a failure record; persistence failures are reported explicitly.
Repeating an output path fails; it does not resume, overwrite
or retry. An intentionally new attempt requires a new request attempt ID and
output directory; operators must keep the original attempt.
The Go CLI alone does not globally deduplicate user-supplied attempt IDs.
The current MMMTAP qualification entry point reserves identities across output
directories in its fixed workspace registry. Distributed exactly-once execution
or provider billing cannot be guaranteed by either mechanism.

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

`provider.go` interprets the shared `mmmtap-systemone-typed-response-v2` schema
before policy is applied. It matches the native Python parser: exact
case-sensitive `model`/`answers`/optional `usage`, exact answer IDs and typed
fields, duplicate/alias/unknown-field rejection, finite probabilities, and
valid Unicode. Legitimate optional answer `type` must exactly match the question;
optional choice `confidence` is retained as a finite [0,1] number. Missing
redundant metadata is not invented, and wrong types/nulls/aliases still fail.
Optional usage counters are nonnegative int64 values; absent
usage stays absent/null rather than becoming zero. Shared noul and choice
fixtures live in `internal/assessment/testdata/systemone_responses.json`;
`systemone_historical.json` is an exact labelled historical response import,
not a new provider call.
Supporting choice parsing does not expand Path B's frozen noul request catalog.

Limits: 8 MiB JSON/file/artifact, 64 JSON nesting levels, 1 MiB source,
128 claims, 2 MiB total policy definitions, 256 policy files/rules. Oversized,
malformed, duplicate-key, unknown request fields, missing provenance,
unmatched questions and incomplete/non-numeric/out-of-range answers fail.
These are offline interface limits, not provider capacity qualification.

## Receipts and epistemic boundary

Preparation embeds exact request and policy bytes, complete cARL trace,
compiled rules, binary digest and hashes for source, assessment, parent,
manifest, native request, policy snapshot and compiled policy.

Offline receipt schema `carl-assessment-challenge-v1-receipt` embeds the preparation,
raw response, their hashes, deterministic result, parser failure when present,
execution binary hash and mode. Base64 byte fields preserve original JSON
formatting independently of canonical derived objects. Return statuses are
`mock_ok`, `imported_unverified`, or `failed`; its `live_calls` is always zero.
Returned model text is labelled unverified even when it resembles a real model.
Raw usage metadata remains in the response artifact. The Python Path B wrapper
also extracts validated available counters from the verified raw response and
records their provenance; unavailable usage/cost is never invented.

Live receipt schema `carl-assessment-challenge-v2-live-receipt`, transport
`carl-assessment-challenge-live-transport-v2`, additionally binds exact native
request bytes, endpoint, request-written evidence, attempt count, HTTP status,
sanitized headers, TLS metadata, timestamps/latency/timeout, response capture
state and execution-binary digest. `status` is `ok` or `failed`. The earlier
unqualified v1 **live draft** schema is intentionally not accepted as v2;
well-formed canonical v1 offline receipts still replay. Previously accepted
ambiguous provider fields or omitted/null/default receipt-field encodings are
now rejected. Historical receipt bytes and historical binaries are not rewritten.

`response_capture` distinguishes:

- `complete`: `raw_response` is the exact HTTP entity body (after HTTP framing,
  with no content decoding or text rewriting).
- `partial`: exact bytes read before a body read error/timeout.
- `truncated`: an exact 4 MiB prefix; a one-byte overflow sentinel establishes
  the size failure.
- `withheld_credential`: literal or JSON-escaped known credential material was
  detected; the body is **not persisted**, no policy result is produced, and
  failure class is `credential_echo`.
- `withheld_encoding`: an unsolicited non-identity encoding is not decoded or
  persisted; the operation fails.
- `not_received`: no HTTP response body was received.

`response_sha256` always hashes the **stored** `raw_response`/`response.bin`,
including the empty byte string when withheld. `response_bytes_observed` and
`response_observed_sha256` describe bytes actually read in memory, including
the overflow sentinel when present; they are not a hash/count of an unread
full response. Withheld bodies and an unread suffix cannot be reconstructed
or independently policy-replayed. Replay checks their failure metadata and
the trusted receipt digest only. It never treats sanitized bytes as originals.
Header values containing the known key are masked, secret-bearing header names
and `Set-Cookie` are omitted; headers are explicitly sanitized, not raw wire
evidence. This is not general-purpose discovery of arbitrary or encoded secrets.

`attempts` counts HTTP transport invocations (0 for local credential failures,
otherwise 1). `live_calls` reflects locally recorded fully written requests,
not independently verified model invocations. A failed/partial write or lost
response cannot establish whether a provider executed or billed a request.
Do not retry on the assumption that `request_written: false` proves nonexecution.

`intent.json` and the preparation precede the call; `live_call.json` precedes
the body and final receipt writes. If the aggregate receipt exceeds 8 MiB,
the call summary and bounded body remain with `failure.json`, but no replayable
aggregate receipt is claimed. Disk failure or process termination can still
prevent final evidence persistence; errors are explicit and never trigger retry.
Ordinary successful and failed receipts enforce required fields, hashes, timing,
count/status/capture consistency, provenance labels and deterministic policy
replay. TLS server name must agree with the recorded endpoint (empty SNI for an
IP literal), and Content-Length must agree with the applicable body-capture
state. These are internal consistency checks, not provider authentication.
Replay never reads credentials or calls the network.

The MMMTAP wrapper also cross-checks the independently retained CLI checksum
line/file, exact prepared bytes, response file, complete partial-call record,
binary hash and replay. Failure evidence is captured on preparation/staging,
process, malformed/missing-file and cleanup paths. Known credential echoes
in raw process streams and nested JSON/base64 artifacts are withheld with
explicit capture metadata, not silently rewritten into apparently original
receipts. Owner-only raw artifacts still require an independent disclosure
review for unknown secrets and sensitive source data.

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
experimental mechanism/plan. The single-attempt transport and request-bound
receipt capture are implemented and locally tested, not live-qualified. Keep
the same underlying SystemOne model policy as native JEV. Validate actual served identity,
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
The transport-specific implementation/validation distinction is recorded only
here and in the active contract. Current Go logs, protected-file hashes,
build metadata and the machine-readable report are under
`../mmmtap_phase2/integration_readiness_v1/go_validation/`.
