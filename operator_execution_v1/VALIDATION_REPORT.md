# Offline validation and evidence preservation

**Zero live provider inferences.** All real CLI negative/positive controls used
authored loopback responses and dummy credentials inside network namespaces
without external connectivity. Mock smoke/pilot runs are explicitly labelled
`mock_not_research`, not research observations or live-stage approval.

## Final results

| Validation | Result | Retained evidence under `evidence/` |
|---|---|---|
| Current operator acceptance suite | **32 tests passed**; 576.646 s test runtime | `final-python-tests/{command.json,stderr.txt,stdout.txt}` |
| Unchanged original Python suite | **144 tests passed**; 429.573 s test runtime | `final-original-suite/{command.json,stderr.txt,stdout.txt}` |
| Real pinned CLI controls | **27 controls passed**; 218.687 s command runtime | `final-cli-controls/results/summary.json`, per-control raw requests/streams |
| Retained end-to-end mock smoke | **5/5 mock_ok**, all five adapters represented | `final-mock-stages/results/runs/smoke/` |
| Retained end-to-end mock pilot | **153/153 mock_ok**, all three generators and every arm | `final-mock-stages/results/runs/pilot/` |
| Completed-stage resume | Zero new invocations; all **158 first attempts byte-identical** | `final-mock-stages/results/summary.json` and stage ledgers |
| Matched native JEV / Path B | **10 byte-identical E1/E2 request pairs**; 56 source-and-claim challenges; 28 contained Path B offline replays | Same retained mock-stage evidence |
| Full matrix, both profiles | **135 input identities, 108 unique hashes, 6,885 positions** planned and validated | Full/strict manifests; final acceptance and mock-validation summaries |
| Frozen evidence preservation | **40,538 original entries unchanged** | `PRESERVATION_BASELINE.json`, `PRESERVATION_FINAL.json` |
| Original v5 seal | **4,699 files and 36 command records verified**, strict live qualification still blocked | `PRESERVATION_FINAL.json` |
| Pinned versions, configuration and local credentials | Offline checks complete; missing explicit Copilot credential retained as a blocker | `PREFLIGHT_FINAL_PRESEAL.json`, `RELEASE_IDENTITIES.json` |
| Budget output and adapter matrix | All three stage estimates generated; five adapter rows with separate billing arrangements | `COST_ESTIMATES.json`, `../ADAPTER_CAPABILITY_MATRIX.csv` |

The final operator tests, CLI controls and retained mock-stage command records
all bind operator software identity
`ad5a3ec52cb9e8c45e44559602db89a316ec0c1ee9320ce5b64a8215d179bc56`.
Each command record includes its argv, minimal environment, elapsed time,
exit code, raw-stream hashes, before/after source checks and explicit
kernel-network-namespace/no-real-provider-call declaration.

The original 144-test suite ran against the unchanged v5 source closure while
operator prerelease `e7758fd3...` was present. Its command record is retained
unchanged. It certifies the **original harness**, not the later operator code;
the package verifier checks its exact v5 source hashes. The separate 32-test
suite and mock/control records certify the current operator source. There was
no redundant rerun of the unchanged original suite after additive corrections.
The old v5 Go results are preserved prior evidence, not a newly rerun Go suite.

## Acceptance coverage

| Requirement | Offline demonstration |
|---|---|
| Profiles distinguishable | Different profile versions, evidence labels, manifest identities and disjoint job IDs; altered profiles rejected |
| Strict remains blocked | Original generator hard block and new strict-stage gate both reject before any launch |
| Research containment applied | Actual bubblewrap read-only mounts, hidden host repositories/auth, selected environment and seccomp child-process denial |
| Separate stage authorisation | Wrong/missing stage, lower-assurance acceptance, frozen-instrument approval or prior-stage review fail; mocks cannot approve live |
| First attempts immutable | Intent precedes preparation; exclusive read-only checkpoint files; artifacts and lineage hash-verified |
| Interrupt/resume | SIGINT/SIGTERM kill subprocesses and retain partial output; hard process death keeps an unreissued incomplete intent |
| Crash recovery | Completed result without ledger event and stage completion without anchor recover without another inference |
| No harness retry or fallback | Permanent budget reservations, single adapter invocation, no cross-directory replay; changed requested model/manifest rejected |
| Tool/retry watchdog | Prohibited JSON events, newline-free tool events, Codex debug routing, visible retries and model switches terminate the subprocess |
| Unsupported/failure preservation | Preparation failure, transport failure, missing credentials and failed parents remain explicit; missing HTTP counts are not invented as zero |
| Source-grounded matched adversaries | Exact source, actual nonempty assessment, source hash and frozen typed question coverage verified; native/Path B canonical requests match |
| Controls and order retained | B0, C1 self-review, C2 placebo, C3 matched neutral control, E1/E2 and both E3 orders covered in the three-input pilot |
| Full frozen matrix retained | All 135 identities through the unchanged model/arm configuration are planned for each profile |
| Billing separated | Unknown charges remain unknown; invocation reservations are not HTTP/credit/charge caps |
| Credential handling | Synthetic OAuth metadata no longer causes false credential-echo failures; actual token/identifier echoes are still withheld and failed |

## Measured CLI controls

For each of Haiku, Gemini and Sol, the final suite exercised ordinary text,
forced tool routing, HTTP 500, HTTP 429, malformed response, disconnected
response, a separate fresh text session, deliberately weakened tool/instruction
positive control, and deliberately injected prior-session-content positive
control.

All guarded text and failure/tool scenarios produced **one observed loopback
POST per invocation** in this collection. Forced tool requests and transport
failures were rejected and observed watchdogs terminated the process.
Deliberately weakened tool controls produced two POSTs, exposed the harmless
host sentinel and inherited instruction marker, and were rejected as
assessment output. No write to the read-only working directory succeeded.

Copilot advertised no tools under research settings. **Codex still advertised
ten internal tool routes.** The negative controls do not erase that limitation.
The unchanged v5 evidence includes Copilot's multi-POST behavior without the
watchdog; this collection cannot establish a preventive single-request bound.

For all three generators, the first-session output contained its canary, the
fresh-session request omitted it, and the deliberately contaminated request
included it. Session identifiers were checked for reuse wherever emitted.
The positive contamination case intentionally injects prior output into a
fresh prompt; it tests detector sensitivity, **not** support for resuming CLI
sessions. Research execution never imports or resumes prior CLI homes.

Namespace controls separately demonstrated:

- approved read-only sentinel visible, host repositories and auth invisible;
- writes to input/work denied with EROFS;
- a trusted `/usr/bin/true` subprocess succeeds in the unguarded positive
  control, but child-process creation fails with EPERM under seccomp;
- runtime threads remain usable, ambient instruction/credential/session keys
  are absent, and external connectivity is denied in offline controls.

These are measurable local controls, not authenticated-route equivalence,
provider attestation or strict-isolation qualification.

## Scope and development evidence

The current release's full **6,885-position matrix was planned, not executed**.
The retained end-to-end current-code execution was the five-position smoke and
153-position representative pilot. All raw first-attempt files are retained,
including actual local Path B prepare/evaluate-offline/replay receipts; resume
did not manufacture replacements.

`prerelease-e7758fd3/` retains the earlier unsealed manifests, exact source
snapshot under `software_source/`, passing 31-test suite and 24-control
collection. They were superseded before any live run. Earlier
`development-python-tests/` and `development_controls/` are development-only
evidence. `final-correction-targets/` retains a failed targeted development run:
an overly broad output-path check rejected the intended default path. That
check was removed; the final tests validate workspace, traversal and temporary
path protection. No failed/stale run is presented as current-code success.
`final-positive-targets/` retains the successful new Codex instruction
positive-control check preceding the final collection.

No original evidence was overwritten or removed to accommodate these changes.
No source corpus code, deployment, APEX modification, model discovery, remote
authentication or account-balance request was performed.

## Remaining limitations and release verification

Explicit Copilot credentials are still absent at preparation time. Remote
authentication, exact model availability, subscription/AI-credit balance and
SystemOne tariff remain unverified. The latest storage snapshot meets the
4 GiB floor but is not reserved capacity. Live egress is not endpoint-filtered,
CLI retries may race the watchdog, Codex served-model identity is unavailable,
and local permissions are not hardware write-once evidence custody.

`SHA256SUMS.txt` seals this package, including raw evidence and development
records. `python -m operator_execution_v1 verify` rejects altered package
contents, stale final operator evidence, changed v5 sources or changed original
workspace files. The operator must still run Stage 0, review the package and
separately authorise each live stage. **This report does not authorise live
inference.**
