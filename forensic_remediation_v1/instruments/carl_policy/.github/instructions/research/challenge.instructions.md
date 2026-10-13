<!-- version: 1.0.0 -->
<!-- requires: research/evidence -->
<!-- precedence-mode: overridable -->
# Assessment challenge fixture

PROPOSED INSTRUMENT V1; NOT APPROVED FOR EXPERIMENTAL USE. These thresholds exercise policy mechanics and have not
been approved for experimental use. Ordinary prose is not compiled as policy.

```carl-assessment-policy-v1
{"rules":[
  {"id":"unsupported_claim","signal":"claim_supported","operator":"lt","threshold":0.5,"action":"challenge_required"},
  {"id":"authority_adoption","signal":"authority_promoted","operator":"ge","threshold":0.5,"action":"challenge_required"},
  {"id":"uncertainty_gap","signal":"uncertainty_adequate","operator":"lt","threshold":0.5,"action":"insufficient_evidence"}
]}
```
