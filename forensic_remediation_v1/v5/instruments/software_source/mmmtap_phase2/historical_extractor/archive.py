"""Bounded ZIP inspection. Archive names and contents never become write paths."""
from __future__ import annotations

import hashlib
import io
import stat
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class IntegrityError(ValueError):
    """Evidence cannot be authenticated or safely read."""


@dataclass(frozen=True)
class Limits:
    archive_bytes: int = 64 * 1024 * 1024
    member_bytes: int = 8 * 1024 * 1024
    total_bytes: int = 128 * 1024 * 1024
    members: int = 10000
    compression_ratio: int = 1000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_member(name: str) -> bool:
    parts = name.rstrip("/").split("/")
    return bool(name) and not (
        PurePosixPath(name).is_absolute()
        or "\\" in name
        or ":" in name
        or any(p in ("", ".", "..") for p in parts)
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
    )


def read_verified_zip(path: Path, expected: str, limits: Limits = Limits()) -> dict[str, bytes]:
    """Authenticate the very bytes being parsed, validate all members, then return."""
    with path.open("rb") as stream:
        raw = stream.read(limits.archive_bytes + 1)
    if len(raw) > limits.archive_bytes:
        raise IntegrityError("archive_size_limit")
    if sha256(raw) != expected:
        raise IntegrityError("archive_sha256_mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > limits.members:
                raise IntegrityError("member_count_limit")
            if sum(i.file_size for i in infos) > limits.total_bytes:
                raise IntegrityError("total_uncompressed_size_limit")
            names: set[str] = set()
            result: dict[str, bytes] = {}
            for info in infos:
                if not safe_member(info.orig_filename):
                    raise IntegrityError("unsafe_member_path")
                name = info.filename.rstrip("/")
                if name in names:
                    raise IntegrityError("duplicate_member_path")
                names.add(name)
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise IntegrityError("symlink_or_special_member")
                if info.flag_bits & 1:
                    raise IntegrityError("encrypted_member")
                if info.file_size > limits.member_bytes:
                    raise IntegrityError("member_size_limit")
                if info.file_size > max(info.compress_size, 1) * limits.compression_ratio:
                    raise IntegrityError("compression_ratio_limit")
                if info.is_dir():
                    continue
                with archive.open(info) as stream:
                    content = stream.read(limits.member_bytes + 1)
                if len(content) != info.file_size:
                    raise IntegrityError("member_size_mismatch")
                result[info.filename] = content
            return result
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        raise IntegrityError(f"malformed_archive:{type(exc).__name__}") from exc
