# Phase 2 execution harness v1

## Scope and evidence boundary

Run with Python 3.11+ and the standard library: `python -m phase2`.
`phase2/core.py` plans and validates; `adapters.py` owns transports and parsers;
`engine.py` owns checkpoints, branch histories and the ledger;
`adjudication.py` exports, freezes and scores independent reviews.
`config.v1.json` and `prompts.v1.json` pin the design and prompts.

The only admitted execution partition is the original P1-014 ZIP, SHA-256
`a3fe94069009f328b0a46bb52a7ff52d2c2bedfcd0eb3babe360eea1c884cc21`.
Every invocation using the corpus rechecks protected document manifests, archive
identity, member identities, lengths and hashes. Historical extraction outputs
remain evidence, not ground truth or additional admissions. No archived code
is imported, executed or restored to executable paths. No deployment is implemented.

### Experimental matrix

Each of 135 inputs has three independent generator baselines, for 405 B0 groups.
Every branch uses that group's immutable B0; C3 and E3 second follow-ups see only
their own preceding assessment and challenge. Each turn is a fresh process with
an explicitly reconstructed history, not a reused provider conversation.

| Arm | Generator calls per B0 group | SystemOne mechanism calls per group |
|---|---:|---|
| B0 | 1 | None |
| C1 self-review | 1 | None |
| C2 placebo/re-expression | 1 | None |
| C3 matched two-turn neutral control | 2 | None |
| E1 | 1 | Native JEV |
| E2 | 1 | cARL-JEV |
| E3_NC | 2 | Native JEV, then cARL-JEV |
| E3_CN | 2 | cARL-JEV, then native JEV |

Both E3 orders are separate histories under every B0, not a pooled treatment.
This adds both order conditions and C3 to the earlier planning estimate without
editing the frozen protocol. The default manifest contains **4,455 generator
jobs + 2,430 adversary jobs = 6,885 jobs**. Native JEV and cARL-JEV share
SystemOne; they are mechanisms, not two independent adversarial models.
The manifest is a deterministic topological schedule, not a randomised wall-clock
interleaving: do not claim that temporal/provider drift has been controlled.

All primary evidence uses `frozen_text_assessment_v1`. Native JEV constructs a
state/questions request from source, prior claims and uncertainty. cARL requires
`authenticated_git_diff_v1`, including a real repository, pinned commits,
verified diff and policy. Diff-looking text alone does not satisfy this contract.
The harness deliberately never generates Git commits from prose.

## Offline operation

All output arguments are direct children of the workspace. New manifests,
reports, exports and review seals refuse overwrite. Run directories resume
only when their manifest, mode, selection and persisted budget are unchanged.

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tests -v

# v1 readiness and v2 plan/run are implementation validation outputs.
# Use new names to create another independent set of outputs.
python -m phase2 readiness --out adapter_readiness_v3.json
python -m phase2 plan --readiness adapter_readiness_v3.json --out execution_plan_v3.json
python -m phase2 validate --manifest execution_plan_v3.json
python -m phase2 dry-run --manifest execution_plan_v3.json --out execution_dry_run_v3
# Exact same command resumes; no successful or failed checkpoint is overwritten.
python -m phase2 dry-run --manifest execution_plan_v3.json --out execution_dry_run_v3
```

Readiness probes local executable versions, credential presence and Codex login
status; they do not infer or validate remote authentication. Dry-run uses the
real planner, prompts, ledger and filesystem, but explicitly mocked responses
with empty findings and `insufficient_evidence`. Expected default statuses:
3,645 `mock_ok`, 1,215 `unsupported_contract`, 2,025 `blocked_parent`.
None of these are successful live integrations or adjudicated assessments.
Test-only mock cARL support exercises both E3 histories but is unavailable from
the production CLI and cannot be passed into live execution.

### Identity, provenance and interruption

The manifest embeds source/config/template/readiness hashes, Python/platform
details, package code hashes, requested model IDs, CLI versions, policy hashes,
case/variant identities, experimental attempts and explicit checkpoint parents.
Identical inputs, environment and code produce the same manifest and job IDs.
Any package/config/template change requires a new manifest; code drift cannot
silently resume an old experiment.

Checkpoint folders use SHA-256 job IDs, never source-authored path components.
`intent.json` is reserved before an inference call. `payload.json`, base64
`raw.json`, and `result.json` bind requests, raw outputs, structured parser
outcomes, source hashes, parent hashes, literal-quote audits and usage/latency.
Raw bytes are retained up to the declared cap; credential echoes are redacted
and marked, and truncation is a failure rather than a repaired response.
Missing usage/cost stays null, not zero; cost is currently `not_priced`.

The hash-chained append-only ledger is fsynced. A run holds a nonblocking flock.
Completed and failed results are reused, not replayed. An intent without a
result is `incomplete_attempt`; it permanently consumes any reserved live call
budget. A result written before its completion event is recovered without
inference. Invalid/truncated ledger records stop for manual inspection.
Hashes detect inconsistent mutation; they are not signatures or protection
against an operator rewriting every file.

Intentional retries are separate **whole experimental attempts**, retaining the
old B0 and results untouched:

```sh
python -m phase2 plan --readiness adapter_readiness_v3.json \
  --attempt 2 --retry-of execution_plan_v2.json \
  --retry-reason 'Separately approved new experimental attempt; explain cause' \
  --out execution_plan_attempt2.json
```

Run the retry into a new directory. There is no automatic per-job retry or
silent successful-attempt selection. Auth failures and invalid model schemas
are outcomes, not reasons for hidden retries.

## Adapter readiness and limitations

| Adapter | Implemented interface | Current limitation |
|---|---|---|
| Haiku | Copilot `--model claude-haiku-5.5`, isolated home, JSONL parser | Explicit Copilot auth environment absent during discovery; served model, event contract, tool isolation and internal retry behaviour unverified. |
| Gemini | Copilot `--model gemini-3.8-flash` | Exact ID found in prior local assessor config, not current authenticated model discovery. Availability and served version unverified. |
| Sol | Codex `gpt-6.1-sol`, reasoning `low`, read-only sandbox, isolated home | Local ChatGPT login and model cache entry found; live auth, event schema and retry/tool settings unverified. |
| Native JEV | `https://api.typesafe.ai/v1/systemone`, state/questions, strict noul/choice parsing | Credential presence is not authentication; resolved version, capacity and response contract need live smoke. Requested `jev-latest` is an alias, not a discovered version. |
| cARL-JEV | Actual `~/bin/carl-jev review` transport and deterministic-result parser | All primary inputs unsupported. Actual binary's SystemOne receipt schema is unverified; signals alone are insufficient provenance. |

The discovered versions are recorded in `adapter_readiness_v1.json`.
All five adapters remain **not live-capable** until their actual smoke evidence
passes validation and operator review. A parser fixture is not interface proof.
No fallback model, fabricated JEV response or pretend cARL policy decision is used.

Copilot receives only an explicit credential environment variable, not cached
user config. Codex receives only transient owner-only copied auth or the API-key
environment; user configuration/rules are not loaded. Source and prompts are
data, never shell strings. No shell is used to launch a model. Output pipes are
bounded, timed-out process groups are terminated, and responses are never
executed. Post-response tool/retry detection alone cannot prevent side effects:
the operator must first establish that the CLI flags actually disable tools and
hidden retries. If this cannot be established, do not approve that adapter.

Prior art inspected: P1-022 `a2_codex.py`, Phase0 `run_packets.py` and
`assessors.json`, P1-017a `p117.py`, `mmmtap_phase0_v5/jev_bridge.py`, KEV
`kev/api.py`, and the actual cARL-JEV CLI help. Their contract/immutability
patterns informed the implementation; their permissive parsing, dynamic imports,
automatic inference and prose-to-Git fixture construction were not reused.
The neighboring cARL checkout is not modified and does not establish the
separate historical binary's live contract.

## Separately authorised live pilot only

**The commands below were not run.** Approval to implement this harness is not
approval to execute them. Resolve current credential/model/isolation limitations
first, without exposing secrets. If discovery requires config or code changes,
produce and validate a new plan and offline run before requesting live approval.

A smoke consumes at most one harness transport attempt and reserves its adapter
directory even if it fails. It is not a research case. For each authorised adapter
(`haiku`, `gemini`, `sol`, `native_jev`), run individually:

```sh
python -m phase2 smoke --manifest execution_plan_v2.json \
  --out live_smoke_v1 --adapter haiku --authorize-live
```

Repeat only by substituting a separately authorised adapter, not by overwriting
an existing adapter folder. Failed smoke attempts require a new smoke directory.
Do not request cARL smoke for this corpus: it returns `unsupported_contract`.

Inspect each adapter's `intent.json`, `raw.json` and `result.json` locally. Verify
actual authentication, structured response, requested and observed model match,
tool isolation and absence of client-internal retries/model switching. Missing
served-model metadata blocks approval even if the assessment parses. Do not
fill it with the requested model or infer it from mock results.

Only after that review, record an evidence-specific attestation:

```sh
python -m phase2 approve-smoke --manifest execution_plan_v2.json \
  --smoke-dir live_smoke_v1 --adapter haiku \
  --confirm-isolation --confirm-no-hidden-retries \
  --review-note 'Describe the actual reviewed isolation, model and retry evidence'
```

Repeat for each successful authorised adapter. This attestation is explicitly
operator evidence, not automatic certification. It is bound to smoke raw/result,
binary and configuration hashes. Then obtain separate pilot authorisation:

```sh
python -m phase2 pilot --manifest execution_plan_v2.json \
  --out live_pilot_v1 --smoke-dir live_smoke_v1 \
  --max-live-calls 81 --authorize-live
```

The three baseline-variant pilot cases are `synthetic-benign-docs`,
`synthetic-token-logging`, and `synthetic-public-metadata` (provisional strata,
not adjudicated truth). Across all generators this selects 153 planned jobs;
81 supported transport calls are possible with current contracts, 27 cARL jobs
are unsupported and 45 descendants are blocked. The ceiling persists across
resume; it is not reset per invocation. A smaller approved ceiling is valid but
may stop midway through a group. Auth, parsing or adapter failures stop the
current live invocation. Repeating it skips all existing first attempts.

`run` exposes the full partition with the same explicit authorisation, smoke and
persisted-budget requirements; **do not use it for the current task**. Native JEV
and generator feasibility do not make E2 or either complete E3 condition feasible.
Supporting those requires an explicitly reviewed evidence-contract amendment.

## Blinded adjudication and scoring

```sh
python -m phase2 export --run-dir live_pilot_v1 \
  --out pilot_blinded_v1 --key-file pilot_private_key_v1.json
python -m phase2 freeze-adjudication --export-dir pilot_blinded_v1 \
  --reviews independently_completed_reviews.json --out pilot_reviews_sealed_v1
python -m phase2 score --export-dir pilot_blinded_v1 \
  --frozen-reviews pilot_reviews_sealed_v1 --key-file pilot_private_key_v1.json \
  --out pilot_scores_v1.json
```

Exports include successful B0/final pairs only, exact source text and neutral
claim IDs. Provider/arm/variant metadata and omissions/metrics remain in the
separate owner-only key. A hash commitment binds that key to the public export.
Content may itself reveal context, so perfect blinding is not claimed. Restrict
reviewer access to public packets until sheets are frozen; the filesystem cannot
establish that a person has never seen another file. Mock exports are labelled
`mock_not_research` and must never be used as real results.

Review JSON has schema `mmmtap-independent-adjudication-v1`,
`export_manifest_sha256` (SHA-256 of public `manifest.json` bytes),
`reviewer_label`, `independently_source_reviewed: true`,
`reviewed_while_blinded: true`, and a `packets` object keyed by every blind ID.
Each packet supplies unique independent `reference_finding_ids`, and `baseline`
and `final` objects with:

```json
{
  "claim_verdicts": {"claim_0000": "supported"},
  "supported_reference_ids": ["independent_reference_1"],
  "authority_adopted_claim_ids": [],
  "evidence_quality": 0.8,
  "uncertainty_calibration": null
}
```

Supply exactly one verdict per observed claim: `supported`, `partial`,
`unsupported`, or `unverifiable`. Independent reference IDs define the recall
denominator; they must come from independent source review, never old model
outputs. Quality/calibration are independent 0..1 rubric ratings or null.
Keep the reference definitions, materiality rationale, reviewer model if any,
and exposure history with the independent review process; this CLI does not
generate ground truth, adjudicate reviewer disagreements, or call a reviewer.

Scores report supported precision (supported / non-unverifiable claims),
supported recall, partial/unsupported/unverifiable counts, introduced unsupported
claims, lost correct reference findings, adopted authority assertions,
quality/calibration and confidence Brier scores separately from disposition
changes. Partial claims are not counted as fully supported. Source quote matches
are observations, not correctness. Complete execution observations include each
selected job's status, schema validity, latency and available usage; unavailable
cost is null, and adversarial/extra-turn costs must not be omitted in comparisons.
No single disposition flip, mock result or model agreement establishes improvement,
compromise, gate bypass or any Stage B conclusion.
