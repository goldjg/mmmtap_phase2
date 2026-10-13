# Phase 2 compatibility

## Classification boundaries

`supported_native` means a capability is present in the installed CLI and
supported by source/offline evidence; it does **not** mean live-qualified.
`supported_with_verified_adapter` requires an actually verified adapter for
the complete stated contract, not just a plausible wrapper.
`requires_explicit_extension` denotes new, separately approved behavior.
`unsupported_contract` denotes a mismatch with the current mode and evidence.

No current end-to-end Phase 2 cARL path earns
`supported_with_verified_adapter`. In particular, an inspected historical
bridge is not a verified current adapter.

## Mode-by-mode assessment

| Mode / scope | Inputs and evidence | Source plus model claims? | Questions and output | Classification |
|---|---|---|---|---|
| Existing Git review, with real repo and refs | Git diff, changed-file metadata, current governance/config; optional task text | Diff plus assessment-as-task text; no typed claim role | Fixed eight booleans + one score; signals and compiled policy findings/decision | `supported_native` for Git semantic-review interface only; live transport unqualified |
| Existing Git dry-run | Same local inputs; no credential needed | Same representation, no evaluation | Full state/default questions plus placeholder result | `supported_native` offline payload inspection, not an adversarial result |
| `--task` / relative `--task-file` transport | String or file read as text; Git repo still mandatory | Bytes for both can be carried in an opaque task string | Caller JSON/questions are not parsed; defaults unchanged | `supported_native` transport; `requires_explicit_extension` for typed assessment challenge |
| stdin / arbitrary absolute source path / custom-question flag | No implemented channel; absolute task paths rejected | No | No assessment output | `unsupported_contract` |
| Primary frozen-text partition through Git review | 135 archive-backed texts, without matching authenticated Git bindings | Archive text cannot become the reviewed Git diff by renaming/wrapping it | Git questions would be mis-scoped or based on unrelated evidence | `unsupported_contract` for all 135 |
| Internal Go evaluator seam used directly | `EvaluationState`, `[]Question`; HTTP endpoint/key | Task/context strings can carry both; current types remain Git-shaped | Generic boolean/choice/score representations, normalized signals | `requires_explicit_extension` to expose a legitimate non-Git assessment interface; not an installed command |
| Historical cARL-to-hosted bridge | cARL HTTP request; mapped noul/choice response | Carries whatever state caller constructs | Model-only translation; cARL policy stays in the CLI | `requires_explicit_extension` for current experimental provenance/validation; old code is not approved for reuse |
| `harness`, `explain`, `trace`, pack diagnostics | Agent loaders or pack selection/composition | Not an assessment evidence channel | Loader status or deterministic pack diagnostics, no SystemOne call | `unsupported_contract` as an adversarial evaluator |
| Proposed versioned assessment-challenge mode | Frozen supplied source, parent assessment, typed questions, approved policy | Explicit typed roles and byte/hash binding | SystemOne judgment separated from assessment-policy arbitration | `requires_explicit_extension`; not implemented or authorised |

For the actual nine question IDs, signal rules, wire shapes and source
citations, see `CLI_CAPABILITIES.md` and `INTERFACE_EVIDENCE.json`.

## The frozen corpus

Reverified the existing archive and every manifest member without writing them:

- 135 case/variant identities, 108 distinct byte hashes.
- Archive SHA-256:
  `a3fe94069009f328b0a46bb52a7ff52d2c2bedfcd0eb3babe360eea1c884cc21`.
- All jobs in the existing 6,885-job plan use `frozen_text_assessment_v1`.
- No primary input was given a new Git binding or a new eligibility decision.
- Historical Git candidates remain pending, separately from primary inputs.

The earlier five locally resolved Git candidates and their mismatching primary
diff hashes remain documented in
`../adapter_qualification_v1/offline/historical_git_candidate_check.json`.
This investigation reused one existing commit pair for read-only payload
inspection, not admission or retrospective authenticity certification.
Archive integrity authenticates correspondence to the frozen inventory;
it does not establish repository history, publisher identity or deployment state.

## Specific existing Phase 2 adapter gaps

These are findings, not changes. All source files remain untouched.

| Gap | Exact evidence | Consequence |
|---|---|---|
| Contract gate | `phase2/adapters.py:442-443,466-470`; `phase2/core.py:127-130` | Primary frozen-text jobs remain unsupported by design |
| Evidence binding never passed by live dispatcher | `phase2/engine.py:175-184` calls `invoke(...)` without `evidence` | Merely adding a Git contract to a future plan would still return `unsupported_contract`; explicit manifest binding/wiring is required |
| Task-file location mismatch | `phase2/adapters.py:492-498` writes an absolute temporary path; cARL `state.go:232-239`; actual negative probe | Even a direct call with genuine Git binding would fail before evaluation |
| Required receipt absent from CLI output | `phase2/adapters.py:459-464`; cARL `policy.go:41-46`, `output.go:20-30`, `jev.go:46-54` | Existing CLI cannot emit the required `systemone_execution`; no configured ID or signal label may substitute |
| Config/policy ambiguity | Phase 2 binds caller `policy_path`; CLI always loads `.github/carl/config.yml`/`.yaml` and compiled `policy.go` | A hash of an arbitrary policy path does not bind active CLI config, governance context or deterministic policy |
| Hosted wire mismatch | cARL `jev.go:40-54`; native `phase2/core.py:284-297`, `phase2/adapters.py:352-377` | Native noul/choice responses do not directly satisfy cARL's `value` response contract |
| Payloads/questions differ | Phase 2 creates indexed claim-support/uncertainty/authority questions; cARL `review.go:64` uses `DefaultQuestions()` | Sending the native request as task JSON cannot turn it into a claim-level cARL evaluation |

Do not repair these by removing evidence checks, accepting an absent receipt,
manufacturing diffs or treating a disabled/fail-open `pass` as a successful
evaluation. A verified Path A adapter must record these interface differences
and supply missing provenance independently, not fabricate it.

## Experimental consequences

The existing matrix is unchanged: 4,455 generator jobs, 1,215 native-JEV jobs
and 1,215 cARL-JEV jobs. The cARL jobs remain `unsupported_contract`; 2,025
descendants are structurally blocked. E2 and complete E3 comparisons therefore
remain unavailable under the current primary contract. The prior generator
qualification blockers also remain unchanged by this investigation.

Claims stored in `--task` may affect a genuine Git-review judgment. Such a
future comparison could honestly measure **assessment-conditioned Git policy
feedback**, provided the complete adapter is verified and the protocol names
that narrower target. It cannot be labelled typed verification of each
generative claim without an explicit interface/protocol amendment.

For primary-text assessment challenge, an approved Path B would be a new
versioned mechanism, not a retroactive reinterpretation of E2 results or an
automatic unlocking of the current plan. Native JEV and cARL-JEV still share
SystemOne. The experimental distinction must be cARL's explicit question
selection/normalization/deterministic assessment policy, not a claimed
independent adversarial model.

## Read-only and independent-history conditions

Existing review does not intentionally modify source and does not retain a
conversation. That is useful, but not sufficient experimental isolation.
Each attempt must bind exact source, reviewed diff, post-redaction/truncation
payload, current governance/config, prior assessment, questions and binary/
policy versions. Separate processes and immutable attempt directories must
carry only the corresponding branch's parent; identical E1/E3 inputs still
require distinct evaluations rather than cached answer reuse.

Pinned commits alone do not freeze worktree governance or branch metadata.
Any transformed or omitted input must be reported, not silently treated as the
same assessment of the frozen bytes. Neither policy changes nor model
probabilities are independently adjudicated correctness.
