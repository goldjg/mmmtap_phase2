Q1 lower-assurance candidate v1

The PI-approved assurance direction is now an explicit immutable designation:
**LOWER_ASSURANCE_ENGINEERING_QUALIFICATION**. This is a versioned extension of
the existing Q1 engine, not another executor. Strict scientific qualification
remains separate and blocked. Lower-assurance receipts cannot be relabeled or
pooled as strict data through configuration/report edits that pass verification.

Review the [one candidate](candidate/manifest.json) and the compact
[PI decision sheet](PI_DECISION_SHEET.md). Launch approval is **NOT APPROVED**.
No live CLI inference, provider/JEV call, actual key/token inspection or account
operation was performed. Existing subscription routes were retained; no direct
API replacement or provider onboarding was introduced.

Changed execution boundary

- Gemini/Haiku use the current pinned Copilot binary; Sol uses the current pinned
  Codex release/closure. All three historical option sets were tested with help
  only in credential-free, networkless sandboxes. Current Copilot explicitly
  requires `--sync-session off` instead of `--no-remote-export`; no restriction
  was silently removed. Raw compatibility output is retained under `evidence/`.
- One unique Q1 reservation/invocation journal commit precedes each CLI Popen.
  A new contained process/home/workspace is created per attempt, with no harness
  retries, reruns, repairs or fallback. Only the selected subscription credential
  may be supplied after an explicit live authorisation. JEVKEY never enters a CLI.
- The CLI profile is separately versioned, allows internal runtime children and
  host networking only in production, and denies namespace/admin/inspection
  syscalls. Host homes/repository/custody are hidden, work/runtime are readonly,
  capabilities are dropped and all child processes die with the context.
  Client tool restrictions plus watchdogs are detective, not a universal tool
  interlock. Endpoint filtering, remote single execution/context isolation and
  serving attestation are not asserted. Selected CLI auth has the same-UID
  inspection limitation explicitly stated in the assurance descriptor.
- Raw available stdout/stderr/events are preserved as **CLI evidence**, never
  provider HTTP. Client-reported and requested models are separate. Codex model
  attestation is unavailable; its output may be contract-valid in this lower
  profile without fabricating an observed serving model. Usage is not billing.
- Native/cARL SystemOne reuse the original strict worker, HTTPS broker, typed
  Choice 1 parser, policy derivation, raw custody and JEVKEY FD handoff. Production
  broker namespace entry is separate from CLI host networking; only reviewed
  namespace handles are admitted, then the existing exact nft/TLS controls apply.
  The strict worker/bootstrap and frozen validators are not changed.

Evidence and authorisation

The [candidate run](evidence/candidate-run/acceptance.json) uses injected event
streams inside the actual CLI containment profile and the existing private TLS
SystemOne peer. One full run is necessary because every generator execution
binding and every receipt's assurance changed. Prior SystemOne transport error/
egress campaigns are reused read-only; no second broad adversarial matrix is run.
This is not actual CLI inference or proof of current remote availability.

All 153 positions receive a receipt, including failures/censored descendants.
Assurance is bound into the manifest, sealed request, transport evidence and
receipt. Read-only reconstruction checks every event/receipt; completed original
evidence is never rewritten or relabeled. A partial reservation is consumed on
recovery, with available stream prefixes and uncertainty; never reinvoke it.

The live guard remains active. A future authorised operator must supply a
non-secret PI decision record adopting the exact proposals/profile, account/cost
acceptance and reviewed deployment, and explicitly name the manifest digest in
the `launch --authorize-exact-manifest … --pi-record … --pi-record-sha256 …`
command. That separate decision is sealed in creation custody. The candidate
continues to say NOT APPROVED. No approved record or automatic enablement is
provided by this task. Production custody and its fixed deployment authority
must be provisioned privately by the operator; no host security configuration
is modified here.

Reproduce offline into a new persistent directory:

```sh
env -u JEVKEY -u COPILOT_GITHUB_TOKEN unshare -Urn python -B -m engineering_qualification_v1.q1_executor.lower_assurance_v1 qualify --output /persistent/private/new-q1-lower-offline
```
