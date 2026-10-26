# Offline engineering qualification preflight v1

Read [RD05 closure](RD05_CLOSURE.v1.md) and the
[evidence-backed gaps and remaining human decisions](READINESS_GAPS.v1.md).
Actual test, custody and preflight results are in [VALIDATION.v1.md](VALIDATION.v1.md).
This package adds no executor and changes no frozen instrument or matrix.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest -q engineering_qualification_v1.test_preflight
PYTHONDONTWRITEBYTECODE=1 python -m engineering_qualification_v1.preflight
```

The preflight reads local files only. Every check reports `PASS`, `FAIL` or
`BLOCKED/UNKNOWN`; it always reports `launch_authorized=false` and zero
provider calls. Exit **1** means an integrity failure; exit **2** means the
inspection completed with launch blockers/unknowns. There is no exit that
grants launch authority. Missing approvals, prices, identities and isolation
evidence remain unknown, never zero or implicitly approved.

`--source-root PATH` selects a local export of the immutable inspected commit
`b06371e48af5919af6fffd563fb1226d8be0dae4`. The exact 96 byte bindings are in
`bindings.v1.json`; changed/missing code cannot inherit this baseline's checks.
`--custody-root PATH` additionally verifies the original **40,538-entry**
preservation baseline and its pinned hash. Public sanitized copies do not
satisfy original custody. This check supplements the existing verifier:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m operator_execution_v1 verify
```

In this session the checkout contains original custody material and unrelated
local edits/deletions, while upstream contains later v2 files and sanitized
historical copies. Those local differences are preserved. Reproduce inspection
against upstream without overwriting them:

```sh
mkdir .offline_qualification_source
git archive b06371e48af5919af6fffd563fb1226d8be0dae4 | tar -x -C .offline_qualification_source
PYTHONDONTWRITEBYTECODE=1 python -m engineering_qualification_v1.preflight \
  --source-root .offline_qualification_source --custody-root .
```

Remove only the temporary export afterward. The source-only receipt leaves
original custody `BLOCKED/UNKNOWN`; the combined receipt checks the original
local custody separately. Default inspection of this locally incomplete v2
checkout correctly fails the source bindings. Receipts record source roots,
exact executable/configuration hashes, UTC observation time and the pinned
commit. They do not establish provider connectivity, current model identity,
policy approval, affordability, strict live isolation or scientific validity.
