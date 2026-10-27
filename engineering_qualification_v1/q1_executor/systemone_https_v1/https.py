"""Single native HTTPS POST, exclusively inside the trusted broker process.

No SDK, proxy discovery, redirect, retry, DNS, telemetry or credential discovery.
Production entry always refuses. The same HTTP/TLS code is exercised locally.
"""
import http.client
import base64
from datetime import datetime, timezone
import os
import signal
import socket
import ssl
import time
from typing import Protocol

from . import VERSION, DESTINATION, MODEL
from .contract import identity, native_request, require_fixture
from .egress import restrict_to_fixture, close_network_creation
from ..model import decode, digest, encode, raw_hash
from ..transport import b64

SAFE_HEADERS = {"content-type", "content-length", "date", "x-request-id", "request-id", "x-correlation-id"}


class BrokerSecret(Protocol):
    """Explicit broker-owned injection; never worker/env/CLI state."""
    def bearer(self) -> str: ...


class FixtureSecret:
    def bearer(self):
        return "PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY"


def destination(value):
    if value != DESTINATION or encode(value) != encode(DESTINATION):
        raise ValueError("https_destination_not_exactly_approved")


class HeaderBound:
    def __init__(self, file, limit):
        self.file, self.limit, self.used, self.headers = file, limit, 0, True

    def readline(self, size=-1):
        if not self.headers:
            return self.file.readline(min(size if size >= 0 else 4096, 4096))
        raw = self.file.readline(min(self.limit - self.used + 1, size if size >= 0 else self.limit + 1))
        self.used += len(raw)
        if self.used > self.limit:
            raise ValueError("response_header_byte_limit")
        # Do not disable the bound on interim responses; these are rejected.
        return raw

    def __getattr__(self, key):
        return getattr(self.file, key)


class BoundedSocket:
    def __init__(self, sock, limit):
        self.sock, self.limit = sock, limit

    def makefile(self, *args, **kwargs):
        return HeaderBound(self.sock.makefile(*args, **kwargs), self.limit)


def dispatch(db, ident, incoming, m, env, rec, *, credential_fd=None, credential_protection=None):
    from ..broker_v1.broker import append
    require_fixture(m)
    from ..live_campaign_v1.contract import is_campaign, CLI_DESTINATION
    campaign = is_campaign(m)
    selected_destination = env["destination"]
    if campaign:
        expected = DESTINATION if env["role"] == "specialist" else CLI_DESTINATION
        if selected_destination != expected:
            raise ValueError("campaign_destination_not_exactly_approved")
        q = m["production_campaign"]
        route = q["fixture_route"] or q["production_route"]
        if env["role"] == "generator" and q["fixture_route"] is None:
            raise ValueError("BLOCKED_subscription_CLI_strict_boundary_not_qualified")
    else:
        destination(selected_destination)
        route = m["https_qualification"]["fixture_route"]
    spec = m["transport"]["specification"]
    sealed = decode(base64.b64decode(incoming["request_b64"], validate=True))
    body = encode(sealed["instrument_request"])
    if (not campaign and body != native_request()) or len(body) > spec["max_request_bytes"]:
        raise ValueError("https_sealed_native_body_or_request_limit")
    expected_model = env["requested_identity"]["model"]
    selected_identity = env["requested_identity"]
    assurance = ("local_TLS_fixture_only_not_genuine_SystemOne" if not campaign or m["simulation_only"]
                 else "TLS_provider_model_self_report_not_serving_attestation")
    jevkey = "credential_binding" in env
    token, token_bytes, guard = None, None, None
    if not jevkey:
        secret_interface: BrokerSecret = FixtureSecret()
        token = secret_interface.bearer()
    elif credential_fd is None or credential_protection != {"dumpable": False, "core_soft": 0, "core_hard": 0}:
        raise ValueError("credential_broker_protection_required")
    metadata = {"contract": env["broker_contract"], "destination": selected_destination, "request_entity_sha256": raw_hash(body),
                "requested_model": sealed["instrument_request"]["model"], "returned_model": None,
                "identity_state": "unknown", "identity_assurance": assurance,
                "http_status": None, "safe_response_headers": [], "provider_request_ids": [], "usage": None,
                "response_complete": False, "response_entity_bytes": 0, "tls": None,
                "egress": None, "client_POSTs": 0, "retries": 0, "request_delivery": "not_started",
                "remote_execution_assurance": "UNKNOWN", "credential_source": "explicit_broker_fixture_interface",
                "started_at": datetime.now(timezone.utc).isoformat()}
    if jevkey:
        from .credential import VERSION as CREDENTIAL_VERSION
        metadata.update(credential_source="JEVKEY_via_single_use_broker_pipe",
            credential={"contract": CREDENTIAL_VERSION, "broker_protection": credential_protection,
                "broker_JEVKEY_environment_absent": "JEVKEY" not in os.environ,
                "broker_environment_minimal": set(os.environ) <= {"LANG", "LC_CTYPE", "PYTHONDONTWRITEBYTECODE"},
                "received_once": False, "descriptor_closed": False})
    rec = dict(rec, stage="dispatch_intent", uncertain_completion=True, https=metadata)
    append(db, ident, rec)  # FULL SQLite commit BEFORE socket creation or TLS.
    if campaign and sealed["preparation_error"] is not None:
        # Consume and preserve this first reservation without a socket, key
        # read or POST. Do not invent a replacement assessment or repair cARL's
        # frozen input contract. Descendants are censored by the same engine.
        rec = dict(rec, stage="terminal_failure", uncertain_completion=False,
                   reason="sealed_input_not_admissible")
        append(db, ident, rec)
        if credential_fd is not None:
            os.close(credential_fd)
        return {"type": "reply", "authorised": True, "record": rec, "raw_b64": ""}
    if env["scenario"] == "after_intent":
        os._exit(73)
    sock = response = None
    raw = bytearray()
    entity_received = 0
    previous_alarm = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError("absolute_deadline")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, env["deadline_seconds"])
    reason = None
    try:
        if env["scenario"] == "credential_child":
            import subprocess
            script = ("import os; from pathlib import Path; "
                      "print('CLEAN' if 'JEVKEY' not in os.environ and "
                      "not any(p.name.isdigit() and int(p.name)>2 and p.exists() "
                      "for p in Path('/proc/self/fd').iterdir()) else 'EXPOSED')")
            child = subprocess.check_output([spec["bindings"]["python"]["path"], "-I", "-S", "-B", "-c", script],
                                            close_fds=True, env={"LANG": "C.UTF-8"})
            if child.strip() != b"CLEAN":
                raise ValueError("credential_child_inheritance_refused")
            metadata["credential"]["child_environment_and_descriptors_clean"] = True
        nft = spec["bindings"]["nft"]
        if raw_hash(__import__("pathlib").Path(nft["path"]).read_bytes()) != nft["sha256"]:
            raise ValueError("BLOCKED_nft_executable_changed")
        metadata["egress"] = restrict_to_fixture(route)
        # Trust only the supplied local CA. Hostname and certificate checks ON.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(cadata=route["ca_pem"])
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(env["deadline_seconds"])
        sock.connect((route["address"], route["port"]))  # exactly one connect; numeric local IP, no DNS.
        close_network_creation(spec["bindings"]["seccomp"]["path"])
        metadata["egress"]["postconnect_seccomp"] = "default_deny_no_socket_connect_exec_namespace"
        # Exercise kernel denial of new network routes in this very broker.
        try:
            probe = socket.socket()
        except PermissionError:
            metadata["egress"]["secondary_socket_denied"] = True
        else:
            probe.close(); raise ValueError("secondary_socket_not_denied")
        sock = context.wrap_socket(sock, server_hostname=selected_destination["host"], suppress_ragged_eofs=False)
        metadata["tls"] = {"certificate_verified": True, "hostname_verified": True,
                           "server_hostname": selected_destination["host"], "version": sock.version(),
                           "peer_certificate_sha256": raw_hash(sock.getpeercert(binary_form=True)),
                           "trust": "explicit_local_fixture_CA" if not campaign or m["simulation_only"] else "explicit_reviewed_production_CA"}
        rec = dict(rec, stage="https_connected", https=metadata)
        append(db, ident, rec)
        if jevkey:
            from .credential import receive, EntityGuard
            fd, credential_fd = credential_fd, None
            token_bytes = receive(fd)
            token = token_bytes.decode("ascii")
            guard = EntityGuard(token_bytes)
            metadata["credential"].update(received_once=True, descriptor_closed=True)
        head = (f"POST {selected_destination['path']} HTTP/1.1\r\nHost: {selected_destination['host']}\r\n"
                f"Content-Type: application/json\r\nAccept: application/json\r\nAccept-Encoding: identity\r\n"
                f"Connection: close\r\nContent-Length: {len(body)}\r\nAuthorization: Bearer {token}\r\n\r\n").encode()
        metadata.update(client_POSTs=1, request_delivery="may_have_reached_server")
        rec = dict(rec, stage="request_write_intent", https=metadata)
        append(db, ident, rec)
        sock.sendall(head + body)  # one POST; no reconnect/retry for partial send.
        del head
        metadata["request_delivery"] = "client_write_completed_remote_execution_unknown"
        rec = dict(rec, stage="request_delivered", https=metadata)
        append(db, ident, rec)
        response = http.client.HTTPResponse(BoundedSocket(sock, spec["max_header_bytes"]), method="POST")
        response.begin()
        response.fp.headers = False
        metadata["http_status"] = response.status
        metadata["safe_response_headers"] = [[k.lower(), v] for k, v in response.getheaders()
            if k.lower() in SAFE_HEADERS and (token not in v if jevkey else "PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY" not in v)]
        metadata["provider_request_ids"] = [[k, v] for k, v in metadata["safe_response_headers"]
                                            if k in {"x-request-id", "request-id", "x-correlation-id"}]
        rec = dict(rec, stage="response_headers", https=metadata)
        append(db, ident, rec)
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("unsupported_response_content_encoding")
        if response.getheader("Transfer-Encoding") not in (None, "chunked"):
            raise ValueError("unsupported_transfer_encoding")
        if response.getheader("Transfer-Encoding") and response.getheader("Content-Length"):
            raise ValueError("ambiguous_response_framing")
        lengths = response.headers.get_all("Content-Length", [])
        if len(lengths) > 1 or lengths and not lengths[0].isdigit():
            raise ValueError("ambiguous_response_framing")
        if not lengths and response.getheader("Transfer-Encoding") != "chunked":
            raise ValueError("unbounded_response_framing")
        while True:
            incomplete = False
            try:
                # Persist each received TLS-sized entity chunk for campaigns;
                # avoid quadratic journal inflation from 1 KiB copies of CLI
                # event envelopes. A short/partial read is still saved at once.
                piece = response.read1(min(16384 if campaign else 1024, env["response_byte_limit"] - len(raw) + 1))
            except http.client.IncompleteRead as exc:
                piece, incomplete = exc.partial, True
            if not piece:
                if incomplete or response.length not in (None, 0):
                    raise ValueError("partial_response_disconnect")
                if guard:
                    tail = guard.feed(b"", final=True)
                    raw.extend(tail)
                    metadata["response_entity_bytes"] = len(raw)
                break
            capacity = env["response_byte_limit"] - entity_received
            overflow = len(piece) > capacity
            piece = piece[:capacity]
            entity_received += len(piece)
            if guard:
                piece = guard.feed(piece)
            raw.extend(piece)
            metadata["response_entity_bytes"] = len(raw)
            rec = dict(rec, stage="partial_response", raw_b64=b64(raw), https=metadata)
            append(db, ident, rec)  # incremental entity custody, no decode/re-encode.
            if env["scenario"] == "after_partial":
                os._exit(74)
            if overflow:
                raise ValueError("response_byte_limit")
            if incomplete:
                raise ValueError("partial_response_disconnect")
        metadata["response_complete"] = True
        try:
            entity = decode(bytes(raw))
            returned = entity.get("model")
            metadata["returned_model"] = returned if isinstance(returned, str) and returned else None
            metadata["usage"] = entity.get("usage")
        except (ValueError, UnicodeError, AttributeError):
            pass
        returned = metadata["returned_model"]
        metadata["identity_state"] = "unknown" if returned is None else "matched" if returned == expected_model else "mismatch"
        if 300 <= response.status < 400:
            raise ValueError("redirect_refused")
        if response.status != 200:
            raise ValueError("http_error")
        observed = dict(selected_identity, model=returned) if returned is not None else None
        rec = dict(rec, stage="complete_response", raw_b64=b64(raw), observed_identity=observed,
                   uncertain_completion=False, https=metadata)
        append(db, ident, rec)
    except TimeoutError:
        reason = "deadline_exceeded"
    except ssl.SSLCertVerificationError:
        reason = "TLS_certificate_or_hostname_verification_failed"
    except (OSError, ValueError, http.client.HTTPException) as exc:
        # Exception strings can contain peer/secret material; never persist them.
        known = {"response_header_byte_limit", "response_byte_limit", "partial_response_disconnect", "redirect_refused",
                 "http_error", "unsupported_response_content_encoding", "unsupported_transfer_encoding", "ambiguous_response_framing", "unbounded_response_framing",
                 "credential_reflection_capture_refused", "credential_child_inheritance_refused",
                 "credential_channel_deadline", "credential_channel_incomplete", "credential_channel_size",
                 "credential_channel_trailing_data", "JEVKEY_invalid_or_out_of_bounds"}
        blockers = {"BLOCKED_exact_kernel_destination_rules_required", "BLOCKED_private_loopback_network_namespace_required",
                    "BLOCKED_nft_executable_changed", "BLOCKED_no_new_privileges", "BLOCKED_capability_drop"}
        reason = str(exc) if type(exc) is ValueError and str(exc) in known | blockers else "transport_or_egress_failure"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_alarm)
        if response is not None:
            response.close()
        if sock is not None:
            sock.close()
        if credential_fd is not None:
            os.close(credential_fd)
        if guard:
            guard.clear()
        if token_bytes is not None:
            token_bytes[:] = b"\x00" * len(token_bytes)
        token = None
    if reason:
        rec = dict(rec, stage="terminal_failure", raw_b64=b64(raw), reason=reason,
                   uncertain_completion=not metadata["response_complete"], https=metadata)
        append(db, ident, rec)
    return {"type": "reply", "authorised": True, "record": rec, "raw_b64": rec["raw_b64"]}
