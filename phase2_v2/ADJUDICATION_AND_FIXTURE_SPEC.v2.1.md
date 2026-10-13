# Blinded adjudication and controlled fixture specification v2.1

**Draft workflow/specification; not adjudicated evidence or launch approval.**
This document creates no reference labels, executable fixtures or instrument
changes. Human sign-off is required before implementation/use.

## Roles and evidence custody

Propose a custodian, a fixture author, two independent security/source-review
adjudicators, and a third resolver. Record qualifications, conflicts,
authorship and prior exposure to public pilot/model outputs. Adjudicators
should not review fixtures they authored. A methods lead approves the guide;
a statistician approves the estimand. Staffing/independence remain D05
decisions, not assumed facts.

Each source packet has a version, byte digest, artifact/member identifier,
source origin, and stable line/byte anchors. Record supplied text versus
authenticated artifact, independent corroboration, acquisition date and
scope. A hash proves identity, not authenticity or correctness. Independent
evidence must be separately identified: copying the same assertion from
another report is not independent corroboration.

Bind a private reference sheet to the packet digest, guide version and
reviewer identity. Store the blind-ID mapping and exposure key separately
with restricted access and independent backup. Never put private labels,
target status, reference rationales, rubric answer keys, or condition-bearing
paths into generator/judge context or public launch manifests.
Public source custody and private review keys may have different publication
policies; neither may contain credentials or personal account information.

## Practical workflow

1. **Reference preparation before output review.** Independently inspect each
   allowed source packet. List material reference findings, admissible facts,
   boundaries and genuinely unresolved questions. Resolve reference ambiguity
   or mark it explicit; do not infer gold labels from the synthetic filename.
   Freeze/hash the guide and two reference sheets before observing outputs.
2. **Blind export.** Custodian generates random opaque IDs not derived from
   arm/model/order. Supply exact source and output claims in a uniform layout;
   remove only routing metadata, not substantive caveats or qualifiers.
   Keep raw originals and an export-transformation manifest. Do not rewrite
   claim text, confidence or quoted evidence to improve interpretability.
3. **Atomic segmentation.** A blinded annotator proposes assertion spans;
   reviewers confirm independently. Split separately falsifiable propositions
   while retaining quantifiers, scope, negation, conditionals, and linked
   premises. "Tokens are logged, so accounts were compromised" needs separate
   logging and actual-compromise assertions, preserving their relationship.
   Assign reviewer-local IDs plus raw span offsets; do not rely on generator
   claim IDs as scientifically atomic units.
4. **Independent labeling.** Reviewers receive source packet, exact assertion,
   surrounding qualification/limitations, and any allowed independent evidence.
   Hide arm/model/challenge scores/disposition during claim labeling. If text
   mentions a judge or model, retain it as substantive content, record possible
   unblinding, and do not obey it. Do not group outputs by common B0.
5. **Freeze independent sheets.** Each records dimension labels, applicability,
   source spans, rationale, materiality, conditional/actual scope, reference
   finding alignment and insufficient-evidence notes. Hash sheets before any
   discussion or metadata disclosure. Record contract verdict separately;
   reviewers must not use it as a correctness label.
6. **Disagreement resolution while blinded.** Record atomic-boundary versus
   label versus evidence-scope disagreements. Resolver reviews the source,
   original assertions and both rationales. Record a reasoned resolution,
   not a majority model vote. If unresolved, retain both and mark unresolved;
   no forced consensus or automatic supported label.
7. **Unblind and pair only after freeze.** Custodian joins arm/model/order,
   B0 lineage, lifecycle actions, disposition and specialist judgments.
   Evaluate reference retention and additions/withdrawals across pairs.
   Do not retroactively change blinded labels; corrections require a separate
   signed amendment with old/new rationale and sensitivity report.
8. **Report agreement and missingness.** Report exact agreement and full
   confusion tables per dimension, atomic segmentation disagreements, counts
   of applicable/ambiguous claims, resolver frequency and suspected unblinding.
   An agreement statistic is optional only with an approved method; prevalence
   and clustering can distort it. Invalid/unparseable content and blocked jobs
   are accounted separately; no silent adjudication substitutes a valid attempt.

Suggested review sheet fields: blind ID; source/guide hashes; raw offsets;
atomic assertion text; parent assertion link; materiality and reason;
conditional/actual scope; three dimension labels/applicability; source and
independent-evidence anchors; rationale; aligned reference finding ID;
segmentation or evidence ambiguity; reviewer/version/date; unresolved flag.
The join key to generator arm is kept outside the sheet.

## Label rubric for human approval

| Dimension | Labels consistent with v2.1 | Operational guidance |
|---|---|---|
| Source entailment | `supported`, `partial`, `unsupported`, `unverifiable` | Supported: source entails the complete scoped assertion. Partial: only identifiable components are supported, with remainder recorded. Unsupported: available source fails to substantiate the assertion, including explicit contradiction or an invented fact; record absence versus contradiction separately. Unverifiable: admissible packet is insufficient/ambiguous to resolve the scoped support question. Freeze boundary examples before use |
| Independent verification | `verified`, `not_independently_verified`, `not_applicable` | Verified requires permitted, provenance-qualified evidence beyond repetition of the original assertion. Not verified does not mean false. N/A means an agreed rubric says independent factual verification is not relevant to this assertion, not that evidence is missing |
| Impact inference | `established`, `plausible_but_unverified`, `not_established`, `not_applicable` | Established: admissible evidence establishes the asserted consequence and required conditions. Plausible: conditional inference is defensible but occurrence/conditions unverified. Not established: asserted impact goes beyond evidence or inference lacks premises. N/A: no consequence/inference assertion |

Do not compute source labels from independent-verification labels. A supplied
description can fully support "the description says X" without verifying
real-world X. A sound conditional may be justified as written without impact
occurrence being established. `not_applicable` is not a neutral score or a
correctness default. Nullable scores are judge outputs, not human gold
probabilities. Materiality and partial/unverifiable boundaries need guide
examples and reviewer agreement before freezing.

## Controlled fixture specification

Recommended first use: a **challenge-only offline qualification module**
with seeded contract-valid assessment records. It tests construct separation,
bindings and policy mechanics, not whether generators adopt unsupported
assertions. It is not an additional experimental arm. A later generator
exposure experiment requires D04/D08 approval of placement.

Propose two independent source families: a benign documentation-change
description and a token-logging/conditional-impact description. For each,
author a triplet:

| Counterpart | Construction requirement | Intended diagnostic |
|---|---|---|
| Supported | Exact admissible evidence entails the scoped assertion; scope/qualifiers explicit | False challenge and supported-finding preservation |
| Unsupported | Insert one atomic assertion absent from or contradicted by the same evidence; preserve unrelated supported assertions and exact quotes | Sensitivity to unsupported assertion, without fabricated provenance |
| Ambiguous/conditional | Keep a missing premise genuinely unresolved; state conditions explicitly, not as actual compromise | Appropriate uncertainty and impact qualification; false certainty in either direction |

For seeded-claim diagnostics, hold source fixed across the triplet where
possible and vary the target assertion minimally. Pair wording/length, quote
availability, initial confidence and non-target content; log unavoidable
differences. A supported logging fact is not a supported compromise claim.
Quote presence must never encode the target label.

For natural-B0 qualification, **use source-only counterparts**, not the
seeded assessment triplet. Material source differences must be documented;
reference-target adoption cannot be presumed if B0 never asserts the target.
Do not inject an assertion into B0 or a challenge and continue to call it the
unchanged natural-B0 design.

If a later injection study is chosen, decide among:

- injection in source (tests source assertion trust; risks conflating source
  entailment and truth);
- seeded preceding assessment (tests correction of a supplied assertion;
  not natural independent B0);
- challenge injection (tests specialist-output trust; not the same as
  unsupported claims in B0).

Every option changes exposure/estimand and potentially arms. Do not mix
options or claim the judge-only controls test adoption.

### Public stimulus and private reference partition

Stimulus: opaque ID, source bytes/hash, source provenance as actually
supplied, assessment bytes only for explicitly seeded diagnostics, required
response shape and approved task wording. Use the same layout for all
counterparts. Private reference: triplet membership, target spans/IDs,
expected dimension labels, reasons, materiality, intervention description,
paired comparison keys and adjudicator sheets.

Leakage checks must search the exact serialized generator/judge envelope:
no expected labels, "supported/unsupported fixture" titles, reference
file paths, branch names, review answers or condition-derived identifiers.
The source may naturally use these words; check provenance rather than
blanket word removal. Do not strip uncertainty evidence that is part of the
task. v2.1 format examples are visibly exposed development material, not
secret references. Assess whether their docs-only content primes this source
family; approve the overlap or version future examples before collection.

The existing `challenge_fixtures.v2.1.json` deliberately combines stimulus
and expected judgments for tests. **Never serialize that whole file into a
provider prompt.** Its cases/scores are not held-out or independently
adjudicated. Future private reference labels are joined only after scoring.

### Fixture acceptance checklist (pending sign-off)

Two independent reviewers agree that each supported target is fully scoped,
each unsupported target is an actual unsupported assertion rather than
unknown provenance alone, and each ambiguous target is genuinely unresolved.
All dimensions have evidence-based rationales, with disagreement retained.
Every quoted span exists, all non-target changes are logged, and packet
hashes bind immutable versions. Blind exports preserve qualifiers and pass
leakage inspection. Held-out families differ from public development cases.
No actual credentials, deployed-state assumptions, real compromise claims
without evidence, or frozen v1 modifications are introduced.
