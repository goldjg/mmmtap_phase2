# Phase 2 source-bound forensic remediation

The current entry point is `python -m phase2.readiness`. The proposed v5 plan
and its current instrument/control artifacts are in `forensic_remediation_v1/v5/`;
the top-level remediation reports identify their exact hashes. V5 uses the
software-bound v4 plan format with `execution_plan_revision: 5`. The unfinished
`integration_readiness_v1/` package, v2/v3 plans, prior controls, original input
bytes and all previous research results remain unchanged historical evidence.
They cannot qualify the changed implementation.

`phase2/integration.py` still uses the existing planner, checkpoint engine,
native question constructor and blinded exporter. It freezes the actual
prompt, question, assessment/evidence schema, roles and policy snapshots,
plus the local Python/imported-extractor/Go/test/embedded-source closure.
The Path B executable requires an independently retained local build receipt
covering compiler inputs, toolchain and exact binary hash. The complete
mounted Codex release is inventoried, not just its main executable.

Plans and job/checkpoint identities bind the implementation and instrument
hashes. Runtime source, helper, prompt, question, role, policy or build drift
fails validation. Plans consume frozen snapshots; a changed runtime prompt
cannot inherit an unchanged instrument digest. Historical v3 plans are not
silently upgraded or executable under the source-bound validator.

The first remediation candidate's v4 artifacts remain at the package root.
That candidate was rejected when comparison with retained provider evidence
showed that its strict parser rejected legitimate answer `type` and choice
`confidence` metadata. Its mock run was deliberately interrupted and losslessly
archived, not retried or overwritten. It is not the sealed current implementation.
The corrected shared fixtures include exact historical response bytes labelled
as an unverified import, not a fresh provider call.

## Offline operations

```sh
cd ~/git/mmmtap_phase2
PYTHONDONTWRITEBYTECODE=1 python -m phase2.readiness validate \
  --manifest forensic_remediation_v1/v5/execution_plan_v5.json
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

Build a new Path B artifact and its source-bound receipt with
`phase2.software.build_path_b(Path("NEW_BUILD_DIR/carl-assessment-challenge-v5"))`.
The helper refuses an existing binary or build receipt, disables dependency
downloads, and never builds or overwrites installed Path A. Network-namespace
confinement remains the validation runner's responsibility. See the sealed
command evidence for exact executed build/test/control commands.

The proposed plan includes all 135 identities, preserving the 108 distinct byte
hashes. Both E3 orders and the two-follow-up C3 remain separate. Path B's supplied
archive evidence contract is not authenticated Git; Path A remains unsupported
for these inputs. Historical candidates remain unadmitted.

`readiness assemble` accepts only a verified current instrument snapshot and
a complete, current-source-bound offline control matrix. It refuses existing
plan/evidence outputs; it is not an overwrite or silent-retry command.
The full mocked chain covers all 135 input identities and all three generator
labels. Authored fixtures retain, revise, withdraw and add nonempty claims in
response to correctly bound mock challenges. Missing or swapped challenges
fail. No source fixture is executed and no mock is a model judgement.

The full mock run is resumed without reinvocation, checked, then losslessly
archived in `end_to_end_mock.tar.gz` with a per-file hash manifest. Every
archived byte is reread and checked before scratch checkpoints are removed.
This avoids leaving multiple GiB on a shared disk; it does not compact or
rewrite checkpoint contents. An incomplete archive is not successful evidence.

## Isolation boundary

Real-CLI **offline controls** start in a new bubblewrap mount/PID/user/IPC/UTS namespace,
with a fresh home, read-only empty work directory, minimal environment and no
host repository/home mounts. Runtime binaries and OS files under `/usr` remain
visible. Prompt/history bytes go on stdin. Only labelled dummy provider keys
are used. Separate controls test owner-only auth staging and no host writeback;
they do not establish live credential confidentiality.

Loopback controls use a network namespace with no external route. Negative
controls test inaccessible host sentinels and read-only writes; positive controls
prove the probe can detect accessible sentinels and tool execution. CLI request
captures distinguish advertised tools from attempted routing and executable
actions. Built-in vendor system text is an unavoidable harness confound.

Copilot's empty tool filter did not mean an empty tool set. The control command uses a
nonempty unmatched filter plus explicit exclusions. Observed loopback requests
must advertise zero tools. Forced responses, filesystem/process/network tools,
fresh-session behavior, transport failures and watchdog-disabled probes are
recorded separately. A detected/rejected tool response is not proof of
preventive authorization, and BYOK does not qualify the authenticated route.

Codex receives an explicit non-reserved provider profile with zero **client**
request/stream retry counts and a stable release-helper layout, avoiding the
previous rejected overrides and `/tmp` helper problem. Internal tools remain
advertised; disabled code-mode execution plus a streaming watchdog reject
routing. **A watchdog is not a pre-execution interlock.** Strict tool-free
compliance remains a blocker, especially for internal collaboration tools.

The Copilot watchdog kills the first observed transport failure. No wrapper
retry exists, but a watchdog cannot prevent every internal retry or race.
Provider-internal retries are not observable. Live qualification uses host
networking in the historical implementation; that is not endpoint-filtered
egress. The current generator live entry points are therefore **blocked in
code**, before credentials are staged or a process is launched. No configuration
checkbox or operator attestation bypasses that block.

The namespace confines host files and external networking but does not deny
all subprocess execution or reads of the mounted OS runtime. Controls report
these properties explicitly. Strict tool/retry/egress criteria are unchanged.
Sol, Haiku and Gemini remain blocked until preventive controls can actually
satisfy them in a newly reviewed and sealed implementation.

## Receipts and qualification

Both provider parsers enforce the frozen exact-key typed-response schema.
Duplicate/aliased fields, invalid types, nonfinite numbers and malformed
representations fail consistently. Shared byte fixtures cover noul and choice
parsing; the Path B request catalog remains noul-only. Underlying SystemOne
judgements match, while cARL's deterministic policy remains a distinct result.
Legitimate optional answer `type` is retained and must match the requested
question type. Optional choice `confidence` is retained as a finite [0,1]
number; aliases, wrong types, nulls and unsupported fields still fail.

The Path B wrapper cross-checks CLI checksum output, checksum files, preparation,
response bytes, receipt, implementation and deterministic replay. CLI launch
attempts, started CLI invocations, HTTP attempts and fully written requests are
different observations. Verified receipts determine transport counts; an
incomplete evaluation records unknown counts, not an invented one or zero.
Validated raw usage is surfaced with its source; missing metrics remain null.

All exits retain safe preparation/process/response/failure evidence. Known
credential echoes, including nested JSON/base64 envelopes, are withheld rather
than presented as unmodified originals. Cleanup failures are explicit and keep
the captured receipt. This is not a general detector for arbitrary unknown or
encoded secrets; raw evidence is private and requires a separate release review.
Local hashes and TLS/model fields are not provider signatures or independent
served-identity attestations.

`readiness qualify` requires separate explicit authorization and first reserves
the plan/adapter identity in the fixed workspace `.qualification_attempts_v4`
registry. A fresh output directory cannot repeat it. Failed parent preparation
and incomplete attempts remain reserved. A deliberate retry needs a linked new
plan, explicit reason and the previous registry record; cross-host/provider
exactly-once execution is not claimed. No live qualification is authorized by
this remediation. Generator attempts remain blocked even with `--authorize-live`.
Native/Path B qualification requires an actual valid nonempty Haiku B0 from a
previous separately authorised qualification, rather than invented claims.

The v4 execution engine rejects all live experiment runs. Qualification cannot
silently unlock it: after successful live qualification and instrument approval,
an explicitly reviewed new plan/gate version is required. See the package's
`LIVE_REQUALIFICATION_PROCEDURE.md`. No pilot or full experiment is authorised.
