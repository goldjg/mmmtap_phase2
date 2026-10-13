# MMMTAP Phase 2: operator execution v1

**No live inference was authorised or initiated while preparing this package.**
Only the human operator may run Stages 1, 2 and 3. They are separate commands;
no command advances to another stage. This package does not qualify any
generator for `strict_isolation`.

The additive CLI is `python -m operator_execution_v1`. The original `phase2`
implementation, v5 remediation, instruments, protocol, scoring criteria,
corpus, qualification findings and previous evidence are unchanged. Do not use
legacy `phase2 pilot/run/qualify` commands as an alternative to these gates.

## Before authorising anything

Read `EXECUTION_PROFILES.md`, `PREFLIGHT_REPORT.md`,
`COST_AND_CALL_BUDGET.md` and `STOP_RESUME_RECOVERY.md`. Check the exact plan and
software identities in `SOFTWARE.json` and the stage manifests.

Supply a **dedicated, minimally permissioned Copilot inference credential** as
`COPILOT_GITHUB_TOKEN` in your own terminal. Do not paste it into an assistant,
command argument, source file or run log. The implementation deliberately does
not import `GH_TOKEN`, the GitHub CLI token, the user's Copilot home, or other
repository credentials. Credential presence is not proof of token scope or
remote validity. At preparation time that explicit Copilot variable was absent.

Sol uses only the existing owner-only `~/.codex/auth.json` ChatGPT OAuth
credential, copied into a fresh private home for each turn. The staged auth
file is read-only; authentication refresh/persistence requirements may fail.
Refresh the host login deliberately outside the experiment if required, never
retry a failed experimental job. No API-key substitution is supported.
Native JEV and Path B use only `JEVKEY`; it is never passed to generators.
Neither authentication nor remaining account allowances have been checked
against live services.

Keep the whole package and future raw records private. Do not run as root.
No Kubernetes, APEX, deployment, corpus execution, or new orchestration
platform is involved.

## Stage 0: offline preflight

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 verify
python -m operator_execution_v1 preflight --stage smoke
python -m operator_execution_v1 estimate --stage smoke --max-calls 5 \
  --rates operator_execution_v1/REFERENCE_RATES.json
```

The verifier checks this package and the preserved originals. Preflight checks
the source-bound v5 implementation, operator implementation, selected manifest,
all 135 source identities, pinned binaries/arguments, credentials **without
printing them**, read-only filesystem and process controls, and disk space.
Its real CLI help/version probes have external networking disabled.

Output: `~/git/mmmtap_phase2/operator_runs_v1/preflight/report-000001.json`
for the first invocation; subsequent reports increment the six-digit suffix.
The exact path is printed. Credential blockers are reported per adapter.
An infrastructure/storage block exits 2. No networked model discovery occurs.

**Resolve preflight blockers before smoke.** Running smoke with a missing
credential permanently records that adapter as unavailable for this stage.
It is not a mechanism for obtaining credentials or repeatedly testing them.

## Stage 1: separately authorised live adapter smoke

**This command makes real requests. It has not been run by the assistant.**

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 smoke \
  --max-calls 5 \
  --authorize-live-stage smoke \
  --accept-lower-assurance \
  --approve-frozen-instruments
```

Output: `~/git/mmmtap_phase2/operator_runs_v1/smoke/`.
There is at most one reserved adapter invocation for each of Haiku, Gemini,
Sol, native JEV and Path B. This is **not a provable five-HTTP-request or
billing ceiling** for opaque CLIs; see the retry limitations.

The smoke uses the frozen `synthetic-token-logging` / `baseline` input, one
fresh B0 per generator. Native JEV and Path B both challenge the **same actual
successful Haiku B0 and original source**, using identical typed questions.
They are separate SystemOne calls, not a replay of one response. If that B0
fails or has no claims, neither mechanism receives invented claims.

Review `completion.json`, the immutable `checkpoints/<job-id>/` records and
all `summary-*.json` files. A failed live invocation stops the command; repeat
the identical command only to move to unattempted positions, not to retry the
failed one. A completion file means every position is accounted for, **not**
that all adapters passed. No smoke record constitutes strict qualification.

## Stage 2: separately authorised bounded pilot

First review the completed smoke, including unavailable adapters, requested
and observed model identity, raw event contracts, watchdog evidence, usage,
and the native/Path B question comparison. All intended generators should
have passed smoke before a complete pilot is expected.

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 preflight --stage pilot
python -m operator_execution_v1 estimate --stage pilot --max-calls 153 \
  --rates operator_execution_v1/REFERENCE_RATES.json
```

Only after the human has reviewed that evidence:

```sh
python -m operator_execution_v1 pilot \
  --max-calls 153 \
  --authorize-live-stage pilot \
  --accept-lower-assurance \
  --approve-frozen-instruments \
  --review-prior-stage 'I reviewed the sealed smoke outcomes, identity limits and all adapter exclusions.'
```

Output: `~/git/mmmtap_phase2/operator_runs_v1/pilot/`.
`PILOT_MANIFEST.json` preregisters the baseline variant of
`synthetic-benign-docs`, `synthetic-token-logging` and
`synthetic-public-metadata`. These are provisional benign/vulnerable/ambiguous
strata, **not adjudicated ground truth**. All three generators, B0, self-review
C1, placebo C2, matched two-turn C3, E1, E2 and both E3 orders are included:
99 generator and 54 SystemOne positions, 153 total.

Unsupported, failed, incomplete and unavailable positions remain visible.
Adapters without successful preceding-stage evidence are not called.
Their descendants are explicitly blocked rather than silently dropped.
The review note is an operator decision, not a claim that failures passed.

## Stage 3: separately authorised full Phase 2

Review the completed pilot first. The full manifest retains 135 identities
(15 cases x 9 variants), all three generators and every arm, one repetition.
Pilot/smoke identities are distinct, predeclared diagnostic stages; they are
not reused as primary results or silently selected as successful retries.

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 preflight --stage full
python -m operator_execution_v1 estimate --stage full --max-calls 6885 \
  --rates operator_execution_v1/REFERENCE_RATES.json
```

Only after the human approves the manifest, pilot evidence and budget:

```sh
python -m operator_execution_v1 full \
  --max-calls 6885 \
  --authorize-live-stage full \
  --accept-lower-assurance \
  --approve-frozen-instruments \
  --review-prior-stage 'I reviewed the completed pilot, exclusions, frozen full matrix and billing assumptions.'
```

Output: `~/git/mmmtap_phase2/operator_runs_v1/full/`.
The schedule contains 4,455 generator positions plus 2,430 SystemOne
positions (1,215 per mechanism), 6,885 total. Execution is deliberately serial
(`max_concurrency=1`), topologically deterministic and resumable. This is not a
randomised wall-clock schedule; temporal/provider drift remains a limitation.

Full preflight requires at least 4 GiB free on the output filesystem; 8 GiB or
more is recommended, not a worst-case capacity guarantee. The final preparation
snapshot meets that floor, although an earlier snapshot did not; always
recheck free space. **Do not delete frozen evidence to make room.**
Use an already provisioned persistent volume with adequate capacity if needed:
add `--runs-root /absolute/persistent/path/mmmtap_operator_runs_v1` to **every**
preflight/live command before the first smoke reservation. Expected outputs
then have the same `preflight/`, `smoke/`, `pilot/`, `full/` suffixes there.
Do not relocate an existing run or use `/tmp`/`/dev/shm` for live evidence.

A lower persisted `--max-calls` is allowed, but cannot later be increased on
that run. To work in resumable chunks without reducing the study ceiling,
keep `--max-calls 6885` and add, for example, `--stop-after 51`. This limits new
invocations in that invocation only; it is not a random representative sample.

## What is recorded

Each stage has `manifest.json`, `run.json`, `authorisation.json`, append-only
`ledger.jsonl`, `preflight-*.json`, `summary-*.json` and, when fully accounted
for, immutable `completion.json`. Each hash-addressed checkpoint has:

- `intent.json`, fsynced before preparation or transport;
- `payload.json`, including the exact prompt or evidence/question request;
- `raw.json`, raw streams/receipt evidence, usage, watchdog and transport metadata;
- `result.json`, parsed outcome, source/parent/artifact hashes, model identities,
  profile and explicit evidence-quality label.

Missing usage, HTTP counts or model identity remain null/unknown, not invented.
Codex's model identity is specifically client-configuration-only. The observed
SystemOne model from smoke is checked on later successful calls; alias drift
fails rather than silently changing the experiment.

The original scoring contract still governs later blinded, independent
adjudication. No scores or claims of scientific improvement are generated by
execution. Preserve the execution-profile labels in every downstream export
and analysis; never pool research-controlled results with strict-profile
results or turn mock output into research evidence.
