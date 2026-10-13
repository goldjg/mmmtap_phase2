# Offline assessment/challenge instrument v2.1

**Purpose:** implement the bounded development increment requested after the
v1 post-pilot review. No live integration, provider calls, pilot, or full run.
See `DECISION_REGISTER.md` for unresolved methodological decisions.

## Changes, rationale, and comparability

The confirmed defects are described in `POST_PILOT_ROOT_CAUSE.md`: vague
lifecycle instructions with exact retained-object/accounting checks,
control-arm attrition, and a single support score mixing entailment,
verification, and impact. This increment:

- reuses `phase2.core.assessment` unchanged and adds raw-preserving diagnostic
  separation of syntax, shape, and lifecycle failures; quote membership is a
  separate audit, not proof of entailment or a relaxed validity rule;
- renders the same generator-arm tasks with a common explicit lifecycle
  contract and valid retained/revised/withdrawn/added examples, including on
  each C1/C2/C3 follow-up;
- creates separately typed judgment records and source/assessment-bound
  requests, without adapting the frozen JEV or cARL implementation;
- requires a caller-supplied test-only policy, preserving judge labels/scores
  separately from per-rule evaluations and untrusted challenges. Missing
  scores are reported as unresolved, never silently coerced to zero;
- supplies authored positive/negative fixtures and deterministic tests.

Prompt wording and the judgment question set are new instruments: do not pool
them with v1, reinterpret v1 failures, or claim improved completion/correctness.
The existing arms are not redesigned. Scores concern each dimension's
proposition, not a probability that a model-selected label is correct; they
are not calibrated probabilities or independent adjudication. A conditional
impact assertion must be judged as written, without pretending it asserts
actual compromise.

## APIs and safety boundary

`instrument.py` exposes offline functions only. `inspect_assessment` returns
raw text, diagnostics, and `parsed=None` for every contract failure.
`render_assessment_prompt` requires the correct B0/follow-up prior context and
checks the supplied source digest. `build_judge_request` takes a contract-valid
assessment diagnostic, separately supplied provenance, and produces three
questions per claim. `parse_judgments` enforces exact fields, claim coverage,
request binding, labels, scores, and quote membership; it preserves raw text.
`map_challenges` accepts only an explicit `offline_fixture` policy; no
experimental threshold or live execution mode exists.

A judge's accepted JSON is still fallible. Exact quote membership is not
entailment; absence of independent verification is not source contradiction.
Every challenge names its dimension/rule and remains untrusted. Mapping
cannot authorize a deployment or an experiment. A `no_challenge` mapping
does not mean an assessment is correct.

Follow-up rendering accepts a contract-valid `AssessmentDiagnostic`, not an
arbitrary prior dictionary. Raw/parsed and source bindings are checked again;
invalid lifecycle diagnostics cannot be used as prior assessments. This is
not checkpoint integrity verification or experimental output adjudication.

The continuation planner still needs caller-verified checkpoint integrity and
lineage. Contract compliance is necessary but insufficient for parent
eligibility: every required parent must have a verified `ok` terminal outcome.
The tests demonstrate this for both assessment and challenge dependencies.
There is no durable/live executor or automatic stage transition.

## Verification plan

Tests will validate all lifecycle examples with the unchanged v1 validator;
check syntax/shape/lifecycle failures and preserve raw text; compare the
91 attempted pilot generator positions against v1 contract results without
repair and account separately for the 8 blocked generator positions;
check typed judgment identity/coverage/score rules; exercise explicit policy
boundaries, missing-score and wrong-dimension false positives; and confirm
multi-parent dependencies and exact 153-position read-only replay.

Actual commands, outcomes, inventory, and remaining limitations are recorded
in `DEVELOPMENT_INCREMENT_REPORT.md` after execution. The public repository
is sanitized: original seals do not verify its previously redacted files.
Preservation during this increment is checked against the existing Git
snapshot, separately from the original local custody bundle.
