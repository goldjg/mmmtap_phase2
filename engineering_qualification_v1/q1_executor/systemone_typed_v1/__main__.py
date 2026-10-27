import argparse
from pathlib import Path
from .acceptance import run
from ..model import encode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Choice 1 offline historical replay acceptance; no provider access")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(encode(run(args.output)).decode())
