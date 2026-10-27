**SYSTEMONE FIRST LIVE PROBE — NO-GO, SPECIFIC PREREQUISITES OUTSTANDING**

Gaia, 2026-10-27; baseline/upstream main
`d1e4189c9fb1d96ee2da21f15d09f1528468273e`. **The existing implementation
remains disabled and unlaunchable. One real request cannot currently be
authorised responsibly.** Only this report and [readiness.json](readiness.json)
are added. No execution code, security configuration or historical evidence changed.

Reusable qualification: durable reservations, one client POST, no retransmission,
incremental raw custody, Choice 1 parsing, receipts/verifier and worker isolation.
The manifest retains one synthetic lamp document, one claim, the exact three
original questions and `jev-1.13.0`; one reservation/dispatch/POST; zero retries,
fallbacks, generator, cARL, continuation or release authority. Limits remain
one-second provider deadline, ten-second supervision, 8,192-byte request/entity
ceilings and 16,384 header bytes. Usage/cost maxima are null. Local dispatch does
not establish remote execution count.

Read-only checks passed: **449 sealed entries**, **22 saved campaign
reconstructions**, both saved tamper rejections, eight historical seal-file
hashes and complete HTTPS-package byte preservation. Original custody again
verified **40,538 entries**, 1,165 operator-sealed files, 4,699 V5 files and 36
command records. No campaign, test suite or TLS qualification was rerun.

Locally verified Gaia capabilities: Linux **6.12.109+rpt-rpi-v8/aarch64**,
Bubblewrap **0.8.0**, nftables **1.0.6**, libseccomp **2.5.4**, OpenSSL **3.0.22**,
Python **3.11.2**, SQLite **3.40.1**; namespace interfaces/positive limits and
seccomp filter actions. Prior Gaia fixture evidence proves their exercised use;
no new namespace/filter was created now. The task sandbox denies Netlink;
outside it the operator has zero effective capabilities and host nftables
inspection returns EPERM. Production policy is **unverified**, not proven absent.
Landlock returns ENOSYS. Current code requires loopback-only interfaces and an
exact `127.0.0.1` fixture ruleset; production routing cannot be configured into
it. IP/port enforcement must accompany exact host/path and TLS checks. Worker
filesystem, socket/process denial and clean environment need no relaxation.

Explicit TLS trust is technically available: Python loaded the public CA bundle
with certificate/hostname verification and TLS ≥1.2; its digest and 148 CA
certificates are recorded. Production trust anchors remain unapproved; no provider
address, certificate, DNS or connectivity was inspected.

**Credentials: BLOCKED.** `BrokerSecret` is a protocol; dispatch hardwires
`FixtureSecret`. No approved broker-specific source/service/principal policy was
identified. Systemd 252 and `/run/credentials` exist, but establish no approval;
contents were not inspected. Clean broker environment/closed descriptors do not
prove isolation from unrelated host processes. The operator is dumpable, with
soft core limit zero and no Yama interface observed. Header scrubbing recognises
only the test-canary literal, not arbitrary credentials/reflections. These are
production assurance gaps. Copilot/Codex/ChatGPT authentication is inapplicable.

| Prerequisite | Classification |
|---|---|
| API/Bearer schema; fixed revision request syntax | DOCUMENTED_ONLY in preserved [provider findings](../q1_executor/systemone_https_v1/provider-contract.json) |
| Current entitlement, actual `jev-1.13.0` availability, account permission | UNKNOWN; historical successes establish none |
| Account tariff, balance, enforceable usage/spend ceiling; error/timeout charges | UNKNOWN; one POST/byte ceilings are not financial bounds |
| Request correlation and usage/billing reconciliation | UNKNOWN; optional IDs and documented counters do not establish a ledger join |
| Serving identity | Self-report DOCUMENTED_ONLY; independent immutable-revision attestation UNKNOWN |
| Provider-internal retry/replay, timeout cancellation/completion | UNKNOWN; local no-retransmission VERIFIED |
| Live permission | BLOCKED; production guard refuses and PI approval is absent |

Required actions, in priority order; detailed evidence/type/verification mappings
are in the machine-readable record:

1. **Operator/provider:** supply dated non-secret account entitlement, revision
   access, permitted-use and financial-bound evidence. Answer the existing
   identity, correlation, internal-replay and timeout/billing questions. Review
   statements and reconciliation specifications without another inference.
   Any later account authentication needs separate operator authority.
2. **Operator configuration:** approve a controlled broker namespace, vetted
   numeric destination(s):443/default-deny policy, explicit trust anchors and an
   available broker-principal-bound secret mechanism, including process/access
   protection. Verify redacted bindings, permissions and rule exports; no general
   worker egress or host-security weakening.
3. **Bounded code gap:** after those choices, separately authorise the minimum
   existing-code production binding/guard, secret hookup, secret-safe errors/
   headers and accurate provenance. Configuration alone cannot supply them.
   These omissions are intentional, not failed offline qualifications. Qualify
   only changed controls offline using synthetic peers and arbitrary dummy
   credentials, including unrelated-process denial. Keep live dispatch disabled;
   no new transport, broker, sandbox or secret-management framework is needed.
4. **PI decision:** review final request/policy/code/deployment/manifest digests,
   an evidenced maximum usage/cost and the treatment of identity limitations and
   an ambiguous first attempt. Explicitly decide any acceptable residual risk
   within approved bounds; missing necessary assurances retain NO-GO.

Maximum eventual approval: **one sealed synthetic native POST** to fixed
`jev-1.13.0`, unchanged Choice 1 questions, one consumed reservation even on
failure, no reissue/fallback/generator/cARL/continuation or operational authority.
The existing [approval sheet](../q1_executor/systemone_https_v1/APPROVAL.md) applies.
No permission is granted here. No provider-domain access, authentication,
credential read/hash/copy/test or live execution occurred; GitHub access served
only the requested repository delivery.


Update — existing JEV access and the Q1 boundary

The historical native/cARL SystemOne path was already working with JEVKEY.
The new [JEVKEY integration qualification](../q1_executor/systemone_https_v1/JEVKEY.md)
closes the broker handoff, arbitrary-secret disclosure, process-inspection and
routed-private-network gaps identified above: 19 dummy-only cases and 40 focused
regressions passed. The original findings above describe the earlier baseline;
credential/broker integration is now **QUALIFIED OFFLINE**, not provider onboarding.
The operator confirms the Gaia variable; the task service does not inherit its
name, so later authorised launch must use the established operator context.
No real value was inspected or used. Production admission remains disabled:
choose the operator's exact peer/trust/controlled namespace binding, namespace-scoped
policy-inspection authority and final one-request approval. Current fixed-version
availability, billing terms, internal replay and independent serving identity
remain unestablished; they do not justify redesigning the working integration.
