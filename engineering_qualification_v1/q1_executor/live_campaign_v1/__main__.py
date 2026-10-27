"""Prepare sealed Q1 packets or run the offline integration qualification."""
import argparse
import os
from pathlib import Path

if "JEVKEY" in os.environ:
    from ..systemone_https_v1.credential import harden
    harden()

from ..model import encode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=("prepare", "qualify"))
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.command == "prepare":
    from .contract import build
    result = build(args.output.absolute())
else:
    from .qualification import run
    result = run(args.output.absolute())
print(encode(result).decode())
