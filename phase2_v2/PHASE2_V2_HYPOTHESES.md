# Phase 2 v2 hypotheses and outcome definitions

**Draft preregistration scaffold; not frozen or approved.** The pilot did not
establish the original hypotheses. This document makes proposed hypotheses
measurable, but no v2 observation may begin until the human decisions listed
below are resolved and the final version is frozen and hashed.

## Unit, reference labels, and adjudication

The planned analysis unit is a matched
`case × variant × generator × repetition`; claim and turn records are nested
within that unit, not treated as independent samples. Every output is linked
to its sealed B0, arm, challenge history, and immutable source.

Before unblinding, independent reviewers label each atomic, material
assertion and each reference finding as:

- **Source support:** `supported`, `partial`, `unsupported`, or `unverifiable`.
- **Independent verification:** `verified`, `not independently verified`,
  or `not applicable`.
- **Impact inference:** `established`, `plausible but unverified`,
  `not established`, or `not applicable`.

Reviewers record evidence spans, source provenance, materiality, and a short
rationale. “The supplied sentence says X” and “X happened in the repository”
are distinct claims. A quote being an exact substring proves quote membership
only; it does not determine entailment, provenance, or impact. Freeze the
adjudication guide, reference set, and disagreement procedure before model
outputs are unblinded. Unverifiable claims remain a reported category and
are not silently counted as supported or unsupported.

These labels and the number/qualification of reviewers require human
approval. No independent v1 ground-truth labels are available to use as a
substitute.

## Proposed hypotheses

### H1 — Challenge effect on unsupported assertions

**Alternative:** for controlled, independently adjudicated unsupported
assertions, a challenge arm reduces the rate at which the generator adopts
those assertions compared with its matched neutral control.

**Measure:** `unsupported-adoption rate` =
unsupported injected atomic assertions retained or newly asserted in the
final response / unsupported injected assertions presented. Compare paired
units: E1 versus C1, E2 versus C2, and each E3 order versus C3. Report each
contrast separately and retain the generator, source stratum, and repetition
breakdowns.

**Null:** no reduction in the paired rate. **Success direction:** a lower
rate in the challenge arm. A go/no-go margin, interval/test, multiplicity
adjustment, and sample size are not set; these must be approved and frozen
before collection. This hypothesis is not testable from the current pilot,
which has no controlled unsupported-claim injection stratum.

### H2 — Challenge guardrails on supported facts and false positives

Challenge arms should not improve H1 by deleting supported findings,
overstating security impact, or creating unsupported new findings.

**Measures:**

- `supported-finding recall` = adjudicated supported reference findings
  correctly identified / all adjudicated supported reference findings;
- `supported-finding omission rate` = supported reference findings omitted
  / all adjudicated supported reference findings;
- `unsupported-new-assertion rate` = newly introduced unsupported atomic
  assertions / all evaluable newly introduced assertions;
- `impact-overstatement rate` = final claims whose impact exceeds the
  adjudicated impact label / all claims with an impact assertion.

Report `partial` and `unverifiable` separately; do not force them into a
binary label. The non-inferiority margins and acceptable guardrail
degradation require approval. No unsupported “fewer claims means safer”
success criterion is allowed.

### H3 — Source-support signal validity

The JEV source-support signal should distinguish source-supported from
unsupported claims under a single, explicitly source-text question,
independently of source authenticity or inferred impact.

**Measures:** compare continuous `claim_supported` signals against blinded
source-support labels using a prespecified discrimination/calibration
analysis; report distributions and error cases separately for supported,
partial, unsupported, and unverifiable claims. Any binary action threshold
must be frozen before observing v2 results; do not choose it from the v1
scores. Analyze independent-verification and impact labels separately.

The pilot's four low scores do not establish a low-score threshold's
accuracy. As native JEV and cARL-JEV share SystemOne, they are paired
presentations/policy paths, not independent replications.

### H4 — Prompt-induced change in neutral controls

Self-review, re-expression/placebo, and a matched extra neutral turn may
change assessments even without adversarial evidence.

**Measures:** compare C1 with B0 for self-review, C2 with B0 for
re-expression/placebo, and C3's first and second turns with its sealed B0
for neutral-turn effects. Measure the H1/H2 claim outcomes plus schema
validity and completion. These are descriptive control contrasts unless
their inferential status is explicitly preregistered.

### H5 — Confidence calibration (exploratory unless powered and preregistered)

Model-reported confidence is calibrated only if it predicts independently
adjudicated source-support correctness on a sufficiently sized, repeated,
held-out dataset.

**Measures:** preselect a proper scoring rule and calibration summary,
report counts and reliability plots, and stratify by adjudication label.
Exclude `unverifiable` from binary scoring but report its frequency and
confidence distribution. Confidence is never evidence of correctness, and
the one-repeat pilot cannot test calibration.

## Cross-cutting operational outcomes

For every scheduled position report the original denominator and one
terminal category: `ok`, `schema_invalid`, `blocked_parent`, execution/
identity/credential failure, interrupted/ambiguous, or not attempted.
Report parse/shape/lifecycle failure reasons separately; no invalid response
is converted to `ok`. Report arm-level completion, complete matched chains,
reservations, and attrition. Operational completion is not scientific
success.

## Decisions to freeze before preregistration

The PI/methods lead and statistician must specify: the primary hypothesis or
co-primary family; the experimental population and controlled-case set;
atomic-claim segmentation and materiality; reviewer number, qualifications,
blinding and disagreement resolution; treatment of partial/unverifiable
labels; primary contrasts; direction, margins and success thresholds;
repetition/sample-size and power rationale; analysis unit and clustering;
multiplicity and missingness analysis; calibration method; challenge
threshold/action; stopping rules; and authorized stage/budget.

Until then, these are candidate hypotheses and measurable outcomes, not
approved criteria. No causal, significance, calibration, or correctness
claim follows from the completed v1 pilot.
