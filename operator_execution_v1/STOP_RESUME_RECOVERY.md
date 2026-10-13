# Stop, resume and recovery

The safe default is **preserve the first attempt, including failure**.
There is no automatic retry of an experimental job and no successful-attempt
selection. Never delete an intent, alter the ledger, recreate the run under
another directory, increase a persisted budget, or change a model to make a
failed position pass.

## Stopping

Use Ctrl-C in the operator's terminal, or send SIGTERM to the **specific**
operator process ID. The signal handler terminates the current subprocess
group, retains captured partial output when available, checkpoints an explicit
interrupted/unknown outcome, and returns 130. Do not use name-based process
killing. An interrupted request may already have reached or been billed by
the provider; the harness never assumes otherwise.

Timeout, output-limit or watchdog failure similarly kills the group and
retains a failure. A watchdog is detective, not proof that a prohibited action
or retry did not occur before termination.

For planned chunks use `--stop-after N`. No running job is interrupted by
that option; execution pauses before the next invocation. The experiment's
persisted `--max-calls` must remain unchanged.

## Resuming

Repeat the **same stage command**, with the same manifest, profile, output
root and `--max-calls`. Repeat the explicit authorisation flags; a resume is
still a deliberate operator action. You may change/remove `--stop-after`,
which only limits new invocations in that invocation.

An example for the default full stage:

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 full \
  --max-calls 6885 --stop-after 51 \
  --authorize-live-stage full \
  --accept-lower-assurance \
  --approve-frozen-instruments \
  --review-prior-stage 'I reviewed the completed pilot, exclusions, frozen full matrix and billing assumptions.'
```

Existing successes, failures, unavailable/unsupported positions and interrupted
attempts are verified and reused. They are never reissued. Descendants of a
failed B0/challenge become explicit `blocked_parent` records; unrelated,
unattempted positions may proceed. A live transport/schema/model-identity
failure stops the current invocation and requires deliberate resume.

`summary-*.json` reports permanent reservations separately from invocations
in this invocation, the stop reason and every not-yet-attempted position.
`completion.json` exists only once all selected matrix positions are accounted
for. It is not a successful-qualification certificate.

## Crash cases

| On-disk state | Recovery behavior |
|---|---|
| No checkpoint directory | Still unattempted, subject to the remaining budget |
| Reserved directory without a valid intent/ledger anchor | Stop for inspection; no automatic reconstruction |
| Intent exists, result missing | `incomplete_attempt`, permanently consumes its reservation; never reissue |
| Result and artifacts exist, completion event missing | Verify hashes, append `recovered_completion`; no inference |
| Stage completion file exists, its ledger anchor missing | Verify it against all outcomes and append its anchor; no inference |
| Invalid/truncated ledger or changed artifacts/parents/profile | Stop; no silent repair |
| Failed preparation | Keep intent, payload/failure and result; never silently retry preparation as a new first attempt |
| Incomplete Path B worker/receipt | Keep partial process output; HTTP/provider execution may be unknown |
| Cleanup failure | Explicit failure; retained private staging may require manual inspection and cleanup |
| Low storage | Stop before the next reservation where possible; never remove old evidence automatically |

Checkpoints use exclusive creation, fsync and read-only file modes. The ledger
is append-only at the application level. These are local integrity controls,
not write-once hardware or signatures. Keep independently controlled copies
of the package seal and run ledger/checkpoint anchors if stronger evidence
custody is needed.

The fixed workspace registry is
`~/git/mmmtap_phase2/.operator_attempts_v1/`. It pins each stage manifest to one
output location and budget, even if a different `--runs-root` is supplied.
A nonblocking lock prohibits simultaneous operator stages. Do not remove
registry files as a recovery technique. There is no cross-host exactly-once
guarantee and no permission to bypass these controls through legacy/direct CLIs.

## Failed credentials or unavailable models

Inspect and correct the environment **before** authorising smoke. Once an
adapter's first stage position is recorded as unavailable or failed, fixing
credentials does not turn it into a successful attempt or reopen it. Subsequent
stages retain its matrix position and failure lineage. A genuinely new
experimental attempt needs a separately reviewed/versioned campaign, preserving
the old run; this package exposes no retry switch.

Do not update the pinned CLIs in place during a run. A binary, source,
instrument or configuration change invalidates the existing execution identity.
The same applies to changing model names or Path B policies. SystemOne alias
resolution is checked against the successful smoke identity. Codex's missing
served identity remains an explicit lower-assurance limitation.

## Storage

Use persistent storage, not `/tmp` or `/dev/shm`, for live records. Current
full-stage preflight requires 4 GiB free; 8 GiB or more is recommended. These
are readiness floors, not worst-case output bounds. Each next job also checks
for at least 128 MiB free. Concurrent disk consumers or power loss can still
cause an incomplete attempt; it must remain incomplete rather than be rerun.
Known temporary/runtime roots (`/tmp`, `/var/tmp`, `/run`, `/dev`) and parent
traversal are rejected. This path guard does not certify persistence of an
arbitrary mounted volume; the operator must verify that separately.

Choose any external `--runs-root` **before Stage 1** and use it consistently.
Do not move a reserved run or delete frozen packages to reclaim space.
