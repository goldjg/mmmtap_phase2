# Execution harness offline validation

## Published evidence

- `adapter_readiness_v1.json`: actual local versions, credential-presence checks
  and explicit unresolved capabilities; zero live-capable adapters.
- `execution_plan_v2.json`: current validated manifest, content identity
  `5163922f2c64af5c8034ec1840485f2573669a6801a6519a8fd128d1390c5544`.
- `execution_dry_run_v2/`: complete mocked run, immutable checkpoints,
  append-only ledger, first-run/resume summaries and `resume_audit.json`.
- `adjudication_mock_v1/`: 1,620 labelled mock blinded pairs; 1,215 final-arm
  pairs omitted because their required mechanism/parent was unsupported.
- `adjudication_mock_key_v1.json`: separate owner-only mapping; do not give
  reviewers this file before their independent sheets are sealed.

`execution_plan_v1.json` is a superseded, never-executed planning artifact.
The first full-corpus validation exposed that its summary counted unique byte
hashes as input identities. The actual job enumeration already included all
135 identities. A regression test now distinguishes identity count from unique
hash count; v2 is the current plan and the only plan used for execution validation.
The superseded plan is retained rather than silently overwritten and will fail
current software-hash validation.

## Actual results

`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -q` passed
**73 tests** (35 extractor tests and 38 harness tests). No live tests were run.

The frozen corpus is **135 case/variant inputs, 108 unique byte hashes**.
Byte-identical variants remain separate experimental inputs. Fifteen cases,
nine variants and three generators produce 405 independent B0 groups.

| Measurement | Actual result |
|---|---:|
| Planned/processed jobs | 6,885 |
| Generator jobs | 4,455 |
| Adversary jobs | 2,430 |
| `mock_ok` | 3,645 |
| `unsupported_contract` | 1,215 |
| `blocked_parent` | 2,025 |
| Live transport reservations/calls | 0 |
| Checkpoints reused on full resume | 6,885 |
| New checkpoints on full resume | 0 |
| Checkpoint files hash-verified unchanged on resume | 27,540 |
| New historical admissions | 0 |

The resume audit also checked that the ledger retained its exact original byte
prefix. Full blinded export verified result/artifact hashes, source identity and
parent lineage before producing packets. No independent research adjudication,
live smoke, live pilot, full live experiment or Stage B conclusion occurred.

The automated suite covers archive integrity, malformed/missing sources, exact
deduplication and provenance; deterministic planning, identical-byte variant
preservation, source/template tampering, retry identities, branch isolation,
both E3 orders, checkpoint parent hashes, incomplete/failed-attempt resume,
mock/live separation, parser failures, unsupported contracts, output bounds,
timeouts, live budgets, smoke approval gates, prompt/command boundaries,
blinding and independently sealed scoring. CLI/API responses in these tests
are fixtures; subprocess limit tests execute only trusted test-authored snippets.

## Remaining limitations

Copilot 1.0.95 and Codex 0.162.1 were found. Sol has local ChatGPT login state,
but remote authentication was not tested. Explicit isolated Copilot credentials
were absent. Gemini `gemini-3.8-flash` is a historical exact configuration ID,
not a verified currently served model. Native JEV credential presence does not
verify the endpoint or resolve `jev-latest`.

The actual cARL-JEV binary reports dev CLI / runtime 1.0.0. Every primary input
lacks its required authenticated Git evidence binding, and the binary's live
SystemOne provenance receipt remains unverified. No synthetic Git wrapper or
adversarial result was substituted.

Real event schemas, served-model metadata, CLI tool isolation, and client/provider
retry behaviour require authorised smoke execution and operator review. Missing
served-model metadata blocks live approval rather than being filled with the
requested model. Costs remain unpriced; available usage is preserved.

Protected document manifests and all 135 primary members were reverified.
All 1,355 files in the existing historical extraction checksum manifest passed.
Its unchanged manifest SHA-256 is
`59380a42e26662af368b5345fe936bd97c707e379a6abe6cfbced084b9e3fa51`.
No neighboring cARL source/docs, original protocol, eligibility decision,
archive or research result was edited.

See [HARNESS.md](HARNESS.md#separately-authorised-live-pilot-only) for the exact
separately authorised smoke, approval and 81-call-ceiling pilot procedure.
