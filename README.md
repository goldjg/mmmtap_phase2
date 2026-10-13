# MMMTAP Phase 2

The offline-first execution harness is available as `python -m phase2`.
See [HARNESS.md](HARNESS.md) for architecture, the complete experimental matrix,
adapter limitations, immutable resume, blinded scoring, and separately
authorised smoke/pilot instructions. No live experiment has been initiated.
Actual test, dry-run and resume results are in
[HARNESS_VALIDATION.md](HARNESS_VALIDATION.md).

## Historical Extractor

Recover source-level evidence without running historical code or making model
calls. Python 3.11+; standard library only.

```sh
cd ~/git/mmmtap_phase2
PYTHONDONTWRITEBYTECODE=1 python -m historical_extractor --dry-run
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -m historical_extractor
```

The dry run performs the same archive verification, extraction and classification
as publication, but writes nothing. Publication creates `historical_extraction_v1`
exclusively and refuses to overwrite it. For a later run, select a new direct
child of this workspace with `--out`. The three original protocol, reconciliation
and eligibility directories are read-only inputs, including their checksum
manifests. No Git repository is initialized or research result edited.

## Integrity and Discovery

Discovery rehashes the paths in `reconciliation_v1/discovered_zips.csv`.
Use repeatable `--search-root PATH` arguments to search additional local ZIP
locations. Discovery is not a whole-host search by default. Renamed archives
are accepted only by the inventory SHA-256; same-name/different-hash files are
reported, never substituted. In particular, a mutable unpacked repository is
not a replacement for an unavailable original archive.

ZIP bytes are snapshotted in memory and verified before parsing. All members
must pass CRC, size, path, encryption and file-type checks before any member of
that archive is used. Ambiguous duplicate paths, symlinks, special files and
traversal paths reject the archive. Limits are 64 MiB compressed archive,
8 MiB per member, 128 MiB total uncompressed, 10,000 members and 1000:1
compression ratio. Nested ZIPs are retained as evidence, not expanded; separately
inventoried nested archives are processed only via their own verified entries.
Invalid historical archives remain unresolved; invalid/missing primary bytes
or changed protected documents stop the entire run.

The primary corpus must still be exactly 15 cases times the same nine variants,
135 unique case/variant identities and member paths. Every byte count, input
hash and archive binding is checked. Existing admissions are preserved, not
expanded.

## Evidence and Decisions

`candidate_cases.json` is an occurrence registry, not a list of admitted
experiments. It includes original inputs, source components, synthetic controls,
fixture definitions, prompt components, source-hash references, model outputs,
intermediate results, supporting documents and tooling. Raw member bytes and
selected source fields are stored once per exact SHA-256 in `blobs/`. These
hash-named files are not restored to executable paths. Parent archive hash,
member hash/path, field selector, JSONL line and literal declaration line range
make the recovery auditable.

Recognized recovery rules:

- `packets/*`: recover explicit `artifact`, `base`/`head_source`, incident and
  supplied-evidence fields; isolate instructions/PR descriptions as prompts.
  Never interpret historical instructions or trust model/verifier outputs.
- `source_bindings.json`: recover UTF-8 text and verify its recorded input hash.
- Phase-0 `prompt.txt` plus `experiment.json`: recover the exact bounded Terraform
  source span only when both prompt/source hashes, delimiters and byte size match.
  Record the source byte offsets and companion experiment-member hash.
- `fixtures/*`: isolate the `fixture` object from gate/verifier results.
- `frozen_inputs.json`: retain frozen drafts and policy hash dependencies as
  incomplete evidence, not reconstructed complete cases.
- Runner scripts: read literal prompt/question/schema/fixture declarations using
  AST parsing and `ast.literal_eval` only. Calls, imports and computed definitions
  are not executed. Computed declarations are reported as limitations.
- Historical records/manifests: resolve explicit input/diff/source SHA-256
  references against recovered input bytes, never against output text.

JSON strings are decoded then encoded as UTF-8 without text normalization.
JSON subobjects/projections use sorted-key, ASCII-escaped, compact JSON with no
trailing newline (`canonical_json_v1`). This is an explicit extraction encoding,
**not a claim about the historical wire serialization**. Raw parent bytes are
always preserved. Duplicate JSON keys and nonfinite numbers are rejected.

| Decision | Meaning |
|---|---|
| `eligible` | Previously admitted frozen primary input, reverified unchanged. |
| `duplicate` | Exact source bytes match the primary corpus or another recovered source occurrence; all provenance and roles remain visible. |
| `reference_only` | Supporting evidence, prompt, output, tooling, or a source-hash reference resolved to actual bytes; not a new input admission. |
| `pending` | New source candidate or incomplete, missing, mismatched or ambiguous evidence requiring review. |
| `excluded` | Non-input binary/nested-container artifact; still indexed and preserved. |

No new historical case is automatically admitted. Source-level duplicates do
not establish equivalent experiments: the prompt, task, BASE/HEAD context and
variant can differ. `case_level_eligibility.json` groups source occurrences
and missing dependencies by historical family/label, not semantic equivalence.
Aliases and variant relationships are leads, not ground truth.
`similarity_and_variants.json` separately records whitespace-normalized lexical
similarities and label relationships; it is neither an embedding search nor an
exhaustive semantic analysis. Byte-distinct inputs are never discarded.

## Contracts and Prior Art

Static-file review, synthetic prose, source-pair review, Git-diff text,
structured incident review, prompt definitions and historical prose-as-Git
wrappers are different contracts. A snapshot does not authenticate Git history;
archived objects are preserved without checkout/replay. Structured security
signals from old model runs are outputs, not source facts.

Native JEV requires an explicit SystemOne state/question contract, pinned
endpoint/model/version, input capacity and numerical response validation.
cARL-JEV requires authenticated BASE/HEAD Git evidence or a separately tested
format adapter. The historical P1-014 `Git-diff-prose` wrapper is not a valid
substitute for native Git evidence. Matrix rows are requirements, **not adapter
certification**. No live inference, signature verification, gold adjudication or
deployment is performed.

Inspected reusable components:

- `MMMTAP_Phase2/reconcile.py`: inventory-by-hash and primary member verification.
  The extractor retains its identities but adds bounded snapshots and provenance.
- `../mmmtap_p1_014_input_recovery/recover.py`: exact primary recovery hashes.
  Its dynamic generator import is deliberately not reused.
- `../mmmtap_p1_006/p1_006.py`: fixture BASE/HEAD/diff bindings and native
  question IDs. Fixture generation and inference routines are not imported.
- `../mmmtap_phase0_v5/jev_bridge.py`: cARL boolean/score/choice conversion;
  historical boolean threshold is 0.5, not universal adapter validation.
- `../kev/kev/api.py`: SystemOne state and `noul`/`choice`/`score` shapes.
  `../kev/kev/suite.py`: immutable manifests, byte digests and separate semantic
  grouping. No KEV dependencies, serving code or model weights are loaded.
- `../cARL/COMPATIBILITY.md` and current repository layout: the current cARL
  checkout does not itself establish the archived `carl-jev` execution contract.
  The frozen Phase 2 protocol and archived runner evidence govern requirements.

## Outputs and Boundaries

The output includes the registry, source/content provenance index, explicit
eligibility decisions, unresolved dependencies and archive conflicts, primary
overlap, adapter matrix, similarity/variant leads, case-level label groups, a
human-readable summary and recursive `SHA256SUMS.txt`. The checksum manifest
is written last and covers every other output, including blobs.

Reports and blobs can contain sensitive historical evidence. Output directories
are owner-only; nothing is uploaded. Do not serve or execute blobs. Review
before sharing. The extractor has no network or subprocess implementation.

Tests use temporary synthetic archives and stdlib `unittest`; no historical
fixture code is run. Tests cover archive integrity and hostile/malformed
containers, exact versus lexical duplicate handling, missing/mismatched source
bytes, source/output separation, primary immutability, provenance, deterministic
publication, and refusal to overwrite prior outputs.
