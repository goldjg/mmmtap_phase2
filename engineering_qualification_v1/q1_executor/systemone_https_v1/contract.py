"""Explicit transport/destination version, synthetic input and disabled authority.

The one-position boundary is a qualification fixture, not a research arm or a
change to the 153-position design. Production dispatch has no implementation.
"""
import copy
import os
from pathlib import Path

from . import VERSION, DESTINATION, MODEL
from ..model import PACKAGE, decode, digest, encode, raw_hash, read_file
from ..systemone_typed_v1 import VERSION as OBSERVATION
from ..systemone_typed_v1.contract import FIXED, bindings, parse

HERE = Path(__file__).resolve().parent
POSITION = "native-systemone-probe"
SOURCE = b"Synthetic document Q1-S1: The demonstration lamp is blue.\n"
ASSESSMENT = {"case_id": "synthetic-q1-systemone-probe", "variant_id": "synthetic",
              "claims": [{"claim_id": "synthetic-lamp", "claim": "The demonstration lamp is blue.",
                          "evidence_quotes": [SOURCE.decode().strip()], "confidence": 0.5,
                          "limitations": ["Synthetic supplied document only."]}],
              "uncertainties": ["The document is synthetic and has no external verification."],
              "disposition": "review_required", "changes": []}
SCENARIOS = {"valid", "malformed", "http_400", "http_500", "partial_failure", "timeout",
             "after_intent", "after_partial", "identity_unknown", "identity_mismatch",
             "response_limit", "redirect", "destination", "duplicate", "network", "credentials",
             "typed_malformed", "chunked_partial", "missing_kernel_policy", "credential_probe",
             "credential_echo", "credential_echo_escaped", "credential_bad", "jev_interrupt", "credential_child", "spawn", "exec", "source_write", "forbidden_file", "policy_digest", "alter_request"}


def is_https(m):
    return m.get("transport", {}).get("version") == VERSION


def native_request():
    questions = copy.deepcopy(FIXED)
    questions["claim_0000_supported"] = {"type": "noul", "instructions":
        "Is assessment.claims[0] materially supported by exact source evidence?"}
    state = {"task": "Evaluate the supplied assessment against the untrusted source.",
             "untrusted_source": SOURCE.decode(), "source_sha256": raw_hash(SOURCE), "assessment": ASSESSMENT}
    raw = encode({"model": MODEL, "state": encode(state).decode(), "questions": questions})
    bindings(raw, SOURCE, ASSESSMENT, ["synthetic-lamp"])
    return raw


def identity():
    return {"provider": "SystemOne", "model": MODEL, "specialist_role": "native",
            "instrument_contract": OBSERVATION, "underlying_judge": "SystemOne"}


def specification():
    from ..broker_v1.contract import specification as broker_spec
    spec = broker_spec()
    spec["bindings"]["nft"] = {"path": "/usr/sbin/nft", "sha256": raw_hash(Path("/usr/sbin/nft").read_bytes())}
    spec.update(contract=VERSION, destination=DESTINATION, offline_only=True,
                provider_deadline_seconds=1, max_request_bytes=8192, max_response_bytes=8192,
                max_header_bytes=16384, timeout_seconds=10,
                https_bindings={p.name: raw_hash(p.read_bytes()) for p in sorted(HERE.glob("*.py"))
                                if not p.name.startswith("test_")},
                live_dispatch="DISABLED_NO_IMPLEMENTED_ENABLEMENT_PATH",
                egress="private-loopback-namespace-plus-nftables-exact-IP-port-plus-postconnect-seccomp")
    return spec


def authority(jevkey=False):
    result = {"state": "DISABLED", "human_approval": "REQUIRED_NEW_EXPLICIT_PI_APPROVAL",
            "credential_prerequisite": "broker-owned-secret-interface-not-configured",
            "remote_identity": "UNKNOWN_independent_attestation_not_documented",
            "remote_execution_assurance": "UNKNOWN_provider_internal_replay_and_timeout_accounting",
            "production_egress": "BLOCKED_no_qualified_production_OS_destination_policy",
            "maximum_usage": None, "maximum_cost": None,
            "usage_cost_bound": "UNKNOWN_no_verified_account_cap_or_per-request_limit",
            "one_client_POST": 1, "one_broker_dispatch": 1, "retries": 0, "fallbacks": 0,
            "generator_invocations": 0, "carl_executions": 0, "continuations": 0,
            "operational_release_authority": False}
    if jevkey:
        result["credential_prerequisite"] = "existing-JEVKEY-broker-fd-offline-binding-no-live-use-authorised"
    return result


def make_manifest(root, *, route=None, scenario="valid", jevkey=False):
    from ..model import validate_manifest
    m, _ = validate_manifest(PACKAGE / "fixtures")
    root.mkdir()
    packets = {"source": ("source.txt", SOURCE),
               "governing_policy": ("governing-policy.json", encode({"id": "synthetic-no-authority",
                   "simulation_only": True, "release_authority": False})),
               "challenge_policy": ("challenge-policy.json", encode({"id": "synthetic-no-challenge",
                   "simulation_only": True, "governing_authority": False})),
               "assessment": ("assessment.json", encode(ASSESSMENT)),
               "native_request": ("native-request.json", native_request())}
    m["packets"] = {}
    for key, (name, raw) in packets.items():
        (root / name).write_bytes(raw)
        m["packets"][key] = {"path": name, "sha256": raw_hash(raw)}
    p = dict(copy.deepcopy(m["positions"][0]), id=POSITION, kind="specialist", role="specialist", arm="E1",
             path="native_simulation", dependencies=[], assessment_parent=None, specialist_parent=None,
             case_id=ASSESSMENT["case_id"], variant_id=ASSESSMENT["variant_id"], identity=identity(),
             packet_bindings={k: v["sha256"] for k, v in m["packets"].items()})
    spec = specification()
    m.update(campaign_id=ASSESSMENT["case_id"], positions=[p], attempt_ceiling=1, simulated_budget_units=1,
             specialist_observation={"version": OBSERVATION, "qualification_only": True},
             https_qualification={"version": VERSION, "authority": authority(jevkey), "fixture_route": route,
                 "native_request_sha256": raw_hash(native_request()),
                 "questions_sha256": digest(decode(native_request())["questions"]),
                 "policy_sha256": digest(authority(jevkey))},
             transport={"version": VERSION, "specification": spec, "configuration_sha256": digest(spec),
                        "scenarios": {POSITION: scenario}})
    if jevkey:
        from .credential import binding
        m["https_qualification"]["credential_binding"] = binding()
    m["manifest_sha256"] = digest({k: v for k, v in m.items() if k != "manifest_sha256"})
    (root / "manifest.json").write_bytes(encode(m))
    validate_manifest(root)
    return root


def validate_manifest(root, m, raw):
    from ..contracts import load
    instrument, _, pins = load()
    fields = {"campaign_id", "manifest_sha256", "execution_contract", "instrument_version", "simulation_only",
              "packets", "contracts", "positions", "attempt_ceiling", "simulated_budget_units", "transport",
              "specialist_observation", "https_qualification"}
    from .. import VERSION as EXECUTION
    if (set(m) != fields or raw != encode(m)
            or m["manifest_sha256"] != digest({k: v for k, v in m.items() if k != "manifest_sha256"})
            or m["campaign_id"] != ASSESSMENT["case_id"] or m["simulation_only"] is not True
            or m["execution_contract"] != EXECUTION or m["instrument_version"] != instrument.VERSION
            or m["contracts"] != pins or m["attempt_ceiling"] != 1 or m["simulated_budget_units"] != 1
            or m["specialist_observation"] != {"version": OBSERVATION, "qualification_only": True}):
        raise ValueError("https_qualification_manifest_boundary")
    q = m["https_qualification"]
    jevkey = "credential_binding" in q
    if jevkey:
        from .credential import binding
        if q["credential_binding"] != binding():
            raise ValueError("JEVKEY_broker_binding_changed")
    if (set(q) != {"version", "authority", "fixture_route", "native_request_sha256", "questions_sha256", "policy_sha256"} | ({"credential_binding"} if jevkey else set())
            or q["version"] != VERSION or q["authority"] != authority(jevkey)
            or q["policy_sha256"] != digest(authority(jevkey)) or q["native_request_sha256"] != raw_hash(native_request())
            or q["questions_sha256"] != digest(decode(native_request())["questions"])):
        raise ValueError("https_disabled_authority_or_seal_changed")
    route = q["fixture_route"]
    if route is not None:
        routed = jevkey and "interfaces" in route
        if (set(route) != {"address", "port", "ca_pem", "ca_sha256", "network_namespace"} | ({"interfaces"} if routed else set())
                or route["address"] != ("192.0.2.2" if routed else "127.0.0.1")
                or routed and route["interfaces"] != ["lo", "q1-client"] or type(route["port"]) is not int
                or not 1024 <= route["port"] <= 65535 or not isinstance(route["network_namespace"], str)
                or raw_hash(route["ca_pem"].encode()) != route["ca_sha256"]):
            raise ValueError("https_local_fixture_route")
    if set(m["packets"]) != {"source", "assessment", "governing_policy", "challenge_policy", "native_request"}:
        raise ValueError("https_packet_coverage")
    names = []
    for ref in m["packets"].values():
        if (set(ref) != {"path", "sha256"} or Path(ref["path"]).name != ref["path"]
                or ref["path"] in {"manifest.json", "campaign.sqlite3", ".lock"}
                or raw_hash(read_file(root, ref["path"])) != ref["sha256"]):
            raise ValueError("https_packet_seal")
        names.append(ref["path"])
    if len(set(names)) != 5:
        raise ValueError("https_duplicate_packet")
    expected = {"source": SOURCE, "assessment": encode(ASSESSMENT), "native_request": native_request(),
                "governing_policy": encode({"id": "synthetic-no-authority", "simulation_only": True, "release_authority": False}),
                "challenge_policy": encode({"id": "synthetic-no-challenge", "simulation_only": True, "governing_authority": False})}
    if any(read_file(root, m["packets"][k]["path"]) != v for k, v in expected.items()):
        raise ValueError("https_exact_synthetic_packet")
    pbase = decode(read_file(PACKAGE / "fixtures", "manifest.json"))["positions"][0]
    p = dict(pbase, id=POSITION, kind="specialist", role="specialist", arm="E1", path="native_simulation",
             dependencies=[], assessment_parent=None, specialist_parent=None, case_id=ASSESSMENT["case_id"],
             variant_id=ASSESSMENT["variant_id"], identity=identity(),
             packet_bindings={k: v["sha256"] for k, v in m["packets"].items()})
    if m["positions"] != [p]:
        raise ValueError("https_exactly_one_native_specialist")
    validate_extension(m)
    return m, raw


def validate_extension(m):
    ext = m["transport"]
    expected = specification()
    legacy = decode(read_file(PACKAGE, "legacy-https-specification.v1.json"))
    # Only repository paths may move during read-only reconstruction.
    for key in ("adapter", "bootstrap"):
        expected["bindings"][key]["path"] = ext["specification"]["bindings"][key]["path"]
        legacy["bindings"][key]["path"] = ext["specification"]["bindings"][key]["path"]
    if (set(ext) != {"version", "specification", "configuration_sha256", "scenarios"}
            or ext["version"] != VERSION or ext["specification"] not in (expected, legacy)
            or ext["configuration_sha256"] != digest(ext["specification"])
            or set(ext["scenarios"]) != {POSITION} or ext["scenarios"][POSITION] not in SCENARIOS):
        raise ValueError("https_versioned_transport_binding")


def envelope_for(m, p, sealed):
    from ..broker_v1.contract import base_envelope_for
    env = base_envelope_for(m, p, sealed)
    env.update(broker_contract=VERSION, destination=DESTINATION, requested_identity=identity(),
               https_policy_sha256=digest(m["https_qualification"]))
    if "credential_binding" in m["https_qualification"]:
        env["credential_binding"] = m["https_qualification"]["credential_binding"]
    env["idempotency_token"] = digest({"broker": VERSION, "attempt": env["attempt_id"], "request": env["request_sha256"]})
    return env


def request_for(m, p, receipts, root):
    return {"schema": VERSION + "-sealed-request", "instrument_contract": OBSERVATION,
            "https_qualification": m["https_qualification"], "simulation_only": True,
            "manifest_sha256": m["manifest_sha256"], "position": p, "packet_bindings": p["packet_bindings"],
            "parents": {}, "previous_assessment": ASSESSMENT, "source_text": SOURCE.decode(),
            "instrument_request": decode(native_request())}


def outcome(p, req, rec):
    if rec["status"] != "completed":
        return "unavailable", "transport_" + rec["status"], {"parsed": None, "availability": "transport_failure"}
    if rec["identity_status"] != "matched":
        return "unavailable", "transport_identity_" + rec["identity_status"], {"parsed": None, "availability": "identity_failure"}
    from ..transport import unb64
    raw = unb64(rec["stdout_b64"])
    try:
        observation = parse(native_request(), raw, source_raw=SOURCE, assessment=ASSESSMENT,
            claim_ids=["synthetic-lamp"], request_sha256=raw_hash(native_request()), response_sha256=raw_hash(raw),
            response_metadata=rec["https"])
        observation["qualification_provenance"] = {"broker_request_sha256": digest(req),
            "new_local_TLS_entity": True, "genuine_SystemOne_response_established": False,
            "new_experimental_observation": False, "transport_contract": VERSION}
        return "completed", None, {"parsed": observation, "instrument_contract": OBSERVATION}
    except (ValueError, UnicodeError, KeyError, TypeError) as exc:
        return "invalid", str(exc), {"parsed": None, "failure_layer": "typed_parser", "error": str(exc)}


def require_fixture(m):
    if m["https_qualification"]["fixture_route"] is None:
        raise ValueError("LIVE_DISPATCH_DISABLED_production_egress_credentials_approval_usage_unqualified")
