# Controlled offline broker acceptance v1

**Q1 OFFLINE BROKER INTEGRATED — DISPATCH/CUSTODY QUALIFIED, LIVE PROVIDERS BLOCKED**

Baseline/upstream main: `4cda2184504147d65b161d60eca1bcbd10ac5398`.
Actual execution: 2026-10-26. Synthetic engineering qualification only.
**Zero real provider calls; zero live experiment launches; zero scientific
outcome claims.** No Q1 execution or operational release is authorised.

## Enforced flow

`Q1 engine → isolated worker → supervised stdio IPC → independent broker → local
stdio mock → broker raw-byte journal → supervised worker echo → existing engine
response custody/validators → terminal receipt`.

The original SQLite reservation, dependency, budget, append-only journal and
first-attempt machinery remain authoritative. `engine.py` and `transport.py`
add version routing and broker-event replay; there is no second scheduler,
attempt registry or evidence database. The broker independently reconstructs
the campaign and requires an exact sealed message backed by its committed
reservation and fixed supervisor grant. It compares campaign/manifest,
position/attempt, exact request bytes/digest, packet and parent bindings, role,
provider/model/version/judge, mock destination, deadline, response limit and
correlation token. A pipe or token alone grants nothing.

The worker uses the original Bubblewrap argv and **byte-identical bootstrap and
seccomp allowlist**. Its only broker channel is preopened stdin/stdout relayed by
the supervisor; it receives no broker/database descriptor, integrity key, socket
permission or additional mount. Broker and mock are separate actual processes.
Dispatch intent commits before mock Popen; an observed process-start event
commits before request delivery. No URL, live adapter, credential, SDK, retry,
fallback destination or model substitution is implemented.

## Actual acceptance accounting

The [machine report](qualification/acceptance.json) accounts for 34 execution
campaigns: one eight-position chain plus 33 single-position scenarios. One
additional unreserved campaign and eight deliberately corrupt copies are
authority/audit probes and are excluded from dispatch totals.

| Measure | Observed |
|---|---:|
| Scheduled positions / durable reservations / verified isolated worker starts | 41 / 40 / 40 |
| Completed / invalid / blocked / interrupted / unavailable receipts | 7 / 2 / 1 / 2 / 29 |
| Broker-authorised / broker-rejected messages | 21 / 15 |
| Durable dispatch intents | 20 |
| Observed mock process starts / mock acceptances | 19 / 19 |
| Complete responses / terminal broker failures | 12 / 5 |
| Explicit uncertain completions | 8 |
| Reserved attempts without dispatch intent | 20 |
| Maximum locally authorised dispatches per attempt | 1 |
| Real provider calls / live launches / scientific claims | 0 / 0 / 0 |

The chain has six completed positions, one invalid parent and one blocked child;
the child has no reservation. Baseline, native specialist, cARL specialist and
both continuations complete through the actual boundary. The final continuation
preserves `review_required → pass` separately from baseline `pass → pass`.
These scripted dispositions are infrastructure fixtures, not findings.

Twenty intents versus nineteen starts is intentional: `after_intent` terminates
before Popen and remains acceptance-unknown. An absent acknowledgement is never
treated as proof of no dispatch. The pre-dispatch termination has authorisation
but no intent/start/acceptance. The eight uncertain completions comprise five
terminal failures and three abandoned post-intent requests. Complete response,
observed identity and assessment validity are separate classifications.

## Executed failure, recovery and adversarial results

| Scenario | Durable observation |
|---|---|
| Valid generator/native/cARL/continuations | Complete chain; unchanged v2 validators accept |
| Malformed output | Exact non-UTF-8 bytes retained; invalid; descendant blocked |
| Unknown / mismatched observed model | Complete bytes retained; identity unavailable; no substitution |
| Partial response then failure | Raw `{"partial":` prefix retained; connection failure |
| Timeout after dispatch | Acceptance and raw prefix retained; deadline failure; uncertain |
| Provider connection loss | Acceptance retained; no fabricated complete response |
| Duplicate delivery | First request dispatches once; second is rejected |
| Broker death before dispatch / after intent | Reserved attempt consumed; no retry; distinct no-intent/unknown-acceptance evidence |
| Broker death after acceptance, before receipt | Actual broker exit 72 and executor exit 75; interrupted receipt on recovery |
| Executor death during outstanding request | Actual executor exit 75 after committed provider prefix; observed supervised processes stop |
| Mock response tampering | MAC failure; corrupted received bytes retained; unavailable |
| Worker response tampering | Original broker bytes retained; echo-hash mismatch; unavailable |
| Response ceiling | Exactly 65,536 bytes retained; explicit limit failure |

Each crash campaign restarts the **broker process itself** with the original
sealed request before executor recovery and again after terminal recovery.
All four replay requests return `duplicate_dispatch` with empty raw bytes.
Each retains one intent and one acceptance. Rejected post-recovery requests
remain valid journal evidence and cannot invalidate the published receipt.
Three further executor restarts per execution campaign leave every campaign
file byte-identical. Uncertain attempts never retransmit or become successful
because an orphaned response happened to parse.

Ten malicious-worker authorisation cases reject invented campaigns/attempts,
unreserved positions, altered request bytes, source/policy digests, role,
destination/model substitution and attempts to obtain another response. They
produce zero dispatch intents. Independent direct checks reject an exact sealed
message without any reservation, and corrupted persisted request/packet bytes.
The original executor separately refuses a duplicate reservation without
changing the first attempt. Nine active isolation cases receive kernel denials:
raw libc AF_INET and AF_UNIX sockets, subprocess and exec return EPERM; source
and policy writes return EROFS; host repository/credential-canary/history reads
return ENOENT. The historical campaign database used for the history probe
actually exists outside the namespace. Synthetic host canaries remain unchanged;
no production credential is read.

Eight corrupt-copy audits reject altered raw response, broker raw prefix,
observed identity, dispatch state, sealed request, receipt, destination/journal
and packet evidence. The read-only verifier leaves the corrupt copies unchanged.
The [full chain reconstruction](readonly_reconstruction.stdout) passes using the
actual Q1 CLI. Every case also records read-only verification and file snapshots.

## Custody and regression anchors

Raw bytes/prefixes are in each `campaign.sqlite3`: the existing `responses` table
and hash-chained `broker_event` records. Interrupted attempts bind broker-prefix
hashes even when no final response row was published. Receipt hashes, raw hashes,
manifest digests and journal tips for every case are in
[acceptance.json](qualification/acceptance.json); full transport/identity records
and receipts are in each scenario's `report.json` and preserved database.

Chain manifest: `c4590f4651628a5a6e44103947a6615c7243411e2c1c0d4747ec82cab380c5c7`.
Chain evidence tip: `1ed275c9db4db08ead25b4c7562098ea535faa21ea48560609d0c1a17e6826e5`.
Baseline raw SHA-256: `4ff2a97ce413d827f36c282cff29f1b32c296959aeb17f61e79c07197d401ee0`.
Baseline receipt SHA-256: `9957ea19da1c2ace29467078a5f55a311637c3ca90e6720d3683cd46cb8b8043`.

**123 tests passed, zero failures:** 9 broker-authority, 13 executor, 13 actual
subprocess transport, 6 preflight and 82 pinned instrument/continuation/RD05/
harness regressions. See [the command receipt](regressions.command.json) and
[test output](regressions.stderr). The 153-position campaign was **not rerun**;
both completed historical matrix campaigns, the original 15-position campaign
and the original subprocess campaign verify read-only without file changes
([historical audit](historical_readonly.json)). Existing unrelated legacy CLI
tests were not repaired or claimed to pass.

[Original custody verification](original_preservation.stdout) passes against the
original custody checkout: **40,538 original entries**, 1,165 operator-sealed
files, 4,699 v5 files and 36 command records; zero changed/missing entries.
[Preservation](preservation.json) also confirms all 392 pre-existing executor
files outside the two intentionally extended code files remain byte-identical,
and all 729 unrelated modified worktree paths and original worktree status are
unchanged. Frozen v1/v2 validators, eight arms, 153-position topology and
RD01/RD02/RD04/IE01 decisions are untouched; RD03 remains proposed. Development
runs are excluded from acceptance and documented separately.

## Remaining limits

This qualifies **at-most-one locally authorised dispatch**, not exactly-once
remote execution. A real provider may internally retry, replay or reroute;
neither attempt IDs nor idempotency tokens prove otherwise. Mock identity is
explicitly untrusted self-report. Local MAC frames exercise this test boundary
and do not attest a served model or provide independently verifiable remote
execution evidence.

Required local mount and syscall containment passed. Landlock and network
namespace setup remain unavailable/unqualified on this host and are not used.
Trusted host/kernel/broker/supervisor and one preserved campaign authority are
assumed; privileged history rewriting, cross-host/copied campaign authority and
kernel exploits are outside this qualification. The exposed read-only `/usr`
runtime has not been audited for embedded secrets; complete production runtime
confidentiality remains **unqualified**. Real credentials, authenticated model/
judge identity, remote context isolation, SDK retry behaviour, production
transport/custody, provider idempotency contracts and usage/tariffs remain
unqualified and blocked. Approved policy/source packets, policy warrant,
scientific correctness and explicit bounded live authorisation remain separate.
The broker interprets no JEV findings and makes no release decision.
