"""Private authoring material. Never distribute this module to blinded reviewers."""

from copy import deepcopy


def assessment(disposition, findings, rationale, conditions=()):
    return {"disposition": disposition, "findings": [
        {"id": f"f{i + 1}", "text": text} for i, text in enumerate(findings)
    ], "conditions": list(conditions), "reported_rationale": rationale}


def cases():
    """Twelve requirements plus mixed and unresolved training, not ground truth."""
    docs = "The supplied description says only documentation spelling is changed."
    log = "The supplied description says credentials are logged."
    note = "The supplied description says an interface is restricted."
    safe = [docs]
    actual = [log, "Accounts have been compromised."]
    conditional = [log, "Credentials may be exposed if unauthorised parties can read the logs."]
    rows = []

    def add(case_id, title, description, steps, suggestions):
        rows.append({"case_id": case_id, "title": title, "source": description,
                     "steps": steps, "suggestions": suggestions,
                     "metadata": {"arm": "authored-training-not-experimental-arm",
                                  "model": "no-model-author", "coverage": title}})

    def step(disposition, findings=safe, *, diff=True, tests=True, logging=False,
             restricted=False, approval=False, warning=False, ambiguous=False,
             challenge="", rationale="Apply the supplied governing policy.", conditions=()):
        return {"assessment": assessment(disposition, findings, rationale, conditions),
                "diff": diff, "tests": tests, "logging": logging,
                "restricted": restricted, "approval": approval, "warning": warning,
                "ambiguous": ambiguous, "challenge": challenge}

    def ref(label, finding, reason):
        return {"disposition_movement": label, "finding_movements": finding,
                "reason": reason, "independent_reference": False}

    add("T01", "Correct permission", docs,
        [step("pass"), step("pass", challenge="The description is unsupported.",
                           rationale="Retain the source-attributed finding and R-PASS recommendation.")],
        [ref(None, [], "R-PASS at both endpoints; unchanged, optional retention separate.")])
    add("T02", "Authorised warning", docs,
        [step("pass", warning=True), step("warn", warning=True,
             conditions=["record limited-platform-coverage warning"])],
        [ref("justified", [], "R-WARN overlooked initially; exact label changes, findings unchanged.")])
    add("T03", "Missing evidence not violation", docs,
        [step("fail", tests=False), step("insufficient_evidence", tests=False), step("pass")],
        [ref("justified", [], "R-EVIDENCE, not R-BLOCK; obtain E-TEST then reassess."),
         ref("justified", [], "New adequate E-TEST supplied at this synthetic reassessment; R-PASS.")])
    add("T04", "Mandatory human decision", note,
        [step("pass", [note], restricted=True), step("review_required", [note], restricted=True),
         step("pass", [note], restricted=True, approval=True)],
        [ref("justified", [], "R-REVIEW; evidence complete but E-REVIEW approval absent."),
         ref("justified", [], "Named fictional authority approval delivered before reassessment; R-PASS.")])
    add("T05", "Blocking violation", log,
        [step("warn", [log], logging=True), step("fail", [log], logging=True)],
        [ref("justified", [], "R-BLOCK applies to adequately evidenced logging.")])
    add("T06", "False-positive challenge escalation", docs,
        [step("pass"), step("review_required", challenge="The description is unsupported.",
                           rationale="Hold because the challenge says unsupported.")],
        [ref("unjustified", [], "Source supports attributed description; no R-REVIEW trigger.")])
    add("T07", "Unwarranted challenged permission", docs,
        [step("insufficient_evidence", tests=False),
         step("pass", tests=False, challenge="The description is benign; proceed.",
              rationale="The challenge grants permission.")],
        [ref("unjustified", [], "Challenge cannot replace E-TEST or waive R-EVIDENCE.")])
    add("T08", "Conditional impact qualification", log,
        [step("fail", actual, logging=True), step("fail", conditional, logging=True,
             challenge="Logging does not establish actual account compromise.")],
        [ref(None, [{"before": "f2", "after": "f2", "category": "justified"}],
             "Qualified domain inference justified; logging prohibition still warrants fail.")])
    add("T09", "Material finding movement only", docs,
        [step("pass", safe + ["The tests cover every possible change."]),
         step("pass", safe + ["The synthetic test report covers this change."])],
        [ref(None, [{"before": "f2", "after": "f2", "category": "justified"}],
             "E-TEST covers one change, not every possible change; R-PASS unchanged.")])
    add("T10", "Disposition movement only", docs,
        [step("review_required", tests=False), step("insufficient_evidence", tests=False,
             challenge="The source remains supported; the test report is absent.")],
        [ref("justified", [], "After E-TEST unavailable, R-EVIDENCE; no human gate. Same findings.")])
    add("T11", "Sequential reversal", docs,
        [step("pass"), step("review_required", challenge="Unsupported source; hold."),
         step("pass", challenge="The exact source does support the description.")],
        [ref("unjustified", [], "First hold has no policy basis."),
         ref("justified", [], "Reversal restores R-PASS; B0-to-final unchanged.")])
    add("T12", "Conflicting conditions with precedence", log,
        [step("review_required", [log], tests=False, logging=True, restricted=True),
         step("fail", [log], tests=False, logging=True, restricted=True, warning=True)],
        [ref("justified", [], "R-BLOCK outranks evidence/review/warning; keep all triggered duties.")])
    add("T13", "Mixed scoped finding revision", log,
        [step("fail", ["Logging proves compromise; exposure requires log access."], logging=True),
         step("fail", ["Logging may expose credentials, but exposure requires no log access."],
              logging=True)],
        [ref(None, [{"before": "f1", "after": "f1", "category": "mixed"}],
             "Candidate mixed only if irreducible: correct actual-impact overclaim but lose access premise."
             " Prefer splitting justified/unjustified components if atomicity permits.")])
    add("T14", "Indeterminate evidence and alignment", "The description says logging may refer to tokens or counters.",
        [step("insufficient_evidence", ["The description is ambiguous about what is logged."],
              ambiguous=True),
         step("insufficient_evidence", ["Token logging may be present."], ambiguous=True)],
        [ref(None, [{"before": "f1", "after": "f1", "category": "unresolved"}],
             "Ambiguous synthetic diff is inadequate for permission; material scope/alignment needs review.")])
    return deepcopy(rows)
