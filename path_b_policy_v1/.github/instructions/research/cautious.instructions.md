<!-- version: 1.0.0 -->
<!-- requires: research/evidence -->
<!-- precedence-mode: additive -->
<!-- priority: 20 -->
<!-- overrides: research/challenge -->
# Cautious reviewer fixture

OFFLINE FIXTURE ONLY. Activated only through the explicit cautious role.
This is a composition test, not a claim that different thresholds improve
security. Overrides retain the original pack in provenance but do not apply it.

```carl-assessment-policy-v1
{"rules":[
  {"id":"unsupported_claim","signal":"claim_supported","operator":"lt","threshold":0.7,"action":"challenge_required"},
  {"id":"authority_adoption","signal":"authority_promoted","operator":"ge","threshold":0.3,"action":"challenge_required"},
  {"id":"uncertainty_gap","signal":"uncertainty_adequate","operator":"lt","threshold":0.7,"action":"insufficient_evidence"}
]}
```
