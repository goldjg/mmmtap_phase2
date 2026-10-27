# Q1 observed live exploratory engineering results — 2026-10-27

**Q1 LOWER-ASSURANCE LIVE ENGINEERING QUALIFICATION COMPLETED — EVIDENCE SEALED**

This report describes the authorized real-provider run, separately from historical pilot evidence and synthetic qualification. The unchanged candidate uses nine matched case/generator units, eight arms, one engineering repetition, 99 generator and 54 specialist positions, and 198 dependency edges. P1–P7 remain the provisional settings recorded at `f1a799823d021bfc35662dfa5f65901ba9eb2b04`. No frozen source, prompt, policy, threshold, validator or historical receipt was changed.

Local execution: **2026-10-27T19:41:58.648719+00:00 to 2026-10-27T21:00:34.715719+00:00**, first CLI process start through last terminal outcome. These are local custody timestamps, not independently attested remote execution times.

## Actual accounting

| Position role | Scheduled | Completed valid | Invalid | Unavailable | Blocked | Interrupted |
|---|---:|---:|---:|---:|---:|---:|
| Generator | 99 | 87 | 1 | 2 | 9 | 0 |
| Specialist | 54 | 46 | 0 | 6 | 2 | 0 |
| **Total** | **153** | **133** | **1** | **8** | **11** | **0** |

There were **142 durable reservations**, **90 generator CLI launches** (Gemini 32, Haiku 33, Sol 25), and **46 SystemOne client POSTs** (native 25, cARL 21). All remained below the authorized 153/99/54 maxima. There were **zero harness retries, fallback invocations or replacement attempts**. Each reservation preceded its unique invocation record; every POST position had one POST intent. Eleven blocked positions consumed no reservation. Six inadmissible specialist reservations consumed no POST. CLI-internal requests and remote replay remain independently unbounded.

## Observed movement and specialist outcomes

All **78 valid preceding-to-current disposition pairs** were unchanged. All **54 available B0-to-final branch comparisons** were unchanged; **nine final endpoints were missing**, not unchanged. Of 27 two-turn chains, **21 were fully observed**, six were incomplete, and none of the fully observed chains reversed after intermediate disposition movement. Stepwise records were checked independently of endpoints.

| Generator arm | Scheduled generator positions | Valid generator outputs | Known stepwise pairs | Disposition changes | Known final endpoints / 9 |
|---|---:|---:|---:|---:|---:|
| B0 | 9 | 9 | 0 | 0 | 9 |
| C1 | 9 | 9 | 9 | 0 | 9 |
| C2 | 9 | 9 | 9 | 0 | 9 |
| C3 | 18 | 16 | 16 | 0 | 8 |
| E1 | 9 | 9 | 9 | 0 | 9 |
| E2 | 9 | 6 | 6 | 0 | 6 |
| E3_NC | 18 | 16 | 16 | 0 | 7 |
| E3_CN | 18 | 13 | 13 | 0 | 6 |

By generator, the valid stepwise comparisons were **Gemini 27, Haiku 29 and Sol 22**, with zero disposition changes in each. Full arm-by-generator counts and disposition pairs are in the [sanitized data](observed-results.sanitized.json). Baselines were eight `insufficient_evidence` and one `fail`; these are observed model outputs, not correctness labels.

Disposition stability did not mean identical assessments: valid follow-ups contained **97 model-declared retained and 12 revised claim records**, with no declared additions or withdrawals. Exact field comparisons found claim-text edits in 11 records, limitations edits in eight, confidence edits in two, and quotation edits in one; these counts overlap. **Materiality and justification remain unadjudicated. RD03 remains unapproved.** Generated reasons are retained in private raw evidence and are not treated as internal cognition.

The **21 valid cARL observations** produced **four `challenge_required` and 17 `no_challenge` outcomes**, with four challenge entries. All 17 eligible generator continuations after `no_challenge` were attempted: 16 completed and one was unavailable. Native feedback has no threshold-mapped challenge flag, so its challenge frequency is not assigned a synthetic zero.

Native and cARL share **SystemOne**. Seven baseline native/cARL pairs had identical sealed request bytes and valid responses; six of those seven returned different probability vectors. Two pairs were unavailable for exact comparison because cARL input admission failed. These are repeated observations of a shared provider, not independent judges, calibrated correctness or a causal presentation effect. All typed probabilities and separate cARL derivations remain in private custody.

## Failures and protocol anomalies

- **Two Gemini CLI exits with code 1**, at `c02-gemini-r1-c3-g1` and `c02-gemini-r1-e2-g1`, captured zero stdout and stderr bytes. Their cause, remote completion and billing remain unknown. No replacement was made.
- **Six cARL inputs** were rejected as `carl_quotation_not_exact_source`, surfaced by the broker as `sealed_input_not_admissible`, before credential delivery or a POST. These occurred in Sol branches for the first two cases. Source-quote auditing accepts these generator assessments as contract-valid while recording non-exact quotations; specialist admission is stricter.
- **One Haiku final assessment**, `c03-haiku-r1-e3-cn-g2`, failed `assessment_top_level_shape`. It remains invalid; its disposition is unavailable.
- **Eleven descendants** were blocked under the frozen dependency policy. Invalid, unavailable and blocked observations were never converted to unchanged behavior or an implicit policy disposition.
- The inherited verifier summary still emits `real_provider_calls: 0` and `live_execution_authorized: false`; receipts also retain the latter field. Those stale summary defaults were preserved unchanged and are **not** used for live accounting. Actual execution is established by the sealed GO, `simulation_only=false`, CLI `fixture=false` records and durable HTTPS POST/response records. Versioned reporting needs to distinguish authorization, execution and serving attestation.

## Provider identity, usage and financial exposure

Copilot client events reported **`gemini-3.8-flash`** for 30 successfully parsed CLI streams and **`claude-haiku-5.5`** for 33. Sol requested **`gpt-6.1-sol`** on 25 launches; its observed serving model remains unavailable. All 46 SystemOne responses self-reported **`jev-1.13.0`** over the qualified TLS broker. These are client/provider reports, not independent serving attestation. CLI streams are not provider HTTP traces.

The retained CLI profile uses host networking without endpoint filtering and detective client restrictions/watchdogs rather than a universal preventive tool interlock. The selected CLI credential remains subject to the documented same-UID inspection limitation. The sealed Codex profile documents `unified_exec`, `realtime_conversation` and `worktrees` reporting true despite false overrides; no tool execution is inferred from those metadata flags. The separate SystemOne worker/broker boundaries were retained. Complete remote context isolation remains unverified.

| Route | Available usage records | Reported input tokens | Reported output tokens | Reported cached input tokens |
|---|---:|---:|---:|---:|
| Gemini / Copilot | 30 | 195565 | 6751 | 0 |
| Haiku / Copilot | 33 | 310242 | 33611 | 46784 |
| Sol / Codex | 25 | 309078 | 10765 | 188800 |
| Native / SystemOne | 25 | 18253 | 1870 | not reported |
| cARL / SystemOne | 21 | 15139 | 1518 | not reported |

Counters are client/provider reports with provider-specific accounting semantics. The two empty-stream CLI failures have no usage report; their usage or charge is not imputed as zero. **Actual monetary charges are unavailable.** The PI approved variable exposure without an additional campaign-specific monetary ceiling, relying on existing account usage limits and historically low JEV cost. None was represented as an independently verified monetary ceiling. Internal CLI requests, remote replay, timeout billing and actual charges remain uncertain.

## Evidence custody and exact bindings

Read-only reconstruction passed for **2,546 journal events and 153 receipts**, with every campaign file unchanged. Canonical authority/database inode checks and unique reservation/invocation/POST accounting passed. All **40,538 original custody entries** remain intact. Raw CLI streams, SystemOne entity bytes, typed probabilities, per-position timing and private deployment records remain outside this repository in canonical private custody. The private hash seal covers **39 artifacts**.

| Binding | SHA-256 or Git commit |
|---|---|
| Executed candidate code | `654f2b8147bca53f55a5ff0f659195a76f1b10f9` |
| Immutable manifest authorization digest | `8d86dae1261e609a49971d6682c9ed57427dd9b012aeaa4030071f6253064471` |
| Implementation / transport configuration | `8058767a05aeb757e51c662126a8ea77db7907cb79a4b03a95c0ed4cf8c3a4cf` |
| Approved launch authorization | `c3775dbdbce42999fa704ec82c3f622d13f14f0ab54e35b2b681932dc7e2a941` |
| Campaign SQLite database | `bc4ad349a9cf45e5ebb7ec9e3fae0ddc93b14d6166f8a0e993d8a6ab81e3e0ae` |
| Journal evidence tip | `57981e63b7c3be6aee7d3643a7f324fc62cead4087ff55921f239b1db16a8b9c` |
| Private evidence seal | `ae684d6fde3b69c9d0f6d249bc84ae0e1f9e8a3774daf60cbad49c4a805bbf31` |
| Source bundle | `ff76e1c1cf41a45e6d77136f2584f1a8d4765bbf9eb7a95c1525d0673f7171ed` |
| Governing policy | `adedb371a0661194cac7f666befa82a524080723cb8ffa4a7b50f9bb759b0f3e` |
| Challenge policy | `4291e804f6c81881ce188246c311590119a4e600d16f340e03e8b2e6910daea7` |
| Compiled cARL policy | `b54ad41b0c9bff40246621a03c7f27492c7270e6c5957de40cd55f5baa616f5e` |

The sanitized data supplies all three exact source-description digests and other packet bindings. No private responses, credential values, provider request identifiers, account identifiers or private network configuration are published.

## Practical changes supported by this run

1. Make exact-source quotation admission explicit across generator diagnostics and specialist preparation: six real cARL observations were censored by the current mismatch. Preserve this run unchanged.
2. Preserve and classify empty-stream CLI exits explicitly, including uncertain completion and billing; this run supplies two real examples without enough evidence to assign a provider cause.
3. Version the live summary counters and authorization/provenance fields so observed live execution cannot be misread as a synthetic run. Preserve existing receipts and seals.
4. Use the eight baseline evidence holds, zero observed disposition changes and retained claim edits to inform future source/policy and measurement design decisions. They do not establish a null effect, instrument validity or calibrated thresholds.

This is one lower-assurance exploratory engineering repetition. The three historical descriptions do not authenticate deployed state or satisfy the candidate policy’s missing E-DIFF/E-TEST evidence. The provisional policy grants no real release authority. Low Noul does not establish a factually correct challenge; caution does not establish security correctness. No significance, calibrated correctness, strict-isolation causal validity or independent native/cARL judging is claimed. Historical evidence and simulated qualification were not relabeled or pooled.
