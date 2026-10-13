# Phase 2 v2 hypotheses and outcome definitions

**RD01/RD02/RD04-amended draft preregistration scaffold; not frozen or approved.** The pilot did not
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
RD02 supplements RD01: **DECIDED BY PI**, any baseline-to-final disposition
change is an outcome change even with identical security claims; material
finding movement is measured independently. See
`OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md`. This expressly amends RD01-H1/H2
as drafted at `0fafdc5c`; their IDs identify lineage, not unchanged definitions.
Operational scoring, inferential primacy and statistical tests remain pending.

RD04 interpretation is **DECIDED BY PI**: disposition means an operational
security decision about whether the assessed change may proceed, not merely
a judgment describing its source. The objective is whether JEV changes those
decisions, what/why, and whether evidence and applicable security policy
warrant them. See `OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md`.
This traceably supplements RD01-H1/H2 without changing RD02's label-movement
rule. Exact policies/obligations/authority and all statistical choices remain
pending; RD03 stays proposed. A model output is an evaluated recommendation,
not actual release approval or enforcement.

### RD01-H1 — Separately reported outcome movement beyond matched controls (RD02)

**Candidate questions:** do disposition movement and material finding
movement differ between JEV-challenge paths and prespecified matched control
paths? Report two outcome families separately. Neither is declared
inferentially primary or statistically co-primary. Hypotheses/tests for
each family and their multiplicity require a methods decision.

**A. Disposition movement (principle DECIDED BY PI).** Record exact baseline
and final disposition values and their ordered transition pair, including
unchanged. For observed admissible dispositions, define `D = 1` when the
final value differs from B0, otherwise `D = 0`. Every difference counts,
irrespective of finding movement or evidence justification. Preserve exact
labels; do not invent an ordinal severity scale. A proposed nondirectional
contrast is the paired difference in disposition-change indicators between
treatment and control; its estimand, admissibility and inferential status
are pending. Do not combine `D` with a finding-change indicator.

**Separate operational action observation (proposed, not a new combined
endpoint):** derive permission/hold/block recommendation and immediate
eligibility from approved policy, recording action pairs, warnings/conditions
and changed obligations alongside exact labels. Different labels may share
immediate eligibility (pass/eligible warn; review_required/fail). An unchanged
warn can have changed prerequisites. No ordinal severity scale or new
disposition value; action mapping of existing `insufficient_evidence` remains
pending. Missing policy/invalid outputs yield unavailable mappings, not no
movement. Detailed fields in `OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md`.

**B. Material finding movement (separate family).** Independently align
atomic security findings from B0 through follow-ups and record substantive
additions, withdrawals, qualifications, strengthening, weakening and changes
in evidential scope, regardless of disposition. Record unchanged findings.
Separate wording-only, formatting-only, confidence-only and administrative
lifecycle changes from substantive findings. If an edited limitation alters
evidential scope, adjudicate that content separately from the metadata edit.
The generator's `revised` action does not establish substantive movement.
Materiality rules and any unit-level summary/indicator remain pending.
Confidence changes are auxiliary observations, not automatic finding movement.

Compare E1 and E2 each with C1 and C2; each E3 order with C3 final turn.
Select the primary contrast family and multiplicity prospectively. These
are proposed comparisons, not redesign or new independent judge arms.
Contract-invalid or blocked outputs are missing scientific outcomes, not
`D=0` or unchanged findings; preserve original scheduled, attempted, eligible
and complete-pair denominators. D07 must fix primary admissibility and
sensitivity analysis without repairing rejected outputs. Maintain matching
by source, generator, repetition and shared sealed B0; B0/C1/C2/C3/E1/E2/
E3_NC/E3_CN remain unchanged design references.

For C3 and both E3 orders preserve exact B0-to-turn-1, turn-1-to-final and
B0-to-final disposition pairs, and intermediate/final finding alignments.
A disposition can move and return to baseline: final `D=0` does not erase
intermediate movement. Native/cARL paths share SystemOne; they are not
independent judge replications.

### RD01-H2 — Evidence justification independent of movement (RD02)

**Candidate questions:** for disposition movement and, separately, material
finding movement, how do evidence-justification profiles differ across
challenge/control paths? Preserve any disagreement between the two families.
Assess these independently, not as a post-hoc definition of whether movement
occurred. Proposed categories for each family are `justified`, `unjustified`,
`mixed`, `unresolved`; detailed decision rules and inferential status remain
pending. No automatic category follows from a judge score or contract validity.

For A, evaluate whether time-available evidence and the frozen applicable
operational policy justify the exact disposition/action recommendation
transition, even with unchanged findings. Source support is not sufficient
permission unless the policy makes it so. Governing policy is a normative
packet distinct from source/challenge evidence; no reviewer-invented
requirements after observing outcomes. Policy changes and later evidence
belong to separate retrospective analysis, not the main time-available warrant.
For B, evaluate each aligned finding's content/evidential-scope transition
using source entailment, independent verification and impact inference
before/after. Evidence-equivalent content may be described as such, but is
not a fifth justification category in this RD02 proposal. Disposition and
finding justification can disagree; preserve both and reviewer disagreement.
No ordinal direction or evidence verdict is inferred from `fail`, `warn`,
`review_required` or `pass`. These labels are examples, not additions to the
instrument's disposition vocabulary.

An unchanged disposition or finding is a recorded outcome, not automatically
failure to respond to a challenge. Any evaluation of justified retention
must be distinct from movement and use the approved future rubric.
Report exact transition profiles, findings and auxiliary edits, including
no movement. Report per-movement justification proportions separately for
each family, with zero-movement denominators undefined; conditioning on
movers may select different populations. Preserve supported-finding recall/retention,
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

RD01's objective and RD02's disposition-movement measurement principle are
decided along with RD04's operational construct, not blanket approval of
decision-register D04. Exact policy obligations, all-five-value mappings and
remaining operational definitions are
pending. The PI/methods lead and statistician must specify: the primary hypothesis or
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
