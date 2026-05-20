#!/usr/bin/env python3
"""Compute the canonical IJT Browser CI image input fingerprint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MANIFEST = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "inputs-manifest.json"
_ALGORITHM = "sha256-v1"
_PREFIX = b"ijt-browser-ci-inputs-v1\n"


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if not isinstance(manifest, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if manifest.get("schema_version") != 1:
        raise ValueError(f"{path} schema_version must be 1")
    if manifest.get("algorithm") != _ALGORITHM:
        raise ValueError(f"{path} algorithm must be {_ALGORITHM!r}")
    paths = manifest.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError(f"{path} must contain a non-empty paths list")
    if not all(isinstance(item, str) and item.strip() for item in paths):
        raise ValueError(f"{path} paths must be non-empty strings")
    return manifest


def _normalize_manifest_paths(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in manifest["paths"]:
        rel = raw.replace("\\", "/").strip()
        if rel.startswith("/") or rel.startswith("../") or "/../" in rel:
            raise ValueError(f"manifest path must stay within the repository: {raw!r}")
        if rel in seen:
            raise ValueError(f"duplicate manifest path: {rel}")
        target = repo_root / rel
        if not target.is_file():
            raise FileNotFoundError(f"manifest path does not exist or is not a file: {rel}")
        seen.add(rel)
        normalized.append(rel)
    return sorted(normalized)


def compute_fingerprint(
    *,
    repo_root: Path = _REPO_ROOT,
    manifest_path: Path = _DEFAULT_MANIFEST,
) -> dict[str, Any]:
    """Return the deterministic fingerprint payload for the manifest inputs."""
    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve()
    manifest = _load_manifest(manifest_path)
    paths = _normalize_manifest_paths(repo_root, manifest)

    digest = hashlib.sha256()
    digest.update(_PREFIX)
    for rel in paths:
        payload = (repo_root / rel).read_bytes()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")

    return {
        "algorithm": _ALGORITHM,
        "fingerprint": digest.hexdigest(),
        "manifest": str(manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "paths": paths,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument(
        "--format",
        choices=("value", "json", "github-output"),
        default="value",
        help="Output format. github-output emits inputs_fingerprint=<value>.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = compute_fingerprint(repo_root=args.repo_root, manifest_path=args.manifest)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "github-output":
        print(f"inputs_fingerprint={result['fingerprint']}")
    else:
        print(result["fingerprint"])


if __name__ == "__main__":
    main()
