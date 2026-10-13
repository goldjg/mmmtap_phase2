# RD05 offline development qualification report v1

**OFFLINE DEVELOPMENT COMPLETE** for deterministic package checks only.
**RD03 AND EXPERIMENTAL READINESS STILL REQUIRE HUMAN DECISION.**
Baseline main: `cf9a95c33999d9cd7510da7057bfb77ad02a54f6`.
No independent reviewers have completed this exercise. We have established
that evidence packets, a toy policy and segregated materials can be built and
checked reproducibly, **not** that human adjudicators consistently agree or
that RD03 is scientifically valid.

## Inventory and byte custody

All additions are under `phase2_v2/rd05_offline/`; no existing tracked file
is changed. [inventory.v1.json](inventory.v1.json) lists every other package
file with exact byte length and SHA-256, including this report. The inventory
excludes only itself to avoid a recursive hash; the Git commit binds it.
Canonical object bindings use sorted keys, ASCII JSON and compact separators,
no NaN/Infinity; file hashes use exact bytes, not canonical objects.
The validator distinguishes those two digest encodings.

| File(s) | Role |
|---|---|
| `__init__.py`, `tool.py` | Separate offline module; policy partition, binding, export and hash checks; no experimental instrument changes |
| `policy.v1.json` | Fictional governing policy, five frozen dispositions, evidence obligations and explicit precedence |
| `authored.py` | Private authored synthetic case definitions and suggested discussion labels, never reviewer stimuli |
| `test_tool.py` | Deterministic mutation, coverage, export, no-network and reproducibility regressions |
| `README.md`, `REPORT.md`, `inventory.v1.json` | Instructions, actual results, limitations, byte inventory |
| `exercise.v1/claims.json` | Blinded content/source/evidence stages; policy disclosed, dispositions/rationales/answers hidden |
| `exercise.v1/pairs.json` | Later exact dispositions/conditions; opaque IDs only |
| `exercise.v1/reviewer_A.json`, `exercise.v1/reviewer_B.json` | Blank independent templates; separate dimensions, movement, warrant and unresolved records |
| `exercise.v1/resolution.json` | Blank disagreement/resolution/amendment template |
| `exercise.v1/custodian/fixtures.json` | Original exact synthetic source, step evidence, assessments and bindings |
| `exercise.v1/custodian/references.json` | Authored private suggestions, mixed/indeterminate discussion, not ground truth |
| `exercise.v1/custodian/identity_key.json` | Blind-ID join to case titles and author metadata |
| `exercise.v1/custodian/linkage.json` | Challenge/rationale disclosure only after independent warrant freeze |

The source repository is public: "private" means segregated distribution,
not secret Git storage. Distribute only staged reviewer files. No labels,
titles, identity metadata or challenge expectations enter blinded content
exports; the normative governing policy itself is necessarily visible.
Hashes/opaque IDs do not promise resistance to a reviewer consulting this
repository. Record prior exposure and suspected unblinding.

## Deterministic policy qualification

Every one of the 16 boolean predicate states selects exactly one primary
recommendation under explicit precedence; independent conditions can trigger
multiple subordinate obligations. Tests reject missing primary coverage,
ambiguous predicate values, wrong precedence, invalid authorities, unknown
evidence and wrong rule/resolution bindings. This is exhaustive **within the
toy predicate space**, not a natural-language policy correctness proof.

| Rule | Selected primary endpoints | Triggered obligation endpoints | Resolution |
|---|---:|---:|---|
| R-PASS | 11 | — | Fictional proceed recommendation only |
| R-WARN | 2 | 3 | Record authorised coverage warning |
| R-EVIDENCE | 8 | 10 | Obtain evidence then reassess, not review or violation |
| R-REVIEW | 2 | 4 | Named authorised human decision then reassess |
| R-BLOCK | 8 | 8 | Established credential-logging prohibition, remediation then reassess |
| Total | 31 | 25 | Overlapping subordinate triggers; endpoint counts are not independent observations or accuracy |

Counts describe policy application to supplied synthetic facts, not the
model-like assessment's agreement with policy and not human RD03 labels.
Observed fixture dispositions deliberately include errors. Rules are
toy governing policy, never JEV/cARL challenge mapping. No challenge thresholds
or challenge adapters are implemented. Scoped evidence coverage is separate
from test-result correctness: other substantive test failures/requirements
are unmodeled and require a new synthetic policy version, not a default
interpretation under this one.

## Trajectory and classification coverage

Fourteen authored trajectories, 31 endpoints, 17 adjacent transitions.
Three-step examples also retain B0-to-final pairs; none of their correlated
steps is an independent repetition. This is not the prior Q0 six-case plan
or any modification of the Q1 153-position matrix.

| ID (custodian only) | Coverage / exact disposition trajectory |
|---|---|
| T01 | Correct permission and false-positive rejection: pass -> pass |
| T02 | Authorised warning: pass -> warn, recorded warning obligation |
| T03 | Missing evidence without violation: fail -> insufficient_evidence -> pass after new scoped evidence |
| T04 | Mandatory human review: pass -> review_required -> pass after named approval |
| T05 | Evidenced blocking violation: warn -> fail |
| T06 | False-positive escalation: pass -> review_required with unchanged warranted source-attributed findings |
| T07 | Unwarranted challenged permission: insufficient_evidence -> pass with mandatory report still absent |
| T08 | Correct conditional-impact qualification, material finding changes but fail -> fail under unchanged logging prohibition |
| T09 | Scoped finding correction without disposition movement: pass -> pass |
| T10 | Disposition-only review-to-evidence-hold correction: review_required -> insufficient_evidence, same findings and same missing report |
| T11 | Sequential movement/reversal: pass -> review_required -> pass; final unchanged does not erase intermediate movement |
| T12 | Established violation outranks missing evidence, review trigger and warning: review_required -> fail; subordinate obligations retained |
| T13 | Candidate mixed finding revision with fail -> fail; split justified correction and unjustified premise loss if atomicity permits |
| T14 | Indeterminate artifact/scope alignment: insufficient_evidence -> insufficient_evidence; finding warrant unresolved, not forced binary |

Authored references include justified, unjustified, candidate mixed and
unresolved finding/transition discussions, plus null no-movement records.
Mixed is not made an automatic disposition-plus-finding composite. Source
entailment, independent verification and impact inference have distinct blank
reviewer fields; no algorithm fills them from scores, templates or reference
suggestions. No agreement-with-author accuracy metric is computed.

## Actual commands, outcomes and corrections

From the public Git worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  phase2_v2.rd05_offline.test_tool \
  phase2_v2.test_instrument phase2_v2.test_continuation \
  tests.test_harness.AdapterTests.test_schema_and_change_accounting -v
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool build \
  phase2_v2/rd05_offline/exercise.v1
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool verify \
  phase2_v2/rd05_offline/exercise.v1
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool inventory \
  phase2_v2/rd05_offline
PYTHONDONTWRITEBYTECODE=1 python -m phase2_v2.rd05_offline.tool verify-inventory \
  phase2_v2/rd05_offline
git diff --check
git diff --exit-code cf9a95c3 -- .
```

Actual final results are appended below before commit. The initial new-only
run had 17 tests with one failure: a blinding assertion searched the entire
claims export for "disposition", erroneously including the necessarily
visible policy-rule vocabulary. It was scoped to reviewer endpoint records.
No outcome/reference was changed to hide that error.

The first combined run passed 41 tests (17 new plus 24 existing) and both
build/verify commands. Subsequent edge review strengthened exact export-file
and hash inventories, warning/template tests and distinguished report coverage
from test success so missing coverage is not misclassified as test violation.
Generated new-only masters were rebuilt; no preserved output was touched.
T03/T04 include explicit synthetic reassessments; T10 keeps the same missing
evidence at both endpoints, avoiding an unintended evidence-availability
confound. These are authored development corrections, not repaired first
attempts or empirical findings.

## Unmeasured assumptions and human gates

Synthetic authentication/adequacy, a small known predicate space and complete
change-bound artifact declarations are assumptions of this exercise.
Natural-language entailment, real provenance/authenticity, negative-evidence
coverage, complex exceptions, real policy applicability and ambiguous
organisational obligations are not validated. No credentials/production
policy are used. Build reproducibility cannot establish reviewer feasibility.

Before any human dry run, D04/D05/D10 need explicit approval of operational
policy use, adequacy and atomicity, allowed domain principles, ambiguity and
mixed handling, reviewer independence/staffing and staged disclosure. D06/D07
need review units, agreement method, sample/repetition choices, availability,
invalid-output and censoring treatment; no empirical thresholds or primary
estimands are selected. D03 challenge policy and D11 live/executor/budget
approvals remain entirely separate.

[README.md](README.md) proposes raw pre-resolution agreement, confusion
tables, unresolved/availability rates, alignment disagreement and resolver/
exposure counts separately by dimension and outcome family. Any chance-
corrected statistic, uncertainty method and numerical acceptance criterion
needs human/statistician approval. None is implemented as a success gate.
Qualitative acceptance should demand reconstructed time-available evidence,
independent frozen sheets, anchored rationale, exact intermediate/final
pairs, no label leakage and no forced consensus. **Zero reviewers completed;
reviewer reliability unestablished.**

Original custody checks are separate from this public sanitized repository.
No provider, JEV, model, external evaluator, experiment or live stage is
invoked/authorised. Existing instruments, validators, prompts, schemas,
manifests, seals, first attempts and RD01/RD02/RD04/IE01 remain unchanged.

## Final verification record (2026-10-13)

| Check | Actual result |
|---|---|
| Final combined unittest command above (`-q` used to bound output) | **45 tests passed**, 7.370 seconds: 21 new RD05 tests and 24 unchanged instrument/continuation/v1 tests |
| Build and verify generated exercise masters | Passed: 14 trajectories, 31 endpoints; all 16 predicate states select one primary rule under precedence; every triggered obligation retained and reported |
| Network/process denial regression | Build and verify succeeded while socket connect/create_connection, URL opening and subprocess creation were mocked to raise; every denied-call mock remained uncalled |
| Reproducible double-build regression | Exact generated file bytes identical in independent temporary output directories; existing output directory cannot be overwritten |
| Export regressions | Private answers/titles/metadata absent from staged stimuli; tampered exports, extra public answer files, symlinks and missing files rejected; blank independent templates retain separate dimensions/movement/warrant |
| `git diff --exit-code cf9a95c3 -- .` | Passed: all 42,442 pre-existing tracked paths unchanged, including proposed qualification matrix and all historical decisions |
| Original `PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify` | Passed: 1,165 operator-sealed files, 4,699 v5-sealed files, 36 command records, 40,538 preserved entries; no changed/missing entries; zero provider calls; strict live qualification blocked |

Final publication checks: exact 17-file addition allowlist (16 content files
plus inventory); 11 local Markdown references including inventory resolve;
local `gitleaks dir phase2_v2/rd05_offline --redact=100 --no-banner
--log-level=error` exits 0 with no findings. Inventory creation/verification
commands pass with all 16 content-file byte hashes matching. No annotation
sheet has been filled by a human, and no synthetic suggestion is certified
as correct.

Final policy-rule hardening made evidence, review and warning triggers
independent of blocking so precedence can select the primary
recommendation while retaining every triggered subordinate obligation.
During this adjustment, one test run found an incorrect validator expectation
that R-PASS required absent evidence; corrected to require evidence. A second
run found its coverage test comparing 31 selected recommendations with 25
non-pass trigger records; corrected to assert their distinct coverage and
test multi-trigger preservation directly. The final tests and generated
exercise below run against this corrected model.
