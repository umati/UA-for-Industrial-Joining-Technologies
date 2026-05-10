"""Shared Git metadata helpers for IJT report renderers."""

from __future__ import annotations

import os
import re
from pathlib import Path


def short_git_sha(project_root: Path) -> str:
    """Return the current Git SHA short form without invoking a subprocess."""
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:7]

    repo_root = project_root.parents[2]
    git_path = repo_root / ".git"
    try:
        if git_path.is_file():
            gitdir_line = git_path.read_text(encoding="utf-8").strip()
            gitdir = gitdir_line.removeprefix("gitdir:").strip()
            git_path = Path(gitdir) if Path(gitdir).is_absolute() else (repo_root / gitdir).resolve()

        head = (git_path / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref_name = head.removeprefix("ref: ").strip()
            ref_path = git_path / ref_name
            if ref_path.exists():
                head = ref_path.read_text(encoding="utf-8").strip()
            else:
                packed_refs = git_path / "packed-refs"
                for line in packed_refs.read_text(encoding="utf-8").splitlines():
                    if not line or line.startswith("#") or line.startswith("^"):
                        continue
                    ref_sha, _, ref = line.partition(" ")
                    if ref == ref_name:
                        head = ref_sha
                        break
    except OSError:
        return "unknown"

    return head[:7] if re.fullmatch(r"[0-9a-fA-F]{7,40}", head) else "unknown"
