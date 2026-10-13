"""Loopback-only mock model provider for offline isolation negative controls.

Runs inside the same network-less namespace as the CLI under test. Every
response is labelled as a mock; nothing here is model output or provider
evidence. It records each request so advertised tools, injected instructions
and client retries can be observed without any external network access.
"""
from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import threading
import time

MOCK_MARKER = "MMMTAP_LOOPBACK_MOCK_NOT_MODEL_OUTPUT"
SCENARIOS = ("text", "tool_call", "forced_tool_call", "http_500", "http_429", "malformed", "disconnect")


class Recorder:
    def __init__(self, path: Path, scenario: str, text: str, target: str = "/nonexistent/SECRET.txt",
                 write_target: str = "/nonexistent/written", forced: dict | None = None) -> None:
        if scenario not in SCENARIOS:
            raise ValueError("unknown scenario")
        self.path, self.scenario, self.text = path, scenario, text
        self.target, self.write_target = target, write_target
        self.forced = forced  # explicit tool call for forced_tool_call negative controls
        self.lock = threading.Lock()
        self.count = 0

    def record(self, entry: dict) -> int:
        with self.lock:
            self.count += 1
            entry = {**entry, "sequence": self.count, "monotonic": time.monotonic()}
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
            return self.count


def _sse(events: list[tuple[str | None, dict | str]]) -> bytes:
    out = []
    for name, data in events:
        if name:
            out.append("event: " + name)
        out.append("data: " + (data if isinstance(data, str) else json.dumps(data)))
        out.append("")
    return ("\n".join(out) + "\n").encode()


def anthropic_reply(model: str, text: str | None, tool: dict | None, stream: bool) -> tuple[str, bytes]:
    block = ({"type": "tool_use", "id": "toolu_mock_1", "name": tool["name"], "input": tool["input"]}
             if tool else {"type": "text", "text": text})
    stop = "tool_use" if tool else "end_turn"
    message = {"id": "msg_" + MOCK_MARKER, "type": "message", "role": "assistant", "model": model,
               "content": [block], "stop_reason": stop, "stop_sequence": None,
               "usage": {"input_tokens": 1, "output_tokens": 1}}
    if not stream:
        return "application/json", json.dumps(message).encode()
    start = {**message, "content": [], "stop_reason": None}
    events = [("message_start", {"type": "message_start", "message": start})]
    if tool:
        events += [("content_block_start", {"type": "content_block_start", "index": 0,
                                             "content_block": {**block, "input": {}}}),
                   ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                             "delta": {"type": "input_json_delta",
                                                       "partial_json": json.dumps(tool["input"])}})]
    else:
        events += [("content_block_start", {"type": "content_block_start", "index": 0,
                                             "content_block": {"type": "text", "text": ""}}),
                   ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                             "delta": {"type": "text_delta", "text": text}})]
    events += [("content_block_stop", {"type": "content_block_stop", "index": 0}),
               ("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None},
                                  "usage": {"output_tokens": 1}}),
               ("message_stop", {"type": "message_stop"})]
    return "text/event-stream", _sse(events)


def chat_reply(model: str, text: str | None, tool: dict | None, stream: bool) -> tuple[str, bytes]:
    call = {"id": "call_mock_1", "type": "function",
            "function": {"name": tool["name"], "arguments": json.dumps(tool["input"])}} if tool else None
    message = {"role": "assistant", "content": None if tool else text}
    if call:
        message["tool_calls"] = [call]
    finish = "tool_calls" if tool else "stop"
    body = {"id": "chatcmpl-" + MOCK_MARKER, "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
    if not stream:
        return "application/json", json.dumps(body).encode()
    delta = {"role": "assistant"}
    if call:
        delta["tool_calls"] = [{"index": 0, **call}]
    else:
        delta["content"] = text
    chunks = [{"id": body["id"], "object": "chat.completion.chunk", "created": 0, "model": model,
               "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
              {"id": body["id"], "object": "chat.completion.chunk", "created": 0, "model": model,
               "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
               "usage": body["usage"]}]
    return "text/event-stream", _sse([(None, c) for c in chunks] + [(None, "[DONE]")])


def responses_reply(model: str, text: str | None, tool: dict | None, stream: bool) -> tuple[str, bytes]:
    if tool and tool.get("custom"):
        item = {"type": "custom_tool_call", "id": "ctc_mock_1", "call_id": "call_mock_1", "name": tool["name"],
                "input": tool["input"], "status": "completed"}
    elif tool:
        item = {"type": "function_call", "id": "fc_mock_1", "call_id": "call_mock_1", "name": tool["name"],
                "arguments": json.dumps(tool["input"]), "status": "completed"}
        if tool.get("namespace"):
            item["namespace"] = tool["namespace"]
    else:
        item = {"type": "message", "id": "msg_mock_1", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}]}
    response = {"id": "resp_" + MOCK_MARKER, "object": "response", "created_at": 0, "model": model,
                "status": "completed", "output": [item],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                          "input_tokens_details": {"cached_tokens": 0},
                          "output_tokens_details": {"reasoning_tokens": 0}}}
    if not stream:
        return "application/json", json.dumps(response).encode()
    events = [("response.created", {"type": "response.created", "response": {**response, "status": "in_progress", "output": []}}),
              ("response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": item}),
              ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": item}),
              ("response.completed", {"type": "response.completed", "response": response})]
    return "text/event-stream", _sse(events)


def _walk_tools(tools: list, prefix: str = "") -> list[str]:
    names = []
    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name") or (tool.get("function") or {}).get("name") or tool.get("type") or "?"
        if isinstance(tool.get("tools"), list):  # namespace container
            names += _walk_tools(tool["tools"], prefix + name + ".")
        else:
            names.append(prefix + name)
    return names


def advertised_tools(body: dict | None) -> list[str]:
    """All tool names offered to the model, including Responses ``additional_tools`` input items."""
    if not isinstance(body, dict):
        return []
    names = _walk_tools(body.get("tools") or [])
    for item in body.get("input") or []:
        if isinstance(item, dict) and item.get("type") == "additional_tools":
            names += _walk_tools(item.get("tools") or [])
    return names


def tool_for(body: dict, flavour: str, recorder: Recorder) -> dict | None:
    """Pick an advertised tool able to read the sentinel, if any is advertised."""
    if recorder.scenario == "forced_tool_call" and recorder.forced:
        return dict(recorder.forced)
    names = {n.rsplit(".", 1)[-1] for n in advertised_tools(body)}
    target = {"path": recorder.target,
              "command": "cat %s; /usr/bin/printenv COPILOT_PROVIDER_API_KEY MMMTAP_PROVIDER_KEY; echo probe > %s" %
              (recorder.target, recorder.write_target)}
    for name, args in (("bash", {"command": target["command"], "description": "probe"}),
                       ("shell", {"command": ["bash", "-lc", target["command"]]}),
                       ("exec_command", {"cmd": target["command"]}),
                       ("view", {"path": target["path"]}),
                       ("read_file", {"path": target["path"]})):
        if name in names:
            return {"name": name, "input": args}
    code = ("const r = await tools.exec_command({cmd: %s}); text(JSON.stringify(r));"
            % json.dumps(target["command"]))
    if flavour == "responses" and "exec" in names:
        return {"name": "exec", "custom": True, "input": code}
    if recorder.scenario == "forced_tool_call":
        # Unadvertised (or advertised-but-disabled) call: does the client execute it anyway?
        if flavour == "responses":
            return {"name": "exec", "custom": True, "input": code}
        return {"name": "bash", "input": {"command": target["command"], "description": "probe"}}
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    recorder: Recorder

    def log_message(self, *args) -> None:  # silence stderr noise
        return

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def _send(self, status: int, ctype: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Mock-Provider", MOCK_MARKER)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self.recorder.record({"method": "GET", "path": self.path, "headers": redact(dict(self.headers))})
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, "application/json", json.dumps({"object": "list", "data": []}).encode())
        else:
            self._send(404, "application/json", b'{"error":"mock_not_found"}')

    def do_POST(self) -> None:
        raw = self._body()
        try:
            body = json.loads(raw)
        except ValueError:
            body = None
        flavour = ("anthropic" if self.path.endswith("/messages") else
                   "responses" if self.path.endswith("/responses") else "chat")
        tools = advertised_tools(body)
        sequence = self.recorder.record({"method": "POST", "path": self.path, "flavour": flavour,
                                         "headers": redact(dict(self.headers)), "body": body,
                                         "body_bytes": len(raw), "tool_count": len(tools),
                                         "advertised_tools": tools})
        scenario = self.recorder.scenario
        if scenario == "http_500":
            return self._send(500, "application/json", b'{"error":{"message":"mock_internal_error"}}')
        if scenario == "http_429":
            return self._send(429, "application/json", b'{"error":{"message":"mock_rate_limited"}}')
        if scenario == "malformed":
            return self._send(200, "application/json", b'{"not": "a provider response"')
        if scenario == "disconnect":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        model = (body or {}).get("model") or "mock-model"
        stream = bool((body or {}).get("stream"))
        tool = tool_for(body or {}, flavour, self.recorder) if scenario in ("tool_call", "forced_tool_call") and \
            sequence_has_no_tool_result(body) else None
        reply = {"anthropic": anthropic_reply, "chat": chat_reply, "responses": responses_reply}[flavour]
        ctype, payload = reply(model, self.recorder.text, tool, stream)
        self._send(200, ctype, payload)


def sequence_has_no_tool_result(body: dict | None) -> bool:
    """Structural check (instruction text may legitimately mention these type names)."""
    body = body if isinstance(body, dict) else {}
    for item in body.get("input") or []:
        if isinstance(item, dict) and item.get("type") in ("function_call_output", "custom_tool_call_output"):
            return False
    for message in body.get("messages") or []:
        if not isinstance(message, dict):
            continue
        if message.get("role") == "tool":
            return False
        content = message.get("content")
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                             for b in content):
            return False
    return True


SENSITIVE = ("authorization", "x-api-key", "api-key", "cookie", "openai-organization", "chatgpt-account-id")


def redact(headers: dict) -> dict:
    return {k: ("[REDACTED]" if k.lower() in SENSITIVE else v) for k, v in headers.items()}


def serve(recorder: Recorder) -> http.server.ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"recorder": recorder})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main(argv: list[str]) -> int:
    """Inside the sandbox: python3 -m ... SPEC_JSON_PATH; runs the CLI against the mock."""
    spec = json.loads(Path(argv[0]).read_text())
    out = Path(spec["capture_dir"])
    recorder = Recorder(out / "requests.jsonl", spec["scenario"], spec["text"],
                        spec.get("tool_target", "/nonexistent/SECRET.txt"),
                        spec.get("write_target", "/nonexistent/written"), spec.get("forced_tool"))
    server = serve(recorder)
    base = "http://127.0.0.1:%d" % server.server_address[1]
    env = {k: v.replace("{BASE}", base) for k, v in spec["env"].items()}
    argv_cli = [a.replace("{BASE}", base) for a in spec["argv"]]
    started = time.monotonic()
    from isolation import stream_run, WATCHDOGS
    watchdog = WATCHDOGS[spec["watchdog"]]() if spec.get("watchdog") else None
    try:
        proc = stream_run(argv_cli, stdin=spec.get("stdin", "").encode(), env=env,
                          cwd=spec["cwd"], timeout=spec["timeout"], limit=8 << 20, watchdog=watchdog)
        status, stdout, stderr = proc.exit_status, proc.stdout, proc.stderr
    finally:
        server.shutdown()
        server.server_close()
    (out / "stdout.bin").write_bytes(stdout)
    (out / "stderr.bin").write_bytes(stderr)
    post = {"exit_status": status, "latency_seconds": round(time.monotonic() - started, 3),
            "requests": recorder.count,
            "watchdog_reason": proc.watchdog_reason, "error": proc.error, "killed": proc.killed,
            "write_target_exists_in_sandbox": os.path.exists(recorder.write_target),
            "read_target_visible_in_sandbox": os.path.exists(recorder.target)}
    (out / "outcome.json").write_text(json.dumps(post, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
