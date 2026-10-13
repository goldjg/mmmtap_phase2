# MMMTAP Phase 2 — Case eligibility registry v1

Input: reconciler's Gaia-generated ZIP; verified SHA-256 shown in SUMMARY.json. **Index-only classification**: no historical archive bytes were included in reconciliation_v1; member paths, sizes and CRC32 cannot establish security-case equivalence or validate adapter inputs. Archive registry is not itself a corpus.

- `primary_cases.csv`: 15 admitted primary cases, each with nine verified frozen inputs. Generative arms can be scheduled once execution adapters are validated.
- `historical_archive_eligibility.csv`: 44 archival provenance decisions, none silently admitted as new cases. A hash mismatch is *not* considered a located original.
- `historical_case_name_leads.csv`: possible case labels mechanically extracted from `/packets/<stem>.json` and `/runs/<name>/` patterns. **Not admissions**; may include variants and artifacts.
- `SUMMARY.json`: quantitative accounting.

## Next practical step

Run an archive-byte-aware extractor on Gaia against the 33 SHA-verified historical ZIPs, recovering candidate *input* files and paired source/manifest evidence. Hash candidate source bytes, group duplicate variants and aliases, and classify each source against the 135 primary inputs. Store explicit reason for every excluded/pending case. Only then promote new historical cases.

## Boundaries

No model calls; no new fixtures; no historical experiments falsely counted as eligible. Two same-name/different-hash archives and nine unfound original hashes remain unresolved. Native JEV and cARL-JEV compatibility require separate adapter proofs.
