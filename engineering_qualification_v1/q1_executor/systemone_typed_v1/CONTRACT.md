# systemone-typed-challenge-v1

The strict executable schema/parser is [contract.py](contract.py). Its
`parse(request_raw, response_raw, source_raw, assessment, claim_ids, hashes, …)`
accepts original bytes with local custody bindings. It rejects duplicate JSON
keys, missing/extra questions or answers, missing/incorrect type discriminators,
non-numerical/nonfinite/out-of-range Nouls, altered question wording, altered
source/assessment and changed frozen claim order. JSON object order is
irrelevant: reordering named answer members is legal. Reordering the request
claims against the sealed claim-ID sequence is rejected.

The root observation has `schema`, `direct_systemone`, `reference_judgments`,
`derived_carl` and an untrusted `authority` notice. Direct observations carry:

| Field | Meaning/origin |
|---|---|
| Request/response/source/assessment/state SHA-256 | Local custody, not provider attestation |
| Catalog version/digest, exact question bindings/digest | Existing `mmmtap-matched-question-pack-v1`; exact instructions and indexed bindings |
| Ordered claim IDs; observation question ID/index/claim ID | Joined exclusively through the frozen request assessment |
| `observations[].noul_decimal` | **String containing the exact original JSON number token**, probability of yes; never a degree score or label |
| `observations[].scope` | `claim` for support; `assessment` for uncertainty/authority, with no claim ID/index |
| Returned model and response pointer | Entity self-report, not identity attestation |
| Usage and available response metadata | Provider entity counters and original local capture metadata/artifact references |
| Explicit unavailable fields/reasons | Provider attestation, rationales, selected quotes and missing accounting metadata |

Usage counts remain integers. Decimal tokens retain original precision,
trailing zeros and exponent notation; no float conversion, rounding or threshold
applies to direct observations. Exact response bodies remain SQLite BLOBs and
broker raw prefixes. The qualification-only `historical-side-effect-choice-v1`
extension preserves its actual Choice/confidence/probability-map tokens as
auxiliary source-scoped observations; it is not added to the matched Q1 catalog.

`reference_judgments` explicitly marks source entailment, independent
verification, impact inference, evidence-policy justification, labels, support
degree scores, provider rationales and provider-selected quotations unavailable,
with null values and exact reasons. Nothing in this contract fills that layer.

For native, `derived_carl` is null. For cARL it has a separate version and
`deterministic_captured_policy_replay_not_judge` origin: exact prepared/policy/
policy-file hashes, pack IDs/versions, implementation hash, all evaluated rule
IDs/predicates, matched flags and dependencies pointing to original response
fields. Signals use the same decimal tokens. Challenges and disposition replay
only the captured historical rules, retaining generator claim quote pointers
and assessment hashes. Both governing and release authority are false.
The captured historical result must agree with replay. No new threshold or
policy compilation is supplied, and no cARL executable is invoked.

The versioned manifest extension `specialist_observation` selects the new
route. The original `instrument_version` still pins the frozen v2 **generator**
assessment/lifecycle checks. New specialist requests explicitly carry
`instrument_contract=systemone-typed-challenge-v1`; unknown versions fail closed.
Historical requests retain their original frozen v2 route and bytes. Specialist
receipts use `systemone-typed-challenge-v1-receipt`, retaining broker and
transport record hashes. Completed archived campaigns use exact historical
producer/configuration fingerprints for read-only reconstruction; incomplete
campaigns cannot inherit changed producer code.

[replay.py](replay.py) pins the original selection, manifest, wrappers, payloads,
intents, results, response bodies, parent checkpoint and captured cARL prepared
artifacts. A sealed replay packet is compared with those originals at every
verification/reservation boundary. It also binds the current broker request to
the historical SystemOne request and response separately. Native historical
requests are available as canonical payload custody, not authenticated original
HTTP wire bytes; cARL has captured request-body bytes.

The route deliberately permits only offline broker replay. Source text and
assessment retain their original case/variant identities. The baseline replays
the assessment supplied to the original judge; it does not claim to replay an
original generator wire body. Continuations receive the exact typed observation
and separately derived cARL result, then return a declared scripted local
assessment. They prove delivery, dependency and lifecycle accounting only.
A changed parent cannot reuse an old specialist response. Full-matrix topology
and eight arms remain unchanged; this bounded slice does not qualify a live
transport or a new scientific continuation/threshold policy.
