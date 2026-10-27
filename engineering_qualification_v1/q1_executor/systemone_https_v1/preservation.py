"""Read-only preservation checks; no re-execution of historical campaigns."""
from pathlib import Path
import subprocess

from .. import engine
from ..model import PACKAGE, encode, raw_hash
from ..transport_qualification import snapshot

BASELINE = "f687d77c244c81ee0acd0bf8b145944696711f69"


def run():
    root = PACKAGE.parents[1]
    seals = [(PACKAGE, PACKAGE / name) for name in ("SHA256SUMS.txt", "SHA256SUMS.full-matrix.v1.txt",
                "SHA256SUMS.transport.v1.txt", "broker_v1/SHA256SUMS.v1.txt")]
    seals += [(root, PACKAGE / "systemone_typed_v1/SHA256SUMS.v1.txt")]
    seals += [(root / folder, root / folder / "SHA256SUMS.txt") for folder in (
        "engineering_qualification_v1/systemone_contract_resolution_v1",
        "engineering_qualification_v1/provider_contract_qualification_v1", "rd05_comparison/v1")]
    results = {}
    for base, seal in seals:
        count, historical = 0, []
        for line in seal.read_text().splitlines():
            expected, name = line.split("  ", 1)
            path = base / name
            count += 1
            if raw_hash(path.read_bytes()) == expected:
                continue
            relative = path.relative_to(root).as_posix()
            commits = subprocess.check_output(["git", "log", "--format=%H", BASELINE, "--", relative], text=True).splitlines()
            for commit in commits:
                blob = subprocess.run(["git", "show", commit + ":" + relative], capture_output=True)
                if blob.returncode == 0 and raw_hash(blob.stdout) == expected:
                    historical.append({"path": relative, "sha256": expected, "revision": commit})
                    break
            else:
                raise AssertionError(("historical_seal_unresolved", str(seal), name))
        results[seal.relative_to(root).as_posix()] = {"entries_verified": count,
            "seal_sha256": raw_hash(seal.read_bytes()), "historical_producer_bytes": historical}
    campaigns = []
    # Read-only compatibility is necessary because shared broker/engine code changed.
    for path in sorted(PACKAGE.rglob("campaign.sqlite3")):
        if "systemone_https_v1" in path.parts or any(p.startswith("tampered-") for p in path.parts):
            continue
        parent = path.parent
        # Only archived completed acceptance campaigns, not deliberately abandoned
        # reservations and partially initialized negative controls.
        if parent.name not in {"demo-campaign", "normal-campaign", "adverse-campaign", "campaign"}:
            continue
        before = snapshot(parent)
        report = engine.verify(parent)
        assert before == snapshot(parent), parent
        campaigns.append({"path": parent.relative_to(root).as_posix(), "verification": "PASS",
                          "positions": report["summary"]["scheduled_positions"],
                          "evidence_tip_sha256": report["summary"]["evidence_tip_sha256"], "files_unchanged": True})
    allowed = {"engineering_qualification_v1/q1_executor/" + name for name in (
        "engine.py", "model.py", "transport.py", "broker_v1/broker.py", "broker_v1/contract.py", "broker_v1/runtime.py")}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", BASELINE], text=True).splitlines())
    additions = {"engineering_qualification_v1/q1_executor/legacy-software.choice1.v1.json",
                 "engineering_qualification_v1/q1_executor/legacy-broker-specification.choice1.v1.json"}
    unexpected = {p for p in changed - allowed - additions
                  if not p.startswith("engineering_qualification_v1/q1_executor/systemone_https_v1/")}
    assert not unexpected, unexpected
    return {"baseline": BASELINE, "historical_seals": results, "archived_campaigns_readonly": campaigns,
            "existing_tracked_changes": sorted(changed), "original_worker_and_seccomp_bootstrap_unchanged": True,
            "frozen_instruments_evidence_RD01_RD02_RD04_IE01_RD05_and_153_topology_unchanged": True}


if __name__ == "__main__":
    print(encode(run()).decode())
