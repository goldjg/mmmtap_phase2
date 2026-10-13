# Phase 2 v2 hypotheses and outcome definitions

**RD01-amended draft preregistration scaffold; not frozen or approved.** The pilot did not
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

## Research direction and candidate hypotheses

Human decision RD01 establishes the primary objective: determine whether
JEV challenges change AI security assessments, what changes, in which
direction, why, and whether those changes are evidence-justified.
See `RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md`. Unsupported-assertion adoption
is deferred to a potential future study. RD01-H1 to RD01-H4 below replace
the earlier draft H1-H4; IDs must not be interpreted as unchanged hypotheses.
No outcome definition or statistical test below has human approval.

### RD01-H1 — Assessment change beyond matched control prompts

**Candidate primary hypothesis:** the probability of a substantive assessment
change from B0 differs between JEV-challenge paths and their matched control
paths. The alternative is nondirectional; JEV may increase, reduce, or
redirect change. The null is no paired difference in this probability.

Candidate indicator `S`: at least one independently adjudicated substantive
change in a final assessment relative to its sealed B0. Candidate contrast:
mean of `S(treatment) - S(control)` over evaluable matched units. Report
unchanged assessments explicitly. Changing wording or lifecycle metadata
alone need not count as substantive; D04/D05 must decide material confidence,
limitations and disposition-change rules before collection. Report those
dimensions separately regardless of the binary definition.

Compare E1 and E2 each with C1 and C2; each E3 order with C3 final turn.
Select the primary contrast family and multiplicity prospectively. These
are proposed comparisons, not redesign or new independent judge arms.
Contract-invalid or blocked outputs are missing scientific outcomes, not
`S=0`; retain scheduled, attempted, eligible and complete-pair denominators.
D07 must fix primary admissibility and sensitivity analysis.

### RD01-H2 — What changes, direction, and evidence justification

**Candidate companion primary question:** does the distribution of
evidence-justified, unjustified, mixed and unresolved assessment changes
differ between challenge and control paths? It does not presume improvement.
Whether this is co-primary or secondary, and any directional hypothesis,
remain D04 decisions.

Align atomic assertions and reference findings across B0 and every follow-up.
Record additions, withdrawals, qualifications, strengthening, evidence
replacement, confidence/limitations and disposition transitions. One
generator `revised` action may be wording-only or several atomic changes.
For each substantive transition, independently adjudicate source support,
independent verification and impact justification before/after. Use a
proposed transition rubric: justified correction/qualification; unjustified
addition/removal/strengthening; evidence-equivalent change; mixed; unresolved.
Neither a higher score nor a move toward `pass` or `review_required` determines
the category. Cross-dimension trade-offs must remain mixed, not averaged
into an invented ordering.

Report unit-level change profiles including no change and counts of each
transition category. Report per-change justification proportions separately,
with zero-change denominators undefined; conditioning on changed units can
select different populations. Preserve supported-finding recall/retention,
unsupported-new assertions and impact-overclaiming as distinct evidence
diagnostics, not the primary objective. Keep partial/unverifiable labels.

### RD01-H3 — Recorded reasons and challenge linkage (explanatory)

**Question, not an established mechanistic hypothesis:** which supplied
challenge dimensions and generator-stated reasons accompany each change,
retention or rejection? After blinded labels freeze, map exact challenge,
source and generator rationale spans to the aligned change record. Code
reported source reconsideration, verification caution, impact qualification,
deference to judge authority, task re-expression or absent/ambiguous reason
using a proposed human guide. Distinguish source-cited reasons from
challenge-cited reasons; permit multiple and unresolved links.

Do not infer an internal reason when the output gives none. Stated reasons
may be post-hoc; textual linkage, temporal order and shared scores do not
prove mechanism or causation. No rationale-elicitation prompt is added to the
instrument. Any such prompt would change the intervention and require
separate approval. Compare linkage profiles descriptively by control,
presentation and order; judge/request lineage is necessary evidence.

### RD01-H4 — Control drift and judge-signal diagnostics

Compare C1, C2 and each C3 turn with B0 using the same change/justification
rubric; controls measure prompt-induced drift. Report E2-E1 and E3_NC-E3_CN
as candidate secondary presentation/order contrasts, not judge independence.
Separately compare each dimension's preserved scores/labels with blinded
human labels and review decisions; discrimination or calibration methods
need approval and an adequate held-out dataset. No binary threshold is
selected from the pilot or fixture constants.

Native JEV and cARL-JEV share SystemOne: paths are not independent underlying
judges. Judge error may explain a challenge's content but does not by itself
establish why a generator changed or whether the change was justified.

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

The objective is decided; all operational definitions remain pending. The
PI/methods lead and statistician must specify: the primary hypothesis or
co-primary family; the natural-source population and reference set;
atomic-claim segmentation and materiality; reviewer number, qualifications,
blinding, change-direction/justification/rationale rubric and disagreement
resolution; treatment of partial/unverifiable
labels; primary contrasts; direction, margins and success thresholds;
repetition/sample-size and power rationale; analysis unit and clustering;
multiplicity and missingness analysis; calibration method; challenge
threshold/action; stopping rules; and authorized stage/budget.

Until then, these are candidate hypotheses and measurable outcomes, not
approved criteria. No causal, significance, calibration, or correctness
claim follows from the completed v1 pilot.
