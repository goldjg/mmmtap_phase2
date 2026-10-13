# MMMTAP Phase 2 forensic remediation

**Status: offline remediation and validation complete.** The corrected
revision-5 implementation passed the complete Python and Go suites, fresh
offline CLI controls, full mocked chains and a separate archive/provenance
audit. This package is the new delivery; its `SHA256SUMS.txt` must verify before
any evidence is relied on.

**Live qualification remains blocked.** No live generator or SystemOne calls,
pilot, full experiment, deployment, historical-code execution or new corpus
admission was performed. Offline mocks do not establish model behavior,
scientific improvement or current served-provider identity.

## Evidence baseline and scope

The original independent forensic report and its separate transport evidence
were treated as findings to reproduce, not instructions to trust. The reviewed
material included the original protocol/scoring contract, HARNESS documents,
plans v2/v3, integration/qualification/investigation/Path B packages, current
Go/Python implementation and tests, and available HydraFusion session records.
No separate Iris review was supplied or required.

The retained history supports an interrupted integration with substantial
working changes, not a rollback or completed delivery. Its component transport
completion did not finish the integration package. Original reports and missing
original deliverables were not rewritten to change that history.

The pre-change baseline covers **35,835 workspace entries** (35,819 files and
16 symlinks) and **198 cARL entries**, including outstanding worktree changes.
Phase 2 is not a Git repository. The cARL branch is
`feature/semantic-evaluation-jev`, at unchanged HEAD
`8a9d5ba6540fb52a7cfa6cbcf4c125e514805c04`. Its existing dirty/untracked Path B
work was preserved; no implementation commit was made. HEAD alone therefore
does not identify the tested implementation.

`evidence/baseline/` retains inventories, original Git state/diffs and source
backups. The baseline JSON SHA-256 is
`ea142c9fb493d9b862ee390a85e8c45c5c6b015043e6b2e76d441d60306e06e2`.
Final implementation source bytes are under
`v5/instruments/software_source/`; intermediate red/green source versions are
content-addressed in `evidence/source_objects/`.

For earlier commands, missing source-object copies were recovered from the
preserved baseline plus this session's recorded edits, and accepted only if
their bytes matched the contemporaneous command hashes. This is derived byte
recovery, not a retroactively executed test. The method, 13 affected command
records and two unapplied edit events are disclosed in
`evidence/source_recovery.json`. Later commands captured source objects directly.
The rejected candidate's original preservation reporter was also recovered to
its recorded producer hash without executing it; see
`evidence/producer_recovery.json`.

## Finding disposition

`REMEDIATION_LEDGER.csv` is the complete finding-level record: D1-D6, I1-I2,
R1-R6, and the additional remediation regression C1. It records original
severity, reproduction, impact, correction, regressions, status and limitations.
Source locations below refer to the final source snapshots. `cARL/` means the
sibling `cARL-semantic-eval` tree.

| Finding | Corrective result and source | Evidence |
|---|---|---|
| D1, HIGH | Native `parse_systemone` and Go `ParseProvider` enforce the same exact-key typed-response schema. Duplicate/case aliases, unknown fields, null/wrong types, invalid ranges, non-finite/overflow numbers and malformed representations fail closed. Legitimate optional metadata is retained. `phase2/adapters.py:353`; `cARL/internal/assessment/provider.go:62`, `policy.go:190`, `json.go:38`. | Shared authored and exact historical response fixtures; `tests/test_remediation.py:27`; `cARL/internal/assessment/remediation_test.go:36-132`; `JEV_PATH_B_EQUIVALENCE.json`. |
| D2, MEDIUM | Planning consumes actual snapshots and rejects runtime semantic/source/build drift. Jobs and checkpoints bind the implementation and instruments. `phase2/integration.py:24,142,192,239`; `phase2/software.py:28,67,132`; `phase2/engine.py:198`. | Prompt/question/schema/role/policy/source/helper/binary mutation regressions, `tests/test_remediation.py:270-361`; `FROZEN_INSTRUMENT_VALIDATION.json`. |
| D3, MEDIUM | CLI launch attempts, started CLI processes, HTTP invocations and request-written events are distinct. A verified missing-key receipt reports zero HTTP attempts; incomplete evaluation evidence reports unknown, not an invented count. `phase2/adapters_v2.py:178`; `phase2/isolation.py:179`. | Missing-key, launch-failure and interrupted-evaluation regressions, `tests/test_remediation.py:80,139,158`; transport report. |
| D4, MEDIUM | Available structured token usage comes from the verified raw receipt response, with provenance `verified_receipt.raw_response.usage`. Missing metrics remain null; costs are not fabricated. `phase2/adapters_v2.py:304-355`. | The original lost 123/45 counters reproduce before correction; `tests/test_remediation.py:90`; full mock receipt/usage comparisons. |
| D5, MEDIUM | Engine reservation precedes payload preparation. Safe request/process/first-attempt artifacts survive preparation, staging, response and cleanup failures. Checksum line/file, prepared request, raw response, executable and replay must agree. `phase2/engine.py:198`; `phase2/adapters_v2.py:178`. | Fifteen Path B lifecycle regressions at `tests/test_remediation.py:54-269`, including partial/missing/malformed evidence, cleanup failure and nested credential echoes. |
| D6, MEDIUM | Controls bind the complete selected source and executable/helper closure. Assembly rejects stale/tampered matrices and rederives analyses from retained raw captures. `phase2/isolation_controls.py:236,287`; `phase2/readiness.py:25`. | Stale-control red reproduction and regression, `tests/test_remediation.py:296`; 48 fresh v5 controls, not reused candidate-v4 controls. |
| I1, HIGH | **Unresolved: all generators remain blocked.** All ten advertised Codex internal routes were probed. Post-routing rejection is not preventive authorization. `phase2/adapters_v2.py:163`; `phase2/isolation_controls.py`. | `ISOLATION_VALIDATION.json`; configuration-bypass regression at `tests/test_remediation.py:437`; raw v5 controls. |
| I2, HIGH | Resolved in this new package; the original unfinished integration package remains untouched. | Required reports, transport contract, exact plan/build/source/instruments, full checksum coverage and `verify_package.py`. |
| R1, MEDIUM | Selected local runtime/config/test/embedded sources, imported extractor code and the full mounted Codex release are bound. The independently rebuilt Path B binary is byte-identical. **Partially resolved:** host kernel and broad read-only `/usr` are not a hermetic runtime image. | `phase2/software.py`; source/helper mutation tests at `tests/test_remediation.py:334,349`; reproducible-build command. |
| R2, MEDIUM | **Unresolved, now with observed client retries:** without the watchdog, one HTTP-500 CLI invocation made six POSTs for Haiku/Copilot and six for Gemini/Copilot. Codex made one. Authenticated-route equivalence and provider-only live egress remain unqualified. | `copilot_retry_no_watchdog`, `gemini_retry_no_watchdog`, `codex_retry_no_watchdog` in the fresh control matrix. |
| R3, MEDIUM | Explicit containment/observability assertions and raw-analysis verification replace collection-only success. Expected blocked outcomes are not mistaken for strict qualification. | `phase2/isolation_controls.py:153,287`; mutation regression at `tests/test_remediation.py:421`; 48 fresh controls. |
| R4, LOW | Replay checks required canonical fields and endpoint/TLS/body-length consistency. **Local integrity is still not provider-origin attestation.** `cARL/internal/assessment/receipt.go:118`, `live.go:363`. | Red receipt mutations; `cARL/internal/assessment/remediation_test.go:133,168`; complete Go suite. |
| R5, MEDIUM | Nonempty mocks cover all 135 identities and depend on correctly bound challenge content, with retained/revised/withdrawn/added claims. All 6,885 jobs and the independent archive/lineage/prompt audit passed. | `phase2/integration.py:261`; `tests/test_remediation.py:378,397`; final chain/archive report. |
| R6, MEDIUM | Current qualification reserves identity in a fixed workspace registry before parent/preparation/staging. A fresh output directory cannot silently repeat it. **Bounded resolution:** direct/legacy CLIs and cross-host/provider exactly-once execution are outside this guarantee. `phase2/readiness.py:138`. | Cross-directory and failed-parent regressions at `tests/test_remediation.py:310,362`. |
| C1, HIGH | The first strict candidate incorrectly rejected legitimate provider `type` and choice `confidence`. It was rejected, corrected and separately revalidated as v5. | Both-language red metadata and exact historical-response runs; new positive/negative fixtures; `CANDIDATE_V4_REJECTED.json`. |

The parser comparison concerns **underlying SystemOne evidence**, not the final
policy decision. cARL's deterministic arbitration and thresholds remain separate
and unchanged. Choice-response parser coverage does not add choice questions to
Path B's frozen noul-only question catalog.

## Rejected candidate and corrective iteration

The first candidate passed its authored fixtures and offline suites, but a
read-only comparison with the retained native provider response exposed missing
schema coverage. The historical response contains answer `type` and choice
`confidence`; those are legitimate metadata, not ambiguous aliases. Both parsers
rejected the exact bytes before the correction.

The original response file remains unchanged:
`adapter_qualification_v1/attempts/native_jev/raw.json`, SHA-256
`c1c0e27543d32406415d615824b67bbcb67592846a3fd882d50c7bf212ec6263`.
Its decoded response hash is
`1c22046848af88847d48723e2019de35dd33b85055563b9c869a0b9818cd0bb8`.
The shared imported fixture is explicitly labelled unverified historical
provider evidence, not a new call. Fifteen additional authored metadata cases
cover valid tags/confidence and invalid aliases/types/ranges.

The obsolete mock run was deliberately interrupted with SIGINT, preserving
**1,112 completed checkpoints and one incomplete reserved attempt**. Its
4,454-entry archive, command exit 130, instruments, executable, plan and controls
remain at the package root, identified by `CANDIDATE_V4_REJECTED.json`.
They do not certify v5. A subsequent Go test-oracle error (decoding metadata as
only floating-point values) was corrected in the test, and its failing log was
also retained. No failed inference was reissued to replace evidence.

V5 lives in a distinct directory with new source/build/instrument/job identities.
Its plan revision is **5**, using the existing software-bound **format v4**.
Names such as `plan_v4`, `config.v4.json` and `adapter_readiness_v4.json` denote
that format, not permission to use rejected root-candidate results.

## Recorded commands and observed validation

All execution below used the retained `offline_run.py` wrapper: read-only target
mounts, private writable scratch/caches, stripped environment, `JEVKEY=""`,
external networking disabled, and dependency downloads disabled. Loopback HTTP
fixtures are not provider calls. Each command directory records exact argv,
cwd, environment, timestamps, exit status, elapsed time, before/after source
hashes and stdout/stderr hashes. Full records are under `evidence/commands/`.

The principal reproduced red commands were:

```sh
# cwd: mmmtap_phase2
python -m unittest discover -s tests -p test_remediation.py -v
python -m unittest discover -s tests -p test_remediation.py -k PathBProvenanceRegressions -v
python -m unittest discover -s tests -p test_remediation.py \
  -k FrozenInstrumentRegressions -k MockChainRegressions -v

# cwd: cARL-semantic-eval
go test -count=1 -json -run '^TestForensic' ./internal/assessment
go test -count=1 -json -run '^TestForensicHistoricalProviderMetadata' ./internal/assessment
```

The first Python run reproduced changed-prompt acceptance, HTTP 1-versus-0,
missing 123/45 usage, lost preparation artifacts and malformed-provider
acceptance. The Go run reproduced case-alias acceptance and receipt consistency
defects. Later red runs reproduced lifecycle, stale-control, cross-directory
reservation, challenge-independence and historical-metadata failures. These were
actual assertions against pre-fix bytes, not inferred from a final test pass.
`REGRESSION_EVIDENCE.json` links eight red command records and their exact
original source objects.

| Final command label | Actual command / entry point | Observed result |
|---|---|---|
| `v5-final-python-suite` | `python -m unittest discover -s tests -v` | **144 tests passed**, no skips; 313.205396 s. Thirty additional Python regression tests relative to the 114-test forensic baseline. |
| `v5-final-go-suite-and-vet` | `go test -count=1 -json ./... && go vet ./... && test -z "$(gofmt -l internal/assessment cmd/carl-assessment-challenge)" && git --no-pager diff --check` | **247 top-level / 512 including subtests**, 16 packages; vet/format/whitespace passed; 31.26897 s. Five additional top-level Go regression tests. |
| `v5-final-bound-build-and-freeze` | `build_path_b(v5/bin/carl-assessment-challenge-v5)`; `freeze(v5/instruments, binary)`; `verify_instruments(...)` | Source-bound sibling build and frozen semantic/source verification passed; 33.678299 s. |
| `v5-final-reproducible-build` | `build_path_b(...)` in a separate retained scratch location; compare both executable hashes | Byte-identical executable; 6.201576 s. |
| `v5-final-bound-isolation-controls` | `run_controls(v5/isolation_controls_final, v5/instruments)` | **48** fresh collection/containment assertions passed; all three generators still **blocked**; 416.355803 s. |
| `v5-final-full-mock-and-plan` | `phase2.readiness.assemble()` | **6,885 `mock_ok` checkpoints**, 4,455 nonempty assessments, 1,215 policy replays, immutable resume, 2,835 blinded pairs and verified lossless archive; 2747.327828 s. |
| `v5-final-transport-audit` | `publish_evidence.py transport` | All **27,546** archived entries, 4,455 prompts/histories, 1,215 receipt/usage links, 405 matched E1/E2 request pairs and both E3 orders/C3 verified; 84.204185 s. |
| `v5-final-preservation-audit` | `publish_evidence.py preservation` | Original inputs/evidence and Path A unchanged; 25.25795 s. |
| `v5-final-post-documentation-preservation` | `publish_evidence.py preservation-final` | Preservation reconfirmed after final source-related documentation; no missing/unexpected baseline entries; 50.420085 s. |
| `v5-report-derivation` | `publish_evidence.py results` | Final bindings revalidated and all **65** paired parser observations matched; machine-readable reports generated; 24.939927 s. |

The JSON records contain the complete `python -c` bodies and namespace wrapper,
not only the abbreviated function names in the table. The Go run emits
machine-readable normalized evidence for the shared parser comparisons.
The cross-language report compares **64 authored fixtures plus one exact
historical response**: both parsers accepted 14 and rejected 51, with identical
normalized model/answer/usage evidence for every accepted response. All current
validation commands match the same 144-file selected implementation closure;
passing old commands was not accepted as a substitute.

Development failures remain visible, including the initial 20-second CLI
startup timeout probe, the Go oracle mistake and the deliberately interrupted
candidate. Optional race testing was not rerun: prior retained evidence records
the host's unsupported 39-bit VMA. No passing race claim is made.

## Complete mocked chains

The complete run produced **6,885 successful mock checkpoints**: 4,455 nonempty
generator assessments and 2,430 adversary evaluations (1,215 native plus 1,215
Path B), across 135 input identities and three generator labels. Assessments
contain one or two claims and exercise all four change actions. Resume preserved
all 6,885 checkpoints with **zero new checkpoints**; blinding exported **2,835
pairs with no omissions**. Independent E1/E2 request bytes matched in all 405
groups; each E3 order and C3 had turns 1 and 2 in all 405 groups.

The separate archive audit rehashed every member, verified every result's
artifact and parent anchors, regenerated all generator prompts from frozen
templates and own-branch histories, and checked 1,215 receipt/raw-response/usage/
binary/policy links. Assembly also reread and verified all **27,546 archive entries**, representing
1,646,425,725 uncompressed bytes, before removing RAM scratch. The lossless
archive SHA-256 is
`e57df1a4d38f064684aeb572eb98a93119209a953c017ad97f9c567a80d7ae9d`.
The rejected candidate's interruption also exercised partial-run preservation.

All claims, challenge effects, token counters and identities in these chains
remain labelled authored mocks. Nonempty source-bound claims and challenge
sensitivity improve wiring coverage; they do not become independent adjudication
or model-quality evidence.

## Isolation, confidentiality and adapter readiness

| Adapter | Current readiness | Decisive limitation |
|---|---|---|
| Haiku via Copilot | **Blocked** | Six POSTs for one no-watchdog HTTP-500 invocation; forced tool responses can cause follow-up requests. No preventive single-attempt guarantee or authenticated-route equivalence. |
| Gemini via Copilot | **Blocked** | The same observed six-POST behavior and live-route/egress limitations. |
| GPT-6.1 Sol via Codex | **Blocked** | Ten internal routes remain advertised; routing/rejection is not a pre-dispatch authorization boundary. Every advertised route was probed. |
| Native JEV | **Offline contract only; live unqualified** | Requires a valid, independently qualified nonempty generator B0 plus separate transport/identity qualification. |
| cARL-JEV Path B | **Offline contract only; live unqualified** | Source-bound build, parser, transport failure handling and deterministic replay work offline; no live provider execution/identity assertion. |

Negative namespace controls deny host sentinel/auth visibility, `/work` writes
(EROFS) and external networking. Fresh-home controls test inherited instructions
and session reuse. Tool-enabled positive controls demonstrate actual sentinel
access and tool follow-up; the Codex positive control also exposes a **dummy**
provider key. These are intentionally weakened offline observability controls,
not evidence of a live credential leak. A trusted subprocess can execute inside
the namespace, and mounted runtime files remain readable; the contract is not
silently reinterpreted as universal no-exec/no-read enforcement.

The current generator entry point returns
`strict_generator_isolation_blocked` before credential staging or process launch,
even with explicit authorization. Configuration cannot override it. The engine
also rejects live integration execution. The loopback BYOK path is not proof
about authenticated GitHub/ChatGPT paths; earlier catalog metadata is not current
served-version attestation.

For exact historical catalog lookup, the canonical workspace-relative file is
`adapter_qualification_v1/adapter_readiness_v2.json`, SHA-256
`e00a5cba57ef1676d7718ff50a2fac7feaf5f386d8d9a2f8a467ee8436d0a35f`.
An unchanged copy is retained at
`evidence/historical_references/adapter_readiness_v2.json`.
The `catalog_evidence.path` string in the generated isolation evidence retains
legacy `../adapter_qualification_v1/...` notation; it is not a locator relative
to the nested `v5/` directory. Use the canonical location or retained copy and
its verified hash, not that descriptive string. No readiness decision depends
on resolving the string or treating the old catalog as current qualification.

Path B captures safe original streams and artifacts before cleanup. Literal,
JSON-escaped and nested-base64 known credential echoes are withheld as whole
artifacts, never rewritten and labelled original raw bytes. Cleanup failures
remain errors and may retain owner-only scratch for controlled handling.
Unknown secrets, arbitrary encodings and sensitive source content still require
private disclosure review. This package is owner-only and is **not approved for
public upload**. Local receipts/checksums/TLS metadata are integrity evidence,
not provider signatures or proof of billing/execution.

## Preservation and experimental architecture

`PRESERVATION_CHECKS.json` records 35,824 unchanged baseline workspace entries and
189 unchanged cARL entries. All other pre-existing differences are explicitly
allowlisted source/documentation changes: no missing or unexpected baseline
entries. New source files are separately enumerated.
`FINAL_PRESERVATION_CHECKS.json` confirms those invariants again after final
source-related documentation changes.

All **135 original identities / 108 distinct input hashes** remain; identities
were not deduplicated. The actual primary archive was reopened and verified,
not merely compared by a declared digest. Historical plans v2/v3, input bytes,
results, original forensic reports and all prior evidence packages remain
unchanged. All 65 protected Go sources, the Python `CarlJEVAdapter` class body
and installed Path A binary match the baseline.

No scoring, question semantics, policy thresholds, defaults, arm design or
experimental-methodology redesign was made. Both E3 orders and matched-turn C3
remain. The prior proposed Path B supplied-evidence substitution is retained
only in the new plan; Path A's Git-evidence interface is not reinterpreted.
Changes are contract corrections: stricter evidence interpretation, authoritative
snapshots/source/build binding, first-attempt reservations, provenance and
failure handling, stronger controls and challenge-sensitive mocks.

R1's OS/runtime boundary and R6's workspace-only reservation scope remain
explicit. Neither local hashes nor a fixed registry establish cross-host or
provider exactly-once execution. The proposed role/policy snapshots still need
PI approval. `REMAINING_RISKS.md` distinguishes observed failures, supported
inferences and untested assumptions.

## Frozen identities

| Artifact | SHA-256 |
|---|---|
| Implementation (`v5/instruments/software.v1.json`) | `c1d1c4d09715893e3c3ccd9deee77b787b189b3c511018f017842ee5ecb20ac3` |
| Instrument manifest (`v5/instruments/manifest.json`) | `be99adbb65cf5dfb2cb9aa2accebf683306ff565ecf81a515676111856fdd06a` |
| Path B executable (`v5/bin/carl-assessment-challenge-v5`) | `b51cb4c86a1e5b54b5bb496e67890ee8efd18f58603616f4eb28da144d7a275d` |
| Execution plan file (`v5/execution_plan_v5.json`) | `779afb5c40b89f610a2214f53df4f1ae2426eefaab6efaf6ad32c4b59e5f0b19` |
| Plan semantic manifest identity | `844703bcc5569894d140f0bf4a1e34d1db7a281b82d4e751cab39b6e77f013cf` |
| Unchanged v2 plan file | `6ac2b63b04f002e0a93d9bcb2cd86c8ffa8880fc99b02977e0416a453dfff62a` |
| Unchanged v3 plan file (superseded, not overwritten) | `6d24e77593e59fb769d234f6b56294c79efef8924b7c1d3cc575029c63172984` |
| Unchanged primary archive | `a3fe94069009f328b0a46bb52a7ff52d2c2bedfcd0eb3babe360eea1c884cc21` |
| Unchanged installed Path A | `b34696d54d0b9c910d48c9adbe0155f825617d8e4c8981e58a2f50b5d0868428` |

The final checksum manifest covers every regular file in this package except
itself. It includes rejected-candidate evidence without promoting it to current
qualification. An independent reader can run:

```sh
cd /home/prometheus/git/mmmtap_phase2/forensic_remediation_v1
sha256sum --check --quiet SHA256SUMS.txt
python verify_package.py
```

The standard-library verifier checks exact file coverage and cross-artifact
bindings without executing retained historical or implementation code. It does
not attest providers or replace the recorded runtime/control validation.
Reproduction must use a new private output location, not modify sealed logs or
checkpoints. The retained historical command tools contain the original absolute
workspace paths; their copies must not be run in place inside this sealed package.

## Prerequisites for separately authorized live qualification

There is no live action to run under this seal. First resolve preventive
tool/process/file/credential boundaries, client retries and provider-scoped
egress with an upstream fix or a separately approved design. Keep the original
acceptance criteria. Obtain PI approval for exact instruments and disclosure,
then produce a new implementation-bound plan and rerun all offline controls
after its final source change; removing the hard block requires reviewed code,
not an operator checkbox.

Only then may separate authorization specify the adapter, exact model and
endpoint/authentication route, inputs, one-attempt budget, timeout, operator,
stop conditions and disclosure rules. Reserve before preparation and preserve
failed/incomplete attempts. Qualify an actual nonempty generator B0 before
separately qualifying native JEV and Path B against matched requests. Require
independent served-identity evidence, raw receipt/usage review and offline policy
replay. Unknown execution is not zero execution and never permits a silent retry.

`LIVE_REQUALIFICATION_PROCEDURE.md` gives the exact gates and stop conditions.
Live qualification, any pilot, and a full study remain three distinct approval
decisions. Work stops at offline remediation, validation and sealing.
