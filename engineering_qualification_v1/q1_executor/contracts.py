"""Load the unchanged, hash-pinned repository validators, never a copied fork.

Some custody checkouts omit the later v2 files. In that case cat-file reads
the exact pinned local Git blob; it never fetches or invokes a filter/hook.
"""
import functools
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]


@functools.lru_cache(maxsize=1)
def load():
    pins = json.loads((PACKAGE / "contracts.json").read_bytes())
    sources = {}
    for name, pin in pins["files"].items():
        path = ROOT / name
        if path.is_symlink():
            raise ValueError("symlinked_contract:" + name)
        raw = path.read_bytes() if path.is_file() else subprocess.check_output(
            ["git", "--no-replace-objects", "cat-file", "blob", pin["blob"]], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise ValueError("frozen_contract_binding_mismatch:" + name)
        sources[name] = raw
    # core is imported by the instrument; its bytes were verified above.
    modules = []
    for name in ("instrument", "continuation"):
        fullname = "phase2_v2._q1_pinned_" + name
        spec = importlib.util.spec_from_loader(fullname, loader=None)
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(ROOT / "phase2_v2" / (name + ".py"))
        sys.modules[fullname] = module
        exec(compile(sources["phase2_v2/" + name + ".py"], module.__file__, "exec"), module.__dict__)
        modules.append(module)
    return (*modules, pins)


def check_bindings():
    _, _, pins = load()
    if json.loads((PACKAGE / "contracts.json").read_bytes()) != pins:
        raise ValueError("contract_pins_changed")
    for name, pin in pins["files"].items():
        path = ROOT / name
        if path.is_symlink() or path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != pin["sha256"]:
            raise ValueError("frozen_contract_binding_mismatch:" + name)
