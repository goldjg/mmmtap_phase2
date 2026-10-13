# Insufficient-evidence planning clarification v2.1-RD04-IE01

**Human-directed planning decision, 2026-10-13; operational meaning proposed.**
Baseline main: `c56bf8712e1d9f1e9790cf6a2674ac07870a1f14`.
This linked clarification supersedes RD04's pending fifth-value meaning
in current planning, not its historical decision or verification record.
Preserve `OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md` unchanged.
No complete policy packet, scoring rubric, implementation or stage is approved.

## Meaning and distinct resolution paths

`insufficient_evidence` is a first-class, existing frozen disposition:
the change does not proceed yet because required evidence is missing or
inadequate. Obtain the specified evidence, then reassess. It does not
collapse into `review_required`, imply a violation, or authorize proceeding
automatically once a document is uploaded.

| Exact disposition | Proposed non-proceed rationale | Resolution and reporting |
|---|---|---|
| insufficient_evidence | Required evidence missing/inadequate | Evidence-remediation hold; obtain specified evidence and reassess; report "blocked for missing evidence" |
| review_required | Authorised human review/decision required | Human-review hold; refer to the named authority; report "awaiting review" |
| fail | Applicable requirement violated | Violation block; applicable remediation/approved exception process; report "blocked for violation" |

These may share immediate non-permission, but rationale, obligations,
downstream handling and reporting stay distinct. No ordinal severity scale.
Lack of proof of compliance is not proof of violation. If an approved policy
explicitly makes a particular absence a violation, cite that rule; do not
invent it from a low judge score. Overlap/precedence of simultaneous evidence,
review and violation conditions requires prospective human-approved rules.

## Governing authority versus challenge policy

PI/human-approved governing security policy determines applicable operational
outcomes, obligations and evidence sufficiency. A model's disposition is an
evaluated recommendation under that policy, not actual release execution.
JEV/cARL outputs do not themselves decide an operational outcome. Their
challenge-generation/mapping policy can inform reconsideration but does not
inherit governing authority, create a gate, waive evidence or supply approval.
Keep policy versions/digests, requirement anchors and challenge rule IDs
separate. Independently examine time-available evidence and governing rules;
neither challenge labels/scores nor generator explanations are ground truth.

## Proposed handling and future annotation fields

Under the sealed policy packet, identify each missing/inadequate evidence
category and requirement ID, its adequacy criteria/provenance, what it would
resolve and who can supply/accept it. Possible categories include authenticated
change/diff provenance, scoped security test results, configuration/impact
verification, or required attestation; none is mandatory by default.
Record `evidence_gap_categories`, `evidence_requirement_ids`,
`evidence_gap_anchors`, `evidence_remediation_steps`,
`evidence_acceptance_authority`, `reassessment_required`,
`resolution_path` and `non_proceed_reason` as proposed annotation fields,
not new assessment-schema keys.

Supplying evidence requires reassessment under applicable approved policy;
it does not guarantee pass and may reveal a violation or a need for review.
Any later reassessment is a separately authorized, provenance-linked
assessment, never a retry, repair or replacement of a first attempt. This
planning package adds no scheduled follow-up, provider call or campaign.
Historical decisions use historical evidence; later evidence is separately
labeled and does not overwrite original warrant.

## Synthetic worked case (not an observation or ground truth)

Source: a description says a change affects documentation only; no
authenticated diff is supplied. Toy governing rule G-E requires an
authenticated diff before permission and directs missing evidence to an
evidence-remediation hold; it does not define absence as a violation.
`insufficient_evidence` is the proposed recommendation: obtain the diff
and reassess. Source entailment may support the description while independent
verification remains absent; no finding of policy violation follows.

Toy rule G-R instead requires a named human security approval even with
adequate evidence: `review_required` awaits that decision. Toy rule G-V
prohibits token logging; an admissible diff establishing such logging warrants
`fail`, not merely missing-evidence handling. These authored alternatives
are neither selected research policies nor additional arms.

For a paired `review_required` -> `insufficient_evidence` correction under
G-E, record exact disposition movement, unchanged immediate non-permission,
changed review-to-evidence resolution obligations, and independently aligned
finding movement (which may be unchanged). Assess warrant separately; a
JEV alarm alone cannot justify this transition. An unchanged
`insufficient_evidence` is a recorded no-movement outcome, not failure to
respond. Preserve intermediate and final pairs in sequential arms.

## Traceability, unresolved decisions and verification

Current drafts updated: `OPERATIONAL_POLICY_CONTRACT.v2.1-RD04.md`,
`DECISION_REGISTER.md`, `PHASE2_V2_DESIGN.md`,
`PHASE2_V2_HYPOTHESES.md`, `SCIENTIFIC_DECISION_BRIEF.v2.1.md`,
`ADJUDICATION_AND_FIXTURE_SPEC.v2.1.md` and
`QUALIFICATION_AND_SIGNOFF_PLAN.v2.1.md`.
Published RD01/RD02/RD04 records and RD03 proposal/training remain historical
records; this clarification supplies the current interpretation without
retroactive pilot classification. RD03 stays proposed.

D04/D05/D10 still require exact policy text, evidence categories/adequacy,
precedence, authority, adjudication/annotation rules and handling of missing
policy. D06/D07 require statistical outcomes/contrasts/multiplicity, sample
size, missingness/admissibility and censoring decisions. D03 challenge policy
and D11 budgets/isolation/execution authorization remain separate and pending.
The 153-position qualification scope, arms and cost method are unchanged.

## Actual offline verification

| Command/check | Result |
|---|---|
| `git diff --check`; `git diff --name-only c56bf871`; `git ls-files --others --exclude-standard` compared with the above inventory | Passed: seven modified planning drafts and this new clarification only |
| `git diff --exit-code c56bf871 -- .` with exclusions for the seven modified drafts | Passed: 42,434 protected tracked paths unchanged, including original decision records, executable instruments/validators/schemas/manifests, evidence and preservation implementation |
| Read-only local Python checks of document references/anchors, current terminology, authority boundaries and frozen enum | Passed: 51 references resolve; all eight changed documents reference IE01 and distinct evidence-hold/reassessment meaning; five disposition strings unchanged |
| Byte comparisons against c56bf871 | Qualification scope/matrix and cost method unchanged; disposition/finding movement definitions and RD01-H2/H3/H4/H5 unchanged |
| `PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify` in original custody folder | Passed: 1,165 operator files, 4,699 v5 files, 36 command records, 40,538 preserved entries; zero changed/missing; zero provider calls; live qualification blocked |

The checks prompted explicit enum wording in the qualification notice;
no validation semantics changed. An initial overbroad terminology-check
expression matched historical pending-language in this clarification; it
was replaced by bounded checks of current drafts, not by editing history.
Custody verification is of the original local bundle, not certification of
previously sanitized public archives. No providers, evaluators, experiments,
additional scheduled positions or stage authorizations were invoked.
Documentation consistency cannot establish policy validity, reviewer
reliability or power.
**REQUIRES HUMAN DECISION** for unresolved methodology and execution.
