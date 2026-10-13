# Integration options

## Path A: preserve the installed Git-review CLI

**Scope:** authentic Git review with optional assessment context, not arbitrary
primary-text claim verification. Keep the installed binary and its nine
questions/policy unchanged.

An eventual verified adapter would:

1. Accept a separately admitted, versioned Git-evidence binding with real
   repository/base/head objects, exact diff bytes/hash, a documented origin
   assurance level, active CLI config, governance context and binary hashes.
   A local Git object check must not be labelled signature or publisher
   verification. Reject unrelated or manufactured diffs.
2. Carry a frozen parent assessment as explicitly untrusted task text using an
   actually supported transport. `--task` avoids the current absolute-path
   failure but exposes text in argv and has size/redaction concerns. A
   repository-relative task file would require an approved isolated workspace
   containing genuine repository history and frozen governance, never a write
   to original evidence. Either approach requires offline verification.
3. Preserve the CLI's compiled questions and policy. Hash `questions.go`,
   `policy.go`, binary, active config and effective payload. Capture both model
   signals and deterministic findings, without turning every changed-file
   attachment into a source citation.
4. If using hosted SystemOne, implement and verify a separately versioned
   transport bridge for the real cARL HTTP contract. Preserve boolean/noul and
   score translation rules, underlying model selection and returned identity.
   Historical bridge code is reference material, not a ready adapter.
5. Capture a genuine out-of-band execution receipt from the bridge/transport:
   exact request/response hashes and protected raw artifacts, requested/
   returned model, endpoint identity, timing, usage, status, translation version
   and attempt ID. Bind this receipt to the particular CLI request and output.
   A configured ID or CLI's constant `typesafe-jev` label cannot attest a call.
6. Have the Phase 2 wrapper emit its own clearly named envelope containing
   raw CLI output plus the independently captured receipt. Do not claim
   `systemone_execution` came from the unmodified CLI. Explicitly wire Git
   bindings through the planner/dispatcher under a new software-bound version.
7. Fail the experimental attempt on disabled evaluation, diagnostics, missing/
   duplicate/type-invalid answers, payload mismatch, unknown identity, timeout,
   or incomplete receipt. Keep cARL's configured fail-open behavior intact as
   an observed CLI behavior, but never classify it as experimental success.
   Record every first attempt before a call and forbid silent retries.

No item above was implemented. An endpoint bridge must constrain credentials
to the approved destination, reject redirects/unapproved endpoints, enforce
request/response bounds and redact secrets without losing auditability.
The CLI default HTTP client and historical bridge are not demonstrated
zero-retry transports. Untrusted repository configuration, symlinks, Git
textconv/drivers, concurrent worktree changes and stale context must be
contained before credentials or live evaluation are introduced.

**Benefit:** preserves the actual cARL Git-review policy and provides a
defensible future Git-specific comparison.

**Limit:** does not make the 135 existing text cases Git evidence, and does
not provide custom claim-support questions. Even with a verified wrapper,
Path A's question is "what does this change imply under cARL policy, given
assessment context?", not "is each supplied assessment claim supported?"

## Path B: explicit assessment-challenge interface

**Recommendation for the primary corpus:** propose a new
`carl-assessment-challenge-v1` contract and a distinct command such as
`carl-jev challenge-assessment`. The command name and contract below are
**design proposals only**; the installed executable does not support them.
Explicit approval is required before implementation, and separate
authorization is required before any live use.

### Minimum architectural changes

Reuse the conceptual `semantic.Evaluator` seam, provider normalization, and
separation between model signals and cARL-owned policy. Do not reuse
`BuildState` by populating fake repository/diff fields. Introduce an explicit
assessment-evidence type, versioned request validator, controlled question
catalog, deterministic assessment-challenge policy, and structured output/
receipt. A versioned union or a separate method can preserve existing Git
review behavior; neither exists today.

`EvaluationState` currently has Git-shaped required fields. Calling its
provider directly with a task string may be technically possible in new Go
code, but that would not by itself provide an honest provenance contract,
claim-role validation or a meaningful assessment policy.

Keep the original Git `review` behavior and `authenticated_git_diff_v1`
unchanged. Do not replace `ApplyPolicy` with a renamed native-JEV pass-through,
or apply Git-change questions to text-only material. cARL must own an explicit,
reviewed assessment policy and record its version/hash.

### Proposed input contract (not an existing schema)

```text
{
  schema: "carl-assessment-challenge-request-v1",
  attempt: {
    id, job_id, branch_id, turn, parent_checkpoint_sha256
  },
  evidence: {
    kind: "supplied_frozen_source_v1",
    source: {encoding: "utf-8", text, sha256},
    provenance: {
      origin_kind: "archive_member" | "operator_supplied",
      archive_sha256?, member_path?, manifest_sha256?,
      assurance: "byte_integrity_verified",
      authenticated_git: false,
      deployment_state: "not_asserted"
    }
  },
  assessment: {
    canonical_json_sha256,
    value: {case_id, variant_id, claims, disposition, uncertainties, changes}
  },
  questions: [
    {id, kind: "boolean" | "score" | "choice", catalog_id,
     target_claim_id?, description, choices?, threshold?}
  ],
  policy_binding: {id, version, sha256},
  provider_binding: {requested_model, transport_version}
}
```

Compute hashes at intake, not just trust declarations. Bind the assessed source
to the frozen corpus and the assessment to the branch's immutable checkpoint.
Use the existing Phase 2 claim/evidence-quote schema for `assessment.value`.
Accept no unknown case/claim references. Question descriptions and options must
match an operator-approved catalog/hash rather than be directives supplied by
the source or generator. Credentials/endpoints belong to trusted execution
configuration, not this untrusted evidence envelope.

Initial question catalog should cover source support per claim, uncertainty,
and adoption of unsupported authority; avoid questions asserting a deployed
change or an authentic Git diff. Types must map explicitly to the hosted
SystemOne API: boolean to noul with a separately versioned conversion, score
to noul if that is the approved mapping, and choice to the provider's criteria.
Record raw probabilities; never interpret them as independent correctness.

The same underlying SystemOne route/model policy should be used for native and
cARL arms. Bind requested version and capture provider-returned version on
every call. Prior native evidence reported `jev-1.13.0` for `jev-latest`;
that is not evidence that the installed cARL CLI used it, or that an alias
will resolve identically in the future. Exact version selection must be
verified before use.

### Proposed output contract (not an existing result)

```text
{
  schema: "carl-assessment-challenge-result-v1",
  mechanism: "carl_jev_assessment_challenge_v1",
  purpose: "challenge_existing_assessment",
  status: "ok" | "unsupported_contract" | "invalid_input" | "failed",
  input_binding: {
    source_sha256, assessment_sha256, parent_checkpoint_sha256,
    questions_sha256, policy_sha256, request_sha256, attempt_id
  },
  provider_evaluation: {
    requested_model, reported_model, identity_evidence,
    raw_response_sha256, signals, usage?, latency?, http_status?
  },
  normalization: {version, thresholds, diagnostics},
  policy_arbitration: {
    id, version, sha256,
    disposition: "no_challenge" | "challenge_required" | "insufficient_evidence",
    challenges: [{claim_id?, question_ids, reason_code, evidence_refs}]
  },
  limitations,
  authority: "untrusted_challenge_not_generator_instruction"
}
```

Failure output must not carry a success-shaped `no_challenge` result. Preserve
raw responses in an access-controlled attempt artifact, separate from parser
outcome. Policy reasons must be deterministic and source/claim-addressable;
do not fabricate a model's rationale from a scalar probability. The generator
then retains/revises/withdraws/adds findings using its own source-grounded
reconsideration contract, not by obeying a purported authority.

Exact thresholds, handling of ambiguity/missing evidence, and question-count/
state-size limits are **open design decisions requiring approval**. They must
be fixed before experimental execution, not tuned to individual cases.

### Meaningful distinction from native JEV

Native JEV supplies typed source/claim judgments directly. The proposed cARL
mode would apply an approved assessment question catalog, validated normalized
signals and deterministic cARL arbitration into a claim-addressed challenge
set. Both retain the same underlying SystemOne identity and preserve raw
judgments separately from policy actions.

For comparability, predeclare which questions overlap with native JEV and which
are cARL-specific. Additional questions, normalization thresholds and policy
are mechanism effects, not independent-model effects. If the new mode merely
forwards the native answer unchanged, it is not a distinct cARL policy
mechanism and should not be presented as E2.

### Security and experimental acceptance criteria

| Boundary | Required property before approval/live qualification |
|---|---|
| Input trust | Source, comments, prompts, assessment and provider text remain evidence; none may select commands, paths, endpoint, policy or credentials |
| Origin | Archive/input/assessment hashes validated; no Git-authenticity/deployment assertions for supplied text |
| Policy control | Operator-owned catalog and policy pinned independently of input; thresholds frozen before experiment |
| Confidentiality | No executing source; explicit data-release approval; protected raw artifacts; bounded payload and reviewed handling of redaction |
| Completeness | Reject or mark unsupported oversized/unrepresentable evidence; no silent redaction/truncation presented as full-source evaluation |
| Transport | Approved endpoint only; authenticated TLS; no redirects or hidden retries; bounded reads/timeouts; exact answer IDs/types and finite ranges |
| Identity | Requested, reported and independently confirmed identity distinguished; model/usage receipts bound to actual request |
| Histories | Fresh independent requests; branch-specific parent/checkpoint; unique immutable attempts; no cross-arm response reuse |
| Errors | Missing/partial/malformed responses, timeout, nonzero exits and receipt failures preserved, never replaced with mock success |
| Interpretation | Model judgments, deterministic arbitration and independently adjudicated correctness exported separately |

Expected future tests include schema rejection, hash mismatch, claim/question
binding, source-preserving transforms, policy determinism, mock/live separation,
strict response parsing, receipt tampering, timeout/redirect/retry accounting,
both E3 orders, lineage and no-overwrite behavior. These are requirements for
future work, not tests claimed to have passed here.

## Approval and versioning

Path B needs a cARL owner-approved interface/policy change and a Phase 2 protocol/
adapter amendment. An implementation could live in an approved cARL branch or
separately named cARL-owned interface; a standalone native wrapper must not be
mislabelled the existing integration. Preserve the installed binary and prior
results. Freeze new code/config/prompt hashes, qualification evidence and job
manifest versions. Require separately authorised smoke tests before any pilot
approval. Existing qualification attempts must not be retried in place.
