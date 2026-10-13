# cARL-JEV assessment challenge v1

Path B is a separate **offline-only** interface. Existing Path A adapter code,
Git-review contracts, plans, frozen sources, previous reports and results stay
unchanged. It does not enable E2/E3 live jobs in the old manifest.

Implementation:

- `../cARL-semantic-eval/cmd/carl-assessment-challenge`: sibling executable;
- `../cARL-semantic-eval/internal/assessment`: validation, matched native
  request, frozen cARL policy, receipts and replay;
- `../cARL-semantic-eval/internal/pack/snapshot.go`: additive read-only access
  to the existing cARL discovery/profile/dependency/override/trace evaluator;
- `phase2/path_b.py`: frozen-corpus/checkpoint adapter using the existing
  native `challenge_request`, not a copied Python question catalog;
- `path_b_policy_v1`: explicitly labelled offline custom-pack/role fixtures.

The actual cARL custom-pack/role machinery is used, not mocked. Its output is
then consumed by a new narrowly typed assessment rule interpreter in cARL.
This new interpreter does not reinterpret ordinary instruction-pack prose or
alter the original Git policy.

## Generate a request without inference

```sh
PYTHONDONTWRITEBYTECODE=1 python -m phase2.path_b \
  --reference-plan execution_plan_v2.json \
  --checkpoints execution_dry_run_v2 \
  --job-id EXISTING_CARL_POSITION_ID \
  --attempt-id UNIQUE_OFFLINE_ATTEMPT_ID \
  --request-out NEW_REQUEST.json
```

The reference plan is checked for its content/corpus bindings, not approved for
execution against changed software. It supplies lineage labels only. The
adapter requires B0 parents for E2/E3_CN and the branch's own first follow-up
for E3_NC, verifies the original parent artifacts, and includes the raw parent
checkpoint. It reopens and authenticates the real archive through the existing
corpus verifier. Historical candidates are not accepted by this adapter.

Build the sibling binary using the instructions in
[`../cARL-semantic-eval/ASSESSMENT.md`](../cARL-semantic-eval/ASSESSMENT.md).
Then, using new output directories:

```sh
carl-assessment-challenge prepare \
  --request NEW_REQUEST.json --policy-root path_b_policy_v1 --out NEW_PREPARATION
carl-assessment-challenge evaluate-offline \
  --prepared NEW_PREPARATION/prepared.json --prepared-sha256 TRUSTED_PREPARATION_HASH \
  --response LABELLED_MOCK_RESPONSE.json --mode mock --out NEW_RESULT
carl-assessment-challenge replay \
  --receipt NEW_RESULT/receipt.json --receipt-sha256 TRUSTED_RECEIPT_HASH
```

Do not substitute a computed digest from an untrusted received file for an
independently retained trust anchor. `imported_unverified` is the other allowed
response mode; it never becomes a verified provider invocation. There is no
live mode, credential lookup or network evaluation route.

Receipts preserve raw request, native request, source/manifest/parent bindings,
policy definitions and resolved trace, raw response, implementation hashes,
parser outcome and deterministic arbitration. Policy replay reconstitutes the
frozen local policy without consulting the current policy directory.
Responses with missing/invalid answers are failed attempts, never neutral or
successful challenges. New output paths preserve prior attempts; callers
must also allocate distinct attempt IDs. Global ID uniqueness is an external
ledger responsibility before live integration.

## Comparability and qualification

The native request bytes, including model, state and typed noul questions, are
matched. No extra cARL prompt text/questions are injected. cARL's distinct
mechanism is the deterministic policy applied to its own independent
SystemOne evaluation. Future live branches must not share provider responses.

The existing `path_b_policy_v1` thresholds and roles are **offline fixtures**,
not a silently approved experimental policy. Freeze and explicitly approve the
real role/policy and thresholds before qualification. Local digest receipts
provide integrity/replay, not cryptographic provider authentication or evidence
of a real model call.

Outstanding gates: implement/review authenticated single-attempt live
transport and trustworthy request-bound receipts; verify actual model/version,
usage, endpoint, no redirects/retries, timeout and full-corpus capacity;
review release of source data; perform separately authorized live smokes;
qualify the generators; freeze a new plan and obtain separate pilot approval.
No historical admission, live qualification or pilot approval is implied.

## Completed offline validation

See [`path_b_validation_v1/VALIDATION_REPORT.md`](path_b_validation_v1/VALIDATION_REPORT.md).
The preserved sibling binary is
`path_b_validation_v1/bin/carl-assessment-challenge-v1`. Full suites passed:
232 Go top-level tests (297 including subtests) and 100 Python tests.
There are 137 successful preparation/mock-evaluation/replay sets: all 135
primary identities and one extra example for each E3 order. All native request
bytes matched. No generator or SystemOne was invoked.

Original corpus-level mocked assessments contain zero claims; unit fixtures
cover nonempty claims and policy thresholds. No model effectiveness or
experimental feasibility conclusion follows from these offline results.
`receipt_anchors.json` and `SHA256SUMS.txt` must be retained independently.

Repeat unit validation without invoking a provider:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
cd ../cARL-semantic-eval
GOPROXY=off GOSUMDB=off go test -count=1 ./...
GOPROXY=off GOSUMDB=off go vet ./...
```
