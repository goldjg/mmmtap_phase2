# Offline one-shot transport v1

Synthetic engineering only. No real provider, JEV, Copilot, cARL or historical
Codex executable is invoked. The 153-position research proposal, frozen v1/v2
assessment validators and policy/approval decisions are unchanged.

```sh
python -m engineering_qualification_v1.q1_executor transport-demo --output /tmp/q1-transport-new
python -m engineering_qualification_v1.q1_executor transport-probes --output /tmp/q1-probes-new
python -m engineering_qualification_v1.q1_executor verify --campaign /tmp/q1-transport-new/campaign --history
python -m engineering_qualification_v1.q1_executor resume --offline-subprocess --campaign /tmp/q1-transport-new/campaign
python -m unittest -q engineering_qualification_v1.q1_executor.test_transport
```

Output directories must be new. For the active filesystem test, preserve the
synthetic `transport_evidence/forbidden-canary.txt`; it is never a credential.
The executable demonstration uses the existing 15-position diagnostic fixture,
not a natural Q1 campaign. All scheduling, dependency blocking, budgets,
reservations, SQLite state, journal and terminal publication remain in `engine.py`.
The transport extension can also bind an unchanged full-matrix manifest;
this increment does not run the 153 positions through subprocesses.

`q1-offline-subprocess-v1` adds an explicit manifest extension, optional
`transports` table in the same SQLite database, journal events and a separately
versioned receipt schema. Original receipt bytes and tables are not rewritten.
Old completed campaigns replay against exact historical producer fingerprints;
incomplete campaigns cannot resume across changed executor bytes.

The interface accepts sealed request **bytes**, their SHA-256, a deterministic
manifest/position attempt ID, role, requested provider/model/version/judge,
configuration digest and execution-context ID. The result separates transport
status, stdout/stderr bytes, partial capture, process/timing/termination data,
observed identity and its provenance from assessment validation. Model text
cannot set argv, environment, network, tools, identity metadata or policy.
Identity metadata is adapter self-report, not provider attestation; unknown
and mismatched versions/models remain unavailable observations.

Reservation and envelope preparation commit before a launch intent and Popen.
The launch intent consumes the already reserved attempt even if startup fails.
Progress snapshots preserve committed raw stream prefixes before terminal
publication. A crash may lose bytes not yet committed; completion stays uncertain.
Restart never launches a reserved/started attempt again or promotes a saved
valid response across a missing terminal receipt. Duplicate launches are refused
by the existing reservation/transport projection, not another registry.

The selectable implementation is **only** a pinned local adapter fixture.
There is no SDK, provider credential or network-enabled mode. Explicit
`--offline-subprocess` and an exact manifest/configuration binding are both
required. Executable, bootstrap, fixture, libseccomp and Python bytes/versions
are bound; changed/missing components fail closed without fallback.

Each request starts Bubblewrap with fresh user, mount, PID, IPC and UTS
namespaces, dropped capabilities and die-with-parent. Only `/usr` and the sealed
inputs are mounted read-only. `/work`, `/home` and `/response` are fresh bounded
tmpfs mounts. The repository, custody paths, host home, `/etc`, `/run` and prior
session stores are not mounted. The child has five literal environment values;
no inherited environment or descriptors other than its standard streams.
Python `-I -S -B` excludes user site, startup hooks and repository import paths.
The response protocol is stdout; stderr carries bootstrap/identity diagnostics.
Both are captured as bytes. `/response` is ephemeral scratch, not evidence.
`started_at` and `ended_at` are local wrapper observation times. After an
interruption, `ended_at` denotes recovery finalization; it does not supply a
provider completion time or acknowledgement. Uncertain completion remains explicit.

Before adapter code runs, the hash-bound bootstrap applies no-new-privileges,
core/CPU/address-space/FD/file-size limits and a native libseccomp **allowlist**.
All unlisted syscalls return EPERM, including process/thread creation, exec,
network sockets (including Unix sockets), ptrace/process_vm, io_uring,
mounts/namespaces and privilege changes. The parent enforces a two-second
deadline, cancellation, SIGKILL and bounded stream capture, then removes only
that attempt's deterministic staging tree. Crash recovery cleans that tree;
saved PIDs are never signal targets. Hashes and process start ticks are evidence,
not protection against a hostile privileged host or kernel exploit.

This host rejects Landlock queries and Bubblewrap network-namespace setup.
Neither is claimed. Filesystem confinement uses the tested mount namespace;
network denial uses the installed syscall filter. Failure of either required
layer aborts before adapter execution. Fresh processes, allowlisted environment
and path conventions alone are never accepted as the containment proof.

The active fixtures attempt forbidden-file reads, source/policy writes, fork/
exec, raw libc socket creation, persistent session use and non-cooperative
hangs. A benign namespace control permits fork before the inner filter; the
filtered adapter receives EPERM. Host-side canary and evidence hashes are also
checked. These observations qualify the stated local profile only. They do not
prove provider-side context separation, served-model identity, absence of
embedded secrets in the exposed runtime tree, production credential isolation,
real SDK/CLI retry behavior or authorized live egress. An audited runtime image,
real adapter/identity/one-shot contracts and separate live approval remain needed.

See [the actual qualification report](transport_evidence/RESULTS.md), preserved
command receipts, probe campaigns and read-only reconstruction. No scientific
claim or live Q1 authorization follows from this local qualification.
