# Actual synthetic full-matrix qualification results

**Synthetic engineering observations only; no scientific findings or live authorization.**

Two separate campaigns exercise the same frozen 153-position topology. They are not research repetitions and their observations are not pooled. All ten offline acceptance criteria passed; live Q1 remains blocked.

| Actual accounting | Normal | Adverse |
|---|---:|---:|
| Scheduled | 153 | 153 |
| Generator / specialist | 99 / 54 | 99 / 54 |
| Matched units / arms | 9 / 8 | 9 / 8 |
| Dependency edges | 198 | 198 |
| Reservations | 153 | 141 |
| Fake invocations | 153 | 140 |
| Completed valid | 153 | 134 |
| Invalid | 0 | 3 |
| Blocked dependencies | 0 | 11 |
| Interrupted | 0 | 1 |
| Unavailable | 0 | 4 |
| Reserved synthetic units | 153 | 141 |
| Spent synthetic units | 153 | 140 |
| Remaining budget units | 0 | 0 |
| Real provider calls | 0 | 0 |

Normal limits: 153 attempts / 153 invented units. Adverse limits: 153 attempts / 141 invented units. Reservations are never refunded. All positions have durable terminal receipts; blocked children have no attempts. These units are not billing, tokens or entitlements.

| Case role / neutral ID | Generator slots | R | Positions per slot | Generator / specialist per case |
|---|---|---:|---:|---:|
| benign documentation / c01 | gemini, haiku, sol | 1 | 17 | 33 / 18 |
| supported security finding / c02 | gemini, haiku, sol | 1 | 17 | 33 / 18 |
| conditional impact/provenance-limited / c03 | gemini, haiku, sol | 1 | 17 | 33 / 18 |

Each generator has 51 total positions: 33 generator and 18 specialist positions across three cases. Source-role labels are sampling metadata outside provider context.

| Arm | Generator positions | Specialist positions |
|---|---:|---:|
| B0 | 9 | 0 |
| C1 | 9 | 0 |
| C2 | 9 | 0 |
| C3 | 18 | 0 |
| E1 | 9 | 9 |
| E2 | 9 | 9 |
| E3_CN | 18 | 18 |
| E3_NC | 18 | 18 |

Every one of the 153 nodes and 198 edges was compared with the unchanged original branch builder. The 72 case × generator × arm rows, including roles and states, are in each `demonstration/*-report.json`; each manifest contains the full node list and frozen configuration. No topology ambiguity was found. Native/cARL specialist paths are 27/27, with one declared shared synthetic SystemOne judge, not independent judges.

Adverse observations: two invalid lifecycle generator outputs, one invalid specialist claim-coverage response, one specialist exception, one missing observed identity and one mismatched observed identity. Their descendants remain censored. One final specialist is budget-unavailable and its child is blocked. Eleven positions are dependency-blocked overall; 19/153 positions have no valid observation (12 generator, 7 specialist). Invalid/unavailable records never have disposition pairs. Valid null specialist scores remain null and are counted separately by dimension.

Normal sequential paths preserve 27 `pass → review_required` intermediate transitions, 27 `review_required → pass` final transitions, and each final `pass → pass` baseline comparison. Another 36 observed follow-ups retain `pass → pass`. Finding movement and policy warrant are not inferred from these scripted labels. All per-position intermediate/final pairs remain in receipts and reports.

Interruption: a real child exited 75 immediately after reserving `c02-sol-r1-e3-nc-g1`. At interruption: 89 reservations, 88 fake invocations, one reserved position. Recovery retained exactly one reservation and zero invocations for that position, recorded it interrupted and blocked its two descendants. The finished adverse campaign has 141 reservations and 140 invocations. Each demo resumed twice after completion; two further explicit resumes per campaign also left every file and evidence tip unchanged (`idempotence.json`). SQLite transaction concurrency tests admitted exactly one of two competing reservations.

All **110 tests passed**: 28 focused executor/full-matrix/preflight tests and 82 pinned instrument, continuation, RD05 tooling and harness regressions. Final test failures: **0**. New targeted tests inspect actual histories/branch markers, all source/policy contexts, frozen baseline references, shared judge identity, intermediate/final pairs, nulls/censoring, interrupted invocation counts, concurrency, provider-side context mutation and corruption before reservation. Eight additional preserved corruption probes rejected edge, source, policy, requested/observed identity, receipt, parent-request and hash-chain changes (`negative_corruption.json`). The focused tests also reject self-rehashed cross-arm/unit/sequence edges, authority escalation and packet/identity substitutions.

Read-only `verify --history` independently reconstructed both complete campaigns from preserved artifacts, including every manifest position, reservation, invocation, response, receipt, parent hash and chain transition. `normal_verify.stdout` and `adverse_verify.stdout` preserve those reconstructions. The exact packet, instrument, design and runtime bindings passed. The old 15-position slice also verifies without changing its files.

| Integrity anchor | Normal | Adverse |
|---|---|---|
| Manifest SHA-256 | `ff52e5e375bb4bdc6f5ff17a91f1a35ef82f7a0c5487af83f73fda52d89bf53c` | `e00675c8d218de30ffde5b2772b9ce10fc1d627a46b17aaed1178a0fc0130ef3` |
| Evidence tip SHA-256 | `9d9e5674f00194735de70c7fa8422eab115543c4d422341a9a5932e7f8e99352` | `5b9b7b2ecdb3b5b856a154d8cdf50ad220153b520e2ef422335e5e351d532b03` |
| Hash-chained events | `766` | `714` |

Original custody passed: **40,538 entries**, 1,165 operator-sealed files, 4,699 v5 files and 36 command records; zero changed/missing entries. All 48 pre-existing executor files outside the three extended code files, including all historical evidence, remain byte-identical. All 726 unrelated pre-existing worktree paths remain unchanged (`preservation.json`). No frozen v1 or v2 validator, decision, arm, source proposal or historical result was edited.

Combined preflight verifies all 96 inspected source bindings, the comparison package and original custody, then exits **2: BLOCKED/UNKNOWN**, with launch unauthorized. An initial temporary export omitted the 24 comparison-package files and exited 1; its receipt is retained as `development_incomplete_preflight.*`. Completing that export corrected the inspection, without altering repository evidence. Two earlier exploratory campaigns in temporary directories failed closed when executor bytes changed during performance work; they are not acceptance campaigns and no reserved position was resumed under changed code. Unrelated legacy CLI integration failures were not repaired or claimed to pass.

Simulation assumptions are isolated in each frozen configuration: deterministic fake identities, opaque unapproved packets, invented unit accounting, continued independent diagnostic branches, scripted review delivery with no JEV threshold/action mapping, and scripted branch markers/reversals. These demonstrate local simulation properties only, not real provider isolation or scientific validity. There is no cross-host/copy reservation authority; deployment-wide scope remains a live blocker.

Remaining live blockers: D01/D02 research prompt and construct approval; D03 challenge policy/thresholds and missing-score semantics; D04/D05/D10 governing policy, evidence adequacy/precedence/authority, approved source/reference packets and RD03 warrant/adjudication; D06/D07 statistical/missingness/censoring rules; D09/D11 actual model/judge identities, qualified one-shot transports, strict isolation/egress/tool containment, durable deployment/reservation scope, tariffs/usage/budget and explicit bounded authorization. No operational action or evidence-policy warrant was selected in this simulation.

**Q1 153-POSITION OFFLINE TOPOLOGY QUALIFIED — LIVE Q1 BLOCKED**
