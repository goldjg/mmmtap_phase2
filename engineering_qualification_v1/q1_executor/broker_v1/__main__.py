import argparse
import json
from pathlib import Path

from .qualification import qualify


def main():
    parser = argparse.ArgumentParser(description="Offline broker qualification; no live mode.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.output)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
