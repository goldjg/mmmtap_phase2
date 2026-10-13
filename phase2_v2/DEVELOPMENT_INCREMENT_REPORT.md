# Bounded v2 instrument increment: development record

**Instrument:** `mmmtap-p2-instrument-v2.1-offline`.
**Readiness:** REQUIRES HUMAN DECISION for experimental use.
**Authorization:** offline development only; no v2 pilot or full experiment.

## Implementation inventory

All eight files below are new, under `phase2_v2/`. No pre-existing tracked
file, v1 code, prompt, instrument, manifest, evidence, seal, or first attempt
was edited. The existing v2 continuation component and its tests are also
unchanged.

| File | Purpose |
|---|---|
| `instrument.py` | Raw-preserving contract diagnostics; explicit prompt rendering; typed three-dimension judgments; bound requests/responses; test-only deterministic mapping |
| `prompts.v2.1.json` | Shared strict lifecycle instructions and unchanged arm roles, particularly C1/C2/C3 |
| `lifecycle_examples.v2.1.json` | Valid retained, revised metadata/confidence, withdrawn/added transitions |
| `challenge_fixtures.v2.1.json` | Authored benign, unsupported, conditional-impact and overclaimed-impact cases; arbitrary test-only policy |
| `test_instrument.py` | Contract, pilot compatibility, binding, policy, false-positive, dependency and network-denial regressions |
| `DECISION_REGISTER.md` | D01-D11 unresolved research decisions and development boundaries |
| `INSTRUMENT.md` | Root-cause rationale, comparability, APIs, gates and verification plan |
| `DEVELOPMENT_INCREMENT_REPORT.md` | Actual outcomes, inventory and limitations |

The implementation reuses the existing strict v1 assessment validator rather
than duplicating or relaxing it. Contract failures always have `parsed=None`;
raw text and diagnostic errors are retained, without repair or retry. Quote
membership remains separate from contract validity and semantic support.
Before a judge request, quote membership is required, matching the existing
Path B source-quote boundary. The generator's contract validity is not
retroactively changed by that judge-request gate.

Judge labels, nullable scores, rationale and quotations remain in an
immutable typed record with the original raw JSON. Policy decisions are
separate records with request/source/assessment bindings, raw-judge/policy
hashes, exact operators/thresholds and per-rule outcomes. Missing scores yield
explicit unresolved outcomes, not fabricated zero scores or a default pass.
No experimental policy is accepted by this development mapper.

## Commands and actual outcomes (2026-10-13)

Run from the Git worktree for `goldjg/mmmtap_phase2`, currently at:

```text
/home/prometheus/.copilot/session-state/0093f928-0a81-40b7-8bbb-e330208f4e42/files/publication-repo
```

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  phase2_v2.test_instrument \
  phase2_v2.test_continuation \
  tests.test_harness.AdapterTests.test_schema_and_change_accounting -v
git diff --exit-code HEAD -- .
```

**24 tests passed**, 4.428 seconds in the final combined invocation:
16 new instrument tests, 7 unchanged continuation tests, and the existing
v1 schema/change-accounting test. The Git comparison exited 0: all
pre-existing tracked contents remained unchanged. New files are local
development additions; this increment was not committed or pushed.

The local pre-publication scanner also exited 0 with no findings:

```sh
gitleaks dir phase2_v2 --redact=100 --no-banner --log-level=error
```

`gitleaks` was the already installed session-local binary, not an external
service; no new dependency or provider access was needed.

The pilot contract compatibility regression checked all **91 attempted
generator outputs**: 63 `ok` and 28 `schema_invalid`, with parsed results and
failure reasons identical to v1. The other **8 generator positions** were
`blocked_parent`, not regenerated. The full unchanged replay reconciled
**114 ok / 28 schema_invalid / 11 blocked_parent**, **142 reservations**,
**153 checkpoints**, **zero provider calls** and **no pilot file changes**.

The first development run failed only its hard-coded attempted-generator
count assertion (expected 88, observed 91); all individual comparisons
matched. The assertion was corrected to the actual generator partition
63/28/8. No pilot data, validity decisions, fixture score, or threshold was
modified to make that assertion pass.

In the separately preserved original custody directory
`/home/prometheus/git/mmmtap_phase2`:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify
```

**Passed:** 1,165 operator-sealed files; 4,699 v5 files and 36 command
records; 40,538 preserved entries, no changed/missing entries, zero provider
calls. Strict live qualification remains `blocked`. This verifies the
original local bundle, not a claim that previously redacted public copies
still satisfy original seals.

## Deterministic coverage

- Explicit whole-object retention, including confidence, limitations and
  quote changes; complete action accounting; invalid transitions/identity,
  duplicate claim/action IDs, extra keys, invalid numeric values, duplicate
  JSON keys, and malformed syntax remain failures.
- C1/C2/C3 receive the common contract and examples. Each existing arm still
  has its original role; controls cannot receive a challenge. Follow-ups
  cannot consume contract-invalid diagnostics or mismatched source/identity.
- Supported benign claims are not treated as source contradictions merely
  because independent verification is low. An explicit verification rule
  remains a verification review, not an `unsupported_claim` verdict.
- Qualified conditional impact can be justified as written without asserting
  compromise. Overclaimed actual compromise produces dimension-specific
  reviews under the authored test policy.
- A deliberately surprising low entailment score is preserved and can
  trigger a fallible review. The mapper never rewrites it to agree with the
  fixture label, nor interprets its challenge as ground truth.
- Bound, reordered multi-claim responses map by claim ID; missing dimensions,
  missing/duplicate IDs, invalid labels/quotes, wrong request identity,
  mutated source/request and invalid policy rules fail explicitly.
- Threshold ties, `lt` versus `ge`, null scores and `not_applicable` outcomes
  are explicit; no empirical threshold choice is made.
- A child requires every assessment/challenge parent to have a
  caller-verified acceptable `ok` outcome. Missing parents defer;
  schema-invalid/blocked parents prevent execution; unverified or unknown
  states stop. Contract compliance alone cannot release a child.
- The fixture pipeline succeeds with socket creation prohibited. No adapters,
  provider clients, subprocess execution, retry, or stage launcher are added.

## Evidence limitations and unresolved issues

Fixtures and scores are authored mechanics controls, **not independently
adjudicated ground truth**, actual JEV judgments, calibration data, security
correctness evidence, or evidence of reduced attrition/causal effectiveness.
The numeric 0.5 fixture threshold is arbitrary and not a recommendation.
The new wording and three constructs are development proposals requiring
experimental instrument approval; no threshold/action/outcome is
preregistered by these tests.

The pure planner's verification input remains caller-attested. This increment
does not implement a durable controller or authenticate checkpoints for
pending live execution. No new arms, sample size, repetition count, policy
success criteria, invalid-output admissibility or statistical analysis plan
is selected. No independent judge is introduced. Source provenance is
explicitly supplied, not independently authenticated by this instrument.

Human decisions remain pending in `DECISION_REGISTER.md`, especially primary
outcomes, adjudication, label/score interpretation, applicability, thresholds,
repetitions/power, dependency censoring and invalid outputs. Strict isolation
and provider identity/transport qualification remain separate blockers.
**The v2 pilot and 6,885-position experiment are not authorized.**
