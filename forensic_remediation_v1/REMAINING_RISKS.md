# Remaining risks and explicit blocks

## Qualification is blocked

**No generator is strictly qualified.** Successful execution of an offline
control matrix is not successful strict-isolation qualification. V5's 48
real-CLI controls use loopback fixtures, dummy credentials, fresh homes and
an external-network-disabled namespace. They establish the recorded local
properties only.

| Finding | Observed result | Unresolved requirement |
|---|---|---|
| I1: GPT-6.1 Sol/Codex | Ten internal tools remain advertised. Every advertised route was probed without the watchdog. The deliberately tool-enabled positive control read the dummy sentinel and exposed a dummy provider key. | A preventive, non-bypassable tool-authorization boundary. Post-routing detection and disabled code execution alone are insufficient. |
| R2: Haiku/Copilot | The no-watchdog HTTP-500 fixture received six POSTs during one CLI invocation. Tool advertising was empty, but forced tool responses could trigger an additional model request. | Preventive single-attempt behavior, not a watchdog race. |
| R2: Gemini/Copilot | The corresponding no-watchdog HTTP-500 fixture also received six POSTs. | The same preventive retry contract; a different requested model does not remove the CLI defect. |
| R2: live transport boundary | Networkless BYOK controls were exercised; authenticated GitHub/ChatGPT routes were not. Historical live generators shared host networking. | Provider/authentication-only egress and evidence that the authenticated route has equivalent instruction, tool, session and retry behavior. |

The current generator adapter returns `strict_generator_isolation_blocked`
before staging credentials or starting a process, even with explicit
authorization. No configuration or operator-attestation checkbox overrides
that decision. The experiment engine also rejects live integration runs.
Changing upstream CLIs or adding a preventive broker is a separately reviewed
engineering/methodology decision, not part of this remediation.

## Integrity is not attestation

R4's internal consistency defects are corrected, but a party able to replace
both a receipt and its trusted digest can still fabricate a consistent local
record. Neither hashes, a CLI checksum line, TLS fields nor a reported model
string independently attest provider execution, served identity or correctness.
Retain anchors in independently controlled storage before any live study.

HTTP invocation, fully written request, provider execution and billing are
different events. A partial error or lost receipt can leave execution unknown.
The harness does not infer zero execution from a failed write and does not
automatically reissue a request.

R6's reservation fix is deliberately bounded to the fixed workspace registry
used by the current qualification entry point. It is not distributed
cross-host deduplication. Direct Go CLI calls and legacy v1/v2 diagnostic APIs
are not authorized alternatives to the current gate and do not acquire its
reservation guarantees. Old plans/receipts must not be relabelled as current
qualification. Disk loss, process death and storage rollback can leave explicit
incomplete attempts; there is no claim of provider exactly-once execution.

## Runtime and confidentiality limits

R1's local source, embedded assets, imported extractor, Path B build and full
mounted Codex release are hash-bound. The host kernel and broad read-only `/usr`
mount are not a hermetic runtime image. The namespace can execute trusted
subprocesses and read the mounted runtime; it does not impose a universal
no-exec/no-read syscall policy. This limitation is explicit, not a relaxed
interpretation of strict generator isolation.

Known credential echoes in literal, JSON-escaped and nested base64 forms are
withheld from published process/artifact evidence. This is not a general
detector for unknown secrets, arbitrary encodings or sensitive source content.
Withheld bytes cannot be reconstructed or treated as an original complete
receipt. Keep this package and future raw evidence private; perform a separate
disclosure review before any publication. Cleanup failure is a recorded error
and may leave an owner-only scratch directory requiring controlled cleanup.

## Scientific limits

The policy/role snapshots are proposed instruments, not PI approval. Thresholds,
question semantics and scoring criteria were not tuned. Native JEV and Path B
share SystemOne evidence; Path B adds deterministic policy arbitration, not an
independent model. Future native/Path B evaluations must remain separate calls.

Authored mock claims and challenge effects establish wiring, lineage, schema
and replay properties only. They do not measure model behavior, mitigation
efficacy, correctness, token cost or scientific improvement. The historical
provider fixture is an explicitly unverified import and not a new call.
Provider schema evolution outside the frozen contract must fail closed and
requires a newly reviewed instrument version.

The rejected v4 candidate illustrates why passing authored tests alone was
insufficient: it rejected legitimate provider `type` and choice `confidence`
metadata. Its artifacts and 1,112 completed mock checkpoints plus one incomplete
reservation are retained. V5 adds exact historical-response coverage and fresh
source-bound validation; earlier candidate controls are not recycled.

No live qualification, 81-call pilot, full experiment, new corpus admission,
deployment or independent Iris review was performed. Optional Go race testing
was not rerun: the prior retained evidence records the host's unsupported
39-bit VMA limitation. This is not claimed as a passing race check.

## Artifact location notation

Plans/build records retain the original absolute workspace paths; they are not
portable execution configurations. The isolation evidence's descriptive
`catalog_evidence.path` retains legacy `../adapter_qualification_v1/...`
notation, which must not be resolved relative to the nested `v5/` directory.
The exact original catalog location/hash and a byte-identical private package
copy are specified in `REMEDIATION_REPORT.md` and verified by `verify_package.py`.
This resolves evidence lookup, not current provider availability or identity.
