# RD05 comparison v1

**Status: COMPARISON COMPLETE / RESOLUTION PENDING.**

This package compares the two separate report texts supplied by the user
against the permitted blinded RD05 v1 materials and the synthetic policy at
commit `9af5992ecccc4d0c34f5a62f4767f9053254adf6`. It preserves original
reviewer conclusions, marks unavailable records as unavailable, and leaves
the resolver's decision fields blank.

## Inputs and reference boundary

- `inputs/reviewer_a.md` and `inputs/reviewer_b.md` preserve the report text
  supplied separately in the conversation. `inputs/review_source_metadata.json`
  records the stated reviewer/provider surfaces and the limitation that no
  original uploaded file containers or original byte streams were supplied.
  The SHA-256 values identify the preserved report text files in this package.
- `reference/` contains copies of the permitted synthetic policy, blinded
  claims and pairs, RD05 workflow README, and proposed RD03 adjudication
  guide. `source_manifest.json` binds these copies to the exact upstream
  commit, paths, Git blob IDs where recorded, and SHA-256 hashes.
- The retrieved materials were limited to the RD05 synthetic policy,
  `claims.json`, `pairs.json`, its README/workflow, and the RD03 proposal.
  `authored.py`, `exercise.v1/custodian/**`, `REPORT.md`, `resolution.json`,
  authored suggestions and answer keys were not consulted.

The source snapshot was retrieved from upstream only after the user expressly
authorized online retrieval to resolve the missing local checkout. Policy
recomputation and comparison were then run locally from the preserved
snapshot. No model, provider, JEV, cARL, or experiment call was made.

## Comparison method and counts

`python3 reproduce.py` verifies the raw-report and reference SHA-256 values,
applies the frozen policy's stated precedence to the supplied evidence at
each endpoint, and regenerates
`comparison/endpoint_policy_comparison.csv`,
`comparison/observed_pair_mismatches.csv`, and
`comparison/summary.json`. Reviewer B's table is manually transcribed without
changing its raw report; that transcription is separately preserved in
`data/reviewer_b_endpoint_values.csv`. Reviewer A's case-level text is
transcribed without converting it into endpoint labels in
`data/reviewer_a_case_notes.csv`.

The frozen materials contain **14 trajectories, 31 endpoints, and 17
adjacent transitions**. Reviewer B supplies 31 policy-warranted disposition
values in the report table. The deterministic application of the written toy
policy agrees with Reviewer B's values at **31/31 endpoints**. This is
concordance with the stated synthetic rules and available fixture facts, not
proof of independent ground truth.

Reviewer A supplies 14 case-level narrative assessments but no explicit
endpoint-granular policy-warranted disposition table. Consequently there are
**0 matched Reviewer A/Reviewer B endpoint disposition records** and no
pairwise endpoint agreement fraction is estimable; this is recorded as
unavailable, not as zero agreement. A's case-level transition assessments
and B's endpoint defensibility labels are different units and are not
cross-scored.

For disposition justification, A expresses **12 transition-level judgments**
and **5 separate retention assessments** for no-movement cases. B reports
**31 endpoint-level defensibility labels** (**22 justified, 9 unjustified**).
The crosswalk in `comparison/disposition_justification_comparison.csv`
preserves each case's wording and marks all **0** as directly matched
judgment records because the units differ. The five retention records are
not movement-justification records.

The observed pair dispositions match the deterministic policy at **22/31
endpoints**; **9/31** observed endpoints differ. All nine are preserved in
`comparison/observed_pair_mismatches.csv`. These are inconsistencies between
the fixture's observed pair values and the written policy result, not nine
reviewer disagreements; Reviewer B's policy-warranted endpoint values match
the recomputation.

Reviewer B's endpoint justification labels also match this recomputed
observed-endpoint check at **31/31** (22 justified where the observed value
matches the policy result; 9 unjustified where it does not). This is an
endpoint-defensibility cross-check, not a transition-level justification
comparison.

For finding movement, both reports explicitly discuss four finding-revision
cases: `b-13d9dacc`, `b-20dbc460`, `b-c2ecd517`, and `b-c9fc13b0`. The
case-level qualitative crosswalk records **2/4 exact category matches**:
Reviewer A and B both judge the revisions justified for `b-c2ecd517` and
`b-c9fc13b0`; their conclusions differ for `b-13d9dacc` and `b-20dbc460`.
This is a post hoc prose-to-category comparison, not a preregistered
reliability statistic. A separately states unchanged findings for
`b-0e862d9a`; both reports convey no finding movement there, while B labels
it “Justified (no movement)”.

Reviewer B labels **10 no-finding-movement cases** with “Justified”; RD03
proposes explicit unchanged status, null movement justification, and optional
retention assessment in separate fields. This is treated as an
annotation-schema disagreement, not silently normalized in either report.
Reviewer A does not provide a finding assessment for nine of these cases.
Reviewer B lists three cases as requiring independent resolution:
`b-13d9dacc`, `b-79b869e4`, and `b-522d4fdb`; details and A's separately
reported reasoning are in `comparison/uncertainty_comparison.csv`.

## Resolution boundary and limitations

`comparison/discrepancies.csv` prioritizes the revised credential-exposure
claim, finding materiality at `b-13d9dacc`, and the unchanged-finding schema
issue. Each entry preserves both reports' positions and proposes a resolver
task without marking it decided. `comparison/source_anchors.csv` lists exact
source JSON Pointers, policy anchors, and original report line anchors for
each discrepancy.
`resolution/independent_resolver_sheet.csv` has source/evidence anchors,
reviewer rationales, proposed handling and blank resolver fields. No
resolver participated; do not fill the sheet by treating this comparison as
a completed adjudication.

Reviewer B's report states that all 14 trajectories and 31 endpoints were
structured in `reviewer_B.json` format, but no completed JSON review file was
provided as an input. The statement is preserved as a report claim only; this
package does **not** claim structured JSON completeness, atomic span
completeness, or verification of that sign-off.

The reports are qualitative LLM first-pass opinions (according to supplied
source metadata). Their agreement is not independently established ground
truth, a human inter-reviewer reliability estimate, or evidence of JEV
effectiveness. The toy policy is explicitly synthetic and has no deployment
authority. No scientific conclusion about JEV effectiveness is made. RD03
remains proposed; this package does not approve RD03 or authorize an
experiment.

## Reproduction and integrity

From this directory, using Python 3 standard library only:

```sh
python3 reproduce.py
sha256sum -c SHA256SUMS.txt
```

The script fails on source/report hash mismatches, missing or extra endpoint
transcriptions, or an inconsistency between claims and pairs. It does not
open prohibited reference material and does not call a model, provider, JEV,
or network service. The `SHA256SUMS.txt` manifest also records the generated
comparison artifacts and supporting transcriptions.
