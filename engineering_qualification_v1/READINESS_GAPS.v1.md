# Engineering readiness gaps v1

Inspected executable baseline: **`b06371e48af5919af6fffd563fb1226d8be0dae4`**.
[bindings.v1.json](bindings.v1.json) binds 96 exact source/configuration,
decision, RD05 and comparison files. This report distinguishes inspected
code from proposed behavior. The proposal remains **153 positions: 99
generator + 54 specialist, nine matched units, R=1**; no runnable Q1 manifest
has been substituted for it. The old 153-position v1 pilot is a different
instrument and is not reusable Q1 authorization.

Priority 1 prevents a reviewable qualification implementation; priority 2
prevents launch after implementation. Both currently block live work.

| Priority / check | Existing implementation and evidence | Missing implementation / impact |
|---|---|---|
| 1 — frozen source and policies | `instrument.py:render_assessment_prompt` checks source hash; `build_judge_request` binds source, assessment and provenance. RD05 `tool.py` binds fictional governing policy. | No approved Q1 source/reference packets, governing policy/approval receipt, challenge policy or executable campaign manifest. Cannot bind a scientifically interpretable comparison. D03/D10 and policy authority decisions precede integration. |
| 1 — identical policy delivery | V2 renderer carries source, prior assessment and challenge; controls reject challenges. | No governing-policy field, packet delivery or equality check across arms/contexts. Requires an approved delivery/prompt contract; adding it now would change the frozen instrument by assumption. |
| 1 — arm/context isolation | V1 `core.py` builds branch dependencies; `engine.py:histories` follows branch ancestry. `isolation.py` offers fresh staging and sandbox primitives. | No v2 executor enforces matched sealed B0, arm/context separation or blinded reference boundaries. Fresh processes alone do not establish isolation. Old `isolation_controls.py:validate_controls` and `adapters_v2.py:GeneratorAdapter` explicitly retain three blocked generators. |
| 1 — first attempts, reservations, resume | V1 `runtime.py:execute/_existing` locks, reserves before preparation/calls, preserves incomplete attempts, checks scope/parent hashes and has no harness retry. V2 `continuation.py` is a read-only planner/auditor. | No durable Q1 campaign-wide registry, manifest publication, crash-safe receipt integration or resumption path. Planner output does not reserve a provider attempt. Reusing v1 live execution would bypass the new instrument; duplicate prevention cannot be claimed for Q1. |
| 1 — dependencies and blocked children | V2 `plan_continuation` requires verified outcomes, topological parents and consistent blocking, stopping on unknown/credential/identity states. `audit_completed_stage` checks ledger/hash/parent/budget reconciliation. | No Q1 executor produces every scheduled position's outcome, including censored descendants. D07 must determine admissibility/analysis; blocked and unavailable cannot become unchanged or successful. |
| 1 — claim lifecycle | Unchanged `core.py:assessment` enforces full retained-object equality, union-of-ID accounting, added/revised/withdrawn rules and empty B0 changes. V2 `inspect_assessment` preserves raw syntax/shape/lifecycle failures; quotes are separately audited. | Deterministic mechanics exist and passed tests; clarified prompts remain unapproved for research use (D01). Do not relax validation or repair invalid outputs. No new lifecycle semantics needed for this offline increment. |
| 1 — separated records | V2 has `AssessmentDiagnostic`, `JudgeRecord`, per-dimension judgments and separate fixture challenge decisions. V1 stores raw/payload/result, requested/observed identity, parent hashes and timestamps. | V2 records are in memory; no durable Q1 generator/specialist/operational recommendation store or approved operational sidecar contract. Governing policy must never be inferred from a challenge disposition. |
| 1 — intermediate/final movement | RD05 `tool.py` preserves synthetic endpoint and adjacent/final pairs. RD02 requires exact B0/intermediate/final pairs independently of findings. | No wired natural-output movement store. Preserve a return to baseline as final no-movement plus intermediate movement. Materiality, action/conditions mapping and RD03 warrant remain undecided; generator `revised` is not adjudicated material movement. |
| 1 — provenance and custody | V1 `Ledger`, `runtime.py` and `checks.py` preserve timestamps, hash chains, raw receipt hashes and original custody. V2 request/raw/policy digests are explicit. | No Q1 seal, durable timestamps/receipts, independent reference preparation/export or evidence chain. Content hashes do not establish source authenticity or reviewer independence. Original custody passes separately; it cannot certify future Q1 evidence. |
| 2 — provider/model/judge identity | `config.v1.json` names haiku (`claude-haiku-5.5`), gemini (`gemini-3.8-flash`), sol (`gpt-6.1-sol`), native/cARL `jev-latest`. V1 `_identity` records requested/observed/confirmed identity and binary/config/CLI information. | No approved v2 transport/per-request version contract, immutable served SystemOne identity or current availability evidence. Native/cARL share SystemOne. Historical names and dated observations cannot verify present service identity offline. |
| 2 — calls, prices, budget | V1 `planning.py:estimate` supports explicit rates; runtime persists adapter-attempt ceilings. V2 plan specifies a tariff/token/wrapper method with unknown rates retained. | No approved tariffs/entitlements, rendered Q1 policy overhead/token bounds, cost range or persisted Q1 cap. 153 scheduled positions is neither an HTTP/billing cap nor 153 guaranteed calls. Internal CLI retries remain a strict-isolation blocker; a watchdog races execution. |
| 2 — invalid/unavailable observations | V2 keeps invalid raw outputs, `parsed=None`, dimension-specific null scores and `score_unavailable`; continuation rejects invalid parents. | Q1 durable denominator/availability accounting and D07 censoring/admissibility policy remain absent. Invalid is not no-change; null is not zero; dependency censoring is not an observed response. |
| 2 — release and launch boundary | V2 has no provider/execution entry point. New preflight imports only standard library, reads local files and emits JSON. RD04 defines evaluated recommendations; no release actuator is wired. | Future live containment must exclude release credentials/tools and any recommendation-to-release integration. This command has no launch/release path; zero real-release possibility in an unbuilt future executor cannot be certified offline. No automatic qualification progression is permitted. |

Implemented here: a separately versioned, read-only preflight with exact byte
bindings, explicit missing/unknown/failure reporting, original-custody checks,
unsafe-path/symlink/duplicate rejection and negative tests. Original v1/v2
code, prompts, schemas, seals, policy semantics, reviewer reports and matrix
are unchanged. This is bounded engineering verification, not a Q1 executor.

Minimum next implementation, **after the relevant decisions**, is a separate
v2 manifest/executor path wiring the existing strict lifecycle and dependency
mechanics to approved packet delivery, isolated one-shot adapters, persistent
reservations/receipts and independent movement sidecars. Preserve all
scheduled outcomes. Then qualify containment and identity independently;
cost the actual rendered requests before requesting launch approval.
No need to add an arm, retry a failed assessment or resolve RD05 prose to do
that work. Building those integrations now would assume unresolved contracts.

Remaining human decisions, using the existing D01–D11 register:

1. Approve bounded Q1 scope/R=1, exact source/reference packets, clarified
   instrument and policy delivery; retain the existing 153-position proposal.
2. Supply/approve governing policy obligations, evidence adequacy, precedence,
   warnings/remediation and authority; separately approve research challenge
   thresholds/actions, applicability, null-score handling and transport.
3. Decide RD03/material finding and operational warrant rules, reviewer
   independence/disclosure/ambiguity handling, invalid-output admissibility,
   dependency censoring and qualification acceptance criteria. Preserve the
   RD05 disagreements; no consensus or scientific reliability is assumed.
4. Approve actual provider/model/judge identity contracts and shared-judge
   interpretation; supply tariff/entitlement and usage assumptions and a
   bounded attempt/cost authorization after isolation evidence is available.
5. Review the implemented, tested executor and containment evidence, then
   give separate explicit qualification launch approval. A primary study
   requires its own statistical design and authorization.

Current environment/provider properties remain unverified offline. No
provider, JEV or external evaluator call, Q1 launch, policy enforcement or
automatic advancement occurs in this increment.
