"""OPC UA simulator ZIP extraction shared by root and client runners.

Each present ZIP is extracted into its own target folder (Windows and Linux
packages never overwrite each other). Extraction uses a cross-process lock,
unique staging, rename-aside swap, restores Unix exec bits from the ZIP, and
rejects unsafe or oversized archives before writing.

Full-repo layout is required for auto-extract. Client-only checkouts should set
``OPCUA_SIMULATOR_EXE`` or ``OPCUA_SERVER_URL`` / ``OPCUA_TEST_ENDPOINT``.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from tool_bootstrap import preparation_lock

log = logging.getLogger(__name__)

WINDOWS_PACKAGE_NAME = "OPC_UA_IJT_Server_Simulator"
LINUX_PACKAGE_NAME = "OPC_UA_IJT_Server_Simulator_Linux"
WINDOWS_ZIP_NAME = f"{WINDOWS_PACKAGE_NAME}.zip"
LINUX_ZIP_NAME = f"{LINUX_PACKAGE_NAME}.zip"
WINDOWS_BINARY_NAME = "opcua_ijt_demo_application.exe"
LINUX_BINARY_NAME = "opcua_ijt_demo_application"
_STAMP_NAME = ".ijt-simulator-extract-stamp"

# Defensive limits (current packages: ~13 members, ~73 MiB uncompressed Linux).
_MAX_ZIP_MEMBERS = 256
_MAX_UNCOMPRESSED_TOTAL = 512 * 1024 * 1024
_MAX_UNCOMPRESSED_FILE = 256 * 1024 * 1024
_MAX_COMPRESSED_ARCHIVE = 128 * 1024 * 1024


def default_server_dir(repo_root: Path) -> Path:
    return repo_root / "OPC_UA_Servers" / "Release2"


def default_package_specs(server_dir: Path) -> list[tuple[Path, Path]]:
    """Return ``(archive, target_dir)`` pairs for known simulator packages."""
    return [
        (server_dir / WINDOWS_ZIP_NAME, server_dir / WINDOWS_PACKAGE_NAME),
        (server_dir / LINUX_ZIP_NAME, server_dir / LINUX_PACKAGE_NAME),
    ]


def expected_binary_name(target: Path) -> str:
    if target.name == LINUX_PACKAGE_NAME:
        return LINUX_BINARY_NAME
    return WINDOWS_BINARY_NAME


def _archive_stamp(archive: Path) -> str:
    st = archive.stat()
    return f"{archive.name}\n{st.st_size}\n{getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9))}\n"


def _target_is_current(archive: Path, target: Path) -> bool:
    """True when *target* has the expected binary and matches the archive stamp.

    Pre-stamp folders (binary present, no stamp yet) are adopted in place by
    writing the stamp — never rename-aside — so a running simulator is not
    torn out from under live suites on the first post-upgrade ensure call.
    """
    if not target.is_dir():
        return False
    binary = target / expected_binary_name(target)
    if not binary.is_file():
        return False
    stamp = target / _STAMP_NAME
    expected = _archive_stamp(archive)
    try:
        if stamp.is_file():
            return stamp.read_text(encoding="utf-8") == expected
        # Legacy extract without stamp: claim it for this archive identity.
        stamp.write_text(expected, encoding="utf-8")
        return True
    except OSError:
        return False


def _normalize_zip_member(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def _member_path_is_absolute_or_drive(original: str) -> bool:
    """True for POSIX abs, Windows drive, or UNC-style paths (checked before strip)."""
    posix = original.replace("\\", "/")
    if posix.startswith("/") or posix.startswith("//"):
        return True
    if PurePosixPath(posix).is_absolute():
        return True
    first = PurePosixPath(posix.lstrip("/")).parts[:1]
    return bool(first and ":" in first[0])


def validate_simulator_zip(archive: Path, top_name: str) -> None:
    """Reject traversal, links, duplicates, and oversized/bomb-like archives."""
    st = archive.stat()
    if st.st_size > _MAX_COMPRESSED_ARCHIVE:
        raise RuntimeError(
            f"{archive.name} compressed size {st.st_size} exceeds {_MAX_COMPRESSED_ARCHIVE}"
        )
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
    if len(infos) > _MAX_ZIP_MEMBERS:
        raise RuntimeError(f"{archive.name} has {len(infos)} members (max {_MAX_ZIP_MEMBERS})")

    total_uncompressed = 0
    seen: set[str] = set()
    for info in infos:
        original = info.filename.replace("\\", "/")
        if not original or original.endswith("/"):
            continue
        if _member_path_is_absolute_or_drive(original):
            raise RuntimeError(f"{archive.name} has absolute/drive member path: {info.filename!r}")
        raw = _normalize_zip_member(info.filename)
        if not raw:
            continue
        if raw.startswith("../") or "/../" in f"/{raw}/":
            raise RuntimeError(f"{archive.name} has unsafe member path: {info.filename!r}")
        parts = PurePosixPath(raw).parts
        if ".." in parts:
            raise RuntimeError(f"{archive.name} has path traversal member: {info.filename!r}")
        if parts[0] != top_name:
            raise RuntimeError(
                f"{archive.name} member {info.filename!r} is outside top-level {top_name}/"
            )
        # Keep full Unix mode (type + perms); 0o7777 would drop S_IFLNK.
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise RuntimeError(f"{archive.name} refuses symlink member: {info.filename!r}")
        if info.file_size > _MAX_UNCOMPRESSED_FILE:
            raise RuntimeError(
                f"{archive.name} member {info.filename!r} file size {info.file_size} "
                f"exceeds {_MAX_UNCOMPRESSED_FILE}"
            )
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_UNCOMPRESSED_TOTAL:
            raise RuntimeError(
                f"{archive.name} uncompressed total exceeds {_MAX_UNCOMPRESSED_TOTAL}"
            )
        if raw in seen:
            raise RuntimeError(f"{archive.name} has duplicate member path: {raw!r}")
        seen.add(raw)


def _restore_exec_bits(archive: Path, staging_parent: Path) -> None:
    """Apply Unix file modes from the ZIP (Python extractall drops them)."""
    if os.name == "nt":
        return
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.filename.endswith("/"):
                continue
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode == 0 or stat.S_ISLNK(mode):
                continue
            dest = staging_parent / _normalize_zip_member(info.filename)
            if not dest.is_file():
                continue
            with contextlib.suppress(OSError):
                dest.chmod(stat.S_IMODE(mode))


def _extract_members(archive: Path, staging_parent: Path, top_name: str) -> Path:
    validate_simulator_zip(archive, top_name)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging_parent)
    extracted = staging_parent / top_name
    if not extracted.is_dir():
        raise RuntimeError(f"{archive.name} has no top-level {top_name}/ folder")
    _restore_exec_bits(archive, staging_parent)
    binary = extracted / expected_binary_name(extracted)
    if not binary.is_file():
        raise RuntimeError(f"{archive.name} missing expected binary {binary.name}")
    (extracted / _STAMP_NAME).write_text(_archive_stamp(archive), encoding="utf-8")
    return extracted


def _sweep_stale_extract_dirs(target: Path) -> None:
    """Remove leftover staging/previous dirs for *target* (caller must hold the lock)."""
    parent = target.parent
    for pattern in (f"{target.name}.extract-*", f"{target.name}.previous-*"):
        for stale in parent.glob(pattern):
            if stale.is_dir():
                shutil.rmtree(stale, ignore_errors=True)


def ensure_simulator_package(
    archive: Path,
    target: Path,
    *,
    logger: logging.Logger | None = None,
) -> bool:
    """Extract *archive* into *target* when missing, incomplete, or stamp-stale.

    Returns True when *target* is usable afterward (already current or freshly
    extracted). Returns False when the archive is missing or extraction fails.
    """
    active = logger or log
    try:
        if not archive.is_file():
            return False
    except OSError:
        return False
    lock_path = target.parent / f".{target.name}.extract.lock"
    try:
        with preparation_lock(lock_path):
            try:
                if _target_is_current(archive, target):
                    return True
            except OSError as exc:
                active.warning(
                    "Could not inspect simulator package state for %s: %s", target.name, exc
                )
                return False
            _sweep_stale_extract_dirs(target)
            try:
                staging_parent = Path(
                    tempfile.mkdtemp(prefix=f"{target.name}.extract-", dir=str(target.parent))
                )
            except OSError as exc:
                active.warning("Could not create staging for %s: %s", archive.name, exc)
                return False
            previous: Path | None = None
            try:
                extracted = _extract_members(archive, staging_parent, target.name)
                if target.exists():
                    previous = target.with_name(f"{target.name}.previous-{uuid.uuid4().hex}")
                    target.replace(previous)
                extracted.replace(target)
                active.info("Prepared simulator package from %s", archive.name)
                return True
            except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                active.warning("Could not prepare simulator package from %s: %s", archive.name, exc)
                if previous is not None and previous.exists() and not target.exists():
                    with contextlib.suppress(OSError):
                        previous.replace(target)
                return False
            finally:
                shutil.rmtree(staging_parent, ignore_errors=True)
                if previous is not None:
                    shutil.rmtree(previous, ignore_errors=True)
    except RuntimeError as exc:
        active.warning("Could not lock simulator extract for %s: %s", target.name, exc)
        return False


def ensure_present_simulator_packages(
    server_dir: Path | None = None,
    packages: Sequence[tuple[Path, Path]] | None = None,
    *,
    logger: logging.Logger | None = None,
) -> list[Path]:
    """Ensure every present ZIP has its own up-to-date target folder.

    Returns target directories that exist and are usable after the call.
    Logs a clear message when no ZIP is found (full-repo clone or env override).
    """
    active = logger or log
    if packages is None:
        if server_dir is None:
            raise ValueError("server_dir or packages is required")
        packages = default_package_specs(server_dir)
    ready: list[Path] = []
    saw_archive = False
    for archive, target in packages:
        if not archive.is_file():
            continue
        saw_archive = True
        if ensure_simulator_package(archive, target, logger=active):
            ready.append(target)
    if not saw_archive:
        active.info(
            "No simulator ZIP found for auto-extract. "
            "Use a full IJT repository clone, or set OPCUA_SIMULATOR_EXE / "
            "OPCUA_SERVER_URL (or OPCUA_TEST_ENDPOINT)."
        )
    return ready
