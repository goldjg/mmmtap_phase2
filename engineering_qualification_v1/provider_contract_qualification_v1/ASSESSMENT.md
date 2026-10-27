# Q1 real-provider contract assessment v1

**Q1 REAL-PROVIDER CONTRACT ASSESSMENT COMPLETE — LIVE PROBES AWAIT HUMAN APPROVAL**

Assessment date: 2026-10-27. Upstream `goldjg/mmmtap_phase2/main` was fetched
and resolved to the supplied baseline, `5cdf8cc0978650a72215fc90ac0da13208b0fe27`.
This assessment used an isolated checkout at that commit because the shared
custody checkout has an older HEAD and unrelated modifications. No provider,
Copilot/Codex inference, JEV evaluation, cARL command, Q1, installation, login,
credential inspection or configuration change occurred. Public documentation
retrieval and GitHub fetch/push are distinct from provider execution.

**Decision: none of the five paths is currently qualified for live Q1.**
Assessment completion is not launch readiness. Technical prerequisites and
provider cooperation remain necessary in addition to human permission.
The machine-readable [matrix](compatibility_matrix.json) assesses all 13
requirements separately for each path; the [probe proposal](proposed_probes.json)
is deliberately non-executable and authorizes zero calls.

## Intended paths and actual local evidence

| Path | Exact requested provider/model | Existing invocation | Candidate decision |
|---|---|---|---|
| Gemini generator | `github_copilot_cli` / `gemini-3.8-flash` | Copilot `--model gemini-3.8-flash … -p PROMPT` | **UNDECIDED**; direct Google `generateContent` is technically preferable if separately authorized |
| Haiku generator | `github_copilot_cli` / `claude-haiku-5.5` | Copilot `--model claude-haiku-5.5 … -p PROMPT` | **UNDECIDED**; direct Anthropic Messages is technically preferable if authorized; its documented ID is `claude-haiku-5-5`, requiring explicit mapping approval |
| Sol generator | `codex_cli` / `gpt-6.1-sol` | Codex `exec --model gpt-6.1-sol --json … -` | **UNDECIDED**; direct OpenAI Responses is technically preferable if separately authorized |
| Native specialist | `systemone_https` / `jev-latest` | Python `urllib` POST to `https://api.typesafe.ai/v1/systemone`, bearer from `JEVKEY` | Conditional candidate: direct SystemOne HTTPS owned by broker, after custody/contract repair |
| cARL specialist | Historical `carl_jev_cli` / `jev-latest`; proposed `carl_assessment_challenge_v1` / `jev-latest` | Historical `carl-jev review …`; newer V5 `prepare`, `evaluate-live`, `replay` | Conditional candidate: existing V5 preparation/policy with broker-owned SystemOne exchange; Git-review CLI is incompatible with frozen primary text |

Exact flags, endpoints and invocation gates are in
[historical config](../../phase2/config.v1.json),
[legacy adapters](../../phase2/adapters.py),
[proposed argv and blocked generator adapter](../../phase2/adapters_v2.py),
[V5 integration config](../../forensic_remediation_v1/v5/instruments/config.v4.json)
and the frozen [cARL command implementation](../../forensic_remediation_v1/v5/instruments/software_source/cARL-semantic-eval/internal/assessment/command.go).
The generator argv includes tool/instruction/update suppression; the proposed
Codex route explicitly uses `https://chatgpt.com/backend-api/codex`, zero request
and stream retries, ephemeral execution and low reasoning effort. These are
source-level intentions, not current runtime guarantees.

The historical pilot/readiness/configuration artifacts are not a current Q1
live manifest. Q1 retains the three original generator slots and two specialist
presentations in its [153-position proposal](../q1_executor/FULL_MATRIX.md).
Its [broker destination](../q1_executor/broker_v1/__init__.py) is exclusively
`local-stdio-mock-v1`; its model/version/judge identities are synthetic.
**Native and cARL use the same underlying SystemOne judge**, with different
presentation/policy paths. Neither constitutes independent judge replication.

[Local inventory](evidence/local_inventory.json) contains executable paths,
full SHA-256 hashes, package versions and scoped absence checks:

| Local artifact | Offline observation | Relationship to historical record |
|---|---|---|
| Copilot | Embedded wrapper build literal `1.0.103`; SHA `1253bb0c…19abb35` | Historical `1.0.95` / `6403d0ba…`; effective selected cached runtime **unknown** |
| Codex | Package metadata `0.164.0`, arm64 musl; SHA `8813c8d8…1e9a8d39` | Pinned historical `0.162.1` executable is absent |
| `~/bin/carl-jev` | SHA `b34696d5…d0868428`; Go metadata entry point `cmd/carl` | Same bytes as historical Git-review investigation; historical CLI version `dev`, not rerun |
| V5 assessment binary | SHA `b51cb4c8…d7a275d`; Go `1.26.5`, static, `cmd/carl-assessment-challenge` | Matches V5 build receipt; V4 also present with distinct hash |
| Gemini/Claude CLIs | Not found on inspected PATH | Neither is the configured transport |
| Provider SDKs | Python `openai`, `anthropic`, `google-genai`, `google-generativeai`, `typesafe-sdk`, `httpx` absent; requests `2.28.1`, urllib3 `1.26.12` present | Scoped to inspected interpreter/package roots, not every environment or embedded CLI dependency |

No provider executable was launched even for help/version. Copilot's embedded
launcher includes package selection/extraction behavior, so we did not assume
its startup flags were side-effect free. Versions above are package/build
metadata, not observed CLI version output. Only Go's local metadata reader was
executed, with `GOTOOLCHAIN=local`; [exact outputs](evidence/go_binary_metadata.json)
are retained. Four relevant sibling cARL source files match the frozen V5
copies byte for byte ([source hashes](evidence/source_index.json)). The build
receipt supports local source correspondence, not independent release attestation.
No user auth/configuration files or private histories were inspected.

## Compatibility matrix

`V` = VERIFIED_OFFLINE at the narrow local-source scope described below;
`D` = DOCUMENTED_NOT_VERIFIED; `P` = REQUIRES_BOUNDED_LIVE_PROBE;
`I` = INCOMPATIBLE as presently implemented; `U` = UNKNOWN.
An `I` is an actionable integration gap, not a claim that a provider can never
support the property. No `V` certifies remote behavior.

| Requirement | Gemini CLI | Haiku CLI | Sol CLI | Native HTTPS | cARL V5 |
|---|---|---|---|---|---|
| Sealed reservation → request | I | I | I | I | I |
| Automatic retry prevention | U | U | D | U | V* |
| Fallback/substitution prevention | U | U | U | U | U |
| Fresh independent context | P | P | P | U | U |
| Raw errors/partial/complete bytes | I | I | I | I | I |
| Requested/observed identity | P | P | P | P | P |
| Deterministic packet delivery | U | U | U | I | I |
| No implicit tools/repo authority | U | U | I | V* | V* |
| Approved-provider egress | I | I | I | I | I |
| Timeout/cancellation/completion | U | U | U | I | V* |
| Request IDs/correlation/metadata | U | U | U | I | P |
| Usage/billing | P | P | P | P | P |
| Current broker/receipt compatibility | I | I | I | I | I |

*V5 source disables redirects, proxies, HTTP/2, connection reuse and automatic
decompression, clears `GetBody`, and issues one `Do` under a whole-call context
deadline. The [local Go transport source](evidence/source_index.json) confirms
the fresh HTTP/1 connection/replay reasoning. This establishes inspectable
client replay prevention only. Native and V5 direct call source contains no
agent/tool runner. Remote retries, hidden routing, cancellations and isolation
are unverified. See [V5 transport](../../forensic_remediation_v1/v5/instruments/software_source/cARL-semantic-eval/internal/assessment/live.go).

The concrete blockers are:

1. **Specialist wire/meaning mismatch.** Frozen
   [v2 judgment validation](../../phase2_v2/instrument.py) requires each claim's
   three dimensions, each with label, finite-or-null support score, rationale
   and source quotes. SystemOne's documented typed answers and the existing
   [V5 catalog](../../forensic_remediation_v1/v5/instruments/software_source/cARL-semantic-eval/internal/assessment/request.go)
   (`claim_*_supported`, `uncertainty_adequate`, `authority_promoted` Nouls)
   do not implement that schema. cARL deterministic policy results do not fill
   the gap. There is no demonstrated semantics-preserving bridge. Do not invent
   rationales, convert probabilities into new support scores, or weaken frozen
   validators. This needs a human instrument decision and offline proposal
   before Q1, not an inference experiment.
2. **CLI dispatch is opaque.** Historical
   [loopback controls](../../integration_readiness_v1/isolation_controls_final/summary.json)
   show watchdog-based Copilot failure detection and ten exposed internal Codex
   routes despite disable flags. They do not qualify the changed local binaries.
   Copilot retry prevention remains unknown; Codex's documented zero-retry
   settings do not bound agent turns or provider-internal execution. Killing a
   CLI after a retry/tool event cannot undo a request. CLI JSON is not raw HTTP.
3. **Response custody gaps.** Native urllib drops headers and may lose a partial
   body when `read()` raises; timeout is not a total exchange deadline. V5 labels
   exact/error/partial/truncated/withheld bodies, but writes them after the call
   returns: a crash can lose received prefixes. Encoded or credential-bearing
   bodies are withheld. Neither can replace broker incremental custody as-is.
4. **Identity is weaker than required.** An event, request parameter or
   nonempty returned `model` is not independent attestation. V5 explicitly marks
   its receipt `provider_authenticated=false`; TLS identifies the service,
   not model weights. `jev-latest` can move. Neither adapter enforces a human
   approved requested-to-resolved revision mapping.
5. **Real broker binding is absent.**
   [Authorization](../q1_executor/broker_v1/broker.py) and
   [receipt validation](../q1_executor/broker_v1/contract.py) bind a mock
   destination, mock stages/MAC frames, synthetic identities, two-second provider
   deadline and byte ceilings. Real output cannot be relabeled as mock evidence.

## Realistic transport choices and documentation limits

Copilot is the existing usable integration surface for Gemini/Haiku; standalone
Gemini/Claude CLIs and provider SDKs were not found. A Copilot SDK would inherit
the opaque service path and is not an evidenced one-shot remedy. Direct APIs
offer explicit request bodies and transport metadata with less agent machinery,
but need separate accounts, keys, billing authority and new offline bindings.
Copilot/ChatGPT subscriptions or cached login state must not be repurposed as
direct API credentials. No adapter or architecture is selected here.

[GitHub's reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
lists both intended Copilot IDs and explicit model/tool controls; it does not
establish a provider-side one-shot guarantee. Google documents the exact
[Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) and
[generateContent metadata](https://ai.google.dev/api/generate-content), including
model version, response ID and usage. Anthropic's
[model catalog](https://platform.claude.com/docs/en/models/overview) and
[Messages API](https://platform.claude.com/docs/en/api/messages/create) establish
the differently spelled direct API ID; its
[SDK retry option](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
must be disabled if that uninstalled SDK is later selected.

OpenAI documents [gpt-6.1-sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Codex retry controls](https://learn.chatgpt.com/docs/config-file/config-reference)
and [explicit conversation state](https://developers.openai.com/api/docs/guides/conversation-state).
Direct Responses would avoid Codex's local agent tool surface, but is not
authorized by the historical ChatGPT route. Account access, fixed revision
evidence and provider execution counts remain unverified.

TypeSafe's [SystemOne contract](https://docs.typesafe.ai/api/system-one) matches
the native typed request family, not frozen v2 judgments. Its
[model page](https://docs.typesafe.ai/models) currently maps `jev-latest` to
`jev-1.14.0`; the API example itself returns an alias. That is vendor
documentation, not account availability or a live resolution observation.
The [SDK](https://docs.typesafe.ai/sdk/python/api/retries) has a documented
zero-retry setting but is not installed. Existing V5 direct transport offers
stronger inspectable controls without adding that dependency. The historical
Git-review cARL CLI instead requires Git state, fixed review questions and a
different wire schema; it is not a substitute for the assessment interface.

All retrieved authoritative links and claim scopes are in the small
[documentation register](evidence/documentation.json). No model-list API or
authentication check was called. Prices, entitlements and token ceilings are
not inferred from model names or subscription presence.

## Containment and integration prerequisites

Keep the qualified worker's mount namespace, syscall allowlist, five-value
environment and supervised preopened stdio unchanged. Provider CLI/Go runtimes
cannot run inside that profile: sockets, exec and thread/process creation are
denied. The [broker design](../q1_executor/broker_v1/README.md) permits a trusted
transport outside the worker, but its real deployment is unqualified.

Offline implementation scope, requiring a separate bounded task:

- Version the broker transport/destination and receipt metadata; retain the
  same reservation authority, exact grant/request checks and pre-dispatch
  durable intent. Preserve original receipt bytes and verifiers. Record both
  sealed logical request and exact provider wire body/translation digest.
- Give only the trusted network transport the required credential through a
  narrow broker-owned secret boundary. No worker credential, inherited user
  home, login cache, argv secret, auth header log or general environment dump.
  Audit the runtime image; the existing exposed `/usr` has no confidentiality
  qualification. CLI processes outside the worker need their own preventive
  permissions and restricted mounts; spawning one from a trusted broker is
  not sufficient containment.
- Enforce default-deny egress outside the worker: exact approved HTTPS
  host/port/path, TLS validation, controlled DNS/CONNECT routing, no redirects,
  environment proxies, telemetry, update, discovery or auth-refresh escape
  routes. Candidate API hosts are in the matrix; they are **not** enabled.
  CLI multi-host/auth needs remain unresolved. Host allowlisting alone does
  not prevent requests to unrelated paths on that host.
- Test actual pinned client retry/replay/error paths offline; deny SDK defaults,
  automatic continuations, sessions and fallback. Freeze complete explicit
  context and policy per request. Do not send an idempotency header merely
  because a correlation token exists: library replay behavior and provider
  semantics must be audited separately.
- Append raw entity-byte prefixes before forwarding/parsing; preserve errors,
  status, safe headers, requested/observed identity, usage, remote IDs and TLS
  evidence separately. Define restricted quarantine for credential echoes
  without publishing secrets or treating redacted bytes as originals. Bind
  any unavailable raw surface explicitly; it cannot pass exact custody.
- Keep reserved/intended/accepted/partial/complete/interrupted states distinct.
  Do not call socket write, process start or HTTP acceptance proof of model
  execution. After crash/deadline, keep prefixes and uncertainty, consume the
  attempt and never retransmit or promote an orphan response to success.

Remote single-execution/no-substitution guarantees, independent revision
evidence, universal context isolation, cancellation finality and billing
reconciliation require provider cooperation. Offline injection tests and a
small success probe cannot prove those properties.

## Minimal separately authorizable probes and decisions

The [manifest](proposed_probes.json) specifies synthetic content, observations,
evidence, ceilings, timeout/cancel rules and pass/fail/inconclusive criteria.
No deliberate live 429, timeout, cancellation, token-count or model-list calls
are proposed; client error/custody behavior belongs in offline tests.

| Proposal | Maximum broker dispatches / client POSTs, conditional | Purpose |
|---|---|---|
| `J-shared` | 2, separately stageable as 1 + 1 | Native tiny synthetic typed request, then cARL prepared request; share SystemOne schema/metadata/usage checks and independent state-delivery checks; cARL policy replay needs zero further calls |
| `G-gemini` | 2 | Synthetic marker then fresh request without marker; combine output, metadata, identity and context checks |
| `G-haiku` | 2 | Same design under an explicitly approved API-ID mapping |
| `G-sol` | 2 | Same design, with no imported Responses conversation/previous-response ID |

These are transport qualification proposals, not Q1 or proof of scientific
compatibility. Exact prepared packets, selected transport hashes and budgets
must be completed offline before approval. The second request is withheld if
the first fails or is inconclusive. Absence of marker leakage is only a bounded
observation, not proof of universal remote isolation. The fixed SystemOne/cARL
numeric catalog cannot meaningfully test prior-conversation recall; provider
isolation assurance is required, and that property remains UNKNOWN.

**Enforceable minimum total provider-execution count: unknown.** Eight is only
conditional success-path client-POST arithmetic. Each request needs an
independently supported provider execution bound; otherwise strict one-shot
qualification is blocked. A token/cost cap cannot fix hidden attempts.
Proposed generator output settings of 128 tokens need model-specific validation;
total-token bounds and costs are explicitly unknown. SystemOne has no established
per-request token ceiling for these payloads. Unknown budget fields are approval
blockers, not unlimited authorization.

Human decisions needed: resolve the specialist v2 wire/meaning mismatch without
altering frozen contracts; choose whether direct generator API authority and
billing may be obtained; approve exact model IDs/revisions and the Haiku mapping;
require provider evidence for strict attempts, identity and isolation; select
account-specific bounds and the separately versioned transport implementation
scope. Later, separately approve a sealed probe manifest and narrow live egress.
No new credentials or external networking were wired here.

**Most important next action:** resolve the specialist wire-to-frozen-v2
contract offline. After the transport/custody prerequisites and provider attempt
bound are satisfied, the first bounded live qualification step should be only
the **first native SystemOne request**, maximum one broker dispatch/client POST,
with separate approval. If the provider cannot bound internal attempts, keep
strict qualification blocked. Any ambiguous result stays inconclusive and
consumes its reservation; it is never permission to retry.

## Preservation and checks

The original local [custody verifier](evidence/original_custody.stdout) passed:
40,538 original entries, 1,165 operator-sealed files, 4,699 V5 files and 36 command
records; zero changed/missing originals. Checks are recorded in
[validation evidence](evidence/validation.json). Existing broker acceptance,
first attempts, RD05, frozen v1/v2 instruments and the 153-position proposal
were read/verified, not regenerated. No simulation, adjudication, live transport
implementation or scientific-contract edit is included in this increment.
