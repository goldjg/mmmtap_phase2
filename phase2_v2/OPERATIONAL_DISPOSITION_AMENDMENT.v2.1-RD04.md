# Operational disposition amendment v2.1-RD04

**Operational-versus-descriptive construct: DECIDED BY PI.**
Baseline main: `9f1968e83d9f9d6eeb2d946d8be06948b9738b1f`.
Preserve this decision record after publication; corrections require a linked
amendment. Exact policy rules, obligations, thresholds and release authority
remain proposals/pending, not blanket approval of decision-register D04.

## Human decision and authority boundary

PI decision:

> MMMTAP dispositions represent operational security decisions about whether
> an assessed change should be permitted to proceed, not merely descriptive
> judgments about the supplied evidence.

The research objective is to establish whether JEV challenges change those
decisions, what changes, why, and whether the changes are warranted by evidence
and applicable security policy. This supplements unchanged approved
`RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md` and
`OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md`. Unsupported-adoption research stays
deferred; every exact disposition difference remains movement irrespective
of findings or justification.

**An assessment decision is an evaluated recommendation.** A label may denote
authorization within its assessment policy, but is not a credential, signed
human approval or actual execution authority. Only a separately authorized
enforcement mechanism and authorized actors could execute a release.
None exists or is wired by this increment. No live stage is authorized.

## Vocabulary verification and proposed policy-bound meanings

The frozen [enum](../phase2/core.py#L19), [validator](../phase2/core.py#L208-L267)
and [output shape](../phase2/core.py#L269-L275) accept exactly:
`pass`, `warn`, `review_required`, `fail`, **`insufficient_evidence`**.
The [v1 prompts](../phase2/prompts.v1.json) prohibit inferred deployed state
and delegated deployment/policy authority. Membership validation does not
establish precise release rules. RD04 intentionally defines a v2 construct;
it does not silently claim these operational meanings were frozen in v1.

| Existing exact value | Proposed semantics under a frozen applicable policy | Proposed immediate assessment action / remaining requirements |
|---|---|---|
| pass | Proceed is authorised under the assessment policy | Permission recommendation, within stated scope; other release approvals still required |
| warn | Proceed is permitted subject to explicit warning or recorded conditions | Permission recommendation with policy-authorized warnings/conditions; unmet mandatory pre-proceed conditions mean not currently eligible, not silently unconditional permission |
| review_required | Proceed is held pending authorised human review | Hold recommendation, named review authority and evidence/decision needed; no auto-release after a challenge |
| fail | Proceed is blocked by an established applicable security requirement or blocking condition | Block recommendation, cited requirement and evidenced applicability/violation; remediation/exception authority and process required |
| insufficient_evidence | Existing value retained; exact operational meaning not yet decided by PI | Action mapping unresolved. Recommend proposing hold pending required evidence, but do not equate it to review_required, treat it as permission, or remove it from validation |

All five strings remain unchanged; no new enum value or ordinal severity
scale. The four requested meanings are **proposals**, not approved obligation
text. Missing verification is neither automatically fail nor automatically
pass: the governing policy must state what is required and how gaps resolve.
An established blocking condition can be a policy-required missing attestation,
not necessarily proven compromise, if that rule is explicitly approved.

`pass` and an eligible `warn` can have the same immediate permission state,
while warning/conditions differ. A `warn` with unmet prerequisites can share
non-permission with a hold but still has a different rationale/remedy.
`review_required` and `fail` both prevent immediate proceeding, but human
review and established blocking/remediation obligations are different.
Do not collapse these requirements or hide exact transition pairs.

## Operational policy contract and measurement records

`OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md` specifies required immutable policy
context, delivery and approval provenance, policy/source separation,
future annotation fields, illustrative policy comparisons and qualification
gaps. It is a planning specification, not an executable schema or approved
policy packet.

Five independent records are proposed:

1. Exact disposition movement, including unchanged and intermediate pairs.
2. Operational permission/hold/block recommendation movement, including
   changed obligations even when immediate eligibility stays the same.
3. Material finding movement and auxiliary/no-movement records.
4. Evidence-and-policy justification, independent for disposition/action
   and findings; proposed justified/unjustified/mixed/unresolved rubric.
5. Generator-reported reasons and challenge linkage after blinded freeze,
   never inferred internal cognition.

No merged binary endpoint or statistical co-primary declaration. A disposition
can change without operational permission changing; an unchanged `warn`
can have changed conditions/eligibility. Unknown policy/action mapping or
invalid output yields unavailable/indeterminate action, not pass or no change.

## RD03 reconciliation and historical boundary

`EVIDENCE_JUSTIFICATION_PROPOSAL.v2.1-RD03.md` remains **RD03 PROPOSED**.
Its time-available evidence, separate dimensions, movement-first recording,
blinded alignment, mixed/unresolved distinction and rationale limitations
remain useful proposals. For future operational cases, replace any merely
description-only task basis with the approved operational scope and policy
packet. Policy selects required evidence; literal source support alone
cannot authorize proceeding unless that policy makes it sufficient.

The local toy semantics in
`ADJUDICATION_TRAINING_EXAMPLES.v2.1-RD03.md` are preserved as authored
illustrations, not current operational authority. T01/T04/T10/T11 cannot
be imported as pass/hold warrant for operational releases; T02 illustrates
the verification dependency. T08's conflicting obligations require approved
policy precedence or unresolved analysis, not a newly invented gate.
No RD03 classification is retroactively approved by RD04.

The historical pilot retains its provisional observed dispositions,
`correctness: not_adjudicated` and failed strict-isolation qualification.
Haiku's pass-to-review_required transition is exact-label movement, not proof
that a release was permitted then held. Gemini retaining pass is not a real
authorization; Sol retaining review_required is not an enacted review hold.
See `POST_PILOT_ROOT_CAUSE.md` and RD03's linked checkpoints. Without a
time-available operational policy, any retrospective policy evaluation must
be separately labeled, never imposed on the pilot or its first attempts.

## Traceability and approval dependencies

| Affected surface | RD04 effect | Still pending |
|---|---|---|
| `PHASE2_V2_HYPOTHESES.md`, RD01-H1/H2 | Interpretation now operational; separate action recommendation movement and policy-bound warrant added, no approved estimand | Inferential primacy, action derivation/admissibility, contrasts/multiplicity |
| `SCIENTIFIC_DECISION_BRIEF.v2.1.md` | Five separately reported records and operational meaning | Exact policy text/obligations/materiality/scoring |
| `ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md` | Freeze policy before output exposure, independent policy anchors and staged action review | Review guide/fields, authorized policy reviewers, resolution |
| `DECISION_REGISTER.md` | RD04 construct DECIDED BY PI, not blanket decision-register D04 approval | D02-D07 policy/rubric/statistics and D10/D11 provenance/launch |
| `QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md` | Existing 153-position structure can cover operational questions conditionally | Actual packets, source adequacy, future approved instrument delivery, scope/launch |
| `PHASE2_V2_DESIGN.md` | Operational interpretation linked without executable integration or historical reinterpretation | All precise rules, policy delivery and launch |
| Existing RD03 proposal/examples and RD01/RD02 records | Unchanged records, contextualized here | RD03 approval still absent |

PI must decide the fifth value's meaning; four-value policy mapping and
warning prerequisites; obligations/precedence/exceptions; evidence/time/
provenance requirements; human authority/expiry; action annotation rules;
and admissible operational population. Statistical success criteria, sample
size, empirical thresholds, executor/isolation, budget and launch stay pending.
No policy comparison factor or new arm is added.

## Change inventory and offline verification

Exact planning-only inventory:

| File under phase2_v2/ | Change |
|---|---|
| `OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md` | Added PI construct record, proposed semantics, traceability and verification |
| `OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md` | Added proposed packet, outcome fields, policy examples and approval gaps |
| `DECISION_REGISTER.md` | Updated construct status and pending policy/adjudication/provenance/authority gates |
| `PHASE2_V2_HYPOTHESES.md` | Traceably supplemented RD01-H1/H2 with operational interpretation, without statistical approval |
| `SCIENTIFIC_DECISION_BRIEF.v2.1.md` | Updated separate outcomes, policy-bound warrant and approval dependencies |
| `ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md` | Added prospective policy freeze/anchors and operational annotations |
| `QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md` | Added feasibility gaps/observations/gates, unchanged scope and cost method |
| `PHASE2_V2_DESIGN.md` | Added linked operational construct and non-retroactive boundary |

RD01/RD02, RD03 proposal/training, executable instruments/validators/prompts/
fixtures/manifests, v1 evidence and first attempts are unchanged.

Actual offline verification against baseline main:

| Command/check | Result |
|---|---|
| `git diff --check`; exact `git diff --name-only` / `git ls-files --others --exclude-standard` allowlist | Passed: six modified draft Markdown files and two new planning Markdown files only |
| `git diff --exit-code 9f1968e8 -- .` with exclusions for the six modified drafts | Passed: all 42,433 other tracked paths unchanged, including preservation implementation, RD01/RD02/RD03 and protected executable/evidence surfaces |
| Read-only local Python document-reference, AST vocabulary and planning-consistency checks | Passed: local document references and source line anchors resolve; exact five-value frozen enum covered; all eight documents mark construct DECIDED BY PI and RD03 proposed; required policy/action fields present |
| Byte comparison of qualification scope/matrix and cost-method sections against baseline | Passed unchanged: 153 scheduled positions, existing arms/repetition proposal; no added policy-factor cells |
| Byte comparison of RD01-H3, RD01-H4 and H5 against baseline | Passed unchanged; H1/H2 supplementation expressly traced to RD04 |
| `PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify` in original custody folder | Passed: 1,165 operator-sealed files, 4,699 v5-sealed files, 36 command records and 40,538 original entries; zero changed/missing, zero provider calls; live qualification blocked |

An initial document consistency check found that the qualification notice
referred only to a "fifth value"; it now explicitly names
`insufficient_evidence`, and the check passed. No validation rule was altered.
Custody verification applies to the original local bundle, not a claim that
previously sanitized public archives reproduce its original seals.

No provider/evaluator calls, experiments, policy implementations or enforcement
were performed. Document checks establish traceability and preservation, not
policy validity, scientific power or reviewer reliability. Exact policy text,
all-five-value semantics, evidence adequacy, adjudication rules/thresholds,
primary estimands/contrasts/multiplicity, sample size, budgets and execution
authorization still need explicit approval. Publication approves none of them.

**REQUIRES HUMAN DECISION for remaining methodological and execution gates.**
