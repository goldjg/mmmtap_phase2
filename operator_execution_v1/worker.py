"""Trusted SystemOne transport worker; only run inside the operator namespace."""
from __future__ import annotations

import json
import sys

from phase2.adapters import NativeJEVAdapter
from phase2.adapters_v2 import PathBAdapter
from historical_extractor.extract import strict_json


def main() -> int:
    message = strict_json(sys.stdin.buffer.read(32 * 1024 * 1024 + 1))
    if message["mode"] not in ("live", "offline_path_b"):
        raise ValueError("Unsupported worker mode")
    spec, cfg = message["spec"], message["config"]
    if message["adapter"] == "native_jev":
        if message["mode"] != "live":
            raise ValueError("Native live transport is not an offline fixture")
        result = NativeJEVAdapter(spec, cfg).invoke(
            message["payload"], "frozen_text_assessment_v1", authorised=True)
    elif message["adapter"] == "carl_jev":
        result = PathBAdapter(spec, cfg).invoke(
            message["payload"], authorised=message["mode"] == "live",
            mock_response=message.get("mock_response"))
    else:
        raise ValueError("Unknown worker adapter")
    sys.stdout.write(json.dumps(result.record(), sort_keys=True, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
