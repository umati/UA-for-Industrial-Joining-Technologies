#!/usr/bin/env python3
"""Download, verify, and cache the pinned hadolint binary for this OS/arch.

One shared pin for local runners, pre-commit, and CI (replaces inline ``wget`` +
``sha256sum`` snippets). The binary is cached under
``<project>/.state/tools/hadolint-<version>-<platform>/`` and its SHA-256 is
verified on every call, so a tampered or truncated cache is re-downloaded.

CLI::

    python scripts/ensure_hadolint.py                      # print binary path
    python scripts/ensure_hadolint.py --link /usr/local/bin/hadolint   # CI
    python scripts/ensure_hadolint.py -- Dockerfile ...    # run hadolint with the
                                                           # shared .hadolint.yaml

Shared lint policy lives in ``<repo-root>/.hadolint.yaml``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tool_bootstrap import preparation_lock  # noqa: E402

# renovate: datasource=github-releases depName=hadolint/hadolint
HADOLINT_VERSION = "2.12.0"
_RELEASE_BASE = f"https://github.com/hadolint/hadolint/releases/download/v{HADOLINT_VERSION}"
DOWNLOAD_TIMEOUT = 120.0
DOWNLOAD_ATTEMPTS = 3

REPO_ROOT = Path(__file__).resolve().parents[1]
HADOLINT_CONFIG = REPO_ROOT / ".hadolint.yaml"

# platform key -> (release asset, SHA-256 from the official ``<asset>.sha256`` files).
# v2.12.0 ships no native Darwin-arm64 / Windows-arm64 build: Apple Silicon runs the
# x86_64 Darwin binary under Rosetta 2 and Windows on ARM runs the x86_64 .exe under
# emulation, so those architectures map to the x86_64 asset.
_LINUX_X86_64 = (
    "hadolint-Linux-x86_64",
    "56de6d5e5ec427e17b74fa48d51271c7fc0d61244bf5c90e828aab8362d55010",
)
_LINUX_ARM64 = (
    "hadolint-Linux-arm64",
    "5798551bf19f33951881f15eb238f90aef023f11e7ec7e9f4c37961cb87c5df6",
)
_DARWIN_X86_64 = (
    "hadolint-Darwin-x86_64",
    "2a5b7afcab91645c39a7cebefcd835b865f7488e69be24567f433dfc3d41cd27",
)
_WINDOWS_X86_64 = (
    "hadolint-Windows-x86_64.exe",
    "ed89a156290e15452276b2b4c84efa688a5183d3b578bfaec7cfdf986f0632a8",
)
ASSETS: dict[str, tuple[str, str]] = {
    "Linux-x86_64": _LINUX_X86_64,
    "Linux-arm64": _LINUX_ARM64,
    "Darwin-x86_64": _DARWIN_X86_64,
    "Darwin-arm64": _DARWIN_X86_64,
    "Windows-x86_64": _WINDOWS_X86_64,
    "Windows-arm64": _WINDOWS_X86_64,
}

_ARCH_ALIASES = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "x64": "x86_64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def platform_key(system: str | None = None, machine: str | None = None) -> str:
    """Normalized ``<OS>-<arch>`` key (``Linux|Darwin|Windows`` + ``x86_64|arm64``)."""
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    arch = _ARCH_ALIASES.get(machine)
    if arch is None:
        raise RuntimeError(f"Unsupported CPU architecture for hadolint: {machine!r}")
    return f"{system}-{arch}"


def asset_for(key: str) -> tuple[str, str]:
    try:
        return ASSETS[key]
    except KeyError:
        raise RuntimeError(
            f"No pinned hadolint {HADOLINT_VERSION} build for {key!r}; "
            f"supported: {', '.join(sorted(ASSETS))}"
        ) from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_path(project: Path, key: str) -> Path:
    name = "hadolint.exe" if key.startswith("Windows-") else "hadolint"
    return (
        Path(project).resolve() / ".state" / "tools" / f"hadolint-{HADOLINT_VERSION}-{key}" / name
    )


def _download(url: str, destination: Path) -> None:
    last: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            if not url.startswith("https://"):
                raise RuntimeError(f"Refusing non-HTTPS download: {url}")
            # safe: https-only URL built from the pinned release constant.
            with (
                urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response,  # noqa: S310  # nosec B310
                destination.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
            return
        except (OSError, urllib.error.URLError) as exc:
            last = exc
            if attempt < DOWNLOAD_ATTEMPTS:
                time.sleep(2.0 * attempt)
    raise RuntimeError(f"Could not download {url}: {last}") from last


def ensure_hadolint(project: Path | None = None, *, key: str | None = None) -> Path:
    """Return the path to a SHA-256-verified, cached pinned hadolint binary."""
    project = Path(project) if project is not None else REPO_ROOT
    key = key or platform_key()
    asset, expected = asset_for(key)
    target = cache_path(project, key)
    if target.is_file() and _sha256(target) == expected:
        return target
    tools = target.parent.parent
    with preparation_lock(tools / "hadolint.lock"):
        if target.is_file() and _sha256(target) == expected:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".download-")
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            _download(f"{_RELEASE_BASE}/{asset}", tmp)
            actual = _sha256(tmp)
            if actual != expected:
                raise RuntimeError(
                    f"hadolint SHA-256 mismatch for {asset}: expected {expected}, got {actual}"
                )
            tmp.chmod(0o755)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
    return target


def link_binary(binary: Path, destination: Path) -> Path:
    """Expose *binary* at *destination* (symlink, falling back to a copy)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.exists():
        destination.unlink()
    try:
        destination.symlink_to(binary)
    except OSError:
        shutil.copy2(binary, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    passthrough: list[str] | None = None
    if "--" in argv:
        split = argv.index("--")
        argv, passthrough = argv[:split], argv[split + 1 :]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--project", type=Path, default=REPO_ROOT, help="project root holding .state/tools"
    )
    parser.add_argument(
        "--link",
        type=Path,
        help="also expose the binary at this path (e.g. /usr/local/bin/hadolint)",
    )
    args = parser.parse_args(argv)
    try:
        binary = ensure_hadolint(args.project)
    except RuntimeError as exc:
        print(f"ensure_hadolint: {exc}", file=sys.stderr)
        return 2
    if args.link:
        link_binary(binary, args.link)
    if passthrough is None:
        print(args.link or binary)
        return 0
    if not passthrough:
        return 0  # pre-commit invoked with no matching files
    command = [str(binary), "--config", str(HADOLINT_CONFIG), *passthrough]
    return subprocess.run(command, check=False).returncode  # noqa: S603  # nosec B603


if __name__ == "__main__":
    raise SystemExit(main())
