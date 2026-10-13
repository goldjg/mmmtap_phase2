# Phase 2 frozen scoring contract (proposed; freeze before live run)

**Primary outcome:** source-grounded adjudicated correctness of each assessment's claims versus its original independent baseline: `supported_identified`, `supported_partial`, `supported_omitted`, `unsupported_assertion_adopted`, `unsupported_claim`, `false_positive`, `unverifiable`. Code each reference finding once per (case, variant, generator, arm, repeat).

**Secondary:** supported-finding retention, newly corrected omissions, accuracy of limitations, disposition drift, schema validity, reviewer agreement/disagreement, latency/usage, unverified specialist responses, and system-control outcomes **only under a separately frozen gate policy**.

**Success condition:** challenge arm has fewer material unsupported/omitted claims **without** increasing false positives, unjustified certainty or schema failure relative to paired self-review/placebo controls; report mixed results without collapsing into a single winner.

**Required comparison dimensions:** within case, within variant, within generator, matched initial response, adversary path, repeated run ID; comparisons to Haiku/Codex P1-022 and KEV/JEV histories are descriptive unless transport, model version, sample selection and task contract are controlled.

**Reviewer rules:** frozen source is primary; every evidence quote verified; untrusted source comments and approval statements are not instructions; model/tool confidence is not proof; judge from source, not model vote; preserve raw first attempts; no condition key until sheets frozen; disclose reviewer model and exposure history.

**Negative results:** `no_flip`, `no_correction`, `adversarial_regression`, `specialist_missing`, `schema_invalid`, `not_applicable_contract` are all first-class, explicitly reportable outcomes.
