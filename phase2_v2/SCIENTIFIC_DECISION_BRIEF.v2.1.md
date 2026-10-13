# Scientific decision brief v2.1

**Planning proposal for human review. Nothing approved or frozen.**
No changes to v1, the v2.1 instrument, validation, hypotheses, or arm schedule
are made by this package. No stage or provider invocation is authorized.

Read alongside `DECISION_REGISTER.md`, `PHASE2_V2_DESIGN.md`,
`PHASE2_V2_HYPOTHESES.md`, `INSTRUMENT.md` and
`DEVELOPMENT_INCREMENT_REPORT.md`. Companion planning documents:
`ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md` and
`QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md`.
The development report describes its pre-commit state; development was
subsequently committed as `30ada9e6`. That publication did not approve a
scientific instrument.

## Decision-ready recommendations D01-D05

| Decision | Recommended option, pending approval | Alternatives and trade-offs | Consequences for existing arms |
|---|---|---|---|
| D01: lifecycle | Keep strict whole-object retention and complete ID accounting; approve clarified instructions/examples only after independent methods review | Narrow retention to substantive claim text: simpler for models, but changes metadata lifecycle and admissibility. Free-text follow-ups: less formatting burden, but loses deterministic lineage. Both require separately versioned contracts, not this increment | Apply identical accounting to C1/C2/C3 and all E follow-ups. C2 rewording is `revised` even without substantive correction. Classify metadata-only versus substantive change during adjudication; do not equate `revised` with improved correctness |
| D02: constructs | Approve three separate rubrics for source entailment, independent verification, and impact justification as written. Preserve labels, scores, rationale, provenance and applicability independently | A single support signal is cheaper but recreates conflation. Labels-only avoids uncalibrated numeric interpretation but changes current question contract. Separate impact-occurrence and inference-validity questions could resolve ambiguity but need a future instrument amendment | E1/E2 compare presentation/policy paths over the same constructs, not independent judges. E3 orders remain separate. No low verification score may silently become an entailment failure; controls do not receive judge output |
| D03: policy | Defer all numeric thresholds. First approve the dimension-specific review meaning, missing-score handling, and an independent development/held-out evaluation plan | Label-based review still needs policy approval and versioned implementation. Always presenting all judgments tests exposure, not threshold policy, and changes treatments. Using the fixture's 0.5 or fitting pilot examples is unjustified | No experimental mapping currently exists: mapper accepts `offline_fixture` only. A research policy requires a later approved implementation. Challenge-only diagnostics can precede it; E1/E2/E3 qualification cannot launch under test constants |
| D04: outcomes | For a later natural-B0 study, nominate paired unsupported-material-assertion burden as the primary candidate, with supported-finding preservation and impact-overclaiming guardrails; keep operational validity separate | Injection adoption is preferable for an approved controlled-injection study, but requires a specified exposure route. A composite can obscure harms. Disposition alone measures label drift, not correctness. Supported-finding recall could be primary for omission-focused research instead | E1/E2 each compared to C1 and C2, not selectively assigning a favorable control. Each E3 order compared to C3 final turn; B0 anchors changes. Choose one primary family and multiplicity plan before collection |
| D05: adjudication | Two independent qualified human reviewers plus a third resolver; separate source/reference preparation, blinded output labeling, and post-label paired analysis | One reviewer is cheaper but cannot establish agreement. Model-only adjudication is correlated/fallible and not an independent reference standard. Third-review all cases is stronger but costly | Assess all arm outputs under one blinded rubric, including false positives in benign controls. Freeze labels before revealing arm/order/model/challenge. Preserve missingness; invalid responses never become valid parent checkpoints |

**Suggested order of approval:** D02/D05 definitions and provenance first;
D01 prompt/contract rationale; D04 estimand and admissibility; then D03
policy validation design. Approval of a rubric is not approval of a run.

### D02 ambiguity requiring an explicit choice

Current `impact_inference` asks whether an inference is justified **as
written**, including conditionals. Its labels include
`plausible_but_unverified`, and its score is degree of justification, not
probability that compromise occurred. Thus high justification with
`plausible_but_unverified` is possible. Reviewers must not rank labels as an
ordinal scale of inference correctness. Recommended clarification: record
conditional versus asserted-actual language in the human sheet, and judge
qualification adequacy separately from occurrence evidence. If humans want
an additional typed instrument dimension, stop and request a future version;
do not repurpose the current score.

## Candidate outcome definitions, not success criteria

Atomic assertions and reference findings are segmented before arm unblinding.
Materiality follows a frozen reviewer rubric; do not add output-dependent
weights. Keep all numerators, denominators and unavailable outcomes visible.

| Candidate | Unit/definition | What it does not establish |
|---|---|---|
| Contract validity | Valid attempted generator responses / attempted generator responses, by arm and turn; separately report valid terminal responses / all scheduled generator positions, blocked descendants and complete chains | Scientific correctness or security |
| Unsupported assertion burden (primary candidate) | Count of material atomic assertions labeled `unsupported` in a final assessment. Paired final-minus-B0 burden and treatment-minus-control burden; report `partial` and `unverifiable` separately | Overall truth, deployment safety, or improvement merely from deleting all findings |
| Source-grounded correctness profile | Counts/proportions of supported, partial, unsupported, unverifiable output assertions, plus reference-finding recall. Output assertion denominators and reference denominators remain distinct | Literal support is not independent verification; unsupported does not always mean contradicted |
| Supported-finding preservation (guardrail) | B0-correct supported reference findings still correctly represented at final / supported reference findings correctly represented at B0. Report partially represented and dropped findings separately | Finding a new true claim is not retention. No B0-supported finding means undefined, not perfect preservation |
| Supported-finding recall | Correctly represented supported reference findings / all material supported reference findings in the source packet | No-reference benign cases have undefined recall; report unsupported findings instead |
| Impact overclaiming (guardrail) | Count and rate of assertions claiming actual consequences not established by admissible evidence; distinguish justified conditionals and unsupported conditionals | `not_established` does not itself prove absence of risk |
| Controlled adoption (conditional candidate) | Unsupported target assertions affirmatively adopted / presented unsupported targets, only in a separately approved exposure design | Judge-only seeded assessments cannot measure generator adoption or treatment efficacy |
| Disposition change (secondary) | Full B0-to-final disposition transition table, paired with claim/rationale labels | `pass` or `review_required` is not correctness or a deployment gate |

Recommend count-based burden plus preservation to expose both hallucination
and blanket deletion. Also report output-length/claim-count and unsupported
proportion sensitivity summaries, not a post-hoc winning metric. Exact
effect margin, inferential method, missingness estimand and multiplicity
remain undecided.

## Matched contrasts and dependency censoring

Match on source family, counterpart, immutable input, generator identity,
repetition, and shared frozen B0. Never fork from a corrected or regenerated
baseline.

| Contrast | Interpretation | Limitation |
|---|---|---|
| C1-B0; C2-B0; C3 turn 1/2-B0 | Self-review, re-expression and neutral-turn change | Shared B0, no independent control sample |
| E1-C1 and E1-C2; E2-C1 and E2-C2 | Single-challenge presentation versus each distinct one-turn control | C1/C2 are different controls, not interchangeable placebo copies. Designate primary comparison prospectively |
| E3_NC-C3 final; E3_CN-C3 final | Sequential presentation beyond two neutral turns | Judge identity shared; both orders not independent replications |
| E2-E1; E3_NC-E3_CN | Presentation/policy and order contrasts | Not independent underlying judge effects; qualify as secondary/exploratory unless powered |

B0 baseline deltas and treatment-control contrasts refer to different
questions. Do not count B0 repeatedly as independent observations. Cluster
at source family with generator/repetition structure; variants/claims/turns
are nested. A proposed qualification matrix cannot support inferential
claims.

Recommend keeping contract-invalid first attempts and parent-blocking in
the scheduled denominator and a parallel descriptive raw-content review
where interpretable. This recommendation does **not** approve raw-content
primary admissibility (D07). Complete-pair estimates are explicitly
conditional on completion; accompany them with arm-specific missingness
and prespecified sensitivity/bounds. A failed pair is not zero unsupported
burden, success, or an invitation to regenerate.

## Dependencies that prevent freezing D06-D11

| Pending decision | Depends on | Cannot freeze yet |
|---|---|---|
| D06 repetitions/statistics | D04 outcome/contrast family, D05 reliability, D07 attrition, D08 unit/exposure | Sample size, effect margin, power, multiplicity, uncertainty method |
| D07 invalid outputs | D01 contract, D04 estimand, D05 extraction feasibility | Raw-output primary admissibility, missingness assumptions, exclusions/bounds |
| D08 arms | D03 action/presentation and controlled-injection placement | Added/merged arms, exposure location, primary matching; existing names are preserved |
| D09 judge dependence | D02 constructs, D03 calibration/policy and transport evidence | Judge identity, independent-judge claims, correlation treatment, request accounting |
| D10 provenance | D02/D05 evidence rubric and fixture scope | Which evidence suffices for verification/impact and permitted source population |
| D11 launch/isolation | All preceding decisions plus executor/containment qualification | Any research-policy integration, stage, budget, credential use or launch |

## Assumptions and explicit deferrals

The three original generator families and existing eight arm names are
retained as design references, not a provider availability claim. Sources
are static supplied evidence; runtime/deployment claims remain unverified
unless independently supplied in the permitted packet. Independent reviewers
are available only as a staffing proposal. Existing public fixtures are
already exposed development material and cannot serve as held-out tests.

No change in pass rate, calibration, security validity, significance or
causal effectiveness is claimed. Approval requests, acceptance criteria and
sign-off records are in the qualification plan; all remain pending.
