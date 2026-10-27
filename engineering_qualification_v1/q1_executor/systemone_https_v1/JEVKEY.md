**JEV HISTORICAL ACCESS REUSED — Q1 BROKER INTEGRATION QUALIFIED OFFLINE, LIVE PROBE PENDING APPROVAL**

Baseline: `7387e5123e21f2e9e38d126f10fc9d69d69c2edb`. This extends the existing
`q1-systemone-https-v1` transport, broker and executor. It does not onboard a new
provider, change Choice 1 or create a new execution framework. No real JEVKEY
value was read and no provider domain was contacted.

| Previously working | New Q1 requirement | Actual incompatibility | Minimum correction now qualified |
|---|---|---|---|
| `phase2/adapters.py::NativeJEVAdapter` obtains configured `key_env`; `operator_execution_v1/transports.py::systemone` passes `JEVKEY` to its worker | Credential belongs only to trusted broker | Q1 deliberately strips inherited environments and previously hardwired `FixtureSecret` | Keep `JEVKEY` as launcher source; one anonymous pipe to broker after its protection ACK |
| Native serialises `json_bytes(request)` and POSTs Bearer auth to `https://api.typesafe.ai/v1/systemone` | Preserve sealed native body, exact destination/path and verified TLS | No provider-schema incompatibility; credentials and route were fixture-only | Same canonical `model/state/questions` and header; same Q1 HTTPS code, new sealed credential binding |
| V5 cARL `assessment-challenge prepare → evaluate-live`; `live.go::EvaluateLive` sends exact prepared native bytes, preserves entity/receipt, then applies local policy | Choice 1 direct observations, no cARL invocation | Old research worker had credentials, tools and host networking | Broker sends native body; worker stays credential-free and cannot create sockets/exec tools; no cARL process |
| Historical native uses `NoRedirect`, bounded reads/timeouts, no explicit retry loop; default urllib opener can inherit proxy configuration | Default-deny egress and no secondary route/request | Historical success was not endpoint-filtered Q1 containment | Numeric peer + exact nftables IP/TCP-port policy; explicit CA/SNI, no proxy/DNS/retry path |
| V5 cARL disables proxies, redirects, reuse/HTTP2 and `GetBody` replay; deadline and partial-failure receipts | Durable first attempt and incremental custody across broker/executor death | Existing Q1 machinery was qualified with fixture credentials only | Reuse its reservation/dispatch journal and read-only replay; qualify new handoff under actual broker/executor exits |
| Prior bodies report `jev-1.13.0` and token usage | Separate requested ID, returned self-report, independent attestation and charges | Historical requests selected `jev-latest`, not a proven current fixed-version entitlement | Keep sealed request `jev-1.13.0`; mismatched/missing IDs unavailable, attestation/accounting remain separate |

The five original selected bodies were checked against original custody, not
executed again. Native low/cARL low both report usage **584/66**, native multi/
cARL multi **688/88**, earlier native qualification **615/104** input/output
tokens; all self-report `jev-1.13.0`. [Historical access summary](jevkey_evidence/historical-access.json)
and [original request/response selection](../../systemone_contract_resolution_v1/evidence/selection.json).
Successful historical native/cARL access and the typed response family are
evidenced facts. They do not prove today's account/model availability or billing.

The new `q1-broker-jevkey-fd-v1` binding contains source/delivery/protection policy
only. The launcher checks the variable name without inspecting its value, then
reads it only for an explicit bound dispatch after hardening itself and receiving
the broker's ACK. The broker receives a clean environment and one startup-control descriptor
number, not the operator environment or key arguments. Its credential pipe does not
exist until it disables dumpability and sets hard/soft core limits to zero.
The broker transfers only the write end to the already protected launcher using
SCM_RIGHTS; kernel SCM_CREDENTIALS must identify the exact launched broker PID
before the launcher reads its source. A stolen startup-control endpoint cannot
receive the outgoing descriptor or forge that PID.
It consumes/closes the pipe after egress/TLS checks; intervening child processes
inherit neither the key environment nor descriptor. Subsequent process creation
is prohibited by the existing broker filter. Worker creation precedes the pipe;
its original namespace/mount/capability/seccomp policy and clean environment
remain unchanged. Only a non-secret observation probe was added to its adapter.

Arbitrary dummy secrets, not the old fixed canary, qualify response-header
suppression and streaming body checks, including mixed JSON escapes across reads.
A reflected credential stops capture; the previously committed safe prefix stays
exact, with an explicit failure and uncertainty. No redacted body is presented as
an original response, and rejected credential-bearing bytes are not hashed or
archived. Process protection covers the launcher/broker after hardening; it does
not erase the operator's pre-existing source environment, eliminate Python's
startup window or promise zeroisation of every interpreter copy. Privileged
inspectors remain outside this protection claim.

[Actual acceptance](jevkey_evidence/acceptance/acceptance.json): **19 one-position
cases, 19 consumed reservations, eight local TLS POSTs, zero provider calls**.
The actual executor/isolated worker/broker used two private namespaces linked by
veth (`192.0.2.1/30` → `192.0.2.2`), with exact nftables default-drop egress and
post-connect capability/seccomp restrictions. No Gaia host rule or route changed.
Both valid exchanges preserve all 237 entity bytes, three Choice 1 observations,
model self-report and usage, with no independent attestation or release authority.

Negatives covered missing/invalid source, unrelated-process opens of launcher/
broker `environ`, `mem`, and descriptor targets (EACCES), worker key/FD absence,
child inheritance, raw/escaped credential reflections, unknown/mismatched model,
actual broker/executor crashes, destination/request/policy alterations, sockets,
spawn/exec, readonly writes and hidden host files. Kernel IP/port probes timed out
with drop counters. Recovery without JEVKEY made no new request and changed no
terminal evidence. Request/policy/receipt projection tampering was rejected.
**40 focused regressions passed**; preservation details are in
[verification.json](jevkey_evidence/verification.json). No 153-position execution
or full historical qualification was repeated. The superseded inherited-pipe
draft and its first-attempt diagnostics are retained separately as unqualified
development; they are excluded from final acceptance and reconstruction counts.

The operator confirms existing Gaia `JEVKEY`. A name-only check found that the
task service does **not inherit** it; this is a launch-context issue, not a reason
to obtain another key/account/login. Later authorised execution must originate
from that established JEVKEY-bearing operator context. Every test executor here
instead received a freshly constructed dummy-only environment.

Remaining before a genuine probe: identify the exact approved production peer,
trust anchors and controlled routed namespace; arrange namespace-scoped authority
to inspect its nftables policy before the broker drops capabilities (ordinary
Gaia UID 1000 lacks host CAP_NET_ADMIN). The current sealed admission allows only
loopback/TEST-NET qualification peers: production admission still requires an
explicitly reviewed binding change and PI permission, not a switch or worker
relaxation. Confirm current fixed-revision availability and applicable account
terms; record acceptable limits for unsigned identity, internal replay and
timeout/billing reconciliation. These remote uncertainties do not invalidate
historical access or require another transport/secret platform. The
[JEVKEY manifest](jevkey-manifest/manifest.json) remains **DISABLED**.

Reproduce the new boundary qualification with new output paths and no real key:

```sh
unshare --user --map-root-user --net sh -c 'ip link set lo up && python -B -m engineering_qualification_v1.q1_executor.systemone_https_v1.jevkey_qualification --output /tmp/new-jevkey-offline'
```

The harness never obtains the operator's value; it constructs dummy-only child
environments and deletes generated fixture private keys. Existing evidence is
read-only. Frozen questions, validators, the 153-position topology, RD05 and
unrelated worktree contents are preserved.
