"""Sealed broker contract layered on the unchanged subprocess bootstrap."""
from pathlib import Path

from . import VERSION, DESTINATION
from .. import transport
from ..model import PACKAGE, digest, raw_hash, encode, decode, read_file

HERE = Path(__file__).resolve().parent
SCENARIOS = {
    "valid", "malformed", "identity_unknown", "identity_mismatch", "partial_failure",
    "timeout", "connection_loss", "duplicate", "before_dispatch", "after_intent",
    "after_acceptance", "executor_interrupt", "tamper", "response_limit",
    "invent_campaign", "invent_attempt", "alter_request", "source_digest", "policy_digest",
    "destination", "model", "role", "no_reservation", "other_response", "worker_tamper",
    "network", "unix_socket", "spawn", "exec", "forbidden_file", "credentials",
    "history", "source_write", "policy_write",
}


def specification():
    spec = transport.specification()
    spec["contract"] = VERSION
    spec["bindings"]["adapter"] = {"path": str(HERE / "worker.py"),
                                    "sha256": raw_hash((HERE / "worker.py").read_bytes())}
    spec["broker_bindings"] = {p.name: raw_hash(p.read_bytes()) for p in sorted(HERE.glob("*.py"))
                               if not p.name.startswith("test_")}
    spec.update(destination=DESTINATION, timeout_seconds=10, provider_deadline_seconds=2,
                max_response_bytes=65536, max_ipc_bytes=1048576,
                communication="supervised-preopened-stdin-stdout-no-new-syscalls")
    return spec


def extension(scenarios=None):
    spec = specification()
    return {"version": VERSION, "specification": spec, "configuration_sha256": digest(spec),
            "scenarios": scenarios or {}}


def validate_extension(m):
    ext = m["transport"]
    expected = specification()
    # Read-only reconstruction may run in a relocated checkout. Executable
    # hashes, runtime and all controls must still match; active creation/launch
    # additionally require the exact current paths.
    for key in ("adapter", "bootstrap"):
        expected["bindings"][key]["path"] = ext["specification"]["bindings"][key]["path"]
    legacy = decode(read_file(PACKAGE, "legacy-broker-specification.v1.json"))
    for key in ("adapter", "bootstrap"):
        legacy["bindings"][key]["path"] = ext["specification"]["bindings"][key]["path"]
    if (set(ext) != {"version", "specification", "configuration_sha256", "scenarios"}
            or ext["version"] != VERSION or ext["specification"] not in (expected, legacy)
            or ext["configuration_sha256"] != digest(ext["specification"])
            or not isinstance(ext["scenarios"], dict)
            or any(k not in {p["id"] for p in m["positions"]} or v not in SCENARIOS
                   for k, v in ext["scenarios"].items())):
        raise ValueError("offline_broker_manifest_binding")


def envelope_for(m, p, sealed):
    # The original bootstrap/filter is reused byte-for-byte. Its v1 request
    # contract remains intact; this explicit extension pins the broker boundary.
    env = transport.base_envelope_for(m, p, sealed)
    adapter_root = Path(m["transport"]["specification"]["bindings"]["adapter"]["path"]).parent
    env.update(broker_contract=VERSION, campaign_id=m["campaign_id"], destination=DESTINATION,
               packet_bindings=p["packet_bindings"], forbidden_probe=str(adapter_root / "host-canary.txt"),
               custody_probe=str(adapter_root.parent / "transport_evidence/demonstration/campaign/campaign.sqlite3"),
               deadline_seconds=m["transport"]["specification"]["provider_deadline_seconds"],
               response_byte_limit=m["transport"]["specification"]["max_response_bytes"])
    if "specialist_observation" in m and p["kind"] == "specialist":
        env["requested_identity"].update(judge="SystemOne", version=m["specialist_observation"]["version"])
    env["idempotency_token"] = digest({"broker": VERSION, "attempt": env["attempt_id"],
                                       "request": env["request_sha256"]})
    return env


def is_broker(m):
    return m.get("transport", {}).get("version") == VERSION


def message(envelope, sealed):
    return {"type": "request", "envelope": envelope, "request_b64": transport.b64(sealed)}


def verify_record(rec, envelope, spec, root, previous):
    if rec["contract"] != VERSION:
        raise ValueError("broker_transport_contract")
    old = dict(previous, contract=transport.VERSION) if previous else None
    transport.base_verify_record(dict(rec, contract=transport.VERSION), envelope, spec, root, old)
