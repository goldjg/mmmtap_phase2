# V2 instrument decision register

This bounded increment is an **offline development instrument**, not a
preregistration, approved scoring policy, or pilot authorization.

**Research direction amended by human decision on 2026-10-13 (RD01):**
determine whether JEV challenges change AI security assessments, what changes,
in which direction, why, and whether those changes are evidence-justified.
Unsupported-assertion adoption is deferred to a potential future study.
See `RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md` for authority and traceability.
RD02 supplements it: **DECIDED BY PI**, any change in baseline-to-final
disposition is an outcome change, even with identical security claims.
Material finding movement and evidence justification of each family are
separately measured. Exact labels/pairs and no-movement outcomes are retained;
no ordinal scale or automatic improvement is implied. See
`OUTCOME_MOVEMENT_AMENDMENT.v2.1-RD02.md`. This is not blanket D04 approval;
remaining methodological and execution choices are pending.

| ID | Matter | Development implementation | Human decision still required |
|---|---|---|---|
| D01 | Lifecycle equality | Reuse the unchanged v1 validator, including equality of the entire retained claim object and complete ID accounting | Approve clarified prompts for research use; any narrower equality definition requires a new contract |
| D02 | Judgment constructs | Separately typed source entailment, independent verification, and impact inference; each has a label, nullable score, rationale, and source quotes | Approve definitions, score interpretation, labels, and applicability rubric before research use |
| D03 | Thresholds/actions | No default experimental policy; only explicitly supplied `offline_fixture` rules are executable here | Approve versioned thresholds, boundary operators, action meanings, target populations, and missing-score handling |
| D04 | Outcome families / primary outcomes | RD01 objective and RD02 disposition-movement principle DECIDED BY PI; disposition and material finding movements separately reported, justification independent of movement | Operational scoring/materiality, justification rules, estimands, inferentially primary outcomes/contrasts, multiplicity, margins if applicable and stops pending; no combined endpoint or co-primary declaration; adoption study deferred |
| D05 | Adjudication | Authored fixtures are labeled synthetic, not independently adjudicated | Select independent reviewers, materiality/atomicity rubric, blinding, disagreement resolution, reference-set custody |
| D06 | Repetitions/statistics | No new matrix, repetitions, or sample size | Approve repetition count, power rationale, clustering, and analysis plan |
| D07 | Invalid outputs/missingness | Raw text retained; syntax/shape/lifecycle failure remains contract-invalid and cannot supply a child assessment | Decide descriptive adjudication versus primary admissibility and dependency-censoring analysis; no retroactive repairs |
| D08 | Experimental arms | Existing B0/C1/C2/C3/E1/E2/E3_NC/E3_CN names/roles preserved; no executor wiring | Any arm/comparison changes require explicit methodological approval |
| D09 | Judge dependence | No independent-judge claim; signals and policy decisions are distinct records | Approve judge identity/transport contract and treatment of shared SystemOne dependence |
| D10 | Evidence provenance | Supplied text never becomes authenticated Git or deployed-state evidence | Approve source population, provenance categories, independent-evidence requirements, and impact applicability |
| D11 | Launch/isolation | No provider adapter, execution entry point, or live-policy mode | Separate bounded-pilot authorization and isolation qualification; full 6,885-position experiment remains unauthorized |

All methodological and execution decisions remain pending for experimental
use except the recorded RD01 direction and RD02 measurement principles.
No statistical plan or execution approval follows. Implementation of
development mechanics does not resolve D02-D11. Test-only numeric constants
are not threshold recommendations and must not be fitted to pilot scores.
