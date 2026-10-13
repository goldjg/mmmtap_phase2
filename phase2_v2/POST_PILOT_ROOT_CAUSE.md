# Phase 2 v1 post-pilot root-cause review

**Status:** evidence review of the completed, bounded pilot. This report does
not authorize a v2 pilot or the 6,885-position experiment. No v1 evidence was
repaired, reinterpreted as valid, or regenerated.

## Evidence scope and identity

The review used the frozen pilot package at `operator_runs_v1/pilot/`, its
manifest, ledger, completion record, final summary, and all 153 checkpoint
directories, including `intent.json`, `payload.json`, `raw.json`, and
`result.json`. The reported identifier
`3062def66204e79ec8bcc3b7565f3de681b5dcb411bee06a6817fb04152ddfc1` is the
canonical manifest identity in `manifest.json`; the manifest file's byte
SHA-256 is `e5759986…` (also recorded in the preserved package seal). These
are different digests and should not be substituted for one another.

The v2 read-only auditor independently reconciles the manifest/job identities,
append-only ledger hash chain, attempt reservations, checkpoint/artifact
hashes, parent bindings, completion anchor, status totals, and final summary.
The detailed test also inventories every pilot file before and after replay.
The frozen package verifier separately checks the operator seals and preserved
source inventory.

## Confirmed pilot results

| Measure | Independently verified result | Primary evidence |
|---|---:|---|
| Scheduled positions / terminal checkpoints | 153 / 153 | `manifest.json` jobs; `completion.json`; `summary-000335.json`; checkpoint set |
| `ok` | 114 | checkpoint `result.json` statuses; ledger completion events; final summary |
| `schema_invalid` | 28 | checkpoint statuses and reasons |
| `blocked_parent` | 11 | checkpoint statuses and dependency lineage |
| Adapter-attempt reservations | 142 | each checkpoint `intent.json`; `ledger.jsonl`; completion and summary |
| Automatic advancement | None | `completion.json` and `summary-000335.json` record no automatic next stage |
| Strict isolation | Not qualified | manifest execution profile and checkpoints state `satisfies_strict_isolation=false` |
| Correctness adjudication | Not performed | each checkpoint records `correctness: not_adjudicated` |

The pilot was classified as
`lower_assurance_operator_supervised_research`. It completed the scheduled
pilot matrix, not the primary experiment. A terminal checkpoint is an
accounted-for outcome, not a claim that the output is correct or that the
study qualified.

## Schema attrition

The frozen parser (`forensic_remediation_v1/v5/instruments/software_source/mmmtap_phase2/phase2/core.py:208-267`)
records these 28 failures:

| Failure reason | Count | Interpretation limited to |
|---|---:|---|
| `retained_claim_was_changed` | 15 | A claim marked retained did not match its prior claim object exactly |
| `incomplete_change_accounting` | 12 | Not every prior/current claim ID had one lifecycle action |
| `assessment_top_level_shape` | 1 | The object did not have exactly the required top-level keys |

Inspecting the preserved raw responses and their parent assessments shows
that the 15 retained-claim failures were not all claim-text changes: 12 also
changed the `claim` text, all 15 changed `limitations`, and 2 changed
`confidence` (these field counts overlap). Across the 12 incomplete-accounting
failures there were 18 omitted lifecycle-action IDs and no unexpected action
IDs. The top-level failure had an extra `uncertainties_note` key in addition
to the required `uncertainties` field. For example, preserved checkpoint
`9200b570…/result.json` has reason `retained_claim_was_changed`; its raw
response and parent show the claim text and limitations changed while its
action was `retained`. Checkpoint `2efccee5…/result.json` has
`incomplete_change_accounting` and omits the only prior claim's action.

Attrition by control arm is also confirmed:

| Arm | Valid / scheduled | Notes |
|---|---:|---|
| B0 | 9 / 9 | No lifecycle comparison required |
| C1 | 4 / 9 | One invalid response is the top-level-shape failure |
| C2 | 1 / 9 | Re-expression prompt still receives lifecycle validation |
| C3 | 7 / 18 | Only 3 / 9 two-turn chains completed both turns |

The manifest's exact assessment shape and validator require a closed set of
keys, exact claim fields, exact object equality for `retained`, and complete
accounting of the union of prior/current claim IDs. The prompts in
`prompts.v1.json` say to retain/revise/withdraw/add findings for source-grounded
reasons, but do not define the equality rule, explicitly require one action
for every prior and current ID, or show a valid retained-versus-revised
example. C2 asks for a second assessment and clear re-expression without
stating those lifecycle obligations in its own text. C3 names a matched
neutral control but likewise does not spell out the exact accounting rule.
The validator's requirements are deterministic and auditable; their
underspecified relationship to the prompts is the demonstrated defect.

**Root-cause assessment:** both prompt clarity and the strict contract
contributed. Some raw outputs also failed to follow the presented shape or
instructions, so generator behavior contributed to observed attrition. The
evidence does not establish that the contract should be relaxed. In
particular, treating changes to claim wording as revision is sensible, while
whether changes only to confidence, evidence, or limitations should require a
`revised` action is a methodological definition that was not made explicit.
No invalid response is thereby scientifically or semantically wrong; the
schema result only says the response did not satisfy the frozen output
contract. The retained raw output remains available for a separately labeled
descriptive adjudication, not for silent conversion to a valid assessment.

Because C1/C2/C3 failures depend on generated first turns and block
downstream positions, the missingness is dependency-linked and plausibly
non-random. The observed arm-specific validity rates therefore cannot be
treated as matched, complete comparisons, nor repaired by excluding failures
without a preregistered missingness analysis.

## JEV / cARL-JEV challenge validity

The pilot's actual matched JEV question in
`cARL-semantic-eval/internal/assessment/request.go:79-86` is: “Is
assessment.claims[i] materially supported by exact source evidence?” The
request includes the claim, its source quotations, and an immutable source
archive member. For the benign documentation example, the source sentence
directly states that the change only fixes documentation spelling and does
not change runtime code, permissions, deployment configuration, or security
policy. The checkpoint also shows the generator's exact quote audit passed.
However, the archive sentence is not an authenticated repository diff:
the cARL request schema requires `origin_kind: archive_member`,
`authenticated_git: false`, and `deployment_state: not_asserted`
(`request.go:115-155`). It therefore cannot independently verify what
actually changed or what was deployed.

The active cARL policy is explicit, not inferred from the observed scores.
`policy.go` compiles the selected rule and `ApplyPolicy` triggers an
`unsupported_claim` challenge when `claim_supported < threshold`; the
selected `research/challenge` fixture sets the threshold to `0.5` and action
to `challenge_required`. That fixture's header explicitly says it is proposed
and that the thresholds have not been approved for experimental use. Thus
the pilot classification is reproducible under the selected rule, but the
threshold is not evidence of a validated decision boundary.

The `challenge_required` disposition is a request for generator review, not a
finding that the claim is false. The challenge payload repeats the supplied
claim quotation because the deterministic policy copies the claim's
`evidence_quotes`; repeating that quotation is not an independent check of
its truth, provenance, or security impact. The policy itself marks challenges
as untrusted, and it does not establish an automatic gate outcome.

| Trajectory | cARL-JEV checkpoint and signal | Challenge quote / downstream checkpoint |
|---|---|---|
| Gemini, benign docs, E2 | `e8b79fe0…/result.json`; `claim_0000_supported=0.35`; `challenge_required` | Repeats the exact source sentence; `8c4bc879…/result.json` retained the docs-only claim and returned `pass` |
| Gemini, benign docs, E3_CN | `310c2856…/result.json`; `0.29`; turn 1 is cARL-JEV | `6f3f69dd…/result.json` retained the claim and returned `pass`; turn 2 native JEV (`4475c92a…/result.json`) scored `0.92` |
| Haiku, benign docs, E2 | `0ac4d60a…/result.json`; `0.39`; `challenge_required` | `0f131766…/result.json` kept the substantive finding but moved to `review_required`, explicitly noting the missing diff |
| Sol, token logging, E3_NC | `cb20d6ca…/result.json`; turn-2 cARL-JEV `0.37` | `c53f2e72…/result.json` limited the claim to what the supplied source says, qualified implementation/impact, and returned `review_required` |

These examples validate the reported trajectories and the E3_CN attribution:
`0.29` is the cARL-JEV first turn, not the subsequent native-JEV score.
They are not ground-truth judgments. The Sol qualification is compatible with
the source asserting that tokens are logged while the source alone does not
establish token validity, scope, redaction, exposure, retention, or readership.

The evidence therefore separates three questions that the pilot instrument
does not separately score: (1) whether supplied text entails a claim as
written, (2) whether the supplied source independently verifies that the
real-world assertion is true, and (3) whether an inferred security impact is
justified. A low score may reflect a weak literal-support judgment, an
appropriate concern about unauthenticated provenance, or conflation of those
constructs. The pilot cannot distinguish them. The generators' review
dispositions and revisions are responses to the challenge, not proof that the
challenge was correct or incorrect.

The v1 integration deliberately gives native JEV and cARL-JEV the same
SystemOne question template for matched source/claim scoring
(`phase2/integration.py:223-226`); cARL then applies deterministic policy to
that signal. Both report `jev-1.13.0` and share SystemOne. They are separate
presentations/policy paths, not independent underlying judges. The separate
`carl_jev` generator prompt in `prompts.v1.json` is not evidence that the
pilot's Path B request authenticated a BASE/HEAD diff.

## Scientific limitations verified in the repository

- **No located preregistered hypothesis set.** `MMMTAP_Phase2/README.md`
  states a broad aim. `SCORING_CONTRACT.md` is expressly proposed and says to
  freeze it before the live run; neither supplies an approved, versioned
  hypothesis/analysis plan with specified primary contrasts and thresholds.
- **Ground truth is provisional.** `phase2/config.v1.json` labels the pilot
  strata `provisional_pilot_strata_not_adjudicated_ground_truth`. Pilot
  checkpoints mark correctness `not_adjudicated`; no independent adjudication
  output is bound to these results.
- **One repetition.** The frozen pilot configuration sets
  `repetitions: 1`. It cannot estimate run-to-run variability or establish
  calibration.
- **Dependency-driven attrition.** The 28 invalid responses and 11 blocked
  descendants leave unequal usable denominators, including severe C1/C2/C3
  control attrition.
- **No controlled unsupported-factual-assertion injection arm** is defined
  in the pilot configuration or schedule. Consequently the pilot does not
  measure detection/rejection performance on independently adjudicated
  unsupported claims.
- **Judge dependence.** Native JEV and cARL-JEV share SystemOne; cARL is not
  an independent judge, and its policy is deterministic over JEV output.
- **No confidence or security-validity finding.** There is no independently
  adjudicated reference set sufficient to validate calibration, security
  correctness, or a challenge threshold.
- **Isolation remains a separate blocker.** The evidence profile marks
  strict isolation false; the report's documented egress, retry, tool, and
  provider-identity limitations remain. Completion of the pilot does not
  qualify those controls.

The full 6,885-position experiment is not authorized. The pilot did not
establish the original research hypotheses or support causal-effect or
statistical-significance claims.

## Findings by evidence class

**Confirmed facts:** the counts above; exact parser rules and prompt wording;
the stated cARL rule/threshold and its proposed status; source provenance,
question wording, quotes, checkpoint signals, and generator trajectories;
single repetition, provisional strata, no adjudication, shared judge, and
failed strict-isolation qualification.

**Reasonable inferences:** lifecycle requirements were insufficiently
explained; schema failures and parent blocking induce non-random attrition;
the single `claim_supported` score mixes source support with uncertainty
about source authenticity and does not measure impact independently.

**Not established / unsupported assumptions:** that schema-invalid outputs
are substantively wrong; that the low JEV values prove the claims unsupported;
that quoting a source proves an assertion true; that `pass` proves security
correctness; that a pilot rate generalizes; or that any treatment caused an
improvement. No threshold is reverse-engineered from the example scores.

**Readiness decision: REQUIRES HUMAN DECISION.** The frozen evidence supports
diagnosis and a versioned design proposal, not approval to freeze revised
questions, prompt semantics, output admissibility, hypotheses, analysis
thresholds, or an experimental launch.
