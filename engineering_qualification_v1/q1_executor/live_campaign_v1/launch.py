"""Deployment authority and explicit launch gate; no manifest enable switch."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path

from ..model import decode, digest, encode

PRODUCTION_AUTHORITY = Path("/var/lib/mmmtap/q1/deployment-authority")


def blockers(m):
    result = [
        "PI: approve exact source-role assignments and packet sufficiency; existing authored pilot sources are not authenticated change evidence",
        "PI: select governing-policy packet; RD05 fictional policy is only a candidate, not organisational authority",
        "PI: approve historical cARL threshold policy and fixed continuation/failure-censoring rules",
        "PI: strict subscription CLI isolation is unqualified; choose strict NO-GO or explicitly change assurance requirements",
        "PROVIDER/PI: Codex observed served-model identity unavailable; CLI internal retries and egress cannot be independently bounded",
        "OPERATOR/PI: confirm current account/model entitlement and accept financial exposure; no verified monetary ceiling",
    ]
    if m["production_campaign"]["production_route"] is None:
        result.append("OPERATOR: provision broker-only production namespace, exact reviewed provider IPv4:443 nft policy and explicit reviewed CA bundle")
    return result


def require_live_authority(m):
    # Deliberately preventive. Current proposed scientific packets and strict
    # CLI profile are unapproved. A flag, environment variable or edited JSON
    # cannot turn this into a live campaign. There is no permissive back door.
    raise ValueError("Q1_LIVE_LAUNCH_BLOCKED:" + "; ".join(blockers(m)))


def initialise_authority(root, fixture):
    """One canonical custody directory per deployment, not a second engine.

    The operator must supply a persistent, protected deployment directory for
    production. Fixtures use a private adjacent directory. Never reset/rebind.
    """
    m = decode((root / "manifest.json").read_bytes())
    deployment = fixture.parent / "deployment-authority" if m["simulation_only"] else PRODUCTION_AUTHORITY
    if m["simulation_only"]:
        deployment.mkdir(mode=0o700, exist_ok=True)
    elif not deployment.is_dir():
        raise ValueError("BLOCKED_operator_must_provision_fixed_deployment_authority")
    if deployment.is_symlink() or deployment.stat().st_mode & 0o077:
        raise ValueError("deployment_authority_must_be_private")
    stat = root.stat(); dbstat = (root / "campaign.sqlite3").stat()
    record = {"manifest_sha256": m["manifest_sha256"], "canonical_custody": str(root.resolve()),
        "custody_device": stat.st_dev, "custody_inode": stat.st_ino,
        "database_device": dbstat.st_dev, "database_inode": dbstat.st_ino,
        "authority_directory": str(deployment.resolve()),
        "scope": "single_host_single_canonical_directory_not_cross_host_rollback_protection"}
    path = deployment / "authority.json"
    try:
        with path.open("xb") as stream:
            stream.write(encode(record)); stream.flush(); os.fsync(stream.fileno())
    except FileExistsError:
        raise ValueError("deployment_already_bound_never_reinitialise") from None
    (deployment / ".lock").touch(exist_ok=False)
    return record


def validate_authority(root, record):
    from ..model import read_file
    deployment = Path(record["authority_directory"])
    if (deployment.is_symlink() or deployment.stat().st_mode & 0o077
            or decode(read_file(deployment, "authority.json")) != record
            or root.resolve() != Path(record["canonical_custody"])):
        raise ValueError("campaign_not_at_authoritative_custody")
    for path, prefix in ((root, "custody"), (root / "campaign.sqlite3", "database")):
        st = path.stat()
        if (st.st_dev, st.st_ino) != (record[prefix + "_device"], record[prefix + "_inode"]):
            raise ValueError("campaign_copied_or_database_replaced")


@contextmanager
def authority_lock(root):
    from .. import engine
    db = engine.connect(root, readonly=True)
    try:
        creation = decode(db.execute("SELECT value FROM meta WHERE key='creation'").fetchone()[0])
    finally:
        db.close()
    record = creation.get("deployment_authority")
    if record is None:
        yield
        return
    validate_authority(root, record)
    with (Path(record["authority_directory"]) / ".lock").open("rb") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("deployment_campaign_instance_already_active") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
