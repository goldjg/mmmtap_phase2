# Outcome movement decision amendment v2.1-RD02

**2026-10-13: disposition-movement measurement principle DECIDED BY PI.**
Immutable-in-intent decision record: preserve this version after publication;
future corrections or decisions require a new linked amendment, not silent
replacement. Baseline: `0fafdc5cf4417d6cab9f6f49ccb1e8ce7dfe6163` (RD01).
This supplements `RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md`, left unchanged.
No executable instrument, validation, vocabulary, arm or qualification-matrix
change; no numerical threshold, statistical success criterion or execution
authorization.

## Human authority and principles

PI instruction, supplied explicitly by the user:

> Any change in assessment disposition counts as an outcome change, even when
> the underlying security claims remain identical. Material changes to
> security findings are measured independently of disposition movement.

The following principles are recorded as approved, not blanket D04 approval:

1. **Disposition movement:** every change from baseline to final disposition
   is an outcome change, regardless of whether claims change. Preserve exact
   disposition values and ordered transition pairs, including unchanged.
2. **Material finding movement:** assess additions, withdrawals, substantive
   revisions or changes in evidential scope separately, regardless of
   disposition movement. Operational materiality/scoring rules remain pending.
3. **Evidence justification:** independently assess whether available evidence
   justifies disposition and finding movements. Proposed categories are
   justified, unjustified, mixed and unresolved; detailed rules are pending.
   Justification is not a post-hoc definition of whether movement occurred.
4. **No movement:** an unchanged disposition or unchanged finding is a
   recorded outcome, not automatically failure to respond to a challenge.
5. **No automatic improvement:** movement toward fail, warn or review_required
   does not imply better judgment; movement toward pass does not necessarily
   imply worse judgment. Preserve exact labels, never invent an ordinal
   severity scale. These examples do not add values to the instrument schema.

RD01's primary objective remains: determine whether JEV challenges change
AI-generated security assessments, what changes, in which direction, why,
and whether those changes are justified by evidence. Unsupported-assertion
adoption remains deferred. RD02 decides a measurement principle, not
inferential primacy, a scoring rubric, policy or analysis plan.

## Independently measurable observations

| Observation | Measurement proposal / approved boundary | Not implied |
|---|---|---|
| A: Assessment decision changed | Exact B0/final disposition pair; observed `D=1` if values differ, otherwise `D=0`; disposition-only differences always count (DECIDED BY PI) | No claim of material finding movement, correctness or improvement |
| B: Security findings changed | Independently align atomic findings and record substantive addition/withdrawal/qualification/strengthening/weakening/evidential scope; record unchanged findings and separate wording/formatting/confidence-only/administrative edits | Generator `revised` does not establish substantive movement; materiality rules pending |
| Evidence justified the decision/finding movement | Separate disposition-justification and per-finding-justification fields, evidence anchors, rationale and disagreement; proposed four categories above | Not movement eligibility, scalar severity, or proof of internal mechanism |

Do not OR/merge A and B into one binary endpoint or declare both statistically
co-primary. Per-family counts, profiles and denominators remain distinct.
Do not default missing/invalid records to `D=0` or unchanged findings.
Any descriptive extraction from contract-invalid raw text needs a separately
identified availability/admissibility rule (D07), not retroactive validation.
Retention evaluation, if undertaken, is distinct from movement.

## Hypothesis amendment lineage and traceability

| RD02 principle / affected draft at RD01 commit | Updated location and planning fields | Remaining decision |
|---|---|---|
| All disposition changes count; RD01-H1 previously proposed a single substantive-assessment indicator `S` with disposition rules pending | `PHASE2_V2_HYPOTHESES.md`, RD01-H1 amended under RD02; family A baseline/final disposition, exact pair, `D`, availability | Observation admissibility, estimand, primary contrasts and inference pending; movement principle no longer pending |
| Finding movement independent of disposition; former RD01-H1/H2 bundled several changes | Hypotheses family B; `SCIENTIFIC_DECISION_BRIEF.v2.1.md` D04/outcome table; atomic alignment, change type, evidential scope, unchanged/auxiliary fields | Materiality, segmentation, aggregation/scoring, reviewer rules |
| Justification separate for each family; former RD01-H2 had a companion primary candidate and equivalent category | Hypotheses RD01-H2; brief evidence-justification row; `ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md` paired sheets | Four-category detailed rules, retention evaluation, disagreements; no fifth category or co-primary designation |
| Preserve movement before justification/arm exposure | Adjudication workflow stage 7: finding alignment freeze, exact disposition recording, then separate justification; stage 8 rationale linkage | Staffing, blinding feasibility/guide, resolver and custody |
| PI decision without blanket D04 approval | `DECISION_REGISTER.md` RD02 notice/D04; `QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md` D04 gate and observation inventory | Primary outcomes/contrasts, multiplicity, estimands, sample size, stops, launch |
| Original scope/comparability retained | Hypotheses matching/sequential section; qualification unchanged Q0/Q1 matrix | Existing unapproved scope and D01-D03/D05-D11 gates remain |

RD01-H1/H2 IDs retain historical lineage but their draft definitions are
explicitly amended here; consult the parent commit for prior text. RD01-H3,
RD01-H4 and H5 are not redefined. The RD01 record and broader design rationale
remain historical/direction references; RD02 governs the movement distinction.

## Comparability, sequential transitions and missingness

B0, C1, C2, C3, E1, E2, E3_NC and E3_CN stay unchanged design references.
Match by source, generator, repetition and shared sealed baseline; never
replace B0. Candidate E1/E2 versus C1/C2 and E3 orders versus C3 final
contrasts remain proposed; prespecify which are inferentially primary.
Keep scheduled denominators, contract-invalid attempts, blocked descendants,
missing matched outcomes and attempted/eligible/complete-pair counts visible.
A schema-invalid response is not automatically an unchanged assessment,
and does not become an acceptable child parent.

For E3_NC/E3_CN record B0-to-intermediate, intermediate-to-final and
B0-to-final exact disposition pairs and finding alignment at each turn.
If disposition returns to baseline, final `D=0` but intermediate movements
remain recorded. Do the same for matched C3. Shared SystemOne judgments
are not independent judge replication.

The proposed qualification matrix is unchanged: three source cases x three
generators x one engineering repetition x 17 existing positions = 153
scheduled positions (99 generator, 54 specialist; 27 native + 27 cARL-JEV).
No fixtures, provider evaluations, annotation dry runs or experiments are
created/executed by RD02.

## Haiku pilot example: classification illustration, not evidence repair

The preserved review `POST_PILOT_ROOT_CAUSE.md` (trajectory table, Haiku
benign-docs E2 row) links cARL checkpoint `0ac4d60a.../result.json`, score
0.39, and generator checkpoint `0f131766.../result.json`, retaining the
substantive finding while moving to `review_required` and noting the missing
diff. For the reported baseline `pass` -> final `review_required` pair,
RD02 would record family A movement (`D=1`) regardless of finding retention.
In an otherwise identical-findings example, family B is unchanged; in the
actual trajectory, finding/evidential-scope movement needs independent
alignment, not inference from the retained substantive finding alone.

Disposition justification and finding justification are separately unresolved
without adjudication; missing-diff caution is a reported reason, not proof
of justified movement or correctness. This is a prospective classification
illustration. No pilot status, first attempt, reference label or evidence
record is reclassified, corrected or modified. See also
`SCIENTIFIC_DECISION_BRIEF.v2.1.md` for the disposition-only illustration.

## Outstanding human decisions and acceptance

D04: detailed scoring, materiality thresholds, statistical estimands,
primary contrasts/outcomes, multiplicity and any success criteria/stops.
D05: blinded alignment, justification and retention rubric, staffing,
resolver/disagreement and custody. D06/D07: sample size/repetitions,
clustering, invalid-output admissibility and censored/missing outcomes.
D01-D03/D08-D11: instrument/prompt approval, construct/applicability/policy,
arms if ever amended, judge transport/dependence, provenance, isolation,
cost/entitlements, stage budgets and separate execution authorization.
No numerical thresholds or success criteria selected here.

Acceptance for this increment: PI disposition principle labeled DECIDED BY
PI across the five amended drafts; independently recorded families and
justification; exact/unchanged/intermediate transitions and no ordinal scale;
explicit RD01-H1/H2 lineage; unchanged matrix, executables, fixtures,
manifests and original evidence; resolving document references; original
preservation verification passes; no provider calls or experiments.

## Change inventory and offline verification

Added: `OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md` (this record).
Modified planning drafts only: `PHASE2_V2_HYPOTHESES.md`,
`SCIENTIFIC_DECISION_BRIEF.v2.1.md`, `ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md`,
`DECISION_REGISTER.md`, `QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md`.
RD01 record, v1, executable instruments, fixtures and validation unchanged.
Actual offline verification on 2026-10-13:

| Command/check | Result |
|---|---|
| `git diff --check` | Passed |
| `git diff --name-status 0fafdc5c` and `git ls-files --others --exclude-standard`, checked with a local inline Python allowlist | Passed: exactly five modified planning Markdown files and this new Markdown record |
| `git diff --exit-code 0fafdc5c -- .` excluding only the five permitted modified planning paths | Passed: all 42,431 other tracked paths unchanged, including RD01, design, executable instrument, validator, fixtures, manifests, pilot and first attempts |
| `PYTHONDONTWRITEBYTECODE=1 python -` with local consistency/reference/section assertions | Passed: all six changed/new documents identify RD02 and DECIDED BY PI and distinguish disposition/finding/justification; 35 document references resolve; RD01-H3/H4/H5 text unchanged; qualification scope and cost sections byte-identical to RD01; all eight arms and 99 + 54 = 153 matrix arithmetic preserved |
| `PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify` in original local custody folder | Passed: 1,165 operator-sealed files, 4,699 v5 files, 36 command records and 40,538 original entries; no changed/missing evidence; zero provider calls; live qualification remains blocked |

The first inline consistency check requested the literal word "ordinal"
in each draft; the adjudication draft instead said never rank labels.
It now states the no-ordinal-scale constraint explicitly; the full rerun
passed. No classification, matrix, evidence or executable change was made
to satisfy that wording check.

The planning review verified independent outcome families, movement before
justification, exact sequential pairs, auxiliary edits, missingness,
explicit hypothesis lineage and remaining approvals. No executable tests
were rerun for Markdown-only changes. Document checks and preserved seals
do not establish the pending materiality/justification rubric, statistical
readiness or evidence-grounded judgment in the pilot example. No provider,
JEV or external evaluator was invoked; no experiment occurred.

**Final readiness: REQUIRES HUMAN DECISION for unresolved methodology and
execution gates.** Commit/push publishes this decision and planning amendment
only, not authorization of any stage.
