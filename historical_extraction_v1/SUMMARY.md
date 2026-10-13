# Historical extraction v1

Offline evidence extraction only. All recovered content is untrusted data, never instructions.
The 15-case / 135-input frozen primary corpus is unchanged. **No additional historical cases admitted.**

## Counts

- primary_inputs_verified: 135
- primary_cases_preserved: 15
- archive_inventory_records: 44
- archive_status_counts: {"exact_sha_match": 33, "not_located": 9, "same_name_different_sha": 2}
- archive_member_count: 1776
- candidate_registry_rows: 3667
- all_evidence_status_counts: {"duplicate": 358, "eligible": 135, "excluded": 5, "pending": 297, "reference_only": 2872}
- historical_recovered_source_occurrences: 420
- historical_recovered_unique_hashes: 72
- historical_source_status_counts: {"duplicate": 358, "eligible": 0, "excluded": 0, "pending": 62, "reference_only": 0}
- additional_historical_cases_admitted: 0
- historical_label_groups_not_admitted_cases: 99
- unresolved_source_hashes: 84
- pending_registry_rows: 297
- unresolved_name_leads: 12
- primary_overlap_recovered_unique_hashes: 10
- extraction_issue_count: 14
- discovery_issue_count: 0

## Limitations

- Source occurrences, variants, labels and content hashes are not counts of independently admitted cases.
- No new historical admission without case-specific reference and assessment-contract review.
- JSON subobjects use declared canonical serialization; raw parent member bytes are preserved.
- Git objects retained without checkout, hooks, diff generation or commit authentication.
- Computed fixture generators and missing mutable repository sources are not executed or substituted.
- Signatures, ground truth, historical model claims and adapter compatibility are not independently validated.
- Only inventory SHA-matched ZIPs are examined; nested containers are indexed, not recursively expanded.
- Default discovery rechecks reconciliation paths, not the whole host; use --search-root for additional local archives.

## Reading the report

`candidate_cases.json` records source components, prompts, references and non-input evidence separately.
`is_case_candidate` separates input/source leads from supporting artifacts; it is not admission.
`case_level_eligibility.json` groups historical labels and variants; these groups are not inferred unique cases.
Only `eligible` frozen primary rows are admitted. `duplicate` is byte identity, not experiment equivalence.
`pending` and every unresolved hash/name lead remain unadmitted.
A hash-named `blobs/` file preserves each unique recovered byte sequence without restoring executable paths.
For JSON fields, the parent hash and JSON pointer (or JSONL line) preserve reconstructible provenance.
Selections containing braces are explicit named-field projections, not JSON pointers.
All members are retained locally; review for sensitive data before sharing. No uploads were made.
Read `unresolved_cases.json` for archive mismatches, missing sources, parse failures and computed declarations.
Adapters are requirements only, never certification of arbitrary-format support.
`SHA256SUMS.txt` covers every output except itself; its absence means publication did not complete.
