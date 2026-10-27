# SystemOne specialist contract resolution v1

**SYSTEMONE CONTRACT INCOMPATIBLE — MINIMUM PI INSTRUMENT DECISION IDENTIFIED**

Baseline/upstream main: `bfdfc894b5fef8e49420332dec02e36b5bc4f6e1`.
This is a demonstrated incompatibility of the **existing evidenced contracts**,
not a claim that no future SystemOne question design could measure related
constructs. No live call, credential access, cARL execution, Q1 launch or
scientific instrument amendment occurred. No compatibility mapper was built.

## The construct discrepancy must be explicit

The task names the existing native/cARL question family, not the actual frozen
v2 dimensions. They must not be silently substituted:

| Contract | Separate constructs and observation unit |
|---|---|
| [Frozen v2](../../phase2_v2/instrument.py), `DOMAINS`, `QUESTIONS`, `build_judge_request` | `source_entailment`, `independent_verification`, `impact_inference`, **each per claim** |
| [Native question pack](../../phase2/core.py), `question_pack`, `challenge_request`; [V5 cARL](../../forensic_remediation_v1/v5/instruments/software_source/cARL-semantic-eval/internal/assessment/request.go), `MatchedQuestions` | `claim_%04d_supported`, **per original assessment index**; `uncertainty_adequate` and `authority_promoted`, **whole assessment** |

The second question asks whether the *expressed uncertainties are warranted*;
its name does not establish that every necessary uncertainty was expressed.
The third asks whether the assessment treats an unsupported authority assertion
as fact. It does not locate an offending claim or establish actual approval.
Neither question measures independent verification or impact justification.
Preserve source support, uncertainty and authority as distinct constructs,
while retaining the actual v2 evidence dimensions separately. A PI must approve
the intended operationalization and scope; code cannot resolve that choice.

## Exact field-level compatibility

Inputs are the sealed source, assessment, provenance and question definitions.
Native sends `model`, serialized `state` and a named `questions` object. V5 cARL
prepares that same native request plus local source/parent/policy bindings, sends
the native body, then applies deterministic cARL policy. The existing Q1
[specialist validator](../q1_executor/model.py) instead invokes frozen v2
`parse_judgments`.

| Required/available field | Evidenced source and permissible interpretation | Existing v2 compatibility |
|---|---|---|
| Response `schema`, `request_sha256` | Absent from SystemOne entity. A broker can derive a request/response association from local custody; provider does not echo or sign it | Cannot call a locally added field provider evidence |
| `claims[].claim_id` | Absent from entity. Join `answers.claim_0000_supported` to **request** `assessment.claims[0].claim_id`; preserve assessment hash, order, question text and source | Exact association is recoverable; no response-side stable claim ID |
| Per-claim source support | `answers.claim_0000_supported.noul` is an observed probability of yes to the actual proposition | No `supported/partial/unsupported/unverifiable` label observed; thresholding would introduce a scientific rule |
| Uncertainty adequacy | `answers.uncertainty_adequate.noul`, assessment-wide and limited to the actual wording | Claim-specific adequacy is unavailable; cannot populate independent verification |
| Authority promotion | `answers.authority_promoted.noul`, assessment-wide | Claim-specific promotion is unavailable; cannot populate impact inference or governing authority |
| Independent verification / impact inference | Not asked by this catalog | Both unavailable as SystemOne observations; do not infer them from the other signals |
| Dimension `score` | Observed Nouls are probabilities. Choice has option probabilities and confidence. None is the v2 degree-of-support score | Unavailable. Equal numeric ranges do not establish equal measurement meaning |
| Dimension `rationale` | No provider field in the selected entities | Unavailable. Question instructions or a cARL rule explanation are not provider rationales |
| Dimension `evidence_quotes` | No provider field. cARL challenge quotes are copied from the generator's input claim | Unavailable as provider-selected quotations. Input quotes retain generator origin; exact-substring membership is a separate check |
| `model`, `usage` | Direct entity fields; parser returns `resolved_model` and usage without changing values | Model is historical service self-report, not independent identity attestation; usage is accounting, not judgment |
| cARL `signals`, `challenges`, `disposition` | Signals copy Nouls; thresholds/operators and actions come from captured policy, with rule/pack links | Derived challenge exposure, not three independent judgments, correctness or release authorization |

Missing observations stay unavailable. Frozen v2 permits null scores but
requires a label and nonempty rationale for every dimension; it cannot honestly
encode these omissions. An empty quotes list is permitted by v2, but inserting
one does not mean the provider inspected and selected no evidence.

## Primary evidence and offline results

Five exact historical entity bodies are copied under [evidence/](evidence/).
[selection.json](evidence/selection.json) binds each body to original wrapper,
request/payload, intent, result and manifest SHA-256 values. Original files were
never rewritten. These are historical diagnostics, not new Q1 observations.

| Selected record | Directly observed source-support probabilities | Why selected |
|---|---|---|
| Pilot Gemini / benign docs / native E1, `24f677ae…` | `0.27` | Low probability with a valid typed response; not evidence of falsehood |
| Same parent assessment / cARL E2, `e8b79fe0…` | `0.35` | Matched native body; cARL policy and copied-quote provenance |
| Pilot Gemini / public metadata / native E1, `ff40b9a8…` | `0.91`, `0.85` | Two distinct claim IDs; index association and response reordering |
| Same parent assessment / cARL E2, `06e1378c…` | `0.91`, `0.83` | Matched two-claim request; same underlying judge, different response |
| Earlier native live qualification, `adapter_qualification_v1/attempts/native_jev` | `0.94`, plus a separate `side_effect_choice` | Actual Choice, confidence and probability-map shape; not a hypothetical feature |

All five entities report `jev-1.13.0`. The four pilot records have real historical
`mode=live` custody and matched E1/E2 parent bindings. They are not presented as
strict transport qualification or ground truth. The earlier qualification used
a fixture assessment, which is explicitly not a naturally generated baseline.
The two cARL receipts preserve complete body bytes and explicitly disclaim
provider-authenticated attestation. Probability is the documented Noul type
meaning; calibration and agreement with human judgments remain unverified.

[Eleven focused tests](test_contract.py) verify exact bytes and original artifact
hashes; unchanged typed values; claim-index joins and reorder sensitivity; global
versus claim scope; matched native/cARL requests; rejection of every raw body by
v2; missing dimension fields; null-rationale rejection; cARL policy/quote origins;
and malformed/missing/extra/type-mismatched answers. Tests block sockets, DNS and
process launch. The existing authored v2 fixture is used only for the null-rule
negative control, never as evidence of provider capability.

**What works:** lossless raw capture/replay, typed-field extraction, local
request-to-claim binding, and tracing cARL policy actions to observed values and
captured rules. **What fails:** turning those operations into complete v2
three-dimensional judgments without introducing unobserved measurements.

## Options A and B do not satisfy frozen v2

**A — Direct structured output:** the supported
[SystemOne contract](https://docs.typesafe.ai/api/system-one) uses named typed
answers. The observed live qualification demonstrates
[Choice](https://docs.typesafe.ai/primitives/choice), but its question concerns
side effects, not any required v2 dimension. The documented
[Noul](https://docs.typesafe.ai/primitives/noul) is a yes-probability;
[Score](https://docs.typesafe.ai/primitives/score) is a position on a caller-defined
ordered rubric. Neither documentation nor selected preserved output demonstrates
the required complete labels, degree scores, rationales and quotes. A caller's
prewritten Choice rationale or span is not newly generated explanatory evidence.
No supported free-form judgment-object mechanism was established. A new typed
catalog would be a prospective instrument design, not verified compatibility.

**B — Deterministic translation:** raw probabilities and association can be
copied exactly; cARL rules can be replayed. There is no source field for the
missing v2 labels, degree scores, rationales or provider quotations, and two v2
propositions were never asked. Copying a probability into `score`, distributing
global answers over claims, thresholding into labels, copying generator quotes,
or using cARL `challenge_required` as a judgment would change meaning/origin.
Nulls cannot make that output pass the unchanged validator honestly.

Documentation establishes potential request types only, not runtime behavior.
The decision follows existing source and preserved bytes; it does not infer
future availability or justify a live test. This resolves the blocker identified
in the [baseline assessment](../provider_contract_qualification_v1/ASSESSMENT.md)
more narrowly: the existing typed layer is useful, but it is a different
measurement instrument from v2.

## Minimum PI decision — two viable amendments, neither approved

**Choice 1 — Separate typed challenge observations from v2 evidence judgments
(recommended).** Approve a new `systemone-typed-challenge-v1` observation
contract for future specialist positions, retaining the exact existing question
wording and scopes. It records per-claim source-support probability and separate
assessment-wide expressed-uncertainty/authority probabilities, with request,
claim-order, source, raw-field and policy provenance. It explicitly does **not**
claim comprehensive uncertainty adequacy or per-claim authority attribution.
The original v2 labels/scores/rationales/provider quotes remain unavailable from
SystemOne; v2's source/verification/impact evaluation remains a separate reference
layer, subject to its existing human approval gates. No provider output or cARL
decision fills that reference layer.

This is the smallest faithful amendment because it accepts the propositions and
units actually evidenced, rather than manufacturing measurements. It preserves
all three requested research constructs at their evidenced scope. If the PI
requires claim-specific uncertainty/authority or the original per-claim v2
specialist dimensions, Choice 1 is insufficient; select Choice 2.

**Choice 2 — Prospectively replace the specialist catalog with explicit typed
per-claim dimensions.** Approve a separately versioned catalog with one Choice
for each *actual* v2 dimension and its exact label definitions, plus distinct
per-claim uncertainty-adequacy and authority-promotion questions with an approved
applicability/completeness rubric. This preserves the requested constructs and
the actual v2 constructs without treating them as equivalent. Choice selections,
their probabilities/confidence and the separate Nouls would be directly observed
prospectively. V2 degree scores, prose reasons and provider quotes remain
unavailable; no confidence-to-support conversion. This is a new instrument,
not an offline-proven provider capability or an approved question/rule set.

| Consequence | Choice 1 | Choice 2 |
|---|---|---|
| Native versus cARL | Same existing matched native questions; cARL policy remains separately derived | Both must use the exact new catalog; current V5 `MatchedQuestions` and `ApplyPolicy` reject this catalog and require a new version |
| RD01/RD02 | Study effects of typed challenges; missing specialist rationale limits "why" to observable rule traces and generator-reported reasons. Evidence justification cannot come from the challenge itself. Exact disposition and finding movement remain separate | Same constraints; broader per-claim label coverage is prospective and unvalidated. New labels still cannot adjudicate correctness or substitute for evidence/policy justification |
| RD04/IE01 | Neither cARL action nor low probability supplies governing policy, release authority, proof of violation or evidence sufficiency | Identical boundary; a provider's authority-promotion label is an observation, never actual authority |
| 153-position proposal | Can retain 99 generator + 54 specialist positions and all dependencies: one typed exchange per specialist, plus offline policy interpretation | Can retain topology if all questions fit one bounded exchange; capacity, usage and transport qualification remain unresolved. No extra calls are assumed |
| Historical pilot comparison | Original typed values/questions can be compared descriptively only under matching source, scope, identity and policy. No new v2 labels, retroactive adjudication, pooling with approved future observations or claim of equal instruments | New labels and claim-specific questions have no pilot counterpart. Retain pilot as diagnostic; do not backfill or pool |
| Implementation after approval | New strict raw-bound typed observation schema/parser and deterministic request-index join; per-field provenance and explicit unavailable v2 blocks; separate policy trace; new Q1 specialist receipt/validator routing and continuation delivery contract. Keep every frozen validator and historical receipt intact | Same new routing/custody work; additionally freeze per-claim question/label/applicability definitions, new native request builder, versioned cARL catalog/parser/policy, and offline missingness tests. Later provider qualification remains separately blocked |

**Exact next decision:** approve or reject Choice 1's separation of the existing
typed challenge instrument from v2 reference judgments, including its explicit
assessment-wide uncertainty/authority scope. Choose Choice 2 if richer per-claim
measurement is required. This is D02/D03 instrument/policy scope approval only;
neither choice authorizes implementation of thresholds, scientific sign-off or
live execution by implication. No unapproved amendment is installed here.

Both choices preserve [RD01](../../phase2_v2/RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md),
[RD02](../../phase2_v2/OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md),
[RD04](../../phase2_v2/OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md) and
[IE01](../../phase2_v2/INSUFFICIENT_EVIDENCE_CLARIFICATION.v2.1-RD04-IE01.md).
RD03/reference and governing-policy decisions remain pending. No new
adjudication exercise is proposed or commissioned by this task.

## Reproduction and preservation

From the repository root:

```sh
python -B -m unittest -v engineering_qualification_v1.systemone_contract_resolution_v1.test_contract
python -B -m unittest -q phase2_v2.test_instrument phase2_v2.test_continuation phase2_v2.rd05_offline.test_tool tests.test_harness
```

Executed results and preservation hashes are in
[verification.json](evidence/verification.json), with captured test outputs.
**93 tests passed: 11 focused contract tests and 82 existing regressions.**
Frozen v1/v2 code, decisions, original SystemOne evidence, RD05/comparison,
existing Q1 topology/executor/broker and baseline qualification report are
unchanged. The original custody verifier checks all **40,538** entries,
1,165 operator-sealed files, 4,699 V5 files and 36 command records.
