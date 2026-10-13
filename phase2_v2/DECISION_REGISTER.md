# V2 instrument decision register

This bounded increment is an **offline development instrument**, not a
preregistration, approved scoring policy, or pilot authorization.

**Research direction amended by human decision on 2026-10-13 (RD01):**
determine whether JEV challenges change AI security assessments, what changes,
in which direction, why, and whether those changes are evidence-justified.
Unsupported-assertion adoption is deferred to a potential future study.
See `RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md` for authority and traceability.
Only the objective is decided; methodological and execution choices remain
pending.

| ID | Matter | Development implementation | Human decision still required |
|---|---|---|---|
| D01 | Lifecycle equality | Reuse the unchanged v1 validator, including equality of the entire retained claim object and complete ID accounting | Approve clarified prompts for research use; any narrower equality definition requires a new contract |
| D02 | Judgment constructs | Separately typed source entailment, independent verification, and impact inference; each has a label, nullable score, rationale, and source quotes | Approve definitions, score interpretation, labels, and applicability rubric before research use |
| D03 | Thresholds/actions | No default experimental policy; only explicitly supplied `offline_fixture` rules are executable here | Approve versioned thresholds, boundary operators, action meanings, target populations, and missing-score handling |
| D04 | Primary outcomes | RD01 establishes assessment change and evidence justification as the research objective; no effectiveness computation or winner selection | Choose change estimand, substantive-change rubric, evidence-justification outcomes, contrasts, margins if applicable, multiplicity and stopping rules; unsupported-adoption study deferred |
| D05 | Adjudication | Authored fixtures are labeled synthetic, not independently adjudicated | Select independent reviewers, materiality/atomicity rubric, blinding, disagreement resolution, reference-set custody |
| D06 | Repetitions/statistics | No new matrix, repetitions, or sample size | Approve repetition count, power rationale, clustering, and analysis plan |
| D07 | Invalid outputs/missingness | Raw text retained; syntax/shape/lifecycle failure remains contract-invalid and cannot supply a child assessment | Decide descriptive adjudication versus primary admissibility and dependency-censoring analysis; no retroactive repairs |
| D08 | Experimental arms | Existing B0/C1/C2/C3/E1/E2/E3_NC/E3_CN names/roles preserved; no executor wiring | Any arm/comparison changes require explicit methodological approval |
| D09 | Judge dependence | No independent-judge claim; signals and policy decisions are distinct records | Approve judge identity/transport contract and treatment of shared SystemOne dependence |
| D10 | Evidence provenance | Supplied text never becomes authenticated Git or deployed-state evidence | Approve source population, provenance categories, independent-evidence requirements, and impact applicability |
| D11 | Launch/isolation | No provider adapter, execution entry point, or live-policy mode | Separate bounded-pilot authorization and isolation qualification; full 6,885-position experiment remains unauthorized |

All methodological and execution decisions remain pending for experimental
use; RD01 decides the research direction only. Implementation of
development mechanics does not resolve D02-D11. Test-only numeric constants
are not threshold recommendations and must not be fitted to pilot scores.
