"""Local executable/source identities shared by freezing, controls and build receipts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

from .core import ROOT, IntegrityError, digest, load, write_new
from .isolation import sha256_file

CARL = ROOT.parent / "cARL-semantic-eval"


def go_sources() -> dict[str, Path]:
    paths = set(CARL.rglob("*.go"))
    paths.update(p for p in (CARL / "embedded/assets").rglob("*") if p.is_file())
    paths.update((CARL / "internal/assessment/testdata").glob("*.json"))
    paths.update(p for p in (CARL / "go.mod", CARL / "go.sum") if p.exists())
    if any(p.is_symlink() for p in paths):
        raise IntegrityError("Go source symlink refused")
    return {str(p.relative_to(CARL)): p for p in sorted(paths)}


def local_sources() -> dict[str, Path]:
    files = {"cARL-semantic-eval/" + name: path for name, path in go_sources().items()}
    for pattern in ("phase2/*.py", "phase2/*.json", "historical_extractor/*.py", "tests/**/*.py",
                    "tests/fixtures/*.json"):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_symlink():
                raise IntegrityError("Local source symlink refused")
            if path.is_file():
                files["mmmtap_phase2/" + str(path.relative_to(ROOT))] = path
    return files


def source_hashes() -> dict[str, str]:
    return {name: sha256_file(path) for name, path in local_sources().items()}


def tree_identity(root: Path) -> dict:
    """Bind additions, deletions, file modes and symlink targets in a mounted release."""
    if root.is_symlink() or not root.is_dir():
        raise IntegrityError("Pinned tree must be a real directory")
    result = {}
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        name = str(path.relative_to(root))
        if stat.S_ISLNK(mode):
            result[name] = {"kind": "symlink", "target": str(path.readlink())}
        elif stat.S_ISREG(mode):
            result[name] = {"kind": "file", "sha256": sha256_file(path), "mode": stat.S_IMODE(mode)}
        elif stat.S_ISDIR(mode):
            result[name] = {"kind": "directory", "mode": stat.S_IMODE(mode)}
        else:
            raise IntegrityError("Special file in pinned tree")
    return result


def build_receipt_path(binary: Path) -> Path:
    return binary.with_name(binary.name + ".build.json")


def build_path_b(binary: Path) -> dict:
    """Build only the additive Path B executable, offline, into a new named artifact."""
    binary = binary.absolute()
    receipt_path = build_receipt_path(binary)
    if binary.exists() or receipt_path.exists():
        raise FileExistsError("Build artifact or first-attempt receipt already exists")
    binary.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    go = shutil.which("go")
    if go is None:
        raise IntegrityError("Go toolchain unavailable")
    go = str(Path(go).resolve())
    env = {k: os.environ[k] for k in ("PATH", "HOME", "GOCACHE", "GOMODCACHE", "GOTMPDIR", "TMPDIR")
           if k in os.environ}
    env.update(GOPROXY="off", GOSUMDB="off", GOTOOLCHAIN="local", GOTELEMETRY="off",
               CGO_ENABLED="0", GOFLAGS="-buildvcs=false", GOENV="off", GOWORK="off")
    sources = {name: sha256_file(path) for name, path in go_sources().items()}
    command = [go, "build", "-trimpath", "-buildvcs=false", "-o", str(binary),
               "./cmd/carl-assessment-challenge"]
    receipt = {"schema": "mmmtap-path-b-source-build-v1", "status": "failed",
               "command": command, "cwd": str(CARL), "environment": env,
               "source_sha256": sources, "network": "dependency_downloads_disabled"}
    try:
        toolchain = subprocess.run([go, "env", "-json", "GOVERSION", "GOOS", "GOARCH", "GOROOT", "GOTOOLDIR"],
                                  cwd=CARL, env=env, check=True, capture_output=True)
        receipt["toolchain"] = json.loads(toolchain.stdout)
        tool_dir = Path(receipt["toolchain"]["GOTOOLDIR"])
        receipt["toolchain_sha256"] = {
            str(p): sha256_file(p) for p in (Path(go), tool_dir / "compile", tool_dir / "link", tool_dir / "asm")}
        listing = subprocess.run([go, "list", "-deps", "-json", "./cmd/carl-assessment-challenge"],
                                 cwd=CARL, env=env, check=True, capture_output=True)
        text, decoder, inputs = listing.stdout.decode(), json.JSONDecoder(), {}
        while text.strip():
            package, end = decoder.raw_decode(text.lstrip())
            text = text.lstrip()[end:]
            for field in ("GoFiles", "CgoFiles", "CFiles", "HFiles", "SFiles", "SysoFiles", "EmbedFiles"):
                for name in package.get(field, []):
                    path = Path(package["Dir"]) / name
                    inputs[str(path)] = sha256_file(path)
        receipt["compiler_inputs_sha256"] = inputs
        with tempfile.TemporaryDirectory(prefix="mmmtap-build-") as tmp:
            target = Path(tmp) / binary.name
            actual_command = [*command]
            actual_command[actual_command.index("-o") + 1] = str(target)
            receipt["executed_command"] = actual_command
            result = subprocess.run(actual_command, cwd=CARL, env=env, capture_output=True, check=False)
            receipt.update(exit_status=result.returncode, stdout=result.stdout.decode("utf-8", "replace"),
                           stderr=result.stderr.decode("utf-8", "replace"))
            if result.returncode != 0:
                raise IntegrityError("Path B build failed; receipt retained")
            if sources != {name: sha256_file(path) for name, path in go_sources().items()}:
                raise IntegrityError("Build source changed during compilation")
            with target.open("rb") as src, binary.open("xb") as dst:
                shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())
            binary.chmod(0o500)
        receipt.update(status="built", binary_sha256=sha256_file(binary))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        receipt["failure"] = type(exc).__name__
        raise
    finally:
        write_new(receipt_path, receipt)
    return receipt


def verify_build(binary: Path) -> dict:
    try:
        receipt = load(build_receipt_path(binary))
    except FileNotFoundError as exc:
        raise IntegrityError("Source-bound Path B build receipt required") from exc
    if (receipt.get("schema") != "mmmtap-path-b-source-build-v1" or receipt.get("status") != "built"
            or receipt.get("binary_sha256") != sha256_file(binary)
            or receipt.get("source_sha256") != {name: sha256_file(path) for name, path in go_sources().items()}):
        raise IntegrityError("Path B executable does not bind current source")
    for group in ("compiler_inputs_sha256", "toolchain_sha256"):
        if not receipt.get(group):
            raise IntegrityError("Incomplete compiler input binding")
        for path, expected in receipt[group].items():
            if sha256_file(Path(path)) != expected:
                raise IntegrityError("Build input or toolchain drift")
    return receipt


def verify_generator_closure(spec: dict) -> None:
    if spec.get("release_root"):
        if digest(tree_identity(Path(spec["release_root"]))) != spec.get("release_sha256"):
            raise IntegrityError("Mounted CLI helper release changed")
    if sha256_file(Path(spec["binary"])) != spec["binary_sha256"]:
        raise IntegrityError("Generator binary changed")
