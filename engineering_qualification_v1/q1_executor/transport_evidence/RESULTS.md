# Actual offline transport and isolation qualification

**Synthetic engineering only. No real provider, JEV, Copilot, cARL, historical Codex executable or live Q1 campaign was invoked.**

Implemented `q1-offline-subprocess-v1`: a sealed-byte transport envelope/result contract; a pinned local subprocess implementation with namespace/syscall confinement; and an explicit offline-only path through the existing Q1 executor. The existing SQLite reservation, budget, dependency, journal, response and validation machinery remains authoritative. There is no second scheduler, attempt registry or evidence database.

Reservation and request/envelope bytes commit before the launch intent and Popen. The manifest pins the requested role/provider/model/version/judge, attempt/context identity, transport configuration and Python/Bubblewrap/libseccomp/bootstrap/fixture bytes. Response bytes and process/identity provenance are separate from assessment diagnostics. A versioned manifest extension, `transports` table, journal events and `q1-offline-subprocess-v1-receipt` explicitly extend the old formats. Original records are never rewritten.

Actual representative execution: **15 scheduled, 10 reserved, 10 subprocess launch intents/verified bootstraps, 6 completed valid, 1 invalid, 4 blocked, 1 interrupted, 3 unavailable**. Generator, native specialist, cARL specialist, continuation and reversal paths completed. Ten invented budget units remained consumed, including the interrupted invocation; remaining budget zero. Fake-provider invocations zero, real-provider calls zero. This is the existing diagnostic slice, not the proposed 153-position natural Q1 campaign. Its terminal categories match the earlier fake-interface slice. The 153-position proposal and scientific contracts are unchanged.

The executor was deliberately terminated with exit 75 while the interruption adapter was running and ignoring SIGTERM. Its three recorded process identities were observed stopped after parent death; the OS namespace/die-with-parent control contained them. Recovery retained `partial-before-hang`, one reservation and one invocation for that position, marked it interrupted and blocked its child. A second demonstration covers interruption before Popen (zero launches), and another covers a valid saved response without a terminal receipt (never promoted to success). All resumed twice without reinvocation; additional completed resumes preserved every campaign file byte. No saved PID was used as a kill target.

| Required scenario | Actual observation | Control exercised |
|---|---|---|
| 1 Valid generator | demo baseline completed | unchanged assessment validation; sealed byte delivery |
| 2 Valid specialist | demo native and carl completed | unchanged three-dimension specialist parser; shared synthetic judge |
| 3 Malformed output | invalid / malformed is invalid | model-output failure retained, no repair |
| 4 Partial output then failure | partial_failure exits 23; raw {"partial": retained | wrapper raw capture + unavailable transport result |
| 5 Timeout after start | timeout exits -9 with partial-before-hang | parent deadline and SIGKILL; completion uncertain |
| 6 Crash before publication | crash exits 24, no response content | process status capture; unavailable, never unchanged |
| 7 Identity mismatch | identity_mismatch unavailable | executor exact requested/observed model+version comparison |
| 8 Identity unavailable | identity_unknown unavailable | executor unknown identity stays null/unavailable |
| 9 Duplicate invocation | additional_checks duplicate rejected before Popen | existing SQLite transport/reservation projection |
| 10 Interruption after reservation | reservation-campaign: 1 reservation / 0 launches | durable reservation; recovery interrupted; two stable resumes |
| 11 Interruption after invocation | demo running invocation killed; receipt-gap campaign also interrupted | OS process-tree teardown; durable stream prefix; no replay/promotion |
| 12 Forbidden files | forbidden_file denied with ENOENT | mount/PID namespaces, not path convention |
| 13 Child process/tool/exec | spawn and exec denied with EPERM | OS irreversible seccomp allowlist |
| 14 Network | raw libc socket denied with EPERM | OS seccomp allowlist; no real connection attempted |
| 15 Conversation/session reuse | new context cannot read prior private session | fresh OS tmpfs home/work/PID context and filtered environment; provider-side remains unqualified |
| 16 Alter sealed inputs | source_write and policy_write denied with EROFS | OS read-only input mount + executor digest rechecks |

Cancellation was also exercised: the non-cooperative hang was killed with SIGKILL, its raw prefix preserved and its private staging tree removed. Six corrupt-copy probes rejected changed envelopes, transport records, observed versions, raw bytes, receipt bindings and journal events. The read-only verifier first accepted pristine relocated copies and left all corrupt copies unchanged. Five self-rehashed manifest mutations additionally reject network/tool permission escalation, executable substitution, request-source rebinding and an unimplemented real-provider scenario.

| Containment property | Enforcing layer | Qualification scope / actual evidence |
|---|---|---|
| Filesystem and research custody confinement | OS: mount/user namespaces | QUALIFIED_LOCAL_PROFILE: forbidden_file ENOENT; host canary existed and unchanged; only /usr + sealed inputs exposed read-only |
| Sealed source/policy integrity | OS read-only mount + executor hash bindings | QUALIFIED_LOCAL_PROFILE: source_write and policy_write received EROFS; envelope/request/packet hashes reconstructed |
| Child process, shell, exec and thread denial | OS seccomp default-deny native allowlist | QUALIFIED_LOCAL_PROFILE: spawn/exec EPERM; benign namespace without inner filter allowed fork |
| Network denial, including direct libc socket | OS seccomp; outer host also restricted | QUALIFIED_LOCAL_PROFILE: raw socket syscall EPERM; no socket syscall admitted by inner allowlist; no inherited sockets |
| Fresh local session/context | OS fresh PID/mount/home; wrapper literal environment and isolated Python startup | QUALIFIED_LOCAL_PROFILE: session_seed wrote private history; next independent reuse received ENOENT; synthetic env/session canaries absent |
| Timeout, cancellation and executor death | Wrapper SIGKILL + OS die-with-parent/PID namespace | QUALIFIED_LOCAL_PROFILE: hang ignores SIGTERM; timeout/cancellation -9; three abandoned process identities observed stopped |
| First attempts and durable accounting | Existing executor SQLite transactions/PK/lock/journal | QUALIFIED_SAME_CAMPAIGN: reserved before launch; duplicate refused without Popen; interruptions consumed once, never reinvoked |
| Raw prefix, output validity and identity missingness | Wrapper capture + executor unchanged v2 validators | QUALIFIED_SYNTHETIC_CONTRACT: partial bytes durable; malformed invalid; missing/mismatched identity unavailable; failed parents censored |
| Landlock | Unavailable platform control | UNAVAILABLE_NOT_USED: ABI query -1 / errno 38 in this environment |
| Network namespace setup | Unavailable platform control | UNAVAILABLE_NOT_USED: bwrap NETLINK_ROUTE socket EPERM; network denial instead enforced by installed seccomp |
| Provider-side conversations, served identity and real CLI/SDK one-shot behavior | Requires provider/adapter cooperation and separate qualification | UNQUALIFIED_LIVE_BLOCKED: no real provider, CLI, SDK or service exercised; identity reports are synthetic and untrusted |
| Production credentials and complete runtime-image confidentiality | Requires reviewed runtime image and production deployment controls | UNQUALIFIED_LIVE_BLOCKED: host home/etc/run/custody absent; no live credentials read; no claim that /usr contains no embedded secrets |

The non-cooperative subprocesses were contained for the stated local profile: forbidden reads could not reach an existing synthetic host canary, sealed input writes failed, process/exec and direct libc socket calls received kernel denials, prior private session state was absent, and timeouts/executor death stopped the process trees. A benign unfiltered namespace control successfully forked, demonstrating that the inner filter adds an actual process-execution restriction. Passing fixture self-reports alone were not accepted: pinned wrapper startup, kernel errno, host-side canary/evidence hashes and process identities were also checked.

The filesystem boundary is an OS mount namespace exposing only read-only `/usr` and sealed inputs, with private 16 MiB tmpfs home/work/response mounts. The syscall boundary is a native libseccomp allowlist installed before adapter code, with no-new-privileges and dropped capabilities. Exec/clone/fork/socket/ptrace/process_vm/io_uring/namespace and privilege operations are not admitted. Limits include two-second wall timeout, ten-second CPU, 256 MiB address space, 32 descriptors, 1 MiB file size and bounded stdout/stderr. The wrapper supplies only five literal environment values and isolated Python startup; the repository, host home, custody directories, `/etc`, `/run`, provider sessions and inherited sockets are not exposed. The response protocol is stdout/stderr; scratch filesystem contents are not response publication or preserved evidence.

This host returns ENOSYS (38) for the Landlock ABI query, and Bubblewrap network setup fails at NETLINK_ROUTE socket creation. Those controls are **unavailable, not qualified or silently assumed**. The required filesystem containment instead uses the successfully exercised namespaces; required network denial uses the installed syscall filter. There is no uncontained fallback if required namespace/bootstrap/filter startup fails. These observations do not characterize every host kernel configuration.

All **123 targeted tests passed, zero final failures**: 41 executor/transport/full-matrix/preflight tests and 82 pinned instrument, continuation, RD05 tooling and harness regressions. Existing unrelated legacy CLI tests were not repaired or claimed to pass. `readonly_reconstruction.stdout` preserves full read-only reconstruction of the transport campaign, including every request/envelope, transport snapshot, raw response, identity, receipt, dependency and hash-chain event. The 15-position legacy and both 153-position historical campaigns still verify read-only against exact original producer fingerprints. Incomplete campaigns cannot inherit changed producer bytes.

Original preservation passed: **40,538 original entries, 1,165 operator-sealed files, 4,699 v5 files and 36 command records**, with zero changed/missing entries. All 167 pre-existing executor files outside the three extended code files, including prior evidence, manifests, receipts and seals, remain byte-identical. All 726 unrelated pre-existing worktree paths remain unchanged. The existing first-attempt, missingness and custody guarantees remain intact within their stated same-campaign/local-authority scope.

Manifest SHA-256: `fa6e20b382c460c0949191df3bb01ff0b21057b649a74a052a817914b4d5d449`. Evidence tip SHA-256: `c98763d65cd16facf36e69271169e3a91ff6f7f9ebf84523a332585a2222e998`. See `acceptance.json`, `additional_checks.json`, `probes/report.json`, command receipts and the separate transport seal. Earlier exploratory runs were in temporary directories; they are not acceptance evidence or scientific repetitions.

Live providers remain blocked: only a pinned synthetic adapter is selectable; networking and tools are denied; real CLI/SDK adapters, approved delivery and one-shot/retry contracts, real served-model/judge attestation and provider-side context isolation have not been qualified. Production credential isolation and runtime-image confidentiality require separate review; a fresh process and environment allowlist do not prove them, and no live credential was read. Requested/observed equality here is explicitly untrusted fixture self-report, not identity attestation. An interrupted end timestamp is local recovery finalization, not remote completion. Cross-host/copy reservation authority, approved policy/source packets, RD03/governing-policy decisions, actual usage budgets and explicit live authorization remain separate blockers.

Primary technical references: [Linux seccomp documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html) explicitly distinguishes syscall filtering from a complete sandbox; [Linux Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html) describes its separate access-control layer and ABI probe. Local qualification above is based on preserved execution evidence, not documentation alone.

**Q1 OFFLINE TRANSPORT INTEGRATED — LOCAL ISOLATION QUALIFIED, LIVE PROVIDERS BLOCKED**
