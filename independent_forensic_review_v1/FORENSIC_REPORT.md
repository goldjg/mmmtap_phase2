# Independent forensic review: HydraFusion Max / MMMTAP Phase 2

**Verdict: not ready for live qualification under the requested strict isolation contract.**
Substantial implementation works offline, including the new Path B transport, but
confirmed parser/provenance defects and incomplete isolation and packaging remain.
Passing tests and a successful status-update turn do not complete the failed
integration task. No pilot or security-improvement conclusion is warranted.

**Review date:** 2026-10-12. **Mode:** read-only target examination and isolated
offline reproduction. **Blindness:** no Iris assessment was located, opened,
requested or used. A fresh, bounded transport-review subagent examined cARL;
the primary reviewer independently examined history, Python isolation/planning,
checkpoints and artifacts. Neither reviewer repaired the target implementation.

## Scope, evidence and limits

Examined `/home/prometheus/git/mmmtap_phase2/`, its original protocol and scoring
contract, HARNESS documents, qualification/investigation/Path B evidence,
`integration_readiness_v1/`, current Python source/tests, and relevant
`/home/prometheus/git/cARL-semantic-eval/` source, tests, Git state and binaries.
Paths below are relative to the Phase 2 root unless prefixed `cARL/`; that prefix
means the sibling `cARL-semantic-eval` worktree. Line numbers refer to the source
snapshots accompanying this report, not future edits.

The local session log is
`/home/prometheus/.copilot/session-state/3374c7d5-61e9-41b6-bfc5-0f0f55533363/events.jsonl`.
All 4,565 available events before the review request were indexed; the 347
integration-phase pre-tool records, user requests, relevant assistant claims,
available checkpoint history (including integration checkpoints 005-011),
failure/handoff/recovery records and retained CLI captures
were examined against the filesystem. Cloud history is coarser and stops earlier;
the local log supplies the failure and later status turn. Tool results can be
elided, and the failed fusion turn does not have a normal root conversation
projection. The hook records and current files fill some, not all, of that gap.
This is the complete *available recorded* history, not a claim of complete hidden
orchestrator internals, deleted temporary output, or provider-side visibility.
`evidence/session_scope.json` fixes the cutoff and hash of the pre-review event
bytes. Current review events and any other reviewer material are excluded.

Before testing, 960 target files were hash-inventoried. The independent tests ran
with external networking disabled and target mounts read-only; only review
outputs and scratch/cache directories were writable. Only trusted test fixtures
and local mock HTTP services were executed. **Zero experimental generator or
SystemOne calls, no pilot, no deployment, no target source repairs.** Ordinary
assistant/orchestrator model activity in the session log is not an experimental
assessor invocation. The two earlier, authorized qualification calls predate
this integration task and remain historical evidence, not new calls.

## Findings at a glance

Severity is impact on experimental integrity/readiness, not a CVSS score.
“Confirmed” means source plus an observed reproduction or filesystem fact;
“incomplete” is an unmet requirement, not proof of an exploit.

| ID | Classification | Severity | Finding | Principal evidence |
|---|---|---|---|---|
| D1 | Confirmed defect | HIGH | Path B accepts ambiguous/case-aliased provider JSON and can disagree with native JEV on the same bytes | `cARL/internal/assessment/policy.go:197-215`; `phase2/adapters.py:352-366`; transport forensic tests |
| D2 | Confirmed defect | MEDIUM | A new plan can use changed prompt text while retaining the original frozen-instrument digest | `phase2/integration.py:57-58,111-114,147-153`; `phase2/core.py:103-104`; scratch reproduction |
| D3 | Confirmed defect | MEDIUM | Python says one transport attempt when the Go missing-credential receipt says zero | `phase2/adapters_v2.py:270-274`; missing-credential reproduction |
| D4 | Confirmed defect | MEDIUM | Path B token usage is preserved in raw bytes but omitted from structured metrics | `phase2/adapters_v2.py:270-291`; `phase2/engine.py:187-195`; usage reproduction |
| D5 | Confirmed defect | MEDIUM | Failed preparation drops its persisted first-attempt artifacts at the Python boundary | `phase2/adapters_v2.py:237-256,275-277`; invalid-request reproduction |
| D6 | Confirmed provenance defect | MEDIUM | All nine “final” isolation captures are bound to an older adapter source hash | `isolation_controls_final/*/invocation.json`; `phase2/readiness.py:24-35`; hash audit |
| I1 | Incomplete requirement | HIGH | Codex strict no-unapproved-tools control is unresolved; post-routing rejection is not prevention | `phase2/isolation.py:142-219,266-284`; `phase2/adapters_v2.py:44-55`; fresh controls |
| I2 | Incomplete deliverable | HIGH | The readiness package is unsealed and lacks two required reports | missing `REMEDIATION_REPORT.md`, `path_b_transport_contract.json`, `SHA256SUMS.txt` |

No critical-severity defect, confirmed sandbox escape, demonstrated live
credential leak, or fabricated research improvement was established. That does
not certify those properties outside the reproduced scope.

## Confirmed defects: evidence, consequence and remediation

### D1 — Ambiguous provider fields change matched judgments (HIGH)

`CheckJSON` rejects duplicate keys with exactly equal spelling
(`cARL/internal/assessment/json.go:52-66`), but `ApplyPolicy` then decodes provider
objects into Go structs. Go JSON struct-field matching is case-insensitive.
The native Python parser selects exact `model`, `answers`, and `noul` keys.

A session-only Go test overlay reproduced this answer:

```json
{"claim_0000_supported":{"noul":1,"NOUL":0}}
```

Path B accepts it and uses **0**, producing `challenge_required`; native exact-key
extraction uses **1**. Similarly `"model":"expected","MODEL":"different"`
reports `different` in cARL, while native uses `expected`. Uppercase-only
`MODEL`/`ANSWERS`/`NOUL` is accepted by cARL without the canonical required API
field names. No target source was changed to reproduce this.

The shared policy decoder serves live, offline and replay paths
(`live.go:338,447`; `receipt.go:103`), so deterministic replay reproduces the
wrong acceptance rather than exposing it. This is malformed-input handling and
comparability failure, not evidence that the actual provider emits such data.
Fix exact-key/schema validation, reject aliases/ambiguous fields, and apply the
same negative corpus to both parsers. Do not merely add another success fixture.
Evidence: `evidence/transport/forensic_test.go`, `forensic.stdout`, `report.txt`.

### D2 — Frozen prompts are a snapshot, not the planning authority (MEDIUM)

`freeze()` writes `instruments/prompts.v1.snapshot.json`, but `plan_v3()` calls
`core.experiment_plan()`, which reads the current package’s `prompts.v1.json`.
`verify_instruments()` verifies the snapshot’s own hashes, not equality with the
prompt text consumed by that planner. `validate_v3()` reconstructs using that
same current-code path.

In a temporary package copy, appending an obvious forensic marker to C1’s prompt
produced a new plan that **passed `validate_v3`**, kept the original
`instruments_sha256`, and differed from the unchanged frozen prompt snapshot.
Original files were never edited. The changed plan had a different plan digest;
this is **not** acceptance of a mutated existing v3 plan. It demonstrates that
instrument identity can falsely imply unchanged prompt semantics across new
plans. Current stored v3 prompt contents match; no historical prompt alteration
was found.

Plan directly from the frozen template/question artifacts or enforce exact
cross-binding before constructing or validating a plan. Any semantic change must
create a new instrument version. Reproduction:
`evidence/reproduce_instruments.py`, `instrument_repro.stdout`.

### D3 — Wrapper invocation is mislabelled as a transport attempt (MEDIUM)

`PathBAdapter` derives `transport_attempts = int(mock_response is None)`, regardless
of whether HTTP was attempted. Running the real pinned sibling with no JEVKEY,
inside a network-isolated runner, produced `credentials_unavailable` and a valid
Go receipt with `attempts=0`, `live_calls=0`; Python provenance says
`transport_attempts=1`.

This overcounts network attempts and contradicts the embedded receipt. Distinguish
CLI invocations, reserved budgets, attempted HTTP requests, request-written events
and unknowable provider processing. Derive network counts from the verified
receipt, or use explicitly unknown values when unavailable. No automatic HTTP
retry was observed. Evidence: `evidence/transport/adapter_results.json` and
`adapter_missing_credential.json`.

### D4 — Available token usage disappears from structured metrics (MEDIUM)

A mock response containing usage `input_tokens=123, output_tokens=45` survived
byte-for-byte inside the receipt, but returned `Response.usage=None`.
`usage_metrics()` consequently writes null token counts and null `usage_raw`.
Native JEV does populate usage (`phase2/adapters.py:429-431`).

This is not destruction of original bytes and is not zero usage. It is a missing
extraction step that prevents comparable cost/usage exports even when the provider
supplies counts. Extract validated available metadata with its provenance; retain
null when genuinely absent, never synthesize zero. Evidence:
`evidence/transport/adapter_repro.py`, `adapter_results.json`.

### D5 — Preparation failures lose first-attempt files (MEDIUM)

The Go command persists intent, supplied request and explicit failure records.
If `prepare` fails, the Python adapter returns early with only process logs; its
artifact collector occurs later. Exiting `TemporaryDirectory` deletes the
preparation files. Actual `request={}` reproduction returned
`unsupported_contract_or_preparation_failed`, only `processes` in provenance,
no captured artifact set, and no top-level stdout/stderr.

The process log retains child stderr and exit status, and an enclosing engine can
retain the payload; this is not total erasure of all failure evidence. It is loss
of the cARL first-attempt artifacts the documentation promises to preserve.
Collect available files on every exit path after attempt reservation; retain
specific failure classes and never retry to manufacture replacement evidence.
Evidence: `evidence/transport/adapter_results.json`.

### D6 — The “final” isolation evidence predates final adapter source (MEDIUM)

Every original `isolation_controls_final/*/invocation.json` records adapter hash
`8296fecf6767c63b2c2ef70ac5106ae3cc51b2d7a40ca9807d04312764aecc42`.
Current/frozen-plan `adapters_v2.py` is
`888de370cc35fb8192b1951497d2fb6483d5f2b9d974311c93a04ed806860a4c`.
The remaining three recorded module hashes match. History places the controls at
02:37 UTC, followed by adapter/parser edits at 02:39-02:43 and assembly at 02:45.
`readiness.assemble()` copies the prior summary without checking these bindings.

Independent rerunning of all nine controls against **current** code succeeded
with the expected outcomes. That is new review evidence, not retrospective repair
of the stale package or proof that every earlier result was false. Require exact
implementation binding at collection/assembly; retain the old collection and
publish a new version rather than overwriting its hashes. Evidence:
`evidence/artifact_audit.json`, `evidence/reproduced_isolation/`.

## Incomplete implementation and qualification boundaries

### I1 — Strict no-tool assessors remain unresolved (HIGH)

Fresh controls confirm Copilot/Haiku and Gemini advertise zero tools on the
loopback BYOK path using the nonempty unmatched filter plus exclusions. Forced
Copilot tool output is rejected; the positive control genuinely executes a tool
and exposes the deliberately bound sentinel. The original empty filter’s 21-tool
failure is real and must not be dismissed as a parser issue.

Codex still advertises ten internal functions/collaboration tools. Forced exec
routing is observed and rejected; disabling the code-mode host prevents that
particular execution. The watchdog acts on debug/event output **after routing**,
not at a pre-execution authorization boundary. Final controls do not individually
exercise every advertised collaboration operation. Earlier retained spawn probes
show a routing failure because ephemeral rollout state is missing, not a robust
pre-dispatch deny proof. No escape or successful hidden child inference is claimed.

Mount isolation is a real read boundary: host sentinels are inaccessible and
`/work` writes fail EROFS. It does not prohibit all activity inside the process’s
own writable home or all internal tools. Thus the requested prevention guarantee
is still incomplete. `INTEGRATION.md:34-58` and the live procedure acknowledge
this correctly; it is not an undocumented live certification claim.

Retain the live block. A reviewed tool-free API/process broker or genuine
pre-dispatch interlock, with negative controls over the entire remaining surface,
is required before claiming compliance. A stronger post-hoc parser alone is not
that interlock.

### I2 — Original integration delivery stopped before sealing (HIGH)

As found, all three files remain absent:

- `integration_readiness_v1/REMEDIATION_REPORT.md`
- `integration_readiness_v1/path_b_transport_contract.json`
- `integration_readiness_v1/SHA256SUMS.txt`

The proposed plan, instruments, matrix, successful test outputs, Go validation
subpackage, mock checkpoint/export artifacts and live procedure exist. The
procedure itself requires the missing remediation report and package checksum.
There is no final target Python-source snapshot made by `finish_readiness.seal()`.
Five original integration todos remain in progress. Do not mark the component
implementation incomplete merely because the reports are missing: Path B’s v2
transport is implemented and independently tested. Conversely, its worker’s
“Complete” claim does not complete the whole package.

Finish only after engineering corrections and fresh evidence, using a new
version when changing frozen instruments. Seal a reconciled report, transport
contract, exact tested source/binary inputs and full manifest. This independent
report does **not** supply or replace the missing target deliverables.

## Suspected risks and untested controls — not promoted to exploits

**R1 — Unpinned runtime dependencies (MEDIUM).** The generator adapter verifies the
main Codex binary but mounts its entire release directory
(`adapters_v2.py:166-182`). It includes separate `codex-resources/bwrap`, `rg`,
code-mode and other helpers whose hashes are absent from frozen config. The broad
read-only `/usr` mount (`isolation.py:63`) also exposes OS runtimes; this is disclosed
but not a hermetic runtime freeze. The embedded sandbox helper in particular is
relevant to read-only behavior. Imported local `historical_extractor.archive` and
`historical_extractor.extract` code also falls outside the planner’s
`phase2/*.py` inventory (`core.py:11-12,104`), despite supplying archive/JSON/hash
validation. No change to those helpers was found. No helper substitution or compromise was observed.
Inventory and bind required helper/package hashes and relevant runtime versions,
or narrow the mounted closure. See `instrument_repro.stdout`; source/build
provenance for cARL is stronger than this generator dependency freeze.

**R2 — Retry and network equivalence (MEDIUM).** Copilot’s watchdog catches the
first observed failure, but cannot establish that an internal retry did not race
that event. A fresh HTTP 500 control saw one POST; that does not prove all
429/disconnect/streaming races or GitHub-authenticated behavior. Codex’s explicit
nonreserved provider correctly exposes client retry settings of zero in debug
logs; provider-internal retries remain unobservable. Live generator mode shares
host networking (`adapters_v2.py:195-196`), unlike the loopback network namespace;
it is not provider-only egress. Model catalogs are earlier authenticated metadata,
not current availability or served-version proof. Keep these distinctions and
perform separately authorized, bounded qualification only after acceptable
preventive controls exist.

**R3 — Controls are partly observations, not regression assertions (MEDIUM).**
`run_controls()` collects per-case analyses without asserting expected no-leak,
no-tool and request-count results for every control
(`isolation_controls.py:133-153`). Only namespace expectations are hard assertions.
Some unit tests parse retained captures rather than launching current CLIs
(`tests/test_integration.py:86-118`). Independent review explicitly checked the
new control outcomes; a future successful collection exit alone would not prove
all controls passed. Add explicit expected-result checks and bind live-equivalent
configuration differences. Staged-auth copying has an offline unit test; truly
separate authenticated arm sessions have not been live-qualified.

**R4 — Replay’s guarantee is anchored integrity, not origin (LOW).** Tests
with *newly recomputed anchors* accepted some internally inconsistent receipt
metadata: mismatched TLS server name / Content-Length in a successful live receipt,
and omitted default `live_calls` or added null error in v1 offline receipts.
These do not bypass an independently retained original digest and do not forge a
provider signature. Receipts expressly disclaim provider authentication. Harden
internal schema/metadata consistency where it is relied on; do not rebrand local
replay as provider attestation. See transport report for exact repro scope.

**R5 — Limited end-to-end behavioral coverage (MEDIUM).** The scripted adapter
reads source and always emits the same authored claim and a retained change,
regardless of challenge content (`integration.py:174-190`). The complete chain
proves wiring, hashes, histories and export, not that a real generator sees,
understands or revises findings correctly. Only three baseline synthetic inputs
are covered with nonempty claims; no attack-variant campaign, full size envelope,
real generated claims or independent adjudication was exercised. Add offline
fixtures that vary retained/revised/withdrawn/added findings and deliberately
swap/miss challenges, then separately qualify real behavior. Do not infer security
improvement from the current 153 mock successes.

**R6 — Attempt identity is not globally enforced (MEDIUM).** Fresh output
reservation prevents overwrite, but the same preparation/job can be explicitly
invoked into another directory and each call reports a first local attempt.
`readiness.qualify()` has per-directory reservation, not a global cross-run attempt
ledger/retry link (`readiness.py:87-101,139-145`). This is not an observed automatic
retry; the procedure demands renewed authorization. Before experimental use,
make intentional retries separately identifiable and enforce the intended global
budget/deduplication semantics.

## Independently verified working controls

| Control | Independent result and evidence |
|---|---|
| Full Python regression suite | **114 tests passed** in 162.588 s; external network disabled, target read-only; AST parsing of 20 files succeeded. `evidence/python_suite.*`, `artifact_audit.json` |
| Full Go suite / static checks | **242 top-level tests / 391 including subtests / 16 packages passed**, no skipped tests; vet, formatting and diff checks clean. `evidence/transport/validation_v2.json` and logs |
| Additional transport forensics | Four independent Go tests / nine including subtests, plus three actual-adapter reproductions. They assert observed defects/limits, not desired correctness. Loopback only. |
| Current real CLI controls | **Nine controls reproduced**. Haiku/Gemini text accepted as mock, zero advertised tools; Codex text accepted as mock with ten advertised tools; forced tools and 500 failures rejected. Positive controls expose bound sentinel with two POSTs. `evidence/reproduced_isolation/` |
| Namespace behavior | Host sentinel absent in negative and present in positive control; `/work` writes denied with errno 30; external connection denied. This is a mount/network test, not universal no-tool certification. |
| New independent mock chain | **153 fresh `mock_ok` checkpoints**, three frozen baseline cases × three generator labels × 17 jobs; all arms, both E3 orders and C3. **99 nonempty generator assessments, 27 Path B policy evaluations/replays**. No generator CLI/provider invoked by this scripted chain. |
| Resume and blinding | Reused all 153 checkpoints, zero new checkpoints, checkpoint bytes unchanged; independent ledger/lineage checks passed; **63 blinded pairs** exported, keys separate and owner-only. 2,772 omitted pairs are unexecuted full-plan pairs, not 2,772 failures. `evidence/e2e_corrected_runner.*` |
| Matrix and gates | v3 validates against current code; **6,885 jobs = 4,455 generators + 2,430 adversaries**, 135 identities / 108 byte hashes; **3,240 feasibility rows**, all explicitly blocked pending live qualification. Engine refuses v3 live experiment execution. |
| Native/Path B request matching | Existing constructor reused; fixture request bytes and typed questions match; independent end-to-end tests preserve separate evaluations and both orders. No cARL-only question pack silently substituted. |
| Path B transport mechanics | Fixed HTTPS endpoint, TLS verification, no proxy/redirect/reuse fallback, bounded body/timeouts, explicit error outcomes, one client attempt; raw response/metadata and local receipt retained for normal post-preparation cases; replay works without provider. Actual API/service capacity remains unqualified. |
| Policy reuse | Additive `pack.PolicyTraceInDir` uses existing pack/profile/dependency/override/conflict machinery; explicit typed rules only from effective non-overridden packs. No ordinary prose-to-policy execution. |

The first independent E2E runner had a shell-quoting SyntaxError before invoking
any target code. The separate corrected runner succeeded; both logs remain. The
transport reviewer likewise preserved an initial runner setup error involving
`/dev/null`, corrected only its private runner, then ran successfully. No target
repair or hidden inference retry was involved. Race testing was not reproduced;
the existing optional race run reports unsupported host VMA, so race safety is
not established by the ordinary Go pass.

## Preservation and instrument reconciliation

Seven pre-existing checksum sets independently pass: protocol/corpus documents,
eligibility, reconciliation, historical extraction, original qualification,
cARL investigation, and sealed Path B v1 validation. The original harness’s
29,185-file manifest has exactly the two already explained source mismatches:
`phase2/adapters.py` from earlier qualification, and the current version-gated
`phase2/engine.py` integration. Original plans, results, checkpoints, ledger,
adjudication packets, frozen archive and historical artifacts remain unchanged.
No historical case was admitted: v3 contains exactly the original 135 identities.

Frozen archive SHA-256:
`a3fe94069009f328b0a46bb52a7ff52d2c2bedfcd0eb3babe360eea1c884cc21`.
Unchanged installed Path A binary SHA-256:
`b34696d54d0b9c910d48c9adbe0155f825617d8e4c8981e58a2f50b5d0868428`.
Current bound Path B v2 binary SHA-256:
`be5a4b98d0acfd516839e9a5ab23071830f39ce0afa808d56a6acbbba1c92716`.
V3 manifest identity:
`6d146b6974663b5ff4b3c790184d05e6652ac693b5a75bb683e53d74b36a5950`.

Independent cARL comparison of all 185 tracked files against HEAD
`8a9d5ba6540fb52a7cfa6cbcf4c125e514805c04` finds only four existing documentation
files changed. `cmd/carl`, `internal/review`, `internal/semantic`, existing pack
code, embedded assets, dependency manifests and shared defaults match HEAD.
All 65 protected cARL baseline hashes match. Most new Path B implementation is
**untracked**, so ordinary `git diff --stat` omits it; it was explicitly inspected.
No source commit was requested or made. Phase 2 itself is not a Git repository.
Sealing source snapshots therefore matters especially here.

The old live-draft binary remains beside v2, but frozen config selects **v2**, not
the draft. Sealed v1 evidence was not overwritten to hide the later interface
revision. The proposed policy copies the earlier numeric thresholds (reviewer
0.5; inactive cautious alternate) into a separate qualification proposal; it is
not PI approval. Native questions and current prompt bytes retain their original
semantics. Path B’s supplied evidence replaces Path A only in the explicitly
amended proposed v3; authenticated Git evidence is not fabricated. Both E3 orders
and matched-turn C3 are preserved. Topological scheduling is not randomized
wall-clock counterbalancing or control of provider drift.

## HydraFusion orchestration failure and actual recovery

All times below are **UTC** (add one hour for the local timestamps shown in the
conversation). Evidence references are original local `events.jsonl` line numbers;
selected metadata and a tool index are frozen under `evidence/`.

1. **2026-10-11 22:36:24–25** — original HydraFusion integration cascade starts
   (`session.fusion_resolved`, line 2792). The draft performs extensive netless
   CLI probes, writes a live-draft transport, and starts isolation code.
2. **2026-10-12 02:01:40** — draft phase records success as a model phase, not
   completed deliverables (line 3678). The separate gate completes at 02:05:18
   (3699), and a strong-repair handoff follows at 02:05:42 (3700). Handoff explicitly
   says workspace effects remain and prior claims are not proof.
3. **02:19–02:42** — repair work and a bounded transport worker implement/fix
   v2, adapters, plan and test wiring. The worker’s “Complete” is scoped to Go
   transport. Full Go logs and current v2 code substantiate that component claim.
4. **02:37–02:45** — controls are captured, then adapter/parser changes occur.
   An initial Python attempt fails; the missing `strict_json` import is corrected, and
   final suite/assembly start together at 02:45:08 (4485). The retained successful
   outputs and files show these bounded commands completed; prior failure logs
   are not hidden. This ordering explains D6’s stale control hash.
5. **02:47:12** — strong repair fails with a model-call `400 internal server
   error` (4491–4492). The runtime explicitly warns that the workspace may contain
   partial changes and that no earlier result was committed or restored. The
   filesystem indeed contains the partial-but-substantial implementation and
   missing final deliverables. This is an orchestration failure, not a failed
   SystemOne experiment and not a target rollback.
6. **02:48** — the quick update inspects files and acknowledges the three missing
   deliverables. **02:57:08** — a *different fusion ID* completes the user’s status
   update (4544–4558). Its “commit started/completed” events are orchestration
   projection, not a Git implementation commit or completion of the original
   task. The update still says the package is unfinished; it inaccurately leaves
   “complete live transport” as future work although v2 already exists and passes.
7. No subsequent original-task seal or repair completion is recorded before the
   review request. Shutdown at 05:59 and resume at 06:05 are session lifecycle
   events, not delivery verification. The five in-progress original todos agree
   with the missing final files, not with a finished readiness package.

Thus the evidence does **not** support a completed/remediated integration, nor a
claim that the whole implementation was lost. It supports a failed orchestration
with preserved draft/repair effects, successful bounded component tests, and an
unfinished integration handoff. The current tests were independently reproduced;
the verdict does not depend on trusting HydraFusion’s success messages.

## Prioritized remediation — separate authorization required

1. **Keep live qualification/pilot blocked.** Resolve the preventive no-tool
   boundary and acceptable retry/egress semantics first (I1, R2). Do not use an
   operator checkbox or a rejected post-hoc output as proof of prevention.
2. **Correct matched parsing and receipt provenance** (D1, D3–D5): exact-key
   provider schema, real transport accounting, usage extraction and complete
   failure artifacts. Add shared adversarial parser fixtures and wrapper tests.
3. **Make the frozen instrument authoritative** (D2), bind required runtime
   helpers (R1), and regenerate a new versioned plan rather than mutating old
   instruments. Preserve explicit supplied-not-Git provenance and model-alias
   uncertainty.
4. **Strengthen/re-run controls against exact final code** (D6, R3, R5), including
   all remaining internal tools, failures and challenge-sensitive negative chains.
   Keep old failed/stale evidence, add fresh hash-bound results, and enforce
   cross-run attempt identity/budget policy (R6).
5. **Finish and seal the target package** (I2): reconciled source-referenced
   remediation report, transport contract, actual limitations, exact build inputs,
   reviewed qualification procedure and SHA-256 manifest. Do not substitute this
   forensic report for those deliverables.
6. Only then seek separately scoped authorization for real adapter qualification.
   Retain first failures and raw evidence; no implicit retry, pilot, historical
   admission, policy approval or security-effectiveness inference follows.

## Report freeze

`SHA256SUMS.txt` covers this report, machine-readable findings, evidence logs,
source snapshots and reproducible review scripts. `REPORT_SHA256.txt` pins the
report itself. These are local integrity anchors, not signatures or provider
attestation; retain an independent copy of the hashes. `evidence/review_preservation.json`
records the final before/after target check. No implementation defect was repaired.
