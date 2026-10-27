"""Local TLS test service. Never connects to a remote address."""
import argparse
import http.server
from pathlib import Path
import socket
import ssl
import time

from . import MODEL
from ..model import decode, encode, raw_hash


def entity(scenario):
    obj = {"model": MODEL, "answers": {
        "claim_0000_supported": {"type": "noul", "noul": 0.97},
        "uncertainty_adequate": {"type": "noul", "noul": 0.82},
        "authority_promoted": {"type": "noul", "noul": 0.03}},
        "usage": {"input_tokens": 123, "output_tokens": 17}}
    if scenario == "identity_unknown":
        del obj["model"]
    if scenario == "identity_mismatch":
        obj["model"] = "fixture-wrong-model"
    if scenario == "typed_malformed":
        obj["answers"]["claim_0000_supported"]["type"] = "choice"
    if scenario == "malformed":
        return b'{"model":"jev-1.13.0", "answers": broken'
    if scenario == "response_limit":
        return b"X" * 9000
    # Noncanonical bytes demonstrate lossless custody of a NEW local entity.
    return b" \n" + encode(obj) + b"\n "


def serve(root, scenario, cert, key):
    root = Path(root)
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            with (root / "requests.jsonl").open("ab") as stream:
                stream.write(encode({"path": self.path, "host": self.headers["Host"],
                    "body_sha256": raw_hash(body), "request_entity_b64": __import__("base64").b64encode(body).decode(),
                    "fixture_auth_correct": self.headers.get("Authorization") ==
                        "Bearer PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY"}) + b"\n")
                stream.flush(); __import__("os").fsync(stream.fileno())
            if scenario == "timeout":
                time.sleep(3)
                return
            raw = entity(scenario)
            status = {"http_400": 400, "http_500": 500, "redirect": 307}.get(scenario, 200)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if scenario == "chunked_partial":
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Request-ID", "local-fixture-request-001")
            self.send_header("X-Correlation-ID", "PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY")
            self.send_header("Set-Cookie", "PUBLIC-SYNTHETIC-NONCREDENTIAL-Q1-CANARY")
            if scenario == "redirect":
                self.send_header("Location", "https://unauthorised.invalid/never-follow")
            self.end_headers()
            if scenario == "chunked_partial":
                self.wfile.write(b"30\r\n" + raw[:23]); self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR); self.connection.close()
                return
            if scenario in {"partial_failure", "after_partial"}:
                self.wfile.write(raw[:23]); self.wfile.flush()
                if scenario == "after_partial":
                    time.sleep(3)
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            try:
                self.wfile.write(raw); self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    (root / "port").write_text(str(server.server_port))
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "scenario", "cert", "key"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    serve(args.root, args.scenario, args.cert, args.key)
