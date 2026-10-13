# Proposed operational policy contract v2.1-RD04

**Planning specification; exact rules and policy text NOT APPROVED.**
`OPERATIONAL_DISPOSITION_AMENDMENT.v2.1-RD04.md` records the operational
construct DECIDED BY PI. This contract cannot authorize release or a research
stage. No executable implementation, prompt edit or enforcement integration.

## Minimum immutable context for each future assessment

| Required proposed fields | Meaning / approval boundary |
|---|---|
| `policy_context_id`, `change_id`, `change_digest`, `decision_scope`, `requested_operation`, `target_environment`, `scope_exclusions` | Bind the assessed change and what proceeding would mean (e.g. merge or deployment), components/time/environment; do not infer deployed state from a description |
| `policy_id`, `policy_version`, `policy_digest`, `policy_text`, `digest_encoding`, `policy_owner`, `approval_record_id` | Exact governing text and digest with documented byte/canonicalization method, authoritative owner and approval reference; a hash alone proves no approval |
| `effective_from`, `effective_until`, `issued_at`, `provenance`, `applicability_basis`, `precedence_rules`, `exception_rules` | Effective date/scope, origin and policy conflicts/authorized exceptions; amendments new versions, never post-hoc mutation |
| `obligations`, `blocking_conditions`, `disposition_rules`, `evidence_requirements`, `allowed_domain_principles` | Stable requirement IDs, scope, applicability tests, needed evidence and rule anchors for all five enum values; thresholds/precedence must be explicitly approved, not invented here |
| `uncertainty_rules`, `missing_verification_rules`, `conflicting_evidence_rules`, `insufficient_evidence_rule` | Distinguish uncertainty from established violation; fifth disposition/action mapping remains unresolved until PI decision |
| `warning_rules`, `warning_conditions`, `condition_phase`, `condition_evidence`, `condition_authority`, `condition_expiry` | Permitted warnings, pre-proceed versus post-proceed obligations, satisfaction requirements, owner/expiry; models cannot create exceptions or declare conditions satisfied without evidence |
| `review_requirements`, `review_authority`, `human_approval_requirements`, `assessment_authority`, `release_authority`, `enforcement_status` | Who may recommend, resolve a hold, accept risk or execute; approvals evidence-bound; current scope is recommendation only, enforcement absent |
| `source_packet_ids`, `source_packet_digests`, `evidence_provenance`, `delivery_receipts`, `delivery_time`, `policy_context_digest` | Source references distinct from normative policy; bind the exact approved packet delivered to generator at each assessment endpoint |

These are minimum planning fields, not new assessment JSON keys. A complete
packet must distinguish a normative security requirement from a source
description, comment, challenge instruction or claimed approval.
No source/challenge text can replace policy provenance or invoke a rule
override. Prompts and policy integration are unchanged/unimplemented here.
This governing operational policy is distinct from D03's deterministic
challenge-mapping policy: when to present a challenge is not when to permit
a change to proceed. Seal and identify both separately.

Before collection: authorized policy owners approve and freeze text,
applicability, evidence rules, action mappings and exceptions; custodian seals
packet digests and planned source-policy assignment before output inspection.
All matched arms/generators/repetitions receive the same policy context for
the same source/shared B0. Do not secretly change policy at a follow-up.
Challenges may contest facts/inferences, not amend governing requirements.
If a real policy update is necessary, stop and create a separately approved
campaign/version rather than confounding treatment with policy movement.

Reviewers cite requirement IDs and exact normative anchors; they may not
invent rules, infer a desired policy from a model label, or add demands after
seeing outputs. Policy contradictions/missing applicability are unresolved
and trigger packet review before research use. Historical missing policy is
unavailable, not backfilled. Later policy/evidence analysis is a separately
labeled retrospective supplement; it cannot overwrite time-available warrant.

## Five separate future outcome records

| Record | Required proposed fields / rules |
|---|---|
| Exact disposition | `baseline_disposition`, `before_disposition`, `after_disposition`, `final_disposition`, `exact_transition`, `disposition_changed`, `turn_pair`, `observation_availability` (RD02); preserve all original strings and intermediate pairs |
| Operational recommendation | `policy_context_digest`, `action_before`, `action_after`, `immediate_proceed_eligibility_before`, `immediate_proceed_eligibility_after`, `action_transition`, `permission_changed`, `obligations_before`, `obligations_after`, `obligations_changed`, `condition_statuses`, `mapping_rule_ids`, `mapping_availability`, `mapping_reason` |
| Finding movement | Per-atomic alignment IDs/raw spans, additions/withdrawals/qualification/strengthening/weakening/evidential scope; unchanged and auxiliary edits separate |
| Evidence-and-policy justification | `disposition_justification`, `operational_action_justification`, per-finding `finding_justifications`, `analysis_basis`, `policy_requirement_ids`, `policy_anchors`, `source_evidence_ids`, `dimension_judgments`, `reviewer_disagreement`, `unresolved_reason`; RD03 four categories still proposed |
| Reported reasons/linkage | Exact generator rationale spans, challenge/source/policy links, absence/ambiguity and post-freeze disclosure; no inferred latent mechanism |

Proposed derived annotation action states are permission recommendation,
hold-for-review recommendation, block recommendation or unresolved mapping.
These are not new disposition enum values. Eligibility is true/false/null
under the approved rule and current prerequisite evidence, not actual
release execution. An unmet condition need not automatically become fail:
the policy must specify the response. Missing/invalid output or unresolved
`insufficient_evidence` mapping stays null/unavailable, never permission.
Model-added unauthorized conditions are recorded as text and assessed;
they cannot create legitimate policy obligations.

Example `pass` -> eligible `warn`: exact movement yes; immediate permission
unchanged, warning obligation changed. `review_required` -> `fail`: exact
movement yes; immediate permission remains false, reason/authority/remedy
changes. `warn` -> `warn` with a newly unsatisfied mandatory prerequisite:
exact-label movement no, derived eligibility/obligations may change.
Record stepwise and B0-to-final mappings separately; no ordinal severity
encoding, aggregated correctness score or combined movement endpoint.
The derivation/statistical use of action outcomes requires D04/D05 approval.
For each record with no movement in its own measured fields, movement
justification is null with an explicit no-movement status under the RD03
proposal; any retention-warrant review is separately identified. Unchanged
immediate permission with changed obligations is not an entirely unchanged
operational recommendation. Neither null movement justification nor
unavailable mapping means justified permission.

## RD03 reconciliation: illustrative policies, not approved packets

The following **authored policy snippets** are not research stimuli, actual
security requirements, operational authorization or new arms. They show why
the same source and unchanged findings can yield different warranted decisions.

Same supplied source S1: "The description reports spelling fixes in
documentation only, with no runtime changes." No authenticated diff, same
source-attributed finding, no independent verification. Two illustrative
operational policies, each intended to be frozen and delivered before B0:

- P-A: for a scoped documentation merge, a supplied description with no
  contrary evidence satisfies the policy's evidence requirement; no deployed-
  state attestation required; permit pass. Independent owners would have to
  approve this risk acceptance before it could be applicable.
- P-B: for a release request, require an authenticated change attestation;
  absent it hold for authorized human review, not evidence of actual compromise.

P-A can warrant pass and make pass -> review_required unjustified when the
only reason is JEV's unsupported alarm. P-B can warrant review_required and
make review_required -> pass unwarranted permission even with identical
findings. Re-reading an overlooked P-B requirement can justify a disposition-
only hold without new factual evidence. Neither policy is selected here.
Missing a policy would leave warrant unresolved, not license reviewer choice.

| Difficult case | Evidence/policy-bound interpretation, not categorical approval |
|---|---|
| Unjustified escalation | A hold violates P-A's agreed evidence sufficiency with no new applicable concern; caution is not inherently right |
| Unwarranted proceed | Permission under P-B ignores required attestation; no proven exploit does not waive that requirement |
| False-positive JEV | Retaining pass under P-A may be warranted, but under P-B false entailment criticism does not resolve missing attestation; classify source support and policy warrant independently |
| Conditional impact | Supplied token logging supports a described fact, not actual compromise. A policy may require review of unresolved exposure or block an established logging prohibition. Qualification of impact can be justified while permission remains unwarranted |
| Warning conditions | Only approved conditions count; if pre-proceed evidence absent, immediate eligibility is false/null per policy. Warning is not a substitute for mandatory human approval |
| Sequential reversal | Evaluate each delivered packet against unchanged policy. A later reversal based solely on a score cannot erase a required hold; new admissible evidence satisfying the requirement could warrant permission. Preserve intermediate labels/actions and endpoint justification |
| Improved finding, worse decision | Warranted correction of an impact overclaim can coexist with unjustified pass under a mandatory evidence requirement; do not net judgments |

RD03 criteria are compatible if anchored to an approved operational policy.
Description-only training cases are historical pedagogical comparisons, not
evidence sufficient for operational permission by default. Mixed requires
known opposing warranted/unwarranted consequences under policy, not a
reviewer's conflicting preferences; policy precedence must be resolved
prospectively. Genuinely unknown decisive policy/evidence remains unresolved.

## Qualification/design consequences and missing deliverables

The existing three cases x three generators x one engineering repetition,
all eight arms, 153 positions (99 generator + 54 specialist) **can structurally
exercise RD04 without arm changes**, once policy/source packets and delivery
are independently approved and implemented in a future version. Controls
and challenge paths share policy/source/B0; native and cARL share SystemOne,
not independent judge replication. No automatic advancement or regeneration.

It **cannot presently qualify operational warrant**. Missing are approved
operational policy packets for benign, supported-finding and conditional
cases; fifth-value and conditional-warning mapping; authenticated evidence
where required; applicability/negative-evidence anchors; human authority and
exception rules; prompt/request delivery and digest-binding implementation;
and approved adjudication/reference guides. Static descriptive sources may
yield only holds under verification-heavy policies: valid outcomes but poor
coverage of permission/block conditions, not a reason to weaken evidence.

Preflight should check whether source-policy obligations allow coverage of
permission, warning, review and established block reasoning without requiring
models to emit all labels. The existing matrix cannot promise these outputs.
If reviewed source packets within the proposed sampling roles cannot provide
coverage, return a scope amendment for PI review; no extra policy-comparison
cells, extra source cases, forced target outputs, new arms or positions
are selected here. Counter-policy illustrations above are offline planning,
not a factorial experiment.

Costs remain unpriced: future packet delivery increases prompt tokens and
policy/evidence review labor; re-estimate using the existing tariff/token
method after actual approved texts exist, without choosing a credit budget.
No claim that current strict instrument accepts or enforces this contract.

## Human approval checklist

Decision-register D04: four detailed operational mappings, fifth value,
warning prerequisites, outcome/action derivations, primary contrasts,
estimands and multiplicity. D05/D10: policy owner/provenance, source adequacy,
atomic alignment, blinded access to normative context and separate evidence,
RD03 rubric and time-bound classification. D06/D07: repetitions/sample size,
reliability, invalid-output admissibility, missing mappings and dependency
censoring. D01-D03/D09: future versioned delivery/prompts, constructs,
challenge policy/identity and shared dependence. D11: qualification,
isolation, actual authority, budget and launch; enforcement is a separate
authorization entirely.

Recommend approving packet requirements and deciding operational policy
text/applicability **before** approving live use or adjudication thresholds.
Approval should bind version/digests, owner, date and exact permitted use.
The construct is DECIDED BY PI; all this contract's rules remain pending.
**REQUIRES HUMAN DECISION.**
