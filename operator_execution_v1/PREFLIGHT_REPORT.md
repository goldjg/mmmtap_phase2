# Offline transport readiness

**No live model, SystemOne, smoke, pilot or full-experiment inference was
initiated.** Readiness means locally verified configuration and offline
contracts, not successful remote authentication, model availability, strict
qualification or sufficient account allowance.

## Selected software

The release is `mmmtap-operator-execution-v1`, layered on the unchanged final
v5 implementation. All executable additions and new tests are under this
package; no original source, corpus, protocol, scoring or sealed evidence was
edited. The workspace is not managed as a standalone Git checkout, so a Git
HEAD is not used as its software identity.

| Binding | SHA-256 |
|---|---|
| Operator software manifest, canonical identity | `ad5a3ec52cb9e8c45e44559602db89a316ec0c1ee9320ce5b64a8215d179bc56` |
| Combined operator + v5 implementation | `6f6243a7a0712ab0d15b0f045c0a9fa741417366c35810236cc07340b294b548` |
| Original v5 implementation | `c1d1c4d09715893e3c3ccd9deee77b787b189b3c511018f017842ee5ecb20ac3` |
| Frozen instruments | `be99adbb65cf5dfb2cb9aa2accebf683306ff565ecf81a515676111856fdd06a` |
| Original v5 plan, semantic identity | `844703bcc5569894d140f0bf4a1e34d1db7a281b82d4e751cab39b6e77f013cf` |
| Path B executable | `b51cb4c86a1e5b54b5bb496e67890ee8efd18f58603616f4eb28da144d7a275d` |

`SOFTWARE.json` enumerates the operator sources and binds Python 3.11.2,
Linux `6.12.109+rpt-rpi-v8` / aarch64, bubblewrap and libseccomp API 6.
`evidence/RELEASE_IDENTITIES.json` includes per-adapter configuration hashes.
The original v5 source closure, build receipt and complete Codex helper tree
are validated by the unchanged v5 verifier. Updating a pinned binary, kernel
binding, source or instrument requires a new reviewed release, not resuming
an old attempt with a new identity.

## Observed local readiness

| Adapter | Exact request / CLI | Credential observation | Research-controlled readiness |
|---|---|---|---|
| Haiku | `claude-haiku-5.5`; Copilot 1.0.95 | `COPILOT_GITHUB_TOKEN` absent | Blocked pending explicit scoped credential; loopback transport supported |
| Gemini | `gemini-3.8-flash`; Copilot 1.0.95 | Same explicit variable absent | Same credential block; no model substitution |
| Sol | `gpt-6.1-sol`, low reasoning; Codex 0.162.1 | Owner-only ChatGPT OAuth file present and structurally supported | Offline configured; remote validity/refresh and served-model identity unverified |
| Native JEV | `jev-latest`; unchanged native HTTPS adapter | `JEVKEY` present | Frozen contract supported; requires actual successful nonempty parent |
| Path B | `jev-latest`; source-bound v5 assessment-challenge binary | `JEVKEY` present | Frozen contract and offline prepare/evaluate/replay supported; same parent requirement |

Native JEV and Path B use `https://api.typesafe.ai/v1/systemone`. They receive
the source bytes, source hash and actual assessment claims, with the frozen
`uncertainty_adequate`, `authority_promoted` and per-claim typed questions.
They are not generic confidence probes. Both mechanisms are individually
recorded and billed; matching requests do not imply matching responses.

Pinned help/version commands ran in namespaces without external networking.
The configured argument lists and raw help/version output are retained in
`evidence/PREFLIGHT_PREPARATION.json` and `evidence/PREFLIGHT_FINAL_PRESEAL.json`.
No token values, authentication requests,
model-list calls or account-balance queries were used.

**Strict mode remains blocked for Haiku, Gemini and Sol.** Neither CLI
loopback success nor credential presence overrides the v5 I1/R2 findings.
Native/Path B therefore have no qualified strict-profile generator parent.

## Infrastructure and storage

Measured containment controls pass on Gaia: host repositories/auth are hidden,
approved read-only input is visible, writes fail with EROFS, process creation
fails with EPERM under the guard, runtime threads still work, and offline
external networking is disabled. Live networking is deliberately host-shared,
not provider-only. See `EXECUTION_PROFILES.md` for preventive, detective and
unenforced controls.

Initial preparation observed **1,449,791,488 free bytes**, below the full-stage
floor. A later explicit refresh observed **7,680,331,776 free bytes**, which
meets the **4 GiB full-stage floor** but remains below the 8 GiB recommendation.
Both observations are retained; capacity changed during preparation and is
not reserved by this package. The final pre-seal report has no infrastructure
blockers. Choose sufficiently sized persistent storage before smoke if
necessary, using one consistent `--runs-root` for all stages.
Do not delete frozen evidence. The CLI rejects known temporary/runtime output
roots; an arbitrary external path still requires the operator to verify its
persistence, privacy and available capacity.

The preparation reports deliberately say
`development_unsealed_not_live_permission`: they preceded the final package
seal. The operator-facing preflight rechecks the completed seal and current
environment and emits a new numbered report outside this package.

## Identity of each separately gated stage

| Manifest | Semantic SHA-256 |
|---|---|
| Smoke | `c98e590de791d9ca0ef191da51a0e9c18c201639ec49983d447fade88780c2b8` |
| Pilot | `3062def66204e79ec8bcc3b7565f3de681b5dcb411bee06a6817fb04152ddfc1` |
| Full research-controlled | `8fdad95530daa987f0d4e3bda035caa7605375f44f3b1810935a0ea122dc0174` |
| Full strict, blocked | `0ae0be13c16dd4a0ff753aba7d1f545892b79b644621971ed48787651c71d4be` |

These are canonical manifest identities, not hashes of JSON file whitespace.
`SHA256SUMS.txt` separately binds the exact file bytes.

## Offline operator command

```sh
cd ~/git/mmmtap_phase2
export PYTHONDONTWRITEBYTECODE=1
python -m operator_execution_v1 verify
python -m operator_execution_v1 preflight --stage smoke
```

Reports go to `operator_runs_v1/preflight/report-NNNNNN.json`, with the exact
path printed. Missing credentials are reported per adapter; infrastructure
blocks return exit 2. A zero preflight exit does not mean every credential is
present. Resolve the relevant adapter blockers before deliberately running
smoke: an unavailable first attempt is immutable, not retried after login.

The final preservation check verified **40,538 pre-existing entries**, the
**4,699-file v5 seal**, and **36 source-bound v5 command records** without
change (`evidence/PRESERVATION_FINAL.json`). Resolved forensic findings were
not reopened; remaining strict limitations were preserved explicitly.
