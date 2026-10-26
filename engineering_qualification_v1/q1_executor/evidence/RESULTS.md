# Observed acceptance results — 2026-10-26

```text
demo --output /tmp/mmmtap-q1-slice-final                 exit 0
deliberate child-process interruption after reservation exit 75
scheduled positions                                    15
completed valid / invalid                               6 / 1
blocked / interrupted / unavailable                     4 / 1 / 3
fake invocations / attempt reservations                 9 / 10
simulated expenditure / reserved units                  9 / 10
remaining simulated reservation budget                  0
first resume / second resume / read-only verification    PASS / PASS / PASS
second resume database bytes unchanged                  true
additional explicit resumes and preserved-copy audit    PASS
real provider calls / live authorization                 0 / false
```

The manifest SHA-256 is
`576f9f13041873eff319d516d6e0a8041b055ee75cde2431553dbc5a544199c5`.
The final 52-event evidence tip is
`e2731679054117be1e726aeb3525941a3d3ca0e5b9b90f99900882bff3bf81ae`.
The preserved SQLite file SHA-256 is
`22fed3d6b6cfa5e41b693aa3cfbc62e1a00cc235d591b789b6ba29b6f8221265`.

The final focused suite passed **19 tests** (13 executor + six existing
preflight tests), 16.776 seconds. Existing RD05, v2 instrument/continuation
and harness suites passed **82 tests**, 38.777 seconds, in an export of
upstream `de9b83299f6732c3d53dff2fc1ab568049e1420f`. Exporting preserved the
pre-existing local deletions/edits; no old contract file was restored.

The original custody verifier passed: **40,538 preserved entries**, **1,165
operator files**, **4,699 v5 files**, **36 command records**, zero changed or
missing entries. All parent engineering-package checksums also match.
The inherited pinned Codex `0.162.1` executable is absent; unrelated legacy
CLI tests were not run or repaired. These offline results do not qualify
live transports, isolation, current models, policies or scientific outcomes.

Each `*.command.json` captures actual argv, working directory, UTC start/end,
exit status and stdout/stderr hashes. `final_verify.stdout` contains the
reconstructed journal and all receipts. The preserved campaign can be checked:

```sh
python -m engineering_qualification_v1.q1_executor verify \
  --campaign engineering_qualification_v1/q1_executor/evidence/demo-campaign
```

**Q1 OFFLINE EXECUTION VERTICAL SLICE COMPLETE — LIVE EXECUTION BLOCKED**
