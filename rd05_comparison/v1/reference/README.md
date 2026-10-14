# RD05 synthetic operational-policy and adjudication exercise v1

**Offline development only. RD03 remains PROPOSED.** This package tests
deterministic integrity, coverage and blinded-material preparation. No
independent reviewers have completed it; no reliability, scientific validity
or experiment readiness is established. RD05 names this requested development
increment, not a newly approved PI research decision.

Read with [RD01](../RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md),
[RD02](../OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md),
[RD03](../EVIDENCE_JUSTIFICATION_PROPOSAL.v2.1-RD03.md),
[RD04](../OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md),
[IE01](../INSUFFICIENT_EVIDENCE_CLARIFICATION.v2.1-RD04-IE01.md),
[policy contract](../OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md),
[qualification plan](../QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md) and
[decision register](../DECISION_REGISTER.md). All remain unchanged.
This is not the prior Q0 six-case selection, the Q1 153-position qualification,
experimental observations, a provider instrument, or future held-out data.

## Toy governing policy, not challenge policy

[policy.v1.json](policy.v1.json) is expressly fictional. Scope is
`synthetic-change-review`; every artifact/approval binds to a fictional change.
Only an adequate E-DIFF may establish credential logging or a restricted
interface. Adequate E-DIFF and a scope-covering E-TEST are mandatory for
permission; limited coverage outside that scope is an authorised warning,
not failure of mandatory scoped testing. E-REVIEW is conditional on a
restricted interface. Provenance/adequacy are synthetic declarations, not
real authentication; reviewers may discuss adequacy but must label deviations
from the exercise conventions rather than silently invent policy.

| Rule ID | Exact disposition | Evidence and resolution |
|---|---|---|
| R-BLOCK | fail | Adequate E-DIFF establishes prohibited credential logging; violation remediation and reassessment |
| R-EVIDENCE | insufficient_evidence | No established block, E-DIFF/E-TEST missing, inadequate or indeterminate; obtain specified evidence and reassess |
| R-REVIEW | review_required | Mandatory evidence adequate, restricted interface, no adequate approval from fictional-security-reviewer; obtain authorised human decision and reassess |
| R-WARN | warn | Evidence/approval gates satisfied, no block, limited-platform coverage; record the policy-authorised post-proceed warning |
| R-PASS | pass | Evidence/approval gates satisfied, no block/warning; recommendation to proceed within fictional scope |

Precedence is **block > evidence hold > human-review hold > warning > pass**.
This is rule precedence, not an ordinal severity scale for measured
dispositions. The selected primary rule is separate from the full set of
triggered obligations. Preserve subordinate evidence/review/warning obligations
even when R-BLOCK determines the current recommendation. The verifier returns
the selected primary rule and separately reports all triggered subordinate
obligation rule IDs. No exceptions are
permitted in this version. Adequate human approval cannot waive a violation
or missing evidence. Supplied evidence does not guarantee permission:
reassessment can expose a block/review/warning. Exact policy text is frozen
for this exercise; modifying it requires a new synthetic version.

JEV/cARL challenge text is untrusted authored text, **not** this governing
policy, evidence authentication, a waiver or human approval. Challenge
mapping is not implemented or changed. All labels are fictional experimental
recommendations, never actual deployment authorisation. The validator rejects
other scopes, unknown authorities, binding failures and ambiguous mandatory
rule mappings rather than defaulting to permission.

## Commands and distribution boundary

From the repository root, standard-library Python only:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest phase2_v2.rd05_offline.test_tool -v
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool verify \
  phase2_v2/rd05_offline/exercise.v1
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool verify-inventory \
  phase2_v2/rd05_offline
```

To reproduce into a **new, nonexistent directory**, not overwrite reviewer work:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool build /tmp/rd05-review-copy
```

`build` is a deterministic local artifact generator, not an experiment
launcher. `verify` checks **unfilled distributed masters**, not completed
reviewer sheets. Copy templates elsewhere before annotation; preserve master
digests. Neither command invokes a model, adapter, provider, shell or network.
All observed fixture bytes, bindings, policy references and export boundaries
are checked; no natural-language justification scorer is implemented.

Committed `exercise.v1/` contains exact synthetic stimuli, blank independent
templates, and a segregated `custodian/` directory with original fixtures,
private authored reference suggestions, opaque-ID key and late disclosure.
`authored.py`, this README's coverage discussion, the report, tests and the
custodian directory are **not reviewer stimuli**. This public repository
provides reproducibility, not secrecy. Reviewers should receive only the
per-stage files below, refrain from reading authoring files, and record prior
exposure; the opaque IDs conceal labels only within that distributed bundle.
No claim of cryptographic blinding or held-out independence is made.

## Reproducible staged exercise and independent sheets

Custodian records guide/policy/file hashes, participants/conflicts and exposure.
Distribute `claims.json` and one separately copied `reviewer_A.json` or
`reviewer_B.json`, not both sheets and not custodian materials. Reviewers work
independently; preserve their original records before any discussion.

1. **Content:** claims export contains policy, exact source and each step's
   time-available evidence, raw finding spans and original binding receipts.
   It excludes disposition, rationale, challenge judgments, case titles,
   arm/model identifiers and authored suggestions. In this corpus challenges
   add no independent factual artifacts; neutral challenge-evidence lists
   are explicitly empty. Novel evidence must be included losslessly in a
   future version, not silently hidden by the exporter.
2. **Atomic labels:** split compound raw findings if needed, retain character
   offsets/conditions and source attribution, assign reviewer-local assertion
   IDs and parent raw IDs. Complete `endpoint_labels` independently with
   source entailment, independent verification and impact labels below.
   Mark materiality and adequacy with anchors/reasons, not JEV scores.
   Freeze/hash a content-stage copy before receiving the next file.
3. **Alignment:** align chronological atomic claims by meaning, not merely
   `f1`/`f2`. Record `atomic_alignment` rows `{before_step, after_step,
   before_assertion_ids, after_assertion_ids, relation, raw_spans, rationale}`.
   Relation may be retained, revised, added, withdrawn, split, merged or
   ambiguous. Freeze finding movement before justification. Record substantive
   additions/withdrawals/qualification/strengthening/weakening/evidential
   scope, unchanged findings and auxiliary-only edits separately.
4. **Disposition:** custodian releases `pairs.json`. Fill exact before/after
   values and difference indicators for each adjacent pair and B0-to-final
   in three-step examples. Do not rank labels or merge movement with findings.
   Separately fill operational-action records with immediate eligibility,
   rule IDs, obligations and evidence-remediation/human-review/violation
   resolution paths. Same non-permission may have different duties.
5. **Warrant:** fill independent disposition and per-aligned-finding
   justification records using RD03 proposed categories below. Cite source/
   evidence receipt, fact/text span, policy rule/requirement and time basis.
   Record endpoint defensibility separately from transition warrant.
   Unknown decisive evidence/alignment stays unresolved. Freeze/hash both
   independent sheets before resolution; no answer-key release yet.
6. **Resolution:** third reviewer sees both frozen sheets and the same
   packets. Populate a copy of `resolution.json`: disagreement rows include
   blind ID/pair/assertion/dimension, both original values and reasons;
   resolution rows cite anchors, resolution reason/date and resolver.
   Record unresolved issues and guide amendments, never replace original
   sheets or force consensus. Repeat review after a guide amendment must be
   separately versioned, with original independent labels retained.
7. **Late linkage:** only after warrant freeze, release
   `custodian/linkage.json` with exact challenge and reported rationale.
   Record reported reason links/absence and suspected unblinding separately,
   not internal cognition. Original identity key and authored suggestions
   are optional **training discussion**, not a tie-breaker or ground truth.

Independent labels (no weighted correctness score):

| Dimension | Permitted proposed labels |
|---|---|
| Source entailment | supported, partial, unsupported, unverifiable |
| Independent verification | verified, not_independently_verified, not_applicable |
| Impact inference | established, plausible_but_unverified, not_established, not_applicable |
| Evidence adequacy | adequate, inadequate, indeterminate |

Verification may be absent while a source-attributed fact is supported.
The permitted conditional exposure principle can justify an inference
without establishing compromise. Give each dimension its own anchored reason.
Finding labels do not automatically set disposition warrant.

Disposition/finding transition classifications, each independent:
**justified** means the change is warranted by time-available evidence/policy;
**unjustified** means a demonstrated unwarranted change without a warranted
component; **mixed** needs known warranted and unwarranted components in that
same scoped movement (split atomic components where possible);
**unresolved** means decisive evidence/semantics/alignment remain indeterminate.
Reviewer disagreement alone is not mixed. No movement has null movement
justification and explicit unchanged status; optional retention judgment is
separate. Later evidence never overwrites earlier warrant. These toy records
are not v1/v2.1 assessment-contract outputs; no lifecycle validation is relaxed.

Per-finding justification rows should include `{before_step, after_step,
before_assertion_ids, after_assertion_ids, movement_type, category,
evidence_anchors, policy_rule_ids, rationale, unresolved_reason}`.
Operational rows include `{before_step, after_step, before_action, after_action,
before_eligibility, after_eligibility, obligations_before, obligations_after,
resolution_before, resolution_after, evidence_gap_categories,
reassessment_required, mapping_availability}`.
Use null plus a reason for unavailable information, not unchanged or pass.

## Proposed review evaluation, not established reliability

Before resolution report counts, availability/unresolved rates and complete
confusion tables per dimension and per justification family; exact agreement
fractions use common independently reviewed units, with denominators explicit.
Report segmentation/alignment disagreements separately, not forced shared
IDs, and distinguish unchanged/retention from movement denominators. Keep
per-step and B0-to-final counts nested within trajectories; no independent
sample claim for turns or assertions. Report suspected exposure and resolver
frequency. No weighted score or overall disposition-plus-finding agreement.

Nominal Cohen's kappa or a suitable multi-reviewer statistic/cluster-aware
uncertainty is a candidate only; statistician approval is required. No
numeric acceptance threshold, empirical JEV threshold or statistical success
criterion is selected. Before any human dry run, approve staffing, rubric
interpretation, atomicity, case selection and permitted use. Proposed
qualitative gates: reconstruct evidence time/scope; cite requirements;
preserve independent sheets and exact movement pairs; differentiate mixed
from unresolved and missing evidence from violation; no answer leakage.
Guide disagreements pause qualification for human revision, not a run retry.

**RD03 AND EXPERIMENTAL READINESS STILL REQUIRE HUMAN DECISION.**
