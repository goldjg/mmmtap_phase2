"""Local TLS peer for the real campaign engine; never a provider client."""
import argparse
import base64
import http.server
import os
from pathlib import Path
import ssl
import time

from .. import engine
from ..model import decode, encode, raw_hash
from .routing import fixture_cli_entity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--expected-dummy-fd", type=int, required=True)
    args = parser.parse_args()
    dummy = os.read(args.expected_dummy_fd, 4096).decode()
    os.close(args.expected_dummy_fd)
    seen = set()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *unused):
            pass

        def do_POST(self):
            try:
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                db = engine.connect(args.root / "campaign", readonly=True)
                try:
                    rows = db.execute("SELECT a.id,a.request FROM attempts a JOIN positions p ON a.id=p.id WHERE p.state='started'").fetchall()
                finally:
                    db.close()
                assert len(rows) == 1
                ident, sealed = rows[0]
                req = decode(sealed); p = req["position"]
                assert raw == encode(req["instrument_request"])
                assert ident not in seen
                seen.add(ident)
                specialist = p["kind"] == "specialist"
                correct_path = "/v1/systemone" if specialist else "/q1-fixture/cli-events"
                assert self.path == correct_path
                bearer_ok = self.headers.get("Authorization") == "Bearer " + (
                    dummy if specialist else "PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY")
                assert bearer_ok
                if specialist:
                    state = decode(req["instrument_request"]["state"])
                    assert state["untrusted_source"] == req["source_text"]
                    assert state["assessment"] == req["previous_assessment"]
                m = decode((args.root / "campaign/manifest.json").read_bytes())
                scenario = m["transport"]["scenarios"].get(ident, "valid")
                record = {"position": ident, "route": p["route"], "method": "POST", "path": self.path,
                    "request_entity_sha256": raw_hash(raw), "request_bytes": len(raw), "bearer_correct": bearer_ok,
                    "credential_recorded": False, "requested_model": p["identity"]["model"],
                    "source_bound": True, "policy_bound": req["governing_policy"] is not None,
                    "controls_without_challenge_policy": not p["arm"].startswith("C") or req["challenge_policy"] is None,
                    "scenario": scenario}
                with (args.root / "posts.jsonl").open("ab") as stream:
                    stream.write(encode(record) + b"\n"); stream.flush(); os.fsync(stream.fileno())
                if specialist:
                    entity = {"model": p["identity"]["model"], "answers": {key: {"type": "noul", "noul":
                        0.2 if key == "authority_promoted" else 0.4 if p["route"] == "carl" and p["arm"].startswith("E3")
                        else 0.6} for key in req["instrument_request"]["questions"]},
                        "usage": {"input_tokens": 101, "output_tokens": 37}}
                else:
                    entity = fixture_cli_entity(req["instrument_request"], scenario)
                if scenario == "identity_unknown":
                    entity.pop("model")
                if scenario == "identity_mismatch":
                    entity["model"] = "unapproved-substitute"
                body = encode(entity)
                status = 500 if scenario == "http_500" else 200
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Request-ID", "local-" + ident)
                self.end_headers()
                if scenario == "jev_interrupt":
                    self.wfile.write(body[:53]); self.wfile.flush(); time.sleep(1.2)
                    return
                self.wfile.write(body); self.wfile.flush()
            except (BrokenPipeError, ConnectionError):
                pass

    server = http.server.HTTPServer(("192.0.2.2", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    (args.root / "port").write_text(str(server.server_port))
    server.serve_forever()


if __name__ == "__main__":
    main()
