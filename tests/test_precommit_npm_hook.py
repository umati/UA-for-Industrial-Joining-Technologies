from __future__ import annotations

import importlib.util
from pathlib import Path

_HOOK_PATH = Path(__file__).resolve().parents[1] / "scripts" / "precommit_npm_hook.py"
_SPEC = importlib.util.spec_from_file_location("precommit_npm_hook", _HOOK_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
hook = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(hook)


def _write_package_files(project):
    (project / "package.json").write_text('{"scripts":{"lint":"eslint ."}}\n', encoding="utf-8")
    (project / "package-lock.json").write_text('{"lockfileVersion":3}\n', encoding="utf-8")


def test_dependencies_current_requires_marker_and_project_bin(tmp_path):
    project = tmp_path / "client"
    bin_dir = project / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    _write_package_files(project)
    (bin_dir / "eslint").write_text("#!/usr/bin/env node\n", encoding="utf-8")

    assert not hook._dependencies_current(project, ["eslint"])

    (project / "node_modules" / hook._MARKER_NAME).write_text(
        f"{hook._dependency_hash(project)}\n",
        encoding="utf-8",
    )

    assert hook._dependencies_current(project, ["eslint"])


def test_dependencies_current_rejects_stale_marker(tmp_path):
    project = tmp_path / "client"
    bin_dir = project / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    _write_package_files(project)
    (bin_dir / "eslint").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (project / "node_modules" / hook._MARKER_NAME).write_text("stale\n", encoding="utf-8")

    assert not hook._dependencies_current(project, ["eslint"])


def test_ensure_dependencies_runs_npm_ci_before_hook_script(tmp_path, monkeypatch):
    project = tmp_path / "client"
    project.mkdir()
    _write_package_files(project)
    calls: list[list[str]] = []

    def _fake_run(cmd, project_dir):
        calls.append(cmd)
        bin_dir = project / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "eslint").write_text("#!/usr/bin/env node\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(hook, "_npm_command", lambda: "npm")
    monkeypatch.setattr(hook, "_run", _fake_run)

    assert hook._ensure_dependencies(project, ["eslint"]) == 0
    assert calls == [["npm", "--prefix", str(project), "ci", "--no-audit", "--no-fund"]]
    assert hook._dependencies_current(project, ["eslint"])


def test_ensure_dependencies_removes_stale_node_modules_before_npm_ci(tmp_path, monkeypatch):
    project = tmp_path / "client"
    stale = project / "node_modules" / "old-package"
    stale.mkdir(parents=True)
    _write_package_files(project)

    def _fake_run(_cmd, _project_dir):
        assert not stale.exists()
        bin_dir = project / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "eslint").write_text("#!/usr/bin/env node\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(hook, "_npm_command", lambda: "npm")
    monkeypatch.setattr(hook, "_run", _fake_run)

    assert hook._ensure_dependencies(project, ["eslint"]) == 0
