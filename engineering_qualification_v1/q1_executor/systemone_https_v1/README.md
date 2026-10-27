**SYSTEMONE LIVE-PROBE TRANSPORT PREPARED — LIVE DISPATCH DISABLED**

The actual Q1 executor now sends one sealed native request through its unchanged
isolated worker and existing durable broker, over HTTPS to a local TLS fixture,
then preserves entity bytes and produces a Choice 1 specialist receipt. This
qualification schedules **one specialist**, supplied with one synthetic document
and one supplied claim. It invokes no generator, cARL or continuation. The
153-position topology and all frozen instruments remain unchanged.

[The disabled manifest](qualification-manifest/manifest.json) freezes the exact
source, assessment, three original Noul questions, `jev-1.13.0`, request/policy
digests, one dispatch/POST, zero retries/fallbacks, an absolute one-second provider
deadline, 8,192-byte request/entity limits and a 16,384-byte response-header limit.
Its simulated reservation unit is not a dollar or token allowance. Usage and
cost ceilings remain null because account-level evidence is unavailable.

The new contracts are `q1-systemone-https-v1` and its exact HTTPS destination.
The API documents `POST https://api.typesafe.ai/v1/systemone`, Bearer auth and
typed named questions. [API contract](https://docs.typesafe.ai/api/system-one).
The fixed revision is deliberate: aliases move, while versioned IDs can be
requested. [Model documentation](https://docs.typesafe.ai/models).
[Provider findings and exact unanswered questions](provider-contract.json).

Offline egress is enforced with a private network namespace containing only
loopback and an nftables default-drop output chain allowing exactly the selected
fixture IP/TCP port plus established traffic. Before connecting, the broker
checks the complete kernel ruleset and drops capabilities. After one connect,
its additional seccomp allowlist prohibits new sockets/connects, process launch
and namespace changes; only FIONBIO is allowed among ioctls for Python TLS.
The worker's existing namespace/seccomp bytes are unchanged. Strict broker checks
enforce the exact logical host, port and path; TLS verifies the chain and host.
The fixture override changes only the numeric local peer and trust root.
No DNS, environment proxy, SDK, telemetry, redirect or retry path is used.

Dispatch intent is committed before socket creation; POST intent precedes the
write. Raw entity prefixes are committed incrementally, including on disconnect,
timeout, output limit and broker death. Restart reconciles uncertainty without
retransmission or refund. HTTP status, selected safe headers, optional request
IDs, exact model strings, usage and TLS/egress evidence accompany the receipt.
Identity absence or mismatch prevents acceptance. A valid schema alone supplies
no provenance: every new observation explicitly identifies a **local fixture**,
and never claims a genuine SystemOne response or independent model attestation.

[Acceptance evidence](evidence/qualification/qualification.json) contains **22
locally exercised cases**: valid and malformed typed bodies, invalid JSON,
4xx/5xx, fixed-length and chunked truncation, timeout after delivery, actual broker
exits after intent/partial bytes, unknown/mismatched identity, oversize, redirect,
destination changes, duplicate submission, worker socket/credential denial,
absent kernel policy, certificate/hostname failures, and raw/receipt tampering.
The valid exchange retains all 237 entity bytes and three scoped observations.
Each of 22 reservations remains consumed. Repeated resume is byte-idempotent;
synthetic credential canaries are absent from custody. Kernel probes against
other IP/ports time out, with firewall drop counters, and the broker itself
observes EPERM for a second socket. Private fixture keys were deleted.

**35 focused regressions passed.** Read-only preservation checks verified eight
historical seals and 46 archived campaigns without changing files. The original
custody root verified all **40,538 entries**, 1,165 operator-sealed files, 4,699 V5
files and 36 command records. The relocated public checkout cannot replace that
original-root check; its stale historical validation diagnostic is retained.
[Recorded checks](evidence/verification.json), [preservation](evidence/preservation.json).
Hash chains and delivered checksums detect evidence edits; they do not provide
provider signatures or protect against rewriting every independent custody anchor.

Production egress/TLS deployment and credential injection remain **BLOCKED**.
Account entitlement, immutable serving identity, remote internal replay,
timeout/billing reconciliation and enforceable usage/cost bounds remain **UNKNOWN**
or unqualified. Local TLS proves none of those provider-side properties.
The default manifest is rejected before campaign creation. Enabling a field and
recomputing its hashes is rejected too. Real dispatch needs a separately reviewed
implementation and the precise later decision in [the PI approval sheet](APPROVAL.md).

Reproduce with new output directories (Linux user/network namespaces, bwrap,
nftables, libseccomp and OpenSSL are required):

```sh
python -B -m engineering_qualification_v1.q1_executor.systemone_https_v1 prepare --output /tmp/new-disabled-manifest
unshare --user --map-root-user --net sh -c 'ip link set lo up && python -B -m engineering_qualification_v1.q1_executor.systemone_https_v1 qualify --output /tmp/new-offline-TLS-qualification'
python -B -m engineering_qualification_v1.q1_executor verify --campaign engineering_qualification_v1/q1_executor/systemone_https_v1/evidence/qualification/valid/campaign
python -B -m engineering_qualification_v1.q1_executor.systemone_https_v1.preservation
```

No real SystemOne/JEV call or provider credential access occurred.
