# Q1 offline execution vertical slice v1

**Synthetic infrastructure simulation. No live adapters, release path or
experimental authorization.** This 15-position fixture is separate from the
unchanged proposed 153-position qualification campaign.

One command creates durable evidence, deliberately terminates a child process
after reservation, resumes twice, checks byte-for-byte idempotence and verifies
the resulting history:

```sh
python -m engineering_qualification_v1.q1_executor demo --output /tmp/mmmtap-q1-slice-final
```

The output directory must be new; existing campaigns are never replaced.
Further execution and read-only audit:

```sh
python -m engineering_qualification_v1.q1_executor resume --campaign /tmp/mmmtap-q1-slice-final
python -m engineering_qualification_v1.q1_executor verify --campaign /tmp/mmmtap-q1-slice-final
python -m engineering_qualification_v1.q1_executor verify --campaign /tmp/mmmtap-q1-slice-final --history
python -m unittest -q engineering_qualification_v1.q1_executor.test_executor
```

`--history` reconstructs the hash-chained journal and emits all terminal
receipts, including separate generator/specialist diagnostics and nulls.
Verification failure exits 1. Deliberate `resume --interrupt-after-reservation
POSITION` exits **75** using `os._exit`, after SQLite commits the reservation;
the demo uses `interruption`. A busy worker refuses execution and recovery.
No automatic process restart, provider retry, repair or model fallback exists.

## Execution and custody

`fixtures/manifest.json` binds exact packet bytes, unchanged instrument
contracts, declared fake identities, every position/dependency, ten maximum
attempts and ten integer simulated budget units. Source and the governing
packet are delivered identically on every branch. The governing packet is
opaque simulation context, not approved operational policy. The separate
challenge packet requests a scripted review: no JEV threshold, policy warrant
or permission mapping is selected. Generator responses use the unchanged
assessment/lifecycle validator; specialist responses use the unchanged v2
three-dimension request/parser. Exact disposition pairs are recorded without
materiality, justification, action mapping or correctness claims.

`contracts.json` pins the seven reused repository source files at
`de9b83299f6732c3d53dff2fc1ab568049e1420f`. There is no validator fork. If a
custody checkout lacks later v2 files, the loader reads their exact local Git
blobs using `git cat-file`, verifies SHA-256 and loads the unchanged code.
No fetch, hooks, filters or provider commands are invoked. A normal upstream
checkout uses its files. Missing Git objects or changed contracts fail closed.
The frozen continuation planner supplies schedule validation; its scientific
global-stop rules remain unchanged. This simulation-specific engine accounts
for unavailable positions and completes independent diagnostic branches; it
does not approve that continuation policy for Q1 research.

Each campaign contains the immutable manifest and three packet files, an
empty `.lock` and `campaign.sqlite3`. SQLite uses full synchronous commits
and rollback journals. Unique position keys and `BEGIN IMMEDIATE` prevent
duplicate reservations, independently of the whole-campaign `flock` that
serializes workers and protects recovery from racing an active worker.
Reservation, start, fake invocation, raw-response preservation and terminal
receipt each have separate committed journal events. Requests, raw response
**bytes**, observed identity, receipts and budget charges are retained in
SQLite. The verifier replays every transition and compares all projections,
hashes, timestamps, packet/parent bindings and validation diagnostics.
Manifest/parent evidence is rechecked at each reservation boundary.

On restart, any reserved or started position without a terminal receipt
becomes **interrupted**, retaining any saved raw response and null disposition;
its provider is never called again. Even a saved parseable response without
a committed terminal receipt is not promoted to success. Descendants are
blocked. Invalid lifecycle output, missing evidence and unknown fake identity
never become unchanged observations. Independent remaining positions can run
only within the frozen simulation budget. Exhausted positions get unavailable
receipts; failed-parent blocking takes precedence. Terminal states never change.

One unit is reserved per attempt and never refunded, including the interrupted
attempt. Observed fake invocations separately count simulated expenditure;
these are invented test units, not prices, entitlements or billing evidence.
Every scheduled position has a terminal receipt after the demo, including
blocked and budget-unavailable positions.

The verifier opens SQLite with `mode=ro`/`query_only` and takes a shared lock;
it does not reserve, invoke or recover anything. Runtime/source bindings are
recorded and checked; changing executor code or its Python/SQLite runtime
requires separate versioned handling. A partially initialized campaign or a
hot journal requiring SQLite recovery fails audit until explicit resume; it
is never recreated. Hashes detect missing/changed/contradictory evidence, not
an attacker rewriting an entire history and every anchor. Preserve the emitted
manifest digest and evidence tip independently for stronger custody. A copied
campaign must not become a second authority: this local slice does not supply
a cross-host/cross-copy reservation registry.

## Actual results and remaining live work

The captured final demonstration and test/custody receipts are in `evidence/`.
See [the observed results](evidence/RESULTS.md) and the preserved
`evidence/demo-campaign/` for an executable audit target. Earlier development
captures, before receipt-byte/schema hardening, are labelled in
`evidence/development/`; acceptance captures are directly under `evidence/`.
Expected observed demo totals: **15 scheduled, 6 completed valid, 1 invalid,
4 blocked, 1 interrupted, 3 unavailable; 9 fake invocations, 10 reservations,
9 spent/10 reserved simulated units, 0 remaining reserved-budget units**.
The second resume changes neither database bytes nor the evidence tip.
`intermediate` records `pass → review_required`; `final` separately preserves
`review_required → pass` and baseline-to-final `pass → pass`.

Before real Q1 execution: approved source/reference and governing/challenge
policy packets; approved prompt/delivery and operational sidecar contracts;
qualified one-shot transports and strict isolation; actual model/judge identity
and dependency/censoring rules; durable deployment/custody and reservation
scope; actual tariffs, usage bounds and authorization; then explicit bounded
qualification approval. RD03 remains proposed. RD01/RD02/RD04/IE01, RD05
reviews and the 153-position proposal are untouched. Fake execution proves
none of live isolation, model availability/identity or scientific effectiveness.
The inherited missing pinned Codex executable remains absent; unrelated legacy
CLI integration tests were not repaired or rerun in this increment.
