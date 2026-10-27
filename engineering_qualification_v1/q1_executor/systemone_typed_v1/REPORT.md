# Choice 1 typed specialist evidence report

**CHOICE 1 TYPED SPECIALIST INTEGRATED — OFFLINE QUALIFIED, LIVE Q1 BLOCKED**

Baseline: `9f375374c9daab1b6ae3a36e15593a340e65b9b7`, verified upstream main.
The [PI amendment](PI_DECISION.md) records the supplied Choice 1 approval without
rewriting the [historical proposal](../../systemone_contract_resolution_v1/DECISION.md).
[Contract and boundaries](CONTRACT.md); [executed acceptance](evidence/acceptance/acceptance.json).

The actual Q1 executor now routes explicitly versioned specialist observations
through its existing SQLite reservations, dependencies, immutable receipts,
read-only reconstruction and offline broker/transport custody. Original request
and response hashes remain distinct from the new broker-request hash. Native
and cARL identities remain distinct while both identify SystemOne as their
underlying judge. cARL derivation is stored separately from direct observations.
No frozen v1/v2 validator, scientific decision or historical result changed.

## Actual preserved-record replay

Five distinct historical response bodies replayed through five successful
specialist positions: **3 native, 2 cARL**, yielding **7 per-claim support Nouls,
10 assessment-wide Nouls and 1 auxiliary historical Choice**. All original
numerical tokens, question bindings, claim IDs/order, model and usage metadata
were retained. All five entities self-report `jev-1.13.0`; this is not attestation.

| Preserved record | Claim support | Assessment uncertainty | Assessment authority | Separate cARL outcome |
|---|---|---|---|---|
| native-low | 0.27 | 0.72 | 0.34 | None |
| carl-low | 0.35 | 0.69 | 0.32 | Historical `challenge_required` reproduced |
| native-multi | 0.91, 0.85 | 0.88 | 0.16 | None |
| carl-multi | 0.91, 0.83 | 0.88 | 0.15 | Historical `no_challenge` reproduced |
| smoke-choice | 0.94 | 0.59 | 0.11 | None; original side-effect Choice retained separately |

Each successful specialist's dependent continuation received the exact stored
observation. These are explicitly scripted offline continuations, not generator
inferences. Their baseline is the historical assessment supplied to the judge;
the historical generator's original wire response is not claimed to be replayed.
Original sources, assessments and provider responses were never modified.

Eight bounded diagnostic campaigns exercised **28 positions, 23 reservations
and 22 local mock dispatches**. Missing, extra, duplicate and wrongly typed
answers were rejected in four additional negative-input campaigns. Their
mutated bytes are labelled derivatives and stored separately from the preserved
originals. Each invalid specialist retained its raw response and blocked its
continuation without reserving a child attempt. A process exit after a cARL
reservation produced an interrupted specialist and blocked child: **2 reserved,
1 dispatched**, with no reissue. Read-only verification and two repeated
resumes left every campaign file unchanged.

## Verification and preservation

**152 tests passed:** 15 focused tests and 137 existing regressions. The focused
tests cover exact values/precision, scopes, original associations, catalog
wording, negative inputs, derived-policy dependencies and quote provenance,
scientific separation, actual broker integration and restart. Existing suites
cover v2 instrument/continuation, RD05, harness, Q1 executor, transport,
full-matrix and broker authority, plus the original SystemOne diagnostics.
See [focused results](evidence/focused.stderr),
[regressions](evidence/regressions.stderr) and [verification metadata](evidence/verification.json).

Original custody verification passed for **40,538 preserved entries**, **1,165
operator-sealed files**, **4,699 V5 files** and **36 command records**:
[original output](evidence/original_custody.stdout). The original shared worktree
was left in place; changes were developed in an isolated checkout.

The existing Q1, full-matrix, transport and broker seals respectively verified
**50, 166, 390 and 480 entries**. Current artifact bytes were checked directly;
three historical source entries per seal were checked against their original
Git revisions, since those seals describe historical producers. Old seals were
not regenerated to describe the new implementation. **38 archived campaigns**
reconstructed successfully with no file changes. The SystemOne resolution,
provider-qualification and RD05 comparison seals also passed unchanged.
[Preservation detail](evidence/preservation.json) records the exact revisions.

RD05 recomputation in a temporary copy matched every frozen byte: 14 cases,
31 endpoints; comparison complete, resolution pending. Reviewer disagreements
were preserved. RD01/RD02 movement/disposition definitions, RD04/IE01, frozen
question wording and the existing eight-arm/153-position topology are unchanged.

## Limits and remaining live blockers

This implementation selects **offline historical replay only**. A changed
assessment cannot reuse a preserved specialist response. Native requests have
canonical payload custody, not authenticated HTTP wire capture; cARL retains
captured request-body bytes. The extra Choice is a qualification-only historical
extension, not a new Q1 question. The captured cARL policy is replayed solely to
check historical derivation; its thresholds have no prospective approval.

Live-provider qualification still requires separately authorised access and
calls, qualified one-shot provider transport/retry behavior, served identity and
context-separation evidence, and usage/budget qualification. Prospective
challenge thresholds/continuation policy, RD03 reference/adjudication rubric,
statistical methods and operational governing-policy decisions remain pending.
Choice 1 approval supplies none of those approvals. No new methodology review
was commissioned.

No live SystemOne/JEV call, remote cARL execution, generator inference,
credential access or experimental Q1 launch occurred. Successful replay proves
local parsing, attribution, custody and delivery only; it does not establish
correctness, calibration, provider identity attestation or experimental readiness.

## Reproduction

From the repository root, using the preserved runtime:

```sh
python -B -m unittest -v engineering_qualification_v1.q1_executor.systemone_typed_v1.test_choice1
python -B -m engineering_qualification_v1.q1_executor.systemone_typed_v1 --output /tmp/new-choice1-acceptance
python -B -m engineering_qualification_v1.q1_executor verify --campaign engineering_qualification_v1/q1_executor/systemone_typed_v1/evidence/acceptance/multi_pair/campaign
PYTHONPATH=. python -B engineering_qualification_v1/q1_executor/systemone_typed_v1/evidence/check_preservation.py
```

The new output path must not already exist. Archived campaign verification may
relocate paths while retaining exact runtime/control hashes; creating or
launching a new campaign requires the current exact configuration. Full
regression commands and output hashes are recorded in the verification metadata.
