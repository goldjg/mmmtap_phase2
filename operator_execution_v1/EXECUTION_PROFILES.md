# Execution profiles

Two explicit profiles exist in the new operator manifests. They have different
profile digests, job IDs and manifest identities. Neither profile can be renamed
or weakened in place: runtime validation reconstructs the exact manifest and
rejects drift. Checkpoints repeat the full profile and an evidence-quality label.

| Property | `strict_isolation` | `research_controlled` |
|---|---|---|
| Version | `frozen-v5-unchanged` | `research-controlled-v1` |
| Acceptance criteria | Original v5 preventive contract, unchanged | Explicit lower-assurance research contract |
| Generator qualification | Haiku, Gemini and Sol remain blocked | Operator may authorise a separately gated stage |
| Strict qualification claimed | No | **Never** |
| Evidence label | `strict_isolation_required_not_qualified` | `lower_assurance_operator_supervised_research` |
| Mock label | `mock_not_research` | `mock_not_research` |
| Native JEV / Path B | Offline contracts; require a qualified actual parent | Actual nonempty parent, same source and question pack, separate calls |
| Stage approval | Cannot override the generator block | Must approve the exact stage, lower assurance and frozen instruments |

The unchanged original `phase2.adapters_v2.GeneratorAdapter` still returns
`strict_generator_isolation_blocked` before credential staging or launch.
The original v5 engine also retains its live block. New operator code does not
patch those functions or edit any old qualification evidence. The separate
`STRICT_EXECUTION_MANIFEST.json` plans the full matrix but cannot be run live.

## Control classification

| Control | Preventive | Detective / residual limit |
|---|---|---|
| Fresh sessions | New process, home and scratch for every generator turn; no resume/fork/session flags | Loopback captures check separate session IDs where emitted and absence of prior-session content; deliberately injected prior output is the detector's positive control, not CLI session resume |
| Branch independence | Only B0 and the current branch's assessment/challenge ancestry are reconstructed | Parent hashes and branch/input/generator checks reject contamination |
| Source and checkpoints | Frozen archive/member verification; source is stdin data; read-only `/work`; exclusive first-attempt files | Hash/ledger verification detects mutation; owner/root can defeat local permissions and rewrite hashes |
| Host filesystem | Bubblewrap mount/PID/user/IPC/UTS namespaces hide host home, run checkpoints and all research repositories | `/usr`, CA/DNS files, pinned CLI and its needed runtime remain visible; not a hermetic image |
| Processes | Seccomp rejects non-thread `clone`, `fork`, `vfork`, `clone3` process creation, `unshare`, `setns`, `ptrace`; threads work | This is not prevention of arbitrary computation or direct replacement of the existing CLI process |
| Tools and instructions | No tool grants, no custom instructions, fresh configuration; CLI tools/features disabled as far as supported | Codex still advertises internal tools. Watchdog detection is not a universal pre-dispatch interlock |
| Corpus code | Never checked out, installed, deployed or executed; never written to an executable path | A hostile CLI/provider exploiting in-process facilities is not fully prevented; that is outside strict assurance |
| Credentials | Only explicit Copilot token, isolated read-only Codex auth copy, or JEVKEY for the relevant process; no ambient secrets | CLI can read its own credential. Scope, expiry and remote validity cannot be proven offline |
| Network | Offline controls unshare networking; SystemOne transports use the fixed HTTPS endpoint and refuse redirects | Live namespaces share Gaia networking. No endpoint allowlist is claimed for Copilot/Codex or worker namespaces |
| Retries | Harness invokes once per reserved job; no retry loop or alternate model; Codex request/stream retry settings are zero | Copilot internal retries cannot be preventively disabled; watchdog races and provider-internal retries remain possible |
| Runtime watchdog | Kills the process group on observed tool routing, extra model calls, failures/retries or visible model switching | Buffered, omitted or later events may hide an action that already occurred |
| Model identity | Exact requested models, binary/helper closure and arguments are pinned | Copilot client event is not provider attestation; Codex observed model is null; SystemOne response model is unsigned |
| Cost/budget | Serial execution and permanent per-stage adapter-attempt reservations | Budget is not an HTTP-attempt, token, AI-credit or provider-charge ceiling |

## Gaia containment decision

Preparation observed Gaia, Linux/aarch64, working unprivileged bubblewrap and
libseccomp API 6. `podman`, `docker` and `unshare` are installed, but no container
daemon, image download, orchestration platform, firewall change or APEX change
was needed. Bubblewrap plus a small trusted seccomp launcher is the minimum
implemented process boundary.
The operator software identity additionally binds the kernel release,
bubblewrap binary and the actually loaded libseccomp library.
Inherited-instruction positive controls deliberately re-enable local instruction
reading only inside the offline dummy-provider namespace; all three CLIs then
expose the planted marker, whereas the research-profile controls do not.

Generators get read-only runtime/binary mounts and `/work`, an ephemeral
writable home and `/tmp`, and only their selected authentication material.
The input is not executable source on disk. Native JEV and Path B run in
separate trusted Python-worker namespaces with only the required harness
modules, the pinned Path B executable/policy when applicable, and JEVKEY.
Path B's deterministic prepare/evaluate/replay processes are allowed; they are
not tools authorised to a generative assessor.

Live egress is deliberately described as **host networking, not
provider-only egress**. Authenticated endpoints, CDN addresses, authentication
refresh and provider routing were not discovered by making calls. An unreliable
allowlist would not establish strict isolation, so none is invented.

## Explicit residual limitations

V5 I1/R2 remain unresolved under the strict contract. Its recorded six-POST
Copilot retry behavior, ten advertised Codex routes, and lack of authenticated
route equivalence are not reopened or declared fixed. The new no-child-process
control reduces exposure; it does not change those findings.

No configuration checkbox turns research-controlled execution into strict
qualification. Offline BYOK loopback controls use dummy keys and authored
responses, not GitHub/ChatGPT authentication or model behavior. Live smoke must
record the first actual route outcome without repairing its schema, substituting
models, hiding errors or manufacturing success.
Even an unchanged reported SystemOne model string cannot establish that the
provider's deployment behind an alias has not changed.

The selected v5 prompts/questions/policy remain proposed frozen instruments
until the human approves their exact hash-bound stage manifest. That approval
does not adjudicate claims, validate provider identity, modify thresholds, or
grant permission to execute untrusted code.
