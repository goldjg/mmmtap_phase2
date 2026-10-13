# Phase 2 v2 design proposal

**Draft for human review; not an approved protocol or launch authorization.**
This proposal does not change the v1 manifest, instruments, source material,
pilot records, or first attempts. No prompt, scoring, hypothesis, or arm
change is being made to the v1 package.

## Human research-direction amendment RD01

The primary objective is now to determine whether JEV challenges change AI
security assessments, what changes, in which direction, why, and whether
those changes are evidence-justified. Unsupported-assertion adoption is
deferred to a potential future study, not a prerequisite for this study.
`RESEARCH_DIRECTION_AMENDMENT.v2.1-RD01.md` records the 2026-10-13 human
decision and supersession map. It approves the direction only; hypotheses,
estimands, rubrics, thresholds, sample size and execution remain unresolved.
Candidate assessment-change hypotheses are in `PHASE2_V2_HYPOTHESES.md`.

## Design goals and boundaries

1. Preserve v1 as immutable evidence, including invalid and blocked results.
   A v2 qualification has its own code, prompts, schemas, manifests, seals,
   run root, and first-attempt records.
2. Improve explicitness and diagnostic separation without making invalid
   first attempts pass, repairing outputs, retrying providers, or selecting
   successful attempts.
3. Separate source-text entailment, source authenticity/independent
   verification, and security-impact inference. Do not treat a challenge as
   a verdict or a disposition as correctness.
4. Keep native JEV and cARL-JEV's shared SystemOne dependence explicit.
   Distinct presentation or deterministic policy is not independent judge
   replication.
5. Do not start the 6,885-position experiment. Any v2 qualification and any
   later full run require separate written approval.

## Proposed protocol changes

### 1. Claim lifecycle and output validation

Retain the current v1 validity conditions provisionally; do not loosen them
to recover pilot pass rates. Version a new prompt/schema package that states,
with machine-readable examples:

- the exact top-level and claim keys, including no additional fields;
- `B0` has an empty `changes` list;
- for a follow-up, every ID in the union of prior and current claims has
  exactly one action; withdrawn claims are absent from current claims, and
  added claims have new IDs;
- `retained` means the entire frozen claim object is unchanged under the
  current exact-equality rule; if any field changes, use `revised` and explain
  the source-grounded change;
- C1, C2, and every C3 turn have the same lifecycle accounting duties, even
  when the task asks for independent review or re-expression.

The v1 evidence shows why this must be explicit: all 15 retained mismatches
changed `limitations`, 12 also changed the claim text, and 2 changed
`confidence`; C2 does not explicitly ask for the required claim-by-claim
accounting. A separate v2 decision may instead define a narrower notion of
claim identity, but that changes lifecycle semantics and must not be decided
by weakening code or by model-output frequency.

In a separately versioned parser, record syntax/decoding, shape, quote
checks, and lifecycle validation as distinct diagnostic fields. Preserve
the exact raw response and report each failed layer. A parseable but
lifecycle-invalid response remains contract-invalid; it is never silently
converted to admissible output. Whether such raw content may be separately
blind-adjudicated as descriptive evidence, and whether it can enter any
primary outcome, requires explicit approval before preregistration.

**Comparability:** changed prompts or lifecycle definitions are a new
instrument. Report their attrition separately; do not pool their outputs with
v1 or claim a direct treatment effect from a v1/v2 pass-rate difference.

### 2. Separate challenge constructs

Replace the single support question only after a new instrument is approved.
For each atomic claim, collect distinct, separately labeled judgments:

1. **Supplied-source support:** does the quoted, supplied source entail the
   claim as written, irrespective of whether that source is authenticated?
2. **Independent verification:** does the evidence establish the assertion
   beyond merely quoting a source, including source provenance and limits?
3. **Impact inference:** does the supplied evidence establish the asserted
   security consequence, or is it only plausible/conditional?

Keep source quotes attached to the claim and verify exact-substring
membership deterministically. Do not infer that quote membership proves
entailment. Do not collapse missing provenance into a negative source-text
score. Keep continuous judge signals distinct from adjudicated labels and
from policy actions. Label `challenge_required` as a request for review, not
as `unsupported` ground truth.

The existing cARL fixture says its threshold is proposed and unapproved;
do not tune that threshold on these pilot examples. Before v2 use, approve a
new question/policy version, establish its source contract and intended
population, and test the deterministic mapping independently of the judge.
Any claim about security impact must not be inferred from literal quotation
or from the challenge disposition alone.

**Comparability:** a new question set changes the measured construct.
Preserve the v1 rule in the historical record and show v1 and v2 outputs
side-by-side only as a clearly labeled bridge, not as one continuous series.

### 3. Controls and matched design

Retain B0 and the existing neutral/self-review/placebo roles as controls
unless a preregistered design review explicitly amends them:

- B0: independent first assessment;
- C1: self-review control;
- C2: re-expression/placebo control;
- C3: matched two-turn neutral control;
- E1/E2: native-JEV and cARL-JEV presentations;
- E3_NC/E3_CN: both sequential orders.

Controls measure changes induced by another prompt or another turn, not
merely “no effect.” Keep each treatment arm forked from the same sealed B0.
Count every scheduled position, schema failure, dependency censoring event,
and completed chain. Preserve the original attrition denominator; never
compare only successful outputs without a preregistered missingness rule.
Any deletion, merger, or addition of an arm is a methodological change
requiring approval.

### 4. Ground truth, challenge cases, and adjudication

Before any provider run, create a versioned reference set for each source:
atomic claims, source-support label, provenance/verification label, impact
label, materiality, evidence pointers, and rationale. Use independent
adjudicators blinded to arm and model output; freeze their sheets and hashes
before unblinding, record reviewer qualifications and model exposure, and
predefine disagreement resolution. A reviewer must be able to label a claim
unverifiable rather than infer truth from model agreement or confidence.

Use natural B0 assessments of independently reviewed sources for the current
study. Cover benign, supported security-finding and conditional/provenance-
limited cases without injecting assertions into sources, B0 or challenges.
Supported/unsupported/ambiguous authored records remain useful offline
challenge diagnostics, not an adoption-study stratum or ground truth.
Controlled unsupported-assertion exposure is deferred to a potential future
study requiring its own decision. Do not retrofit cases into v1.

Adjudicate substantive versus wording-only changes, confidence/limitations,
evidence use, findings, impact assertions and disposition separately.
Retain unchanged assessments as outcomes. Evidence justification may improve,
worsen, remain equivalent, be mixed, or be unresolved; change itself is not
improvement. Link recorded generator reasons to exact challenge/source spans
only after blinded content labeling. Those explanations are reported
rationales, not established internal mechanisms or proof of causation.

**Comparability:** independently adjudicated v2 labels establish a new
reference baseline. Cross-version claims require a blinded bridge review on
the same immutable source; no retroactive relabeling of v1 outputs.

### 5. Preregistration, analysis, and qualification gates

Before v2 observations, freeze explicit directional hypotheses, primary
contrast family, outcome definitions, claim-unit rules, missingness handling,
repetition count, power/sample-size rationale, multiplicity plan, exclusions,
adjudication rubric, and stop criteria. Match within case, variant, generator,
and repetition; analyze at the planned clustered unit, not by treating
claims or turns from one source as independent samples. Keep all scheduled
positions and dependency outcomes visible.

One repetition and control attrition cannot estimate variability or support
statistical readiness. Require a statistician or methods lead to approve the
analysis plan before sample size is selected. Treat confidence calibration
and security correctness as unestablished until an adjudicated dataset and
adequate repeated observations exist.

Qualification is staged: deterministic, provider-free contract and replay
tests first; separate human approval for any bounded v2 pilot; then a further
review before any primary experiment. Isolation qualification is an
independent gate. The current pilot explicitly failed strict-isolation
qualification; v2 must not call that fixed by changing the study protocol.

## Alternatives considered

| Alternative | Decision | Reason |
|---|---|---|
| Relax exact lifecycle checks to raise valid counts | Reject | It changes output admissibility and may reward ambiguous or incomplete claim accounting; rates alone are not scientific rationale |
| Repair/retry v1 failures | Reject | Destroys first-attempt and missingness evidence and creates outcome-dependent selection |
| Call low JEV scores proof that claims are false | Reject | The request, source provenance, and impact question are not separated; the disposition is a challenge, not ground truth |
| Tune the threshold to fit the four examples | Reject | Post-hoc calibration on pilot examples is circular and the fixture is explicitly unapproved |
| Treat native and cARL-JEV as independent judges | Reject | Both use the same SystemOne model; cARL applies a deterministic policy |
| Repeat v1 unchanged as the primary experiment | Defer | It would preserve the prompt/contract ambiguity, unadjudicated truth, single-repeat limitation, and missingness risks |

## Decisions required before v2 is frozen

The PI/methods lead must approve lifecycle equality semantics, treatment of
parseable lifecycle-invalid outputs, the three challenge construct
definitions, policy action/threshold and intended source population, control
arms and comparisons, adjudicator qualifications/disagreement resolution,
change/justification and rationale rubrics, primary outcome family and multiplicity, power
and repetitions, and qualification authorization. Until those decisions are
recorded, this remains a proposal. The full 6,885-position run remains
unauthorized.
