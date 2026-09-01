"""
Documentation integrity guards for the IJT Test Client docs/ tree.

These are cheap structural checks, not a documentation review:

  - every fenced code block in a Markdown file is closed, so a stray fence
    cannot swallow the rest of a document;
  - documentation does not point at project paths that no longer exist.

No OPC UA server required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parents[2]  # = IJT_Test_Client/
_REPO_ROOT = _PROJECT_ROOT.parents[2]  # = repository root
_DOCS_DIR = _PROJECT_ROOT / "docs"
_MARKDOWN_FILES = sorted(_DOCS_DIR.glob("*.md")) + [_PROJECT_ROOT / "README.md"]

_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")

# Repository-relative paths referenced from prose.  Only paths under a known
# IJT_Test_Client source directory are validated, so repo-root or generated
# artifact names are not misread as broken project references.
_PROJECT_DIRS = (
    "helpers/",
    "scripts/",
    "tests/",
    "specification_tests/",
    "target_server_cu_profiles/",
    "reference_workflows/",
    "profiles/",
    "assets/",
    "events/",
    "results/",
    "joining_process/",
    "joint/",
    "common/",
)
_PATH_TOKEN_RE = re.compile(r"[`\[(]((?:" + "|".join(_PROJECT_DIRS) + r")[A-Za-z0-9_./-]*\.(?:py|ya?ml|md))[`\])]")


def _iter_referenced_paths(text: str):
    for match in _PATH_TOKEN_RE.finditer(text):
        yield match.group(1)


@pytest.mark.parametrize("md_path", _MARKDOWN_FILES, ids=lambda p: p.name)
def test_all_code_fences_are_closed(md_path: Path) -> None:
    """An unclosed ``` fence renders the rest of the document as code."""
    if not md_path.exists():
        pytest.skip(f"{md_path.name} not present")
    fences = [line for line in md_path.read_text(encoding="utf-8").splitlines() if _FENCE_RE.match(line)]
    assert len(fences) % 2 == 0, (
        f"{md_path.name} has {len(fences)} code fences — an odd count means a fence is never closed"
    )


@pytest.mark.parametrize("md_path", _MARKDOWN_FILES, ids=lambda p: p.name)
def test_documented_project_paths_exist(md_path: Path) -> None:
    """Docs must not reference deleted helper/script/workflow files.

    A path is accepted when it resolves either against this project or against
    the repository root (docs legitimately point at repo-root launchers).
    """
    if not md_path.exists():
        pytest.skip(f"{md_path.name} not present")
    missing = []
    for candidate in _iter_referenced_paths(md_path.read_text(encoding="utf-8")):
        if not (_PROJECT_ROOT / candidate).exists() and not (_REPO_ROOT / candidate).exists():
            missing.append(candidate)
    assert not missing, f"{md_path.name} references project paths that do not exist: {sorted(set(missing))}"


def test_skills_md_has_no_references_to_removed_components() -> None:
    """Guards the specific paths removed in the Aug-31 consolidation."""
    text = (_DOCS_DIR / "SKILLS.md").read_text(encoding="utf-8")
    removed = [
        "reference_workflow",
        "reference_workflows/",
        "run_target_server_cu",
        "TARGET_SERVER_CU_QUICK_START",
        "CONTROLLER_PROFILE_GUIDE",
        "ADVANCED_TESTING",
        "REFERENCE_WORKFLOWS",
    ]
    found = [name for name in removed if name in text]
    assert not found, f"docs/SKILLS.md still references removed components: {found}"
