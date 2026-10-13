import base64
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

E = Path(__file__).resolve().parent
M = Path("/home/prometheus/git/mmmtap_phase2")
os.environ["TMPDIR"] = str(E / "work")
os.environ.pop("JEVKEY", None)
sys.dont_write_bytecode = True
sys.path.insert(0, str(M))
from phase2 import adapters_v2

env_template = json.loads((E / "validation_v2.json").read_text())["environment"]
calls = []
prefix = ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--bind", str(E), str(E),
          "--dev", "/dev", "--proc", "/proc", "--unshare-net", "--die-with-parent", "--"]

def offline_guarded_run(argv, *, stdin, env, timeout, limit):
    start = time.monotonic()
    merged = {**env_template, **env, "JEVKEY": ""}
    p = subprocess.run(prefix + argv, input=stdin, capture_output=True, env=merged, timeout=timeout)
    calls.append({"command": argv[1], "exit_status": p.returncode,
                  "network": "isolated namespace", "credential": "blank"})
    return SimpleNamespace(stdout=p.stdout, stderr=p.stderr, exit_status=p.returncode,
                           latency_seconds=time.monotonic()-start, error=None)

adapters_v2.stream_run = offline_guarded_run
cfg = json.loads((M / "integration_readiness_v1/instruments/config.v2.json").read_text())
cfg["timeout_seconds"] = 1
spec = cfg["adversaries"]["carl_jev"]
prepared = json.loads((M / "integration_readiness_v1/go_validation/binary_missing_credential/prepared.json").read_text())
request = json.loads(base64.b64decode(prepared["input"]))
adapter = adapters_v2.PathBAdapter(spec, cfg)
output = {}
response = adapter.invoke(request, authorised=True)
receipt = json.loads(response.stdout)
output["missing_credential"] = {
    "error": response.error,
    "python_transport_attempts": response.provenance["transport_attempts"],
    "go_attempts": receipt["attempts"], "go_live_calls": receipt["live_calls"],
    "go_failure_class": receipt["failure_class"],
}
(E / "adapter_missing_credential.json").write_text(json.dumps(dataclasses.asdict(response),
    default=lambda b: base64.b64encode(b).decode(), indent=2))
native = json.loads(base64.b64decode(request["native_request"]))
answer = {"model": "MOCK_NOT_PROVIDER", "answers": {k: {"noul": 0.8} for k in native["questions"]},
          "usage": {"input_tokens": 123, "output_tokens": 45}}
response = adapter.invoke(request, mock_response=answer)
receipt = json.loads(response.stdout)
raw_response = json.loads(base64.b64decode(receipt["raw_response"]))
output["mock_usage"] = {"error": response.error, "python_usage": response.usage, "go_raw_usage": raw_response["usage"]}
response = adapter.invoke({}, mock_response=answer)
output["prepare_failure"] = {
    "error": response.error, "provenance_keys": sorted(response.provenance),
    "has_preserved_artifacts": "artifacts" in response.provenance,
    "stdout_bytes": len(response.stdout), "stderr_bytes": len(response.stderr),
}
output["guarded_subprocesses"] = calls
(E / "adapter_results.json").write_text(json.dumps(output, indent=2))
print(json.dumps(output, indent=2))
