# Q1 offline provider broker v1

Synthetic engineering qualification only. No live adapter, endpoint, credential,
experiment authorisation or release integration is implemented.

```sh
python -B -m engineering_qualification_v1.q1_executor.broker_v1 --output /tmp/q1-broker-new
python -B -m engineering_qualification_v1.q1_executor verify --campaign /tmp/q1-broker-new/chain/campaign --history
python -B -m engineering_qualification_v1.q1_executor resume --offline-subprocess --campaign /tmp/q1-broker-new/after_acceptance/campaign
python -B -m unittest -q engineering_qualification_v1.q1_executor.broker_v1.test_broker
```

The output directory must be new. The qualification runs an eight-position
diagnostic chain and single-position adversarial/failure cases. It does not
repeat the 153-position campaign. All source/policy packets and identities are
synthetic and unapproved; cARL/native designate the existing specialist fixture
paths, not live services or independent judges. RD03 remains proposed.

Flow: the existing engine commits its reservation, canonical request and sealed
envelope in `campaign.sqlite3`; its versioned transport starts the worker through
the **unchanged** `q1-offline-subprocess-v1` Bubblewrap argv and bootstrap/filter.
The worker writes a bounded request frame to its preopened stdout and reads a
reply from stdin. The supervisor forwards it to a separate trusted broker
process holding a fixed campaign/manifest/position grant. No extra descriptor,
socket syscall or filesystem mount is granted to the worker. The bootstrap and
its syscall allowlist are not extended. The broker has no network implementation.

The broker independently replays the campaign, checks its grant, requires a
committed started reservation and prepared transport, then compares **all**
message fields and exact request bytes with the stored envelope/request. This
binds campaign, position, deterministic attempt ID, request digest, packet and
parent bindings, generator/specialist role, provider/model/version/judge,
destination, deadline, byte ceiling and correlation token. Pipe possession and
the token alone confer no authorisation. A rejected message receives no raw
response from another attempt. There is no lookup/retrieval API.

Authorisation and dispatch use `BEGIN IMMEDIATE` in the original database. A
broker journal event consumes the existing reservation; a second request is
refused even if the first broker died before dispatch. There is no second
scheduler, reservation registry or evidence database. `broker_event` and
`broker_rejected` extend the original hash-chained journal; existing transport,
response and receipt tables remain in use. New receipt fields bind the broker
record and its raw prefix. Original receipts and first attempts are never edited.

Durable states distinguish reservation without dispatch, broker authorisation,
dispatch intent with acceptance unknown, observed mock process start, mock
acceptance, partial bytes, complete bytes, terminal failure and interruption.
Intent commits with SQLite FULL synchronisation **before** Popen; observed
process start commits before request delivery. Acceptance is recorded after the
mock's authenticated frame is received. A crash between a side effect and its
acknowledgement remains uncertain. No missing acknowledgement implies that
dispatch did not occur. This proves at-most-one locally authorised dispatch per
attempt, **not exactly-once remote execution**. The deterministic idempotency
token is correlation only; no real provider idempotency contract is assumed.

The only destination is a pinned local standard-library mock process. It sends
sequence/attempt-bound MAC frames using an ephemeral key that the worker never
receives. These test byte integrity at this local boundary, not provider/model
attestation. Raw bytes, including malformed, partial and corrupted bytes, are
committed as journal prefixes before forwarding. The provider ceiling is 65,536
bytes; excess bytes are deliberately not retained, and the truncation is a
terminal limit failure. Broker and worker framing have a 1 MiB ceiling with
nonblocking backpressure; the provider deadline is two seconds and the entire
supervised worker request has a ten-second deadline. Raw broker custody is
authoritative: an altered worker echo cannot replace it. Observed mock identity,
transport status and unchanged v2 assessment validation remain separate.

Broker and mock use parent-death SIGKILL; the worker also retains the original
PID namespace/die-with-parent controls. Explicit recovery retains every saved
prefix, publishes interrupted receipts and blocks descendants. It never
retransmits a reserved attempt or promotes an orphaned complete response to
success. Saved PIDs are evidence only and are never used as recovery kill targets.
The executable crash cases restart the broker itself against the original
request before executor recovery, then restart the executor three times. Journal
replay and byte snapshots check for retransmission or custody changes.

`engine.py` and `transport.py` contain the small version-routing hooks. The old
launch argv is shared; the original bootstrap, fixture and scientific validators
are byte-identical. Exact old producer fingerprints and the old transport
configuration support read-only historical reconstruction. Relocated archived
paths can be audited when executable hashes/runtime and all controls match;
creation and active launch additionally require exact current paths. An
incomplete campaign cannot resume under changed producer bytes.

The host qualification uses mount/PID/user/IPC/UTS namespaces plus the original
seccomp allowlist. Landlock and network namespaces remain unqualified/unavailable
on this host; neither is required or silently substituted. Denied raw libc
AF_INET/AF_UNIX sockets, spawn/exec, host-file/credential-canary/history reads and
input writes are actively exercised, including a real historical campaign DB
path that exists outside the namespace. No production credential is read.

Limits remain: a trusted host/kernel, trusted broker/supervisor and preserved
database authority are assumed. Privileged host compromise, copied campaigns or
cross-host authorities are not solved. The read-only `/usr` tree has not been
audited for embedded secrets. Real provider credentials, authenticated served
identity, remote context separation, retries/replays/rerouting, provider-side
idempotency, usage/tariffs, production transport and deployment custody remain
unqualified. The mock MAC key is local test evidence, not independent remote
attestation. Packet/policy warrant and scientific correctness remain outside the
broker. No scientific outcome or operational release decision follows.

See `evidence/RESULTS.md` and `evidence/qualification/acceptance.json` for executed
acceptance evidence. New artifacts are sealed separately in this directory.
