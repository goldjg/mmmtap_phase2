# Phase 2 integration remediation

The new entry point is `python -m phase2.readiness`. Existing `python -m phase2`
commands, Path A, and old v2 results remain historical interfaces/evidence.
Do not run the old plan after code changes or relabel old qualification receipts.

`integration_readiness_v1/` contains the proposed v3 plan and independently
frozen instruments. `phase2/integration.py` reuses the existing planner,
checkpoint engine, native question constructor and blinded exporter.
`adapters_v2.py` provides isolated generator commands and the cARL Path B
wrapper. The Go transport is owned by `../cARL-semantic-eval`.

## Offline operations

```sh
cd ~/git/mmmtap_phase2
PYTHONDONTWRITEBYTECODE=1 python -m phase2.readiness validate \
  --manifest integration_readiness_v1/execution_plan_v3.json
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

The proposed plan includes all 135 identities, preserving the 108 distinct byte
hashes. Both E3 orders and the two-follow-up C3 remain separate. Path B's supplied
archive evidence contract is not authenticated Git; Path A remains unsupported
for these inputs. Historical candidates remain unadmitted.

`readiness assemble` creates new instruments and evidence; it intentionally
refuses an existing instrument directory. It is not a resume/overwrite command.
The offline chain uses explicitly authored nonempty fixture claims grounded in
three frozen synthetic baseline inputs, not generated findings or adjudication.
No source file is executed. All provider responses are mocks.

## Isolation boundary

Each generator turn starts in a new bubblewrap mount/PID/user/IPC/UTS namespace,
with a fresh home, read-only empty work directory, minimal environment and no
host repository/home mounts. Runtime binaries and OS files under `/usr` remain
visible. Prompt/history bytes go on stdin. Copilot gets only an explicit token;
Codex gets an isolated owner-only auth copy, never user configuration or prior
conversation. The implementation never writes back host auth; rotated credentials
may require separate operator login maintenance.

Loopback controls use a network namespace with no external route. Negative
controls test inaccessible host sentinels and read-only writes; positive controls
prove the probe can detect accessible sentinels and tool execution. CLI request
captures distinguish advertised tools from attempted routing and executable
actions. Built-in vendor system text is an unavoidable harness confound.

Copilot's empty tool filter did not mean an empty tool set. The v2 command uses a
nonempty unmatched filter plus explicit exclusions. Observed loopback requests
advertise zero tools; forced tool responses are rejected. This needs verification
on the authenticated GitHub path, not merely BYOK loopback.

Codex receives an explicit non-reserved provider profile with zero **client**
request/stream retry counts and a stable release-helper layout, avoiding the
previous rejected overrides and `/tmp` helper problem. Internal tools remain
advertised; disabled code-mode execution plus a streaming watchdog reject
routing. **A watchdog is not a pre-execution interlock.** Strict tool-free
compliance remains a blocker, especially for internal collaboration tools.

The Copilot watchdog kills the first observed transport failure. No wrapper
retries exist, but it cannot prove an internal retry never races the event.
Provider-internal retries are not observable. Live qualification uses host
networking for authentication/provider traffic; it is not endpoint-filtered
egress. These limitations require review, not an automatic approval checkbox.

## Receipts and qualification

The Path B wrapper verifies pinned binary/policy hashes, prepares the exact
native request, performs one authorised transport attempt, and locally replays
the returned receipt. It preserves all preparation/response/failure artifacts
inside checkpoint raw provenance before cleaning temporary files. Local hashes
are not signed provider receipts. Request-bound TLS/model metadata is observable
evidence, not independent correctness or identity attestation.

`readiness qualify` reserves a fresh diagnostic directory and invokes at most
one adapter. It is disabled unless `--authorize-live` is explicitly provided.
No such command was run during implementation. Even a parsed result is labelled
unqualified and requires independent raw-evidence review.
Native/Path B qualification requires an actual valid nonempty Haiku B0 from a
previous separately authorised qualification, rather than invented claims.

The v3 execution engine rejects all live experiment runs. Qualification cannot
silently unlock it: after successful live qualification and instrument approval,
an explicitly reviewed new plan/gate version is required. See the package's
`LIVE_QUALIFICATION_PROCEDURE.md`. No 81-call pilot is authorised.
