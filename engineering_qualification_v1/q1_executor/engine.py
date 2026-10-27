from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import sqlite3
import sys

from . import VERSION
from .model import (PACKAGE, TERMINAL, FakeProvider, Provider, decode, digest, encode,
                    raw_hash, read_file, request_for, validate_manifest, validate_response)


def now():
    return datetime.now(timezone.utc).isoformat()


def software():
    files = {p.name: raw_hash(p.read_bytes()) for p in sorted(PACKAGE.iterdir())
             if p.suffix in (".py", ".json") and not p.name.startswith("test_")}
    for folder in ("systemone_typed_v1", "systemone_https_v1"):
        typed = PACKAGE / folder
        files.update({p.relative_to(PACKAGE).as_posix(): raw_hash(p.read_bytes())
                      for p in sorted(typed.iterdir()) if p.suffix in (".py", ".json") and not p.name.startswith("test_")})
    return {"files": files, "python_version": sys.version, "sqlite_version": sqlite3.sqlite_version,
            "python_executable_sha256": raw_hash(Path(sys.executable).resolve().read_bytes())}


def historical_software_compatible(m, recorded):
    # Exact historical producer fingerprints, accepted only for fully terminal
    # read-only replay below. Incomplete campaigns cannot inherit new code.
    from .broker_v1.contract import is_broker
    name = ("legacy-software.broker.v1.json" if is_broker(m) else
            "legacy-software.transport.v1.json" if "transport" in m else
            "legacy-software.matrix.v1.json" if "full_matrix" in m else "legacy-software.v1.json")
    legacy = decode(read_file(PACKAGE, name))
    runtime = software()
    choice1 = decode(read_file(PACKAGE, "legacy-software.choice1.v1.json"))
    https = decode(read_file(PACKAGE, "legacy-software.https.v1.json"))
    return (recorded in (legacy, choice1, https)
            and all(recorded[k] == runtime[k] for k in
                    ("python_version", "sqlite_version", "python_executable_sha256")))


@contextmanager
def lock(root, *, readonly=False):
    # No verifier writes, including lock-file creation or SQLite sidecars.
    read_file(root, ".lock")
    with (root / ".lock").open("rb") as stream:
        try:
            fcntl.flock(stream, (fcntl.LOCK_SH if readonly else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("campaign_busy_no_recovery_or_duplicate_worker") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def connect(root, *, readonly=False):
    path = root / "campaign.sqlite3"
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing_or_symlinked_database")
    db = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True,
                         isolation_level=None, timeout=10)
    db.row_factory = sqlite3.Row
    if readonly:
        db.execute("PRAGMA query_only=ON")
    else:
        db.execute("PRAGMA synchronous=FULL")
    return db


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def event(db, kind, ident, data, at=None):
    tail = db.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
    body = {"sequence": tail["seq"] + 1 if tail else 0, "previous_event_sha256": tail["hash"] if tail else None,
            "at": at or now(), "kind": kind, "position": ident, "data": data}
    db.execute("INSERT INTO events VALUES (?,?,?)", (body["sequence"], encode(body), digest(body)))
    return body


def receipts(db):
    return {r["id"]: decode(r["body"]) for r in db.execute("SELECT * FROM receipts")}


def schema_digest(db):
    return digest([list(r) for r in db.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")])


def create(root: Path, fixture: Path = PACKAGE / "fixtures"):
    root = root.absolute()
    manifest, manifest_raw = validate_manifest(fixture)
    if "transport" in manifest:
        from .transport import specification
        from .broker_v1.contract import is_broker, specification as broker_specification
        current = broker_specification() if is_broker(manifest) else specification()
        from .systemone_https_v1.contract import is_https, specification as https_specification, require_fixture
        if is_https(manifest):
            require_fixture(manifest)
            current = https_specification()
        if manifest["transport"]["specification"] != current:
            raise ValueError("historical_transport_configuration_readonly")
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    # A partial initialization is refused on restart; never reset an existing campaign.
    for name in ["manifest.json", *(r["path"] for r in manifest["packets"].values())]:
        if Path(name).name != name:
            raise ValueError("simulation_packets_must_be_flat_files")
        with (root / name).open("xb") as stream:
            stream.write(read_file(fixture, name)); stream.flush(); os.fsync(stream.fileno())
    (root / ".lock").touch(exist_ok=False)
    db = sqlite3.connect(root / "campaign.sqlite3", isolation_level=None)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        db.executescript("""
            CREATE TABLE meta (key TEXT PRIMARY KEY, value BLOB NOT NULL);
            CREATE TABLE positions (id TEXT PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE attempts (id TEXT PRIMARY KEY, request BLOB NOT NULL, cost INTEGER NOT NULL);
            CREATE TABLE invocations (id TEXT PRIMARY KEY, at TEXT NOT NULL, cost INTEGER NOT NULL);
            CREATE TABLE responses (id TEXT PRIMARY KEY, raw BLOB NOT NULL, observed BLOB NOT NULL);
            CREATE TABLE receipts (id TEXT PRIMARY KEY, body BLOB NOT NULL);
            CREATE TABLE events (seq INTEGER PRIMARY KEY, body BLOB NOT NULL, hash TEXT UNIQUE NOT NULL);
        """)
        if "transport" in manifest:
            db.execute("CREATE TABLE transports (id TEXT PRIMARY KEY, envelope BLOB NOT NULL, record BLOB)")
        db.row_factory = sqlite3.Row
        with transaction(db):
            creation = {"manifest_file_sha256": raw_hash(manifest_raw), "manifest_sha256": manifest["manifest_sha256"],
                        "software": software(), "execution_contract": VERSION, "schema_sha256": schema_digest(db)}
            db.execute("INSERT INTO meta VALUES ('creation',?)", (encode(creation),))
            for p in manifest["positions"]:
                db.execute("INSERT INTO positions VALUES (?, 'scheduled')", (p["id"],))
            event(db, "created", None, creation)
    finally:
        db.close()
    for directory in (root, root.parent):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return root


def make_receipt(db, root, m, p, state, reason, at, *, saved=None, times=None):
    ident = p["id"]
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (ident,)).fetchone()
    response = db.execute("SELECT * FROM responses WHERE id=?", (ident,)).fetchone()
    saved = receipts(db) if saved is None else saved
    req = decode(attempt["request"]) if attempt else None
    diag = {"parsed": None, "availability": state}
    transport_record = None
    if "transport" in m:
        row = db.execute("SELECT record FROM transports WHERE id=?", (ident,)).fetchone()
        transport_record = decode(row[0]) if row and row[0] else None
    if state in ("completed", "invalid") or state == "unavailable" and response is not None:
        if "transport" in m:
            from .transport import outcome
            actual_state, actual_reason, diag = outcome(p, req, transport_record)
        else:
            actual_state, actual_reason, diag = validate_response(p, req, response["raw"], decode(response["observed"]))
        if (actual_state, actual_reason) != (state, reason):
            raise ValueError("terminal_validation_contradiction")
    disposition = diag["parsed"]["disposition"] if state == "completed" and p["kind"] == "generator" else None
    previous = req["previous_assessment"]["disposition"] if req and req["previous_assessment"] else None
    baseline = next((saved[q["id"]]["disposition"] for q in m["positions"]
                     if q["arm"] == "B0" and q["id"] in saved and saved[q["id"]]["state"] == "completed"
                     and ("full_matrix" not in m or q["unit_id"] == p["unit_id"])), None)
    if p["arm"] == "B0" and disposition is not None:
        baseline = disposition
    if times is None:
        observed_events = [decode(r["body"]) for r in db.execute("SELECT body FROM events ORDER BY seq")]
        times = {e["kind"]: e["at"] for e in observed_events if e["position"] == ident}
    receipt = {"schema": VERSION + "-receipt", "position": ident, "manifest_sha256": m["manifest_sha256"],
            "packet_bindings": p["packet_bindings"], "requested_identity": p["identity"],
            "observed_identity": decode(response["observed"]) if response else None,
            "parents": {d: digest(saved[d]) for d in p["dependencies"]},
            "state": state, "reason": reason, "diagnostics": diag, "disposition": disposition,
            "preceding_disposition_pair": [previous, disposition] if previous is not None and disposition is not None else None,
            "baseline_disposition_pair": [baseline, disposition] if baseline is not None and disposition is not None else None,
            "request_sha256": raw_hash(attempt["request"]) if attempt else None,
            "response_sha256": raw_hash(response["raw"]) if response else None,
            "reserved_at": times.get("reserved"), "started_at": times.get("started"), "outcome_at": at,
            "simulated_reserved_units": attempt["cost"] if attempt else 0,
            "live_execution_authorized": False}
    if "transport" in m:
        receipt.update(schema=m["transport"]["version"] + "-receipt", transport_record_sha256=(
            digest(transport_record) if transport_record is not None else None))
    from .broker_v1.contract import is_broker
    if is_broker(m):
        from .broker_v1.broker import receipt_binding
        receipt.update(receipt_binding(db, ident))
    if "specialist_observation" in m and p["kind"] == "specialist":
        receipt.update(schema=m["specialist_observation"]["version"] + "-receipt",
                       instrument_contract=m["specialist_observation"]["version"],
                       transport_contract=m["transport"]["version"])
    return decode(encode(receipt))


def finish(db, root, m, p, state, reason):
    ident, at = p["id"], now()
    receipt = make_receipt(db, root, m, p, state, reason, at)
    db.execute("INSERT INTO receipts VALUES (?,?)", (ident, encode(receipt)))
    db.execute("UPDATE positions SET state=? WHERE id=?", (state, ident))
    event(db, "outcome", ident, {"state": state, "reason": reason, "receipt_sha256": digest(receipt)}, at)


def reserve(db, root, m, p):
    """Transaction + unique primary key; never calls a provider or retries."""
    with transaction(db):
        # Recheck the full manifest, packets and parent evidence at the reservation boundary.
        if verify_database(db, root)["manifest"] != m:
            raise ValueError("manifest_changed_before_reservation")
        if db.execute("SELECT state FROM positions WHERE id=?", (p["id"],)).fetchone()["state"] != "scheduled":
            return False
        saved = receipts(db)
        if any(d not in saved or saved[d]["state"] != "completed" for d in p["dependencies"]):
            raise ValueError("unverified_or_unsuccessful_parent")
        used, cost = db.execute("SELECT count(*),coalesce(sum(cost),0) FROM attempts").fetchone()
        if used >= m["attempt_ceiling"] or cost + 1 > m["simulated_budget_units"]:
            return False
        req = request_for(m, p, saved, root)
        db.execute("INSERT INTO attempts VALUES (?,?,1)", (p["id"], encode(req)))
        event(db, "reserved", p["id"], {"request_sha256": digest(req), "cost": 1, "parents": req["parents"]})
        db.execute("UPDATE positions SET state='reserved' WHERE id=?", (p["id"],))
        if "transport" in m:
            from .transport import envelope_for
            envelope = envelope_for(m, p, encode(req))
            db.execute("INSERT INTO transports VALUES (?,?,NULL)", (p["id"], encode(envelope)))
            event(db, "transport_prepared", p["id"], {"envelope_sha256": digest(envelope)})
    return True


def execute_transport(db, root, m, p, req, interrupt_position):
    from .transport import OfflineSubprocessTransport, decode as transport_decode, outcome, unb64
    row = db.execute("SELECT envelope,record FROM transports WHERE id=?", (p["id"],)).fetchone()
    if row[1] is not None or db.execute("SELECT state FROM positions WHERE id=?", (p["id"],)).fetchone()[0] != "started":
        raise ValueError("duplicate_transport_launch_refused")
    envelope = transport_decode(row[0])
    workspace = root / ".transport-work" / envelope["attempt_id"]
    def persist(record):
        with transaction(db):
            old = db.execute("SELECT record FROM transports WHERE id=?", (p["id"],)).fetchone()[0]
            if record["status"] == "launch_intent":
                if old is not None:
                    raise ValueError("duplicate_transport_launch_refused")
                at = record["launch_intent_at"]
                db.execute("INSERT INTO invocations VALUES (?,?,1)", (p["id"], at))
                event(db, "transport_invoked", p["id"], {"cost": 1}, at)
            elif old is None:
                raise ValueError("transport_progress_without_launch_intent")
            db.execute("UPDATE transports SET record=? WHERE id=?", (encode(record), p["id"]))
            event(db, "transport_progress", p["id"], record)
        if (interrupt_position == p["id"] and record["status"] == "running"
                and unb64(record["stdout_b64"]) and unb64(record["stderr_b64"])):
            # Abrupt executor death while the adapter is still running. bwrap's
            # die-with-parent and PID namespace tear down the execution context.
            os._exit(75)
    sealed = db.execute("SELECT request FROM attempts WHERE id=?", (p["id"],)).fetchone()[0]
    from .broker_v1.contract import is_broker
    if is_broker(m):
        from .broker_v1.runtime import BrokerTransport
        implementation = BrokerTransport(m["transport"]["specification"], root, p["id"])
    else:
        implementation = OfflineSubprocessTransport(m["transport"]["specification"])
    result = implementation.invoke(envelope, sealed, workspace, persist)
    with transaction(db):
        db.execute("INSERT INTO responses VALUES (?,?,?)", (p["id"], result.raw, encode(result.observed)))
        event(db, "response", p["id"], {"raw_sha256": raw_hash(result.raw), "observed_identity": result.observed})
    state, reason, _ = outcome(p, req, result.record)
    with transaction(db):
        finish(db, root, m, p, state, reason)
    if workspace.parent.exists() and not any(workspace.parent.iterdir()):
        workspace.parent.rmdir()


def recover_transport(db, root, m, p):
    import shutil
    from .broker_v1.contract import is_broker
    if is_broker(m):
        from .broker_v1.broker import reconcile
        reconcile(db, root, m, p)
    from .transport import now as transport_now
    row = db.execute("SELECT * FROM transports WHERE id=?", (p["id"],)).fetchone()
    if row is None:
        raise ValueError("missing_reserved_transport_envelope")
    envelope = decode(row["envelope"])
    workspace = root / ".transport-work" / envelope["attempt_id"]
    if row["record"] is not None:
        record = decode(row["record"])
        if record["status"] in ("launch_intent", "running"):
            # No signal to a saved PID: PID reuse cannot kill an unrelated task.
            # The namespace supervisor is bound to the dead executor by the OS.
            record.update(status="interrupted", uncertain_completion=True, ended_at=transport_now(), cleanup=True)
            with transaction(db):
                db.execute("UPDATE transports SET record=? WHERE id=?", (encode(record), p["id"]))
                event(db, "transport_progress", p["id"], record)
    if workspace.is_symlink() or workspace.parent.is_symlink():
        raise ValueError("unsafe_transport_cleanup_path")
    if workspace.exists():
        shutil.rmtree(workspace)
    if workspace.parent.exists() and not any(workspace.parent.iterdir()):
        workspace.parent.rmdir()


def resume(root: Path, provider: Provider | None = None, *, interrupt_after_reservation=None,
           offline_subprocess=False, interrupt_after_transport_start=None):
    root = root.absolute()
    provider = FakeProvider() if provider is None else provider
    if type(provider) is not FakeProvider:
        raise ValueError("only_the_local_fake_provider_is_permitted")
    with lock(root):
        db = connect(root)
        try:
            m = verify_database(db, root)["manifest"]
            if ("transport" in m) != offline_subprocess:
                raise ValueError("explicit_offline_subprocess_selection_required_for_transport_manifest")
            for p in m["positions"]:
                state = db.execute("SELECT state FROM positions WHERE id=?", (p["id"],)).fetchone()["state"]
                if state in TERMINAL:
                    continue
                if state in ("reserved", "started"):
                    if "transport" in m:
                        recover_transport(db, root, m, p)
                    with transaction(db):
                        finish(db, root, m, p, "interrupted", "abandoned_reservation_no_reissue")
                    continue
                saved = receipts(db)
                if any(saved[d]["state"] != "completed" for d in p["dependencies"]):
                    with transaction(db):
                        finish(db, root, m, p, "blocked", "unsuccessful_parent")
                    continue
                if not reserve(db, root, m, p):
                    with transaction(db):
                        finish(db, root, m, p, "unavailable", "simulated_budget_exhausted")
                    continue
                if interrupt_after_reservation == p["id"]:
                    # Real process termination: SQLite reservation already committed and fsynced.
                    os._exit(75)
                with transaction(db):
                    db.execute("UPDATE positions SET state='started' WHERE id=?", (p["id"],))
                    event(db, "started", p["id"], {})
                req = decode(db.execute("SELECT request FROM attempts WHERE id=?", (p["id"],)).fetchone()[0])
                if "transport" in m:
                    execute_transport(db, root, m, p, req, interrupt_after_transport_start)
                    continue
                def record_invocation():
                    with transaction(db):
                        at = now()
                        db.execute("INSERT INTO invocations VALUES (?,?,1)", (p["id"], at))
                        event(db, "fake_invoked", p["id"], {"cost": 1}, at)
                try:
                    # The provider owns its request copy. Validation uses the
                    # persisted canonical request, never provider-mutated context.
                    raw, observed = provider.invoke(decode(encode(req)), record_invocation)
                except RuntimeError:
                    with transaction(db):
                        finish(db, root, m, p, "unavailable", "fake_provider_exception_before_response")
                    continue
                with transaction(db):
                    db.execute("INSERT INTO responses VALUES (?,?,?)", (p["id"], raw, encode(observed)))
                    event(db, "response", p["id"], {"raw_sha256": raw_hash(raw), "observed_identity": observed})
                state, reason, _ = validate_response(p, req, raw, observed)
                with transaction(db):
                    finish(db, root, m, p, state, reason)
            return verify_database(db, root)["summary"]
        finally:
            db.close()


def verify_database(db, root):
    """Reconstruct the append-only history, then check every materialized projection."""
    m, raw_manifest = validate_manifest(root)
    if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("sqlite_integrity_failure")
    meta = list(db.execute("SELECT * FROM meta"))
    if len(meta) != 1 or meta[0]["key"] != "creation":
        raise ValueError("creation_record_missing_or_extra")
    creation = decode(meta[0]["value"])
    expected_creation = {"manifest_file_sha256": raw_hash(raw_manifest), "manifest_sha256": m["manifest_sha256"],
                         "software": software(), "execution_contract": VERSION, "schema_sha256": schema_digest(db)}
    if (historical_software_compatible(m, creation.get("software"))
            and all(r[0] in TERMINAL for r in db.execute("SELECT state FROM positions"))):
        expected_creation["software"] = creation["software"]
    if creation != expected_creation or meta[0]["value"] != encode(creation):
        raise ValueError("manifest_or_software_binding_changed")
    positions = {p["id"]: p for p in m["positions"]}
    states = {ident: "scheduled" for ident in positions}
    attempts = {r["id"]: r for r in db.execute("SELECT * FROM attempts")}
    invoked = {r["id"]: r for r in db.execute("SELECT * FROM invocations")}
    responses = {r["id"]: r for r in db.execute("SELECT * FROM responses")}
    saved = receipts(db)
    transport_rows = {r["id"]: r for r in db.execute("SELECT * FROM transports")} if "transport" in m else {}
    prepared_seen, progress = set(), {}
    reserved_seen, started_seen, invoked_seen, response_seen, finished_seen = set(), set(), set(), set(), set()
    tip = None
    event_rows = list(db.execute("SELECT * FROM events ORDER BY seq"))
    # Reuse decoded audit projections only within this verification boundary.
    # Every boundary still rereads all persisted bytes and replays every event.
    decoded_events = [decode(row["body"]) for row in event_rows]
    times_by_id = {ident: {} for ident in positions}
    for e in decoded_events:
        if e["position"] in times_by_id:
            times_by_id[e["position"]][e["kind"]] = e["at"]
    last_time = None
    for index, row in enumerate(event_rows):
        e = decoded_events[index]
        if (set(e) != {"sequence", "previous_event_sha256", "at", "kind", "position", "data"}
                or e["sequence"] != index or row["seq"] != index or e["previous_event_sha256"] != tip
                or row["hash"] != digest(e) or row["body"] != encode(e)):
            raise ValueError("event_hash_chain_changed")
        at = datetime.fromisoformat(e["at"])
        if at.tzinfo is None or last_time is not None and at < last_time:
            raise ValueError("event_timestamp_order")
        last_time, tip = at, row["hash"]
        kind, ident, data = e["kind"], e["position"], e["data"]
        if index == 0:
            if (kind, ident, data) != ("created", None, creation):
                raise ValueError("creation_event_mismatch")
            continue
        if ident not in positions:
            raise ValueError("unknown_journal_position")
        p, state = positions[ident], states[ident]
        if kind == "reserved":
            if state != "scheduled" or ident in reserved_seen or any(states[d] != "completed" for d in p["dependencies"]):
                raise ValueError("duplicate_reservation_or_unsuccessful_parent")
            a = attempts[ident]
            expected_request = request_for(m, p, saved, root)
            if (decode(a["request"]) != expected_request or a["cost"] != 1
                    or data != {"request_sha256": raw_hash(a["request"]), "cost": 1, "parents": expected_request["parents"]}):
                raise ValueError("request_policy_source_or_parent_binding_changed")
            reserved_seen.add(ident); states[ident] = "reserved"
        elif kind == "started":
            if state != "reserved" or data != {}:
                raise ValueError("invalid_start")
            started_seen.add(ident); states[ident] = "started"
        elif kind in ("fake_invoked", "transport_invoked"):
            if (kind == "transport_invoked") != ("transport" in m):
                raise ValueError("invocation_transport_kind_changed")
            if state != "started" or ident in invoked_seen or data != {"cost": 1}:
                raise ValueError("duplicate_or_invalid_fake_invocation")
            if dict(invoked[ident]) != {"id": ident, "at": e["at"], "cost": 1}:
                raise ValueError("invocation_trace_changed")
            invoked_seen.add(ident)
        elif kind == "transport_prepared" and "transport" in m:
            from .transport import envelope_for
            envelope = envelope_for(m, p, attempts[ident]["request"])
            if (state != "reserved" or ident in prepared_seen
                    or decode(transport_rows[ident]["envelope"]) != envelope
                    or transport_rows[ident]["envelope"] != encode(envelope)
                    or data != {"envelope_sha256": digest(envelope)}):
                raise ValueError("transport_envelope_binding_changed")
            prepared_seen.add(ident)
        elif kind == "transport_progress" and "transport" in m:
            from .transport import verify_record
            if state != "started" or ident not in invoked_seen or ident not in prepared_seen:
                raise ValueError("transport_progress_without_reserved_invocation")
            verify_record(data, decode(transport_rows[ident]["envelope"]), m["transport"]["specification"],
                          root, progress.get(ident))
            progress[ident] = data
        elif kind in ("broker_event", "broker_rejected"):
            from .broker_v1.contract import is_broker
            if not is_broker(m):
                raise ValueError("broker_event_without_broker_contract")
            if kind == "broker_event" and (state != "started" or ident not in invoked_seen):
                raise ValueError("broker_event_without_reserved_worker")
            # Full broker state/authorisation replay follows this engine replay.
        elif kind == "response":
            r = responses[ident]
            if (state != "started" or ident not in invoked_seen or ident in response_seen
                    or data != {"raw_sha256": raw_hash(r["raw"]), "observed_identity": decode(r["observed"])}
                    or r["observed"] != encode(decode(r["observed"]))):
                raise ValueError("raw_response_or_identity_changed")
            response_seen.add(ident)
        elif kind == "outcome":
            target, reason = data["state"], data["reason"]
            failed = any(states[d] != "completed" for d in p["dependencies"])
            if target not in TERMINAL or state in TERMINAL or ident in finished_seen:
                raise ValueError("nonmonotonic_or_duplicate_outcome")
            if target == "blocked":
                valid = state == "scheduled" and failed and reason == "unsuccessful_parent"
            elif target == "interrupted":
                valid = state in ("reserved", "started") and reason == "abandoned_reservation_no_reissue"
            elif state == "scheduled":
                valid = (target == "unavailable" and not failed and reason == "simulated_budget_exhausted"
                         and (len(reserved_seen) >= m["attempt_ceiling"] or len(reserved_seen) >= m["simulated_budget_units"]))
            elif target == "unavailable" and ident not in response_seen:
                valid = state == "started" and ident in invoked_seen and reason == "fake_provider_exception_before_response"
            else:
                valid = state == "started" and ident in response_seen
            if not valid:
                raise ValueError("contradictory_terminal_state")
            expected = make_receipt(db, root, m, p, target, reason, e["at"], saved=saved, times=times_by_id[ident])
            stored = db.execute("SELECT body FROM receipts WHERE id=?", (ident,)).fetchone()[0]
            if (saved[ident] != expected or stored != encode(expected)
                    or data != {"state": target, "reason": reason, "receipt_sha256": digest(expected)}):
                raise ValueError("receipt_or_diagnostics_changed")
            finished_seen.add(ident); states[ident] = target
        else:
            raise ValueError("unknown_journal_event")
    if not event_rows:
        raise ValueError("missing_journal")
    if "transport" in m:
        from .transport import unb64
        if set(transport_rows) != reserved_seen or prepared_seen != reserved_seen or set(progress) != invoked_seen:
            raise ValueError("transport_projection_coverage")
        for ident, row in transport_rows.items():
            expected = encode(progress[ident]) if ident in progress else None
            if row["record"] != expected:
                raise ValueError("transport_record_projection_changed")
            if ident in responses and (responses[ident]["raw"] != unb64(progress[ident]["stdout_b64"])
                                       or decode(responses[ident]["observed"]) != progress[ident]["observed_identity"]):
                raise ValueError("transport_raw_or_identity_projection_changed")
    if (set(attempts) != reserved_seen or set(invoked) != invoked_seen or set(responses) != response_seen
            or set(saved) != finished_seen or dict(db.execute("SELECT id,state FROM positions")) != states):
        raise ValueError("missing_extra_or_changed_materialized_evidence")
    reserved_cost = sum(r["cost"] for r in attempts.values())
    if len(attempts) > m["attempt_ceiling"] or reserved_cost > m["simulated_budget_units"]:
        raise ValueError("attempt_or_budget_ceiling_exceeded")
    summary = {"campaign_id": m["campaign_id"], "scheduled_positions": len(positions),
               "states": dict(sorted(Counter(states.values()).items())), "fake_provider_invocations": len(invoked),
               "attempt_reservations": len(attempts), "simulated_reserved_units": reserved_cost,
               "simulated_expenditure_units": sum(r["cost"] for r in invoked.values()),
               "remaining_simulated_budget": m["simulated_budget_units"] - reserved_cost,
               "manifest_sha256": m["manifest_sha256"], "evidence_tip_sha256": tip,
               "journal_events": len(event_rows), "verification": "PASS", "real_provider_calls": 0,
               "all_positions_terminal": all(s in TERMINAL for s in states.values()), "live_execution_authorized": False}
    if "transport" in m:
        summary.update(fake_provider_invocations=0, subprocess_transport_launch_intents=len(invoked),
                       subprocess_bootstraps_verified=sum(r["bootstrap_verified"] for r in progress.values()),
                       transport_contract=m["transport"]["version"])
    from .broker_v1.contract import is_broker
    if is_broker(m):
        from .broker_v1.broker import audit
        summary.update(audit(db, m))
    return {"manifest": m, "summary": summary, "history": [decode(r["body"]) for r in event_rows], "receipts": saved}


def verify(root: Path):
    root = root.absolute()
    with lock(root, readonly=True):
        db = connect(root, readonly=True)
        try:
            db.execute("BEGIN")
            return verify_database(db, root)
        finally:
            db.close()
