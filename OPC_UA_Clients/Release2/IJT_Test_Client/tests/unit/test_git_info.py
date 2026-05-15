"""Unit tests for git_info helpers."""

from pathlib import Path

from helpers.git_info import short_git_sha


def _project_root_under(repo_root: Path) -> Path:
    project_root = repo_root / "clients" / "release2" / "project"
    project_root.mkdir(parents=True)
    assert project_root.parents[2] == repo_root
    return project_root


def test_short_git_sha_reads_from_github_sha_env(monkeypatch):
    full_sha = "a" * 40
    monkeypatch.setenv("GITHUB_SHA", full_sha)

    assert short_git_sha(Path(__file__).parents[2]) == full_sha[:7]


def test_short_git_sha_reads_from_git_directory(monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    result = short_git_sha(Path(__file__).resolve().parents[2])

    assert len(result) == 7 or result == "unknown"


def test_short_git_sha_handles_missing_git_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    project_root = _project_root_under(tmp_path / "repo")

    assert short_git_sha(project_root) == "unknown"


def test_short_git_sha_handles_invalid_head_format(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    repo_root = tmp_path / "repo"
    project_root = _project_root_under(repo_root)
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("invalid-not-a-sha", encoding="utf-8")

    assert short_git_sha(project_root) == "unknown"


def test_short_git_sha_resolves_worktree_git_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    repo_root = tmp_path / "repo"
    project_root = _project_root_under(repo_root)
    actual_git_dir = tmp_path / "common-git-dir"
    actual_git_dir.mkdir()
    (repo_root / ".git").write_text(f"gitdir: {actual_git_dir}\n", encoding="utf-8")
    (actual_git_dir / "HEAD").write_text("1234567890abcdef\n", encoding="utf-8")

    assert short_git_sha(project_root) == "1234567"


def test_short_git_sha_reads_packed_refs(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    repo_root = tmp_path / "repo"
    project_root = _project_root_under(repo_root)
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\nabcdef1234567890abcdef1234567890abcdef12 refs/heads/main\n",
        encoding="utf-8",
    )

    assert short_git_sha(project_root) == "abcdef1"
