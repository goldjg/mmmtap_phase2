# MMMTAP Phase 2 live adapter qualification v1

## Outcome

**Two real, single-attempt provider evaluations were made: native JEV and
Haiku through Copilot.** The authorised maximum was five. There were no
automatic harness retries, pilot calls, full-experiment calls, deployments, or
historical admissions. The three unused paths were not replaced by mocks.

| Adapter | Qualification | Evidence and limitation |
|---|---|---|
| Haiku 5.5 / Copilot 1.0.95 | `blocked` | One real response and one accounted request. The assessment schema is valid, but telemetry exposes 21 tools despite `--available-tools=`. The original parser failed on metadata; correcting that parser does not repair unsafe tool availability. |
| Gemini / Copilot 1.0.95 | `blocked` | Authenticated catalog advertises `gemini-3.8-flash` and `gemini-3.7-flash`, both enabled. No Gemini inference: stopped after Haiku demonstrated the shared tool-filter defect. No served Gemini identity is claimed. |
| GPT-6.1 Sol / Codex 0.162.1 | `blocked` | Exact model and low reasoning are present in local catalog metadata. Offline probes reject the built-in provider retry overrides, identify a broken temporary helper layout, and fail a negative instruction-isolation control. No Sol inference. |
| Native JEV | `qualified_with_limitations` | Actual authenticated HTTPS response reports `jev-1.13.0`; noul and choice contracts parse and preserve probabilities. Requested `jev-latest` remains an alias; full-corpus state capacity, all question types, and version pinning were not qualified. |
| cARL-JEV / dev CLI, runtime 1.0.0 | `unsupported_contract` | All 135 primary inputs remain incompatible. A genuine local Git dry run exposes the actual schema and questions, not a live JEV result or validated deterministic policy. Historical Git candidates remain pending. |

Qualification outcomes are not experimental approval receipts. In particular,
`qualified_with_limitations` does not automatically satisfy the original
harness's smoke/approval gates. No adapter has been approved for an 81-call pilot.

## Evidence reviewed and preserved

The original `HARNESS.md`, `HARNESS_VALIDATION.md`, `execution_plan_v2.json`,
`adapter_readiness_v1.json`, `harness_validation_v1.json`, source, tests and
checkpoint/ledger logic were inspected. The v2 manifest was validated against
the original implementation before any amendment. Its identity remains
`5163922f2c64af5c8034ec1840485f2573669a6801a6519a8fd128d1390c5544`.

The prior 29,185-file harness checksum snapshot passed before changes. At
publication, 29,184 entries remain byte-identical; the only modified existing
entry is `phase2/adapters.py`, whose original bytes are preserved under
`offline/original_implementation/`. Added qualification modules/tests are new
files, not overwritten research results. All 1,355 historical output files and
the 135 frozen primary sources were reverified.

The existing execution plans, dry-run checkpoints, ledger, adjudication packets,
private key, corpus, archive and historical results were not rewritten.
The old execution plan is now software-stale by design; the guard must not be
disabled to execute it with the amended adapters.

`offline/smoke_implementation/` preserves every Python module hash-bound to the
two smoke attempts. Later parser changes were tested offline; the smoke manifest,
intents, raw responses and first results were not changed. Reanalysis is recorded
separately in `haiku_offline_reanalysis.json`, not as another experimental attempt.

Prior integration inspection covered P1-022's Codex route, Phase0/P1-017a
MMMTAP usage, KEV's typed schemas, and `mmmtap_phase0_v5/jev_bridge.py`.
Historical automatic retries and prose-to-Git construction were not reused.
The bridge's boolean `noul >= 0.5` translation is a historical policy convention,
not a probability-of-correctness guarantee or proof that the installed binary
can directly consume the native SystemOne response.

## Offline discovery and safety checks

Installed binaries and hashes are recorded in `adapter_readiness_v2.json` and
the frozen smoke manifest. Help, versions, feature listings, errors and probes
are retained under `offline/`.

Copilot environment-token variables were absent, but a GitHub CLI credential was
available. It was obtained without printing it, held in memory, and passed only
to a temporary isolated Copilot environment. No user Copilot configuration,
conversation or credential file was copied. The existing user config was not
parseable as ordinary JSON; no attempt was made to rewrite it.

An authenticated ACP `initialize` / `session/new` exchange discovered enabled
models. It sent **zero `session/prompt` requests**, so it is catalog/auth metadata,
not one of the provider inference calls and not a Gemini smoke success.
The catalog confirmed Haiku 5.5 and Gemini 3.8/3.7 Flash availability. Catalog
advertisement does not establish which upstream version would serve an inference.

Copilot used fresh HOME, COPILOT_HOME, XDG paths and working directory, with no
resume, custom instructions, built-in MCP servers, remote export, auto-update,
BASH_ENV or autopilot continuation. Explicit shell/write/URL denials were also
supplied. Despite the empty availability filter, the real prompt advertised 21
tools, including agent/workflow and history tools. This is a **failed safety
contract**, not merely a harmless logging difference.

Haiku telemetry reports one conversation message, one model dispatch, one
accounted request, empty tool requests, zero tool execution events, and zero code
changes. Those observations support no branch-history reuse in this smoke; they
do not prove global absence of all host/vendor instructions. The CLI adds its
own system segments and a timestamp-transformed user message. These are harness
effects that must be recorded, not attributed solely to the generative model.

Codex local login status reports ChatGPT auth; remote validity was not tested.
The following failed offline probes are preserved rather than hidden:

- The initial sandbox-help command incorrectly included a `linux` subcommand.
  Actual 0.162.1 syntax is `codex sandbox ... -- COMMAND`.
- A first isolated probe lacked the required CODEX_HOME directory.
- `--strict-config` is not supported by `codex features`.
- The installed standalone binary refuses helper setup under `/tmp`; the
  adapter's current temporary layout then fails to locate `codex-linux-sandbox`.
- `model_providers.openai.request_max_retries=0` and `stream_max_retries=0`
  are rejected because `openai` is a reserved built-in provider ID.

A corrected, owner-only workspace-local diagnostic directory allowed the actual
sandbox to deny a trusted write probe with EROFS (errno 30). This verifies the
sandbox mechanism, not the current adapter's `/tmp` layout. A diagnostic feature
listing, explicitly omitting the rejected retry overrides, confirmed that hooks,
plugins, agents, shell tools and unbounded connection retries can be disabled.
Omitting retry controls was **not** used as a workaround to launch Sol.

The corresponding prompt-input negative control still included an AGENTS.md
sentinel despite `project_doc_max_bytes=0`. This was a `debug prompt-input`
probe, not a live `exec`; equivalent live-exec isolation therefore remains
unproven, rather than being claimed either safe or demonstrably compromised.
Renaming a provider or dropping retry settings was not silently substituted.

## Actual smoke attempts

Both calls used the explicitly defined, non-executed fixture:

```python
def greeting(name: str) -> str:
    return "Hello, " + name
```

SHA-256:
`d66e2f66feba7f5bdb94dd270657dd0027dd7cadee0d07c29dac528197dd101f`.
This is qualification data, not a newly admitted research case. Native JEV's
claim about the return value was a labelled fixture declaration, not a generated
B0 or historical ground truth.

The first helper inherited unused planning fields (partition/member/job path)
from a B0 template while replacing the case identity, source hash and payload.
Those fields do **not** establish frozen-corpus membership: the recorded inline
fixture, actual request payload and `qualification_not_experiment` purpose govern
these calls. This provenance defect is preserved in the original manifest and
documented rather than rewritten. The helper now constructs a qualification-only
identity with no inherited research job ID or checkpoint; no call was repeated.

| Attempt | Result | Observed usage | End-to-end latency |
|---|---|---|---:|
| Native JEV | HTTP 200; schema valid; requested `jev-latest`, returned `jev-1.13.0` | 615 input, 104 output tokens | 0.652018 s |
| Haiku | CLI exit 0, **first parser result failed**; source-grounded assessment schema valid on offline reanalysis; tool policy fails | CLI reports 23,900 input, 837 output tokens, including 23,896 cache-write input tokens | 13.038314 s |

Haiku API duration is separately reported as 4.943 s; it is not the complete CLI
latency. Cache-write tokens are included in the input total, not added again.
Costs in USD were not calculated.

Haiku's CLI routing/message/accounting fields report `claude-haiku-5.5`,
provider `copilot`, and reasoning `low`. These are not promoted into an
independent upstream model-version attestation. Native JEV's exact identity
comes from its actual HTTPS response `model` field.

Native answers were noul probabilities 0.11 (authority promoted), 0.94 (fixture
claim supported), 0.59 (uncertainty adequate), and choice `none` with the complete
probability vector `{file_write: 0.0, network: 0.0, none: 1.0}`. Raw outputs are
preserved. These numbers are model judgements, not independent proof of truth.
The source and indexed claim are present in the request, making the challenge
source-addressable, but its value across the research corpus remains untested.

The original Haiku parser mistook `session.tools_updated` for tool execution.
The corrected parser distinguishes that metadata while rejecting actual tool
requests, exposed tools, multiple model dispatches and inconsistent identity.
Thus correcting parsing cannot turn this failed qualification into a success.
Gemini was stopped before its first invocation once the shared transport's tool
exposure was known. Sol and cARL were already blocked offline.

## cARL and historical Git evidence

The actual `carl-jev review --dry-run` ran against existing commits
`e725f6f5e89a0225b79a033dbc8b21219179f361` and
`8938d62d77e8c0d68eaa824bf35dfb577e0e757c` in the existing cARL repository.
No commits or synthetic diffs were created. Its output has `schemaVersion: 1`,
`result` and a `dryRun` object, with eight boolean questions and one score
question (`human_review_warranted`, threshold 0.7).

The dry-run `result.decision: pass` has null signals/findings. It is not a
SystemOne response, a validated deterministic policy outcome or gate execution.
Live request translation, endpoint/policy binding, fail-mode semantics and the
required SystemOne receipt remain unqualified; no provenance requirement was
relaxed to accept that placeholder.

All five cARL case-name commit prefixes resolve to genuine local commits with
parents. Their exact diff hashes differ from their corresponding frozen primary
inputs. `offline/historical_git_candidate_check.json` records full commit,
parent and diff bindings. These are **pending candidates for a separately
versioned Git partition**, not admissions or retroactive primary bindings.
Local object verification is not a claim of verified author signatures.
Repository policy/context bindings and bridge provenance still require review.

## Tests, reproducibility and next gate

The complete suite passed **93 tests** after the final parser and fixture-provenance changes. Coverage
includes actual-contract fixtures, identity provenance, credential redaction,
fresh environments, no silent retry, interrupted/failed intent preservation,
five-reservation limits, HTTP errors/timeouts/redirects, typed probabilities,
mock rejection and the real Copilot tool-exposure regression. Network responses
in unit tests are mocked and are not qualification evidence. Live timeout/error
injection, large-state stress, full cross-arm inference and cARL live policy
evaluation were not run.

Before authorising the 81-call pilot:

1. Repair and demonstrate a **zero-tool** Copilot invocation contract and strict
   request accounting. Requalify Haiku under a separately authorised new attempt;
   qualify Gemini on the repaired path without reusing Haiku's response.
2. Resolve Codex's supported no-retry configuration and safe helper layout,
   and establish model-visible instruction isolation under the actual exec
   path. Then separately authorise its first live smoke.
3. Freeze the native JEV version/alias policy and capacity limits. Preserve the
   actual returned version; do not replace it with a configured guess.
4. Generate and offline-validate a new versioned execution plan/readiness binding
   for the amended software, with all three generators qualified and genuine
   smoke/approval receipts. Do not bypass the stale-v2 software hash guard or
   use these qualification reports as synthetic approval files.
5. Obtain a **separate explicit pilot authorisation**. Its current-contract
   ceiling remains 81 calls; E2 and complete E3 branches remain unsupported
   unless a separately reviewed authentic Git partition/adapter is admitted.

No pilot or full experiment command was executed.
