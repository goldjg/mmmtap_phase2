# Scientific decision brief v2.1

**RD01/RD02/RD04-amended planning proposal for human review.**
The human-approved direction is to determine whether JEV challenges change AI
security assessments, what changes, in which direction, why, and whether
those changes are evidence-justified. Unsupported-assertion adoption is
deferred to a potential future study. See
`RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md`.
RD02's disposition-movement principle is **DECIDED BY PI**: every exact
baseline-to-final disposition difference counts as outcome change even with
unchanged claims. Material finding movement is independent, and justification
is a separate assessment for each family. See
`OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md`.
RD04 operational-versus-descriptive construct is **DECIDED BY PI**:
dispositions concern permission to proceed under applicable security policy.
Model decisions are evaluated recommendations, not executed authorizations.
See `OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md` and proposed
`OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md`. Exact obligations/action rules
and RD03 rubric remain pending. Human-directed planning clarification
`INSUFFICIENT_EVIDENCE_CLARIFICATION.v2.1-RD04-IE01.md` proposes
`insufficient_evidence` as a distinct evidence-remediation hold: obtain
required missing/inadequate evidence then reassess, not review or violation.
PI/human-approved governing policy determines operational outcomes;
JEV/cARL challenge policy informs reconsideration without governing authority.
Draft hypotheses are traceably updated; remaining methods are not approved or frozen. No changes
to v1, the v2.1 instrument, validation or arm schedule are made.
No stage or provider invocation is authorized.

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
| D04: outcomes | RD02 label movement and RD04 operational construct DECIDED BY PI; separately report exact dispositions, policy-derived recommendation action/eligibility, findings, evidence-policy warrant and reasons | Same immediate action can hide different warning/review/block obligations; keep label/action pairs and conditions. Source-limited permission or verification-required hold needs approved policy. A merged endpoint is not adopted | Eight arms and 153-position proposal unchanged; policy packets/source adequacy/delivery and primary/statistical choices pending; RD03 not approved |
| D05: adjudication | Two independent qualified human reviewers plus a third resolver; separate source/reference preparation, blinded output labeling, and post-label paired analysis | One reviewer is cheaper but cannot establish agreement. Model-only adjudication is correlated/fallible and not an independent reference standard. Third-review all cases is stronger but costly | Assess all arm outputs under one blinded rubric, including false positives in benign controls. Freeze labels before revealing arm/order/model/challenge. Preserve missingness; invalid responses never become valid parent checkpoints |

**Suggested order of approval:** D02/D05 definitions and provenance first;
RD04 governing operational policy/scope/evidence obligations before output
review (distinct from D03's challenge-mapping policy);
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
| A: Disposition movement (principle DECIDED BY PI) | Exact B0/final values and ordered pair including unchanged; observed `D=1` iff values differ, otherwise `D=0`; separately preserve intermediate pairs | Counts even with identical findings. No ordinal severity scale, correctness interpretation, or primary status implied; invalid/missing is not `D=0` |
| Operational recommendation movement (proposed) | Policy-bound permission/evidence-hold/review-hold/violation-block and eligibility pairs; separate rationale/resolution/reporting, obligations, rule IDs and availability | No execution; insufficient_evidence obtains evidence then reassesses, review_required awaits authorised decision, fail concerns violation; shared non-permission does not merge meanings |
| B: Material finding movement (separate family) | Independently aligned additions, withdrawals, substantive qualification/strengthening/weakening and evidential-scope changes; record unchanged findings | Materiality rubric pending. Wording/formatting/confidence-only and administrative edits recorded separately; `revised` is not substantive-change evidence |
| Evidence-and-policy justification (independent records) | RD03 proposed categories for disposition/action and per-finding transition, source/policy anchors, time-available evidence and disagreement | Neither permission automatically unsafe nor caution justified; movement recorded first; policy cannot be invented after outcomes; RD03 pending |
| Unsupported assertion burden (secondary diagnostic) | Count of material atomic assertions labeled `unsupported` in a final assessment; report `partial` and `unverifiable` separately | Not the primary objective; deletion alone is not improvement |
| Source-grounded correctness profile | Counts/proportions of supported, partial, unsupported, unverifiable output assertions, plus reference-finding recall. Output assertion denominators and reference denominators remain distinct | Literal support is not independent verification; unsupported does not always mean contradicted |
| Supported-finding preservation (guardrail) | B0-correct supported reference findings still correctly represented at final / supported reference findings correctly represented at B0. Report partially represented and dropped findings separately | Finding a new true claim is not retention. No B0-supported finding means undefined, not perfect preservation |
| Supported-finding recall | Correctly represented supported reference findings / all material supported reference findings in the source packet | No-reference benign cases have undefined recall; report unsupported findings instead |
| Impact overclaiming (guardrail) | Count and rate of assertions claiming actual consequences not established by admissible evidence; distinguish justified conditionals and unsupported conditionals | `not_established` does not itself prove absence of risk |
| Recorded reasons (explanatory) | Exact generator rationale/source/challenge links for change, retention or rejection; absent/ambiguous reasons retained | Reported explanations are not internal mechanisms or proof of causal mediation |
| Controlled adoption (deferred future study) | No current-study endpoint or injection exposure | Judge-only seeded assessments cannot measure generator adoption |
| Auxiliary edits | Confidence-only, wording-only, formatting-only and administrative lifecycle changes, independently recorded | Not silently treated as material findings or discarded |

Report exact label and operational action movements separately from finding
movement, warrant and reasons. Preserve RD02's two movement families without
combining them or declaring both
statistically co-primary; methods must choose inferential outcomes/contrasts.
An unchanged disposition or finding is an outcome, not automatically failure
to respond. No transition label is ranked as severity. Count-based burden,
preservation and output-length summaries
remain supporting diagnostics. Rationale linkage addresses reported "why"
without inventing mechanisms. Exact effect margin, inferential method,
missingness estimand and multiplicity remain undecided.

Under RD02, a disposition-only `pass` -> `review_required` trajectory such
as the pilot Haiku E2 example has `D=1` even if substantive findings stay
identical. Finding movement must be independently assessed: retained
substantive content does not establish byte-identical claims or unchanged
evidential scope. Neither family's justification is decided by the transition.
See the RD02 record for evidence pointers and the non-retroactive boundary.
Under RD04 this pilot observation is not a historical release permission/
hold event: no approved time-available operational packet is inferred.

## Matched contrasts and dependency censoring

Match on source family, case/variant, immutable input, generator identity,
repetition, and shared frozen B0. Never fork from a corrected or regenerated
baseline.

| Contrast | Interpretation | Limitation |
|---|---|---|
| C1-B0; C2-B0; C3 turn 1/2-B0 | Self-review, re-expression and neutral-turn change | Shared B0, no independent control sample |
| E1-C1 and E1-C2; E2-C1 and E2-C2 | Single-challenge presentation versus each distinct one-turn control | C1/C2 are different controls, not interchangeable placebo copies. Designate primary comparison prospectively |
| E3_NC-C3 final; E3_CN-C3 final | Sequential presentation beyond two neutral turns; record B0-to-intermediate, intermediate-to-final and B0-to-final pairs/findings | Judge identity shared; both orders not independent replications; return to baseline does not erase intermediate movement |
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
and prespecified sensitivity/bounds. A failed pair is not no change, zero
unsupported burden, success, or an invitation to regenerate.

## Dependencies that prevent freezing D06-D11

| Pending decision | Depends on | Cannot freeze yet |
|---|---|---|
| D06 repetitions/statistics | D04 outcome/contrast family, D05 reliability, D07 attrition, D08 unit/exposure | Sample size, effect margin, power, multiplicity, uncertainty method |
| D07 invalid outputs | D01 contract, D04 estimand, D05 extraction feasibility | Raw-output primary admissibility, missingness assumptions, exclusions/bounds |
| D08 arms | D03 action/presentation and RD01 natural-B0 scope | Added/merged arms and primary matching; existing names preserved, controlled-injection placement deferred |
| D09 judge dependence | D02 constructs, D03 calibration/policy and transport evidence | Judge identity, independent-judge claims, correlation treatment, request accounting |
| D10 provenance | D02/D05 evidence rubric, RD04 policy provenance/scope | Which evidence suffices under applicable policy, independent source/policy anchors and permitted population |
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
