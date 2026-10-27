"""Small real-executor offline acceptance campaign using historical byte replay."""
import copy
from pathlib import Path
import subprocess
import sys

from . import VERSION
from .replay import load_record, identity, b64, unb64, observe, selection
from .. import engine
from ..model import PACKAGE, decode, digest, encode, raw_hash, validate_manifest
from ..broker_v1.contract import extension, message
from ..transport_qualification import snapshot


def fixture(root, sample_ids, *, negative_inputs=None, scenarios=None):
    root.mkdir()
    contexts = {ident: load_record(ident) for ident in sample_ids}
    first = next(iter(contexts.values()))
    assessment = first["assessment"]
    state = decode(decode(unb64(first["request_b64"]))["state"])
    m, _ = validate_manifest(PACKAGE / "fixtures")
    packets = {"source": ("source.txt", state["untrusted_source"].encode()),
               "governing_policy": ("governing-policy.json", encode({"id": "synthetic-no-release-authority",
                    "simulation_only": True, "release_authority": False})),
               "challenge_policy": ("challenge-policy.json", encode({"id": "synthetic-captured-policy-replay-only",
                    "simulation_only": True, "governing_authority": False,
                    "threshold_approval": "pending_no_new_policy_or_thresholds",
                    "captured_prepared_sha256": {k: raw_hash(unb64(v["prepared_b64"])) for k, v in contexts.items() if v["prepared_b64"]}})),
               "replay": ("replay.json", encode({"version": VERSION, "records": contexts}))}
    m["packets"] = {}
    for kind, (name, raw) in packets.items():
        (root / name).write_bytes(raw)
        m["packets"][kind] = {"path": name, "sha256": raw_hash(raw)}
    pbase = copy.deepcopy(m["positions"][0])
    pbase.update(packet_bindings={k: v["sha256"] for k, v in m["packets"].items()},
                 case_id=assessment["case_id"], variant_id=assessment["variant_id"], fake_disposition=assessment["disposition"])
    positions = [pbase]
    samples = {}
    for ident, context in contexts.items():
        role = "carl" if context["mechanism"] == "carl_jev" else "native"
        arm = "E2" if role == "carl" else "E1"
        p = dict(pbase, id=ident, kind="specialist", role="specialist", arm=arm, path=role + "_simulation",
                 dependencies=["baseline"], assessment_parent="baseline")
        p["identity"] = identity(p)
        positions.append(p)
        positions.append(dict(pbase, id=ident + "-continuation", role="challenge_continuation", arm=arm,
                              path=role + "_simulation", dependencies=["baseline", ident],
                              assessment_parent="baseline", specialist_parent=ident))
        samples[ident] = ident
    m.update(campaign_id="synthetic-q1-choice1-" + digest([sample_ids, negative_inputs, scenarios])[:12],
             positions=positions, attempt_ceiling=len(positions), simulated_budget_units=len(positions),
             specialist_observation={"version": VERSION, "replay_only": True, "samples": samples,
                                     "negative_inputs": negative_inputs or {}}, transport=extension(scenarios))
    m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
    (root / "manifest.json").write_bytes(encode(m))
    validate_manifest(root)
    return root


def run_case(root, name, sample_ids, *, negative_inputs=None, crash=None):
    case = root / name; case.mkdir()
    frozen = fixture(case / "fixture", sample_ids, negative_inputs=negative_inputs)
    campaign = engine.create(case / "campaign", frozen)
    interrupted = None
    if crash:
        child = subprocess.run([sys.executable, "-B", "-m", "engineering_qualification_v1.q1_executor",
                                "resume", "--offline-subprocess", "--campaign", str(campaign),
                                "--interrupt-after-reservation", crash], capture_output=True)
        (case / "interruption.stdout").write_bytes(child.stdout)
        (case / "interruption.stderr").write_bytes(child.stderr)
        if child.returncode != 75:
            raise AssertionError((child.returncode, child.stderr))
        interrupted = engine.verify(campaign)["summary"]
    engine.resume(campaign, offline_subprocess=True)
    frozen_files = snapshot(campaign)
    report = engine.verify(campaign)
    for _ in range(2):
        engine.resume(campaign, offline_subprocess=True)
    if frozen_files != snapshot(campaign):
        raise AssertionError("repeated_resume_changed_evidence")
    # Verify raw entity bytes and continuation delivery from actual SQLite custody.
    details = {}
    with engine.connect(campaign, readonly=True) as db:
        for ident in sample_ids:
            receipt = report["receipts"][ident]
            context = load_record(ident)
            raw = db.execute("SELECT raw FROM responses WHERE id=?", (ident,)).fetchone()
            details[ident] = {"state": receipt["state"], "response_sha256": receipt["response_sha256"],
                              "original_response_sha256": context["response_sha256"],
                              "exact_original_body": raw is not None and raw[0] == unb64(context["response_b64"]),
                              "role_identity": receipt["requested_identity"], "observation": receipt["diagnostics"]["parsed"]}
            child = report["receipts"][ident + "-continuation"]
            if negative_inputs and ident in negative_inputs:
                assert receipt["state"] == "invalid" and raw is not None
                assert child["state"] == "blocked" and child["request_sha256"] is None
            elif ident == crash:
                assert receipt["state"] == "interrupted" and raw is None and child["state"] == "blocked"
            else:
                assert receipt["state"] == "completed" and details[ident]["exact_original_body"]
                sealed = db.execute("SELECT request FROM attempts WHERE id=?", (ident + "-continuation",)).fetchone()[0]
                req = decode(sealed)
                assert req["specialist_observations"] == receipt["diagnostics"]["parsed"]
                assert child["state"] == "completed"
                details[ident]["continuation_received_exact_observation"] = True
    outcome = {"summary": report["summary"], "specialists": details, "interrupted_before_resume": interrupted,
               "readonly_and_repeated_resume_files_unchanged": True,
               "receipt_sha256": {k: digest(v) for k, v in report["receipts"].items()}}
    (case / "report.json").write_bytes(encode(outcome))
    return outcome


def run(root):
    root.mkdir()
    reports = {
        "low_pair": run_case(root, "low_pair", ["native-low", "carl-low"]),
        "multi_pair": run_case(root, "multi_pair", ["native-multi", "carl-multi"]),
        "qualification_choice": run_case(root, "qualification_choice", ["smoke-choice"]),
    }
    for negative in ("missing", "extra", "duplicate", "wrong_type"):
        reports[negative] = run_case(root, negative, ["native-multi"], negative_inputs={"native-multi": negative})
    reports["reservation_restart"] = run_case(root, "reservation_restart", ["carl-low"], crash="carl-low")
    replayed = [d for name in ("low_pair", "multi_pair", "qualification_choice") for d in reports[name]["specialists"].values()]
    assert len(replayed) == 5 and all(d["exact_original_body"] for d in replayed)
    result = {"status": "CHOICE 1 TYPED SPECIALIST INTEGRATED — OFFLINE QUALIFIED, LIVE Q1 BLOCKED",
              "instrument_contract": VERSION, "exact_historical_bodies_replayed": len(replayed),
              "native_observations": 3, "carl_observations_with_separate_policy_trace": 2,
              "negative_specialist_responses_retained_and_rejected": 4,
              "real_provider_calls": 0, "generator_inferences": 0, "remote_carl_executions": 0,
              "experimental_execution": False,
              "campaigns": {k: {"summary": v["summary"], "report": k + "/report.json",
                                 "readonly_and_repeated_resume_files_unchanged": v["readonly_and_repeated_resume_files_unchanged"]} for k, v in reports.items()}}
    (root / "acceptance.json").write_bytes(encode(result))
    return result
