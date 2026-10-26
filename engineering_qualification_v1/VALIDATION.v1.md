# Observed offline validation — 2026-10-26

Baseline: `b06371e48af5919af6fffd563fb1226d8be0dae4`. Commands, actual
outputs and hashes are under [evidence/](evidence/); final command receipts
include UTC start/end times and exit statuses. Earlier tool-observed results
are explicitly identified as having no separate timestamp receipt in
[observed_offline_checks.v1.json](evidence/observed_offline_checks.v1.json).

| Check | Observed result |
|---|---|
| Committed-source RD05 + v2 instrument + continuation + complete harness suite | **82 tests passed**, 41.616 seconds |
| New preflight negative tests | **6 tests passed**, 0.068 seconds; altered/missing bytes, unsafe paths, symlinks, duplicate/invalid inventory entries, malformed JSON, changed custody manifest, missing inputs and no-network/process/write boundary |
| RD05 fixture verification / inventory | Passed: 14 trajectories, 31 endpoints, all 16 predicate states, 16 content-file hashes; historical blank structured reviewer templates remain blank |
| Comparison checksum / read-only recomputation | All 23 checksum lines passed; B matches recomputation **31/31**; before/after hashes of all 24 comparison files identical. `reproduce.main()` was never called, so no comparison files were regenerated |
| Combined preflight against committed source + original custody | **Exit 2, BLOCKED/UNKNOWN**: six checks PASS, twelve launch-readiness checks BLOCKED/UNKNOWN; no FAIL. Always `launch_authorized=false`, zero calls |
| Default preflight against existing locally incomplete v2 checkout | **Exit 1, FAIL**, correctly reporting pre-existing missing/changed upstream files; no originals restored or overwritten |
| Existing final custody verifier | **Exit 0**: 40,538 original entries, 1,165 operator-sealed files, 4,699 v5 files, 36 command records; no changed/missing entries; live qualification blocked |
| Broad legacy suite | **Not passing**: 116 tests ran, plus three class setup errors because Go's default build cache is read-only |
| Affected legacy classes with repository-local Go cache | Go build progressed; **15 tests passed**, but two other class setups still fail because frozen integration code requires the absent Codex `0.162.1-aarch64-unknown-linux-musl` executable. Exact stderr/receipt retained; no substitute executable or instrument was introduced |

The last environmental errors are reproducible offline at
`phase2/integration.py:34`; the historical pinned executable is absent.
Installing/rebinding it or editing the frozen configuration is outside this
bounded increment. The broad suite is not represented as green. The new
preflight and the applicable v2 deterministic tests passed, but full legacy
environment qualification remains incomplete.

Existing custody-verifier output SHA-256:
`3edbc2744e840148b5efda742fb9d8bf8cc339db6519993bda5dd6e76e33eb2e`.
Combined preflight output SHA-256:
`0eff805f00154b98a53a9a6dd54bda802fb07e86bbea61cb67a7fc8d2520589d`.
Preservation-baseline SHA-256:
`edd040e78fc0d5ad152c1b33763f9871e39d2d02cc6fb74753c726eb40793a4f`.

The pre-existing tracked working diff is separately fingerprinted before and
after this increment; committed changes are confined to the new package.
The original local custody evidence and sanitized upstream evidence are
different preservation surfaces and are checked separately. No provider,
JEV, external evaluator or campaign call occurred. Passing deterministic
tests establishes neither experiment readiness nor scientific validity.

**OFFLINE ENGINEERING PREFLIGHT INCOMPLETE — BLOCKERS LISTED**

The executable preflight is implemented and verified. Q1 engineering remains
incomplete as detailed in [READINESS_GAPS.v1.md](READINESS_GAPS.v1.md), with
method/policy decisions outstanding and the full legacy regression environment
unavailable. Explicit human approval alone would not remove those technical
blockers.
