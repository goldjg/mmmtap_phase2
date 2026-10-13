# Public sanitized research snapshot

This repository publishes MMMTAP Phase 2 source, post-pilot review, and
research evidence. It is **not a byte-identical copy of the original frozen
evidence bundle**.

Credential-like values were removed from copied files and nested archives.
Authentication files and nonportable runtime symlinks were excluded.
`PUBLICATION_REDACTIONS.json` records original and published hashes for each
changed file/archive member and records exclusions. The original evidence
remains unchanged in its local custody location. Original seals are retained
for provenance, but they cannot validate redacted copies. Do not regenerate
seals to make changed evidence appear original.

`publication_external_evidence/manifest.json` inventories externally referenced
MMMTAP archives copied for publication, their original locations and hashes,
and missing references. It does not authorize uploading unrelated files from
the historical filesystem-discovery inventory. For a changed external archive,
the redaction manifest takes precedence over its original hash.

Two large evidence archives use Git LFS. Clone with Git LFS installed and run
`git lfs pull` to retrieve their contents.

The Phase 2 v1 pilot had 153 terminal checkpoints: 114 `ok`, 28
`schema_invalid`, and 11 `blocked_parent`, with 142 attempt reservations.
Its evidence classification is lower-assurance operator-supervised research;
strict isolation was not qualified. Scientific correctness, calibration,
causal effectiveness, and statistical significance were not established.

The versioned review and proposed remediation documents are in `phase2_v2/`.
The continuation component is offline-only, not a live executor. A child is
runnable only if every required parent has a verified acceptable `ok`
outcome; terminality alone is insufficient.

**No live provider calls or full experiment are authorized by publication.**
The 6,885-position experiment remains unauthorized. V2 methodological changes
and qualification require human decisions.

The original package verifier depends on unchanged original evidence and
historical machine paths. Failure against this sanitized snapshot is expected
where files were redacted/excluded; it is not evidence that the originals
failed verification. Restore originals through separately authorized custody
procedures, not by treating the public snapshot as an original sealed bundle.
