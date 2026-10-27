import argparse
from pathlib import Path
from ..model import encode

parser = argparse.ArgumentParser(description="Disabled native SystemOne preparation; local TLS qualification only.")
parser.add_argument("command", choices=("prepare", "qualify"))
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.command == "prepare":
    from .contract import make_manifest
    result = {"manifest": str(make_manifest(args.output.absolute())), "state": "DISABLED"}
else:
    from .qualification import run
    result = run(args.output.absolute())
print(encode(result).decode())
