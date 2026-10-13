# Independent audit of the frozen experimental plan

The immutable `execution_plan_v2.json` was validated against its original
software before changes. A separate structural auditor subsequently recomputed
manifest/job identities, source bindings, parent lineage, branch shapes,
challenge consumers and dependency feasibility without trusting the prior
implementation summary or changing the plan.

Verified: **135 input identities; 108 distinct content hashes; 15 cases;
nine variants; three generators; 405 B0 groups; 6,885 total jobs**.
Content-identical variants are retained, not deduplicated out of the experiment.
There are 4,455 generator calls and 2,430 planned adversarial evaluations
(1,215 native JEV and 1,215 cARL-JEV), not 6,885 generative-model calls.

| Arm | Generator jobs | Native JEV jobs | cARL jobs | Contract-executable jobs* | Unsupported cARL jobs | Blocked descendants |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 405 | 0 | 0 | 405 | 0 | 0 |
| C1 | 405 | 0 | 0 | 405 | 0 | 0 |
| C2 | 405 | 0 | 0 | 405 | 0 | 0 |
| C3 | 810 | 0 | 0 | 810 | 0 | 0 |
| E1 | 405 | 405 | 0 | 810 | 0 | 0 |
| E2 | 405 | 0 | 405 | 0 | 405 | 405 |
| E3_NC | 810 | 405 | 405 | 810 | 405 | 405 |
| E3_CN | 810 | 405 | 405 | 0 | 405 | 1,215 |
| Total | 4,455 | 1,215 | 1,215 | 3,645 | 1,215 | 2,025 |

\* Conditional on qualified generators/native JEV. **No complete comparison is
currently executable:** Haiku, Gemini and Sol are blocked by qualification.
The CSV has 24 per-arm/per-generator rows and distinguishes structural contract
feasibility from current readiness. No research jobs ran during qualification.

## Isolation and independence

Every first follow-up references the same B0 within its own
case/variant/generator/repetition group. C3 and both E3 second turns reference
only their own first follow-up. Assessment and challenge parents cannot cross
groups or unrelated arms.

Each E3 group has both orders: native-then-cARL and cARL-then-native, with
independent checkpoint identities and histories. C3 supplies two neutral
generator follow-ups, matching the E3 generator turn count. It does not pretend
to incur the specialist's cost.

Each planned adversarial output has exactly one generator consumer. E1 and
E3_NC native requests can contain identical B0 evidence, but they remain distinct
jobs; the harness does not cache/reuse one branch's adversarial result in the
other. Identical probabilities from deterministic SystemOne would not establish
independent model evidence. Native JEV and cARL-JEV share an underlying mechanism,
not two independent adversarial models.

The deterministic wall-clock schedule is not randomised across arms/providers.
Running both E3 order conditions is not evidence that time, service drift or
session-system prompts have been controlled.

## First attempts and failure accounting

Intents precede invocation; checkpoint writes are exclusive, and ledger records
are append-only and hash-linked. Malformed or failed results are not repaired
and retried. An interrupted intent remains incomplete; a new intentional
experimental retry requires another recorded attempt.

The two qualification first attempts are likewise immutable. The failed Haiku
result remains failed. Offline decoding established a valid assessment but an
unsafe tool contract; no second model invocation or substituted result occurred.
The corrected parser rejects observed exposed tools and additional dispatches
rather than counting metadata as tool execution.

Native HTTP 429, timeout and redirect behaviour is covered by transport mocks
with one attempted request and no retry. This is not a claim that those failure
conditions were injected into the live provider. Codex's bounded/internal retry
controls remain an unresolved **blocking** issue, not an observed no-retry success.

## Inference-interface confounders

Haiku's actual CLI telemetry includes 21 tool schemas, vendor/host instruction
segments, timestamp transformation, one input conversation message and low
reasoning routing metadata. The empty tool filter did not enforce the intended
contract. Gemini's shared path was therefore stopped rather than treated as
an independent successful integration.

Codex's isolated diagnostic metadata still loaded an AGENTS.md sentinel.
That debug-path result does not prove live-exec contamination, but it does not
validate the required absence either. Exact served Sol identity and live auth
remain unknown. Provider defaults, prompt compilation, tool schemas, cache
accounting and version reporting must be separated from model effects.

No disposition change, high noul probability, CLI exit code, dry-run `pass`,
or mocked output is used as proof of source correctness or operational gate
semantics. No Stage B conclusion or primary corpus admission changed.
