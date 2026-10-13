# Local cARL-JEV CLI capabilities

## Finding and scope

The installed `carl-jev` is a cARL development CLI with a **Git-based semantic
review command**, not a general SystemOne question CLI. It can include caller
text (including JSON text and an existing assessment) in `state.task`. That
transport does not replace its Git evidence collector, its nine fixed questions,
or its compiled review policy. The underlying evaluator is a separate Go
interface and HTTP adapter; its architecture does not establish an inherent
SystemOne limitation to Git diffs.

This investigation made **zero live evaluator calls**. Seven invocations of
`review --dry-run` exercised input handling, including three expected failures.
No bridge, experimental job, pilot, test suite, deployment, source rewrite or
historical admission was run. Existing source and tests were read as evidence,
not executed. Only this investigation directory and a session-local evidence
collector were written.

## Binary and accessible implementation

| Property | Observed value |
|---|---|
| Located and resolved executable | `/home/prometheus/bin/carl-jev` |
| SHA-256 | `b34696d54d0b9c910d48c9adbe0155f825617d8e4c8981e58a2f50b5d0868428` |
| CLI version | `dev` |
| Bundled runtime | `1.0.0`, source `goldjg/cARL`, tag `v1.0.0`, commit label `dev` |
| Go build | `go1.26.5`, Linux/arm64, CGO enabled |
| Go module / entry point | `github.com/goldjg/carl` / `github.com/goldjg/carl/cmd/carl` |
| Relevant source worktree | `/home/prometheus/git/cARL-semantic-eval` |
| Clean source revision | `8a9d5ba6540fb52a7cfa6cbcf4c125e514805c04` |
| Worktree branch | `feature/semantic-evaluation-jev` |

The main `/home/prometheus/git/cARL` worktree is at a different revision,
`8938d62d77e8c0d68eaa824bf35dfb577e0e757c`. The separate semantic-evaluation
worktree contains `internal/review`, `internal/semantic` and their tests.
Binary disassembly debug paths point to this worktree, with matching function
names/line locations. Help and offline behavior agree with the implementation.
This is strong local source correspondence, **not** a reproducible-build,
signed-release or exact source-to-binary attestation; build metadata contains
no VCS revision.

Exact stdout, stderr, argv, cwd, hashes and process status are under `evidence/`.
In particular: `root_help.*`, `review_help.*`, `version.*`,
`go_build_metadata.*`, `binary_*_disassembly.*`, `source_revision.*`,
`worktrees.*`, and `binary_identity.json`. `source_index.json` binds copied,
unmodified source evidence to paths, line counts and SHA-256 hashes.

## Exact command help

The following is the root help, emitted on stderr despite exit 0
(`evidence/root_help.stderr.txt`); raw captured streams remain authoritative.

```text
Usage: carl <command> [arguments]

Commands:
  convert    Migrate durable governance knowledge from legacy sources into cARL artefacts
  doctor     Diagnose runtime issues and provide actionable remediation guidance
  explain    Explain pack-level policy provenance and evaluation
  harness    Manage and inspect harness adapters for AI coding agents
  init       Install the cARL runtime into the current repository
  map        Generate and update .github/carl/repo-map.json from repository structure
  pack       Discover, verify, install, select, and compose instruction packs
  plan       Discover, validate, and summarise plans in .github/carl/plans/
  reconcile  Update repository-specific memory sections from current repo-map data
  repair     Restore modified managed cARL artefacts to their canonical state
  review     Run bounded semantic review over a git diff
  status     Report whether the installed cARL runtime is healthy, missing, or drifted
  trace      Trace the effective pack-level policy evaluation
  version    Show CLI, bundled runtime, and repository runtime version information

Run 'carl <command> --help' for more information on a command.
```

```text
Usage: carl review [--base <ref>] [--head <ref>] [--format text|json|markdown] [--dry-run] [--task-file <path>] [--task <text>]
```

Source `internal/review/review.go:147-174` supplies the details omitted from that
one-line help:

| Flag | Implemented behavior |
|---|---|
| `--base` | Git base ref; defaults to first resolvable `origin/main`, `main`, then `HEAD~1` |
| `--head` | Git head ref; omission compares base to the working tree, not an immutable committed head |
| `--format` | Output selection only: `text`, `json`, `markdown`; not an input format |
| `--dry-run` | Build state and load config, then print questions/state without constructing/calling evaluator |
| `--task` | Caller string, redacted before inclusion; takes precedence over `--task-file` |
| `--task-file` | Repository-relative file, lexically confined to the repo, read as text, limited to 12,000 bytes, redacted |
| `--help` | Print usage before repository discovery |

There are no registered `evaluate`, `systemone`, `challenge`, `--questions`,
`--source`, `--stdin`, `--policy-file` or `--config` paths in the review
implementation. Positional arguments are rejected. `--task-file -` would mean a
file named `-`, not stdin.

`harness` exposes `list`, `status`, `sync`: it manages coding-agent loader files,
not SystemOne execution. `explain <pack-id> [--json]` and `trace [--json]` explain
deterministic instruction-pack selection/composition, not JEV responses or the
review signal policy. See exact corresponding help captures and
`cmd/carl/main.go:72-105`, `ARCHITECTURE.md:315-335`.
No mutation-oriented commands were invoked.

## Transport, origin and evaluation are different

1. **Transport:** `--task` carries arbitrary string content. JSON remains a
   string; fields called `source`, `assessment` or `questions` have no special
   parser meaning. A repo-relative task file is another string transport.
2. **Origin:** `BuildState` requires a real Git repository and collects a diff,
   refs, resolved object IDs and changed-file metadata. It does not verify
   signatures, publisher identity, correspondence to the Phase 2 archive,
   deployment state, source hashes or a research provenance receipt. Mutable
   working-tree review is deliberately supported. Git collection is not
   equivalent to authenticated historical provenance.
3. **Evaluation:** `DefaultQuestions()` always supplies eight booleans and one
   score. The provider returns signals; compiled cARL code maps them to findings
   and a decision. Task text can condition the evaluation but cannot add typed
   claim-support questions or a structured assessment role.

The stricter `authenticated_git_diff_v1` requirement belongs to the Phase 2
adapter/research contract. This report does not weaken it. Conversely, it
corrects any reading of earlier reports that treated that contract as a
cryptographic feature of the installed CLI.

## Offline input probes

All seven commands used `--dry-run --format json --base
e725f6f5e89a0225b79a033dbc8b21219179f361 --head
8938d62d77e8c0d68eaa824bf35dfb577e0e757c`. Except for the no-repository negative
control, cwd was the existing cARL worktree. No commits or diffs were manufactured.
An allowlisted environment excluded API credentials; Git hooks/fsmonitor/global
configuration/replacement objects were disabled. This was a bounded probe over
an already inspected documentation diff, not a general sandbox qualification.

| Probe | Actual result | What it establishes |
|---|---|---|
| Baseline | Exit 0; full dry-run state | Real Git state collection and fixed question schema |
| Inline JSON task | Exit 0; exactly that string in `state.task` | Source/claim bytes can travel as task text, not typed assessment input |
| Same JSON on stdin | Exit 0; payload identical to baseline | stdin is not an input channel |
| Existing relative governance task file | Exit 0 | Repo-relative text-file transport |
| Absolute Phase 2 task-file path | Exit 1; `task file must be repository-relative` | Current Phase 2 absolute temporary task path is incompatible |
| Inline task outside any Git repo | Exit 1; `locate git repository: fatal: not a git repository ...` | Task-only text mode does not exist |
| `--questions not-read.json` | Exit 1; `flag provided but not defined: -questions` | No direct custom-question flag |

The benign inline payload is recorded verbatim in
`evidence/dry_run_inline_json_task.json`. It contained `source: "Hello"`,
an assessment claim `"Greeting only"`, and a proposed `claim_supported`
question. The dry-run question array stayed byte-equivalent as parsed JSON to
the nine defaults. No evaluator answered any of these questions.

## Request construction and actual schemas

See `INTERFACE_EVIDENCE.json` for machine-readable capability references and
`evidence/contract_schemas.json` for source-derived structural schemas.
Those schemas are investigative descriptions, not an installed validation
feature. Exact Go JSON tags are preserved in the source snapshots.

The CLI HTTP request is:

```text
{
  model?: string,
  state: {
    repository: {name: string, root?: string, currentBranch?: string, remoteOrigin?: string},
    review: {base: string, head?: string, baseSha?: string, headSha?: string,
             changedFiles: ChangedFile[] | null},
    diff: {text: string, limitBytes: integer, truncated?: boolean, redacted?: boolean},
    context?: [{path: string, content: string, truncated?: boolean, redacted?: boolean}],
    task?: string,
    dataCategories: [{name: string, description: string, included: boolean,
                      redacted?: boolean, truncated?: boolean}] | null
  },
  questions: [{id: string, kind: "boolean" | "choice" | "score",
               description: string, choices?: string[], threshold?: number}] | null
}
```

`ChangedFile` has `path`, optional `additions`, `deletions`, `binary`, `redacted`.
Repository root is defined in the type but not populated by `BuildState`.
State sources are the diff, four fixed governance files and optional task.
Diff is capped at 200,000 bytes; each context/task file at 12,000 bytes.
These are post-read truncation limits, not hard pre-read memory bounds.
Inline `--task` has no analogous explicit size limit. Redaction may alter task
or source bytes, including an entire one-line JSON string; truncation/redaction
must not be mistaken for assessment of the original full evidence.

The expected HTTP response is:

```text
{
  signals?: [{id: string, value: any JSON, confidence?: number,
              source: string, metadata?: object}],
  answers?: {question_id: {value: any JSON, confidence?: number, metadata?: object}}
}
```

Both collections are normalized into `Signal` values with source overwritten
to `typesafe-jev`. They are not checked for an exact answer-ID set, declared
question type, duplicates, range-valid probabilities or completeness.
Unknown fields are ignored by Go JSON unmarshalling. Empty valid JSON can
therefore yield no signals rather than a schema error. The label `typesafe-jev`
is assigned locally, not a provider attestation.

The CLI JSON output is:

```text
{
  schemaVersion: 1,
  result: {
    signals: Signal[] | null,
    findings: [{id: string, severity: "info" | "warning" | "review" | "error",
                title: string, description: string, signalIds: string[],
                files?: string[]}] | null,
    decision: "pass" | "warn" | "review_required" | "fail",
    diagnostics?: [{severity: string, code: string, message: string}]
  },
  dryRun?: {provider: string, questions: Question[], state: EvaluationState,
            dataCategories: DataCategory[]}
}
```

The dry-run placeholder is exactly
`{"signals":null,"findings":null,"decision":"pass"}`. It is not a model judgment
or an evaluated policy result. Normal output has no raw HTTP body, returned
model identity, usage, request digest, policy version, assessment lineage or
`systemone_execution` receipt.

## SystemOne wire compatibility and authentication

`internal/semantic/jev.go:29-113` POSTs the above request to the configured
endpoint using bearer authentication. Default timeout is 30 seconds; config
accepts 1-300. One application-level `client.Do` exists, with no explicit
retry loop. The default Go client still has normal transport/redirect behavior;
zero on-wire retries and no redirects are not established by this source.
Successful response reads are limited to 2 MiB without an explicit overflow
sentinel check. HTTP and transport errors are sanitized into diagnostic codes.

This wire shape is **not** the hosted `/v1/systemone` shape used by native JEV:
that path uses a string `state`, an object keyed by question IDs, `type: noul`
or `choice`, and answers containing `noul` or `choice` rather than `value`.
Pointing the CLI directly at that endpoint is not a verified integration.

The historical `mmmtap_phase0_v5/jev_bridge.py:13-50` demonstrates a distinct
translation layer: serialize state to JSON text; map boolean and score questions
to noul; map choices to criteria; convert noul to boolean at `>= 0.5`, retaining
scores. This was inspected, **not run or reused as a qualified adapter**.
It returns normalized answers and stores limited model/usage stats in memory,
not a durable raw-response receipt. It also labels raw noul as confidence,
which is not generally confidence in a boolean classification. Both translation
threshold and policy threshold must be recorded separately.

## Configuration and deterministic policy

Config is loaded from cwd's `.github/carl/config.yml`, otherwise `config.yaml`.
It is not selectable through `--policy-file`; the two inspected worktrees
currently have neither file. The parser supports a small YAML-like subset:

```yaml
semantic_evaluation:
  enabled: true
  provider: jev
  fail_mode: closed
  jev:
    api_key_env: TYPESAFE_API_KEY
    endpoint: https://example.invalid/adapter/evaluate
    model: OPERATOR_APPROVED_MODEL
    timeout_seconds: 30
```

This is a **nonfunctional configuration illustration**, not an installed
configuration or a verified provider/model choice. Defaults are disabled,
fail-open, key name `TYPESAFE_API_KEY`, 30 seconds, with no endpoint/model.
Neither credentials nor endpoint authentication were tested here.
Phase 2 config's `JEVKEY` and `jev-latest` are not automatically applied by
the cARL executable; actual cARL config must bind them explicitly.

Questions and policy are compiled in `questions.go` and `policy.go`, not
configured by these YAML fields or instruction-pack prose:

| Signal | Kind | Triggered cARL finding/decision |
|---|---|---|
| `security_sensitive` | boolean | warning / warn |
| `scope_expansion` | boolean | warning / warn |
| `architectural_change` | boolean | warning / warn |
| `authentication_or_authorisation_change` | boolean | review / review_required |
| `trust_boundary_change` | boolean | review / review_required |
| `security_control_reduction` | boolean | review / review_required |
| `breaking_change` | boolean | warning / warn |
| `new_external_dependency` | boolean | warning / warn |
| `human_review_warranted` | score, threshold 0.7 | review / review_required |

`signalTriggered` accepts boolean true, JSON numbers >= 0.7 for the last signal
or >= 1 for others, or the strings `true`, `yes`, `high`, `review`,
`review_required`. Unknown IDs do not create findings. Confidence is displayed,
not used in policy selection. The highest severity wins. Known policies have
no error-level entry, so model-derived signals currently reach at most
`review_required`; `fail` is also used for fail-closed provider unavailability.
Finding file lists contain **all** changed files, not independently localized
evidence. Findings/answer order is not canonical because answer-map iteration
is unordered; the maximum decision remains order-insensitive.

Exit 0 covers pass, dry-run, disabled evaluation and fail-open unavailability;
exit 2 covers evaluated non-pass decisions; exit 1 covers execution/config
errors or fail-closed unavailability. Inspect diagnostics and call receipts,
not exit code alone. These are CLI decisions, not proof of deployment gating.

## Reproducibility and remaining limits

The review path reads files/Git and has no conversation store or source-write
operation. Fresh processes can keep supplied assessment histories independent,
but context/config/branch metadata come from the current worktree, even with
pinned base/head. Host Git config, textconv, symlink resolution, concurrent
edits and redaction/truncation require explicit containment/binding in any
future adapter. Lexical task-file containment is not a symlink safety guarantee.

Existing `review_test.go`, `policy_test.go`, `config_test.go`, `jev_test.go` and
`redact_test.go` document mocked evaluators, local HTTP fixtures, policy mapping
and negative cases. They were inspected, not executed, and do not establish
hosted SystemOne compatibility or binary live qualification. Full paths,
source line references and evidence-level distinctions are in
`INTERFACE_EVIDENCE.json`.
