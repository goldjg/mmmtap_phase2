# Synthetic Q1 full-matrix qualification v1

Engineering simulation only. All source, governing-policy and challenge-policy
packets are synthetic and explicitly unapproved. No provider adapter, JEV/cARL
call, scientific threshold, policy warrant, release action or live approval.

From the repository root:

```sh
python -m engineering_qualification_v1.q1_executor matrix-demo --output /tmp/q1-full-matrix-new
python -m engineering_qualification_v1.q1_executor verify --campaign /tmp/q1-full-matrix-new/normal-campaign --history
python -m engineering_qualification_v1.q1_executor verify --campaign /tmp/q1-full-matrix-new/adverse-campaign --history
python -m unittest -q engineering_qualification_v1.q1_executor.test_full_matrix engineering_qualification_v1.q1_executor.test_executor engineering_qualification_v1.test_preflight
```

The output directory must be new. `matrix-build --scenario normal|adverse
--output NEW_DIRECTORY` reproduces either frozen fixture byte for byte.
`resume --campaign DIRECTORY` uses the existing executor and its one-shot
reservation, raw-response, receipt and recovery machinery. The read-only
`verify --history` reconstructs every event and receipt from SQLite, checks
the manifest and every request/response/binding, and invokes no provider.

The demonstration executes two separate 153-position campaigns: all valid
normal paths, then adverse paths. They are separate engineering scenarios on
the same topology, never experimental repetitions or pooled observations.
Each campaign preserves all 153 positions, including censored descendants.
Adverse execution deliberately exits a child process with status 75 after a
committed reservation, recovers it as interrupted, then resumes twice more.
Both repeated resumes must leave every campaign file byte unchanged.

The 12 local Git design anchors in `full_matrix_fixture/design-pins.json`
bind RD01–RD04/IE01, the current hypotheses/qualification plan, instrument,
continuation code, original generator configuration and branch builder at
`c9f546b1113de079adbced5995d0a1ffb3c8fc07`. The unchanged v2 assessment and
specialist validators remain pinned by `contracts.json`. Missing local blobs
fail closed; the executor never fetches them. No historical file is repaired.

The full-matrix contract is `synthetic-q1-full-matrix-v1`, layered on the
existing `mmmtap-q1-simulation-executor-v1` reservation/receipt protocol.
Each manifest embeds its frozen configuration, all 153 nodes, explicit
dependencies, shared B0 references, case/generator/R=1/arm/turn/role, fake
provider/model/shared-judge identity, three packet digests, instrument/contract
versions, expected accounting and explicit invented attempt/budget limits.
Validation regenerates the entire manifest and compares every node and edge
with the original `phase2.core.experiment_plan` builder. Counts alone never
authorize an edge. Case sampling-role labels remain outside provider requests.

| Arm | Generator | Specialist | Dependencies within each matched unit |
|---|---:|---:|---|
| B0 | 1 | 0 | No parent; one frozen baseline |
| C1 | 1 | 0 | B0 → self-review |
| C2 | 1 | 0 | B0 → re-expression |
| C3 | 2 | 0 | B0 → neutral 1 → neutral 2 |
| E1 | 1 | 1 | Native judges B0; continuation binds both |
| E2 | 1 | 1 | cARL judges B0; continuation binds both |
| E3_NC | 2 | 2 | Native judges B0; G1 binds both; cARL judges G1; G2 binds both |
| E3_CN | 2 | 2 | cARL judges B0; G1 binds both; native judges G1; G2 binds both |
| Per unit | 11 | 6 | 22 dependency edges |

Three source roles × original gemini/haiku/sol identity slots × R=1 gives
nine matched units: **99 generator + 54 specialist = 153 positions**, with
27 native and 27 cARL specialist paths and 198 edges. The paths have distinct
presentation identifiers and the same synthetic underlying SystemOne judge.
They do not represent independent judge replication or actual served models.

Each request receives only its dependency ancestry: the shared B0 plus its
own branch's earlier assessments/specialist observations. Frozen baseline
receipts are referenced by position and hash; nine B0 attempts supply every
matched arm. Private branch markers test that one arm's output cannot appear
in another. Provider request objects are copied before invocation so provider
mutation cannot alter canonical validation context. Packet bytes and all parent
receipts are rechecked at each reservation. Tests demonstrate this isolation
for the simulation; they do not certify real provider context isolation.

Governing context is identical across a case's matched arms. Controls receive
no challenge-policy content or specialist review. The separate challenge
packet contains adversarial text claiming permission, explicitly without
governing authority; it cannot change the persisted governing packet. Native
and cARL paths use the existing three-dimension judge request/parser. Review
delivery remains a clearly isolated simulation placeholder with no selected
JEV threshold, cARL policy semantics or derived operational action.

Simulation assumptions: one non-refundable invented unit per reservation;
local fake identities; independent diagnostic branches may continue after
failure; scripted disposition reversals and private history markers. These
are engineering choices, not future live transport/stop/analysis contracts.
Operational action, obligations, evidence adequacy and policy warrant remain
unavailable. Invalid, unavailable, interrupted and blocked observations never
become unchanged dispositions. Intermediate and final exact pairs remain
separate even when the final label returns to B0.

The preserved v1 slice is still audited without changing its artifacts.
`legacy-software.v1.json` explicitly anchors its historical producer/runtime
fingerprint; compatibility replay accepts only that exact old fingerprint
under the same Python/SQLite runtime. Newly created campaigns bind the current
auditor/executor bytes. The original `SHA256SUMS.txt` remains the historical
slice seal; the full-matrix increment has a separate seal and evidence.

See `full_matrix_evidence/RESULTS.md` for actual counts and validation receipts.
Before live Q1: approved source/reference and governing/challenge packets,
prompt/delivery and operational sidecar contracts; RD03/policy warrant and
evidence adequacy/precedence/authority decisions; D06/D07 analysis, missingness
and censoring rules; qualified one-shot transports, actual identities and
strict live isolation/containment; tariffs, usage/budget/reservation scope and
explicit bounded authorization. None is supplied by deterministic success.
