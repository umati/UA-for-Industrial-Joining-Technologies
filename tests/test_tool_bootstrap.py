"""Offline regression checks for isolated tooling preparation."""

import importlib.util
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tool_bootstrap as bootstrap


@pytest.fixture(autouse=True)
def local_environment(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("IS_DOCKER", raising=False)


def test_reuses_reviewed_provisioned_uv_without_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.shutil, "which", lambda tool: "provided-uv")
    monkeypatch.setattr(bootstrap, "_uv_usable", lambda executable: True)
    assert bootstrap.ensure_uv(tmp_path) == "provided-uv"
    assert not (tmp_path / ".state").exists()


@pytest.mark.parametrize("isolated", ["GITHUB_ACTIONS", "IS_DOCKER"])
def test_isolated_environment_never_downloads_uv(tmp_path, monkeypatch, isolated):
    monkeypatch.setenv(isolated, "true")
    monkeypatch.setattr(bootstrap.shutil, "which", lambda tool: None)
    with pytest.raises(RuntimeError, match="no bootstrap download"):
        bootstrap.ensure_uv(tmp_path)
    assert not (tmp_path / ".state").exists()


def test_uv_prepares_once_and_reuses_verified_install(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.shutil, "which", lambda tool: None)
    installed = []
    monkeypatch.setattr(bootstrap, "_uv_usable", lambda executable: bool(installed))

    def create(directory, project):
        executable = directory / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
        executable.parent.mkdir(parents=True)
        executable.touch()
        return bootstrap.environment_python(directory)

    monkeypatch.setattr(bootstrap, "_create_environment", create)
    monkeypatch.setattr(bootstrap, "_run", lambda command, project: installed.append(command))
    first = bootstrap.ensure_uv(tmp_path)
    assert bootstrap.ensure_uv(tmp_path) == first
    assert len(installed) == 1
    assert installed[0][-1] == f"uv=={bootstrap.UV_VERSION}"
    assert str(tmp_path / ".state") in installed[0][0]


def test_failed_uv_install_is_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.shutil, "which", lambda tool: None)
    monkeypatch.setattr(
        bootstrap, "_create_environment", lambda directory, project: directory / "python"
    )
    monkeypatch.setattr(
        bootstrap,
        "_run",
        lambda command, project: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    with pytest.raises(RuntimeError, match="offline"):
        bootstrap.ensure_uv(tmp_path)


def test_lock_serializes_two_threads_and_releases_after_error(tmp_path):
    lock = tmp_path / "tool.lock"
    entered = threading.Event()
    release = threading.Event()
    second_entered = threading.Event()

    def first():
        with bootstrap.preparation_lock(lock):
            entered.set()
            assert release.wait(5)

    def second():
        assert entered.wait(5)
        with bootstrap.preparation_lock(lock):
            second_entered.set()

    a = threading.Thread(target=first)
    b = threading.Thread(target=second)
    a.start()
    b.start()
    assert entered.wait(5)
    assert not second_entered.wait(0.1)
    release.set()
    a.join(5)
    b.join(5)
    assert second_entered.is_set()
    with pytest.raises(ValueError), bootstrap.preparation_lock(lock):
        raise ValueError("failure")
    with bootstrap.preparation_lock(lock, timeout=1):
        pass


def test_lock_times_out_while_held(tmp_path):
    with (
        bootstrap.preparation_lock(tmp_path / "lock"),
        pytest.raises(RuntimeError, match="Timed out"),
        bootstrap.preparation_lock(tmp_path / "lock", timeout=0),
    ):
        pytest.fail("second owner must not enter")


def test_lock_coordinates_separate_processes(tmp_path):
    lock = tmp_path / "process.lock"
    script = (
        f"import sys; sys.path.insert(0, {str(Path(bootstrap.__file__).parent)!r}); "
        "from pathlib import Path; from tool_bootstrap import preparation_lock; "
        f"\nwith preparation_lock(Path({str(lock)!r}), timeout=0): pass"
    )
    command = [sys.executable, "-B", "-c", script]
    with bootstrap.preparation_lock(lock):
        blocked = subprocess.run(  # noqa: S603 - offline fixture interpreter
            command, cwd=tmp_path, capture_output=True, text=True, timeout=10, check=False
        )
    assert blocked.returncode != 0
    assert "Timed out waiting" in blocked.stderr
    released = subprocess.run(  # noqa: S603 - offline fixture interpreter
        command, cwd=tmp_path, capture_output=True, text=True, timeout=10, check=False
    )
    assert released.returncode == 0, released.stderr


def test_nested_requirements_changes_invalidate_fingerprint(tmp_path):
    first = tmp_path / "requirements.txt"
    child = tmp_path / "child.txt"
    first.write_text("-r child.txt\n", encoding="utf-8")
    child.write_text("example==1\n", encoding="utf-8")
    before = bootstrap._requirements_fingerprint(first, set())
    child.write_text("example==2\n", encoding="utf-8")
    assert bootstrap._requirements_fingerprint(first, set()) != before


def test_requirements_environment_never_installs_globally(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("pytest~=9.0\n", encoding="utf-8")
    commands = []
    monkeypatch.setattr(
        bootstrap,
        "_create_environment",
        lambda directory, project: bootstrap.environment_python(directory),
    )

    def run(command, project):
        commands.append(command)
        directory = Path(command[0]).parent.parent
        directory.mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(bootstrap, "_run", run)
    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0),
    )
    python = bootstrap.ensure_requirements_environment(tmp_path, [req], ["pytest"])
    assert all(command[0] == str(python) for command in commands)
    before = len(commands)
    assert bootstrap.ensure_requirements_environment(tmp_path, [req], ["pytest"]) == python
    assert len(commands) == before


def test_bootstrap_uv_pin_matches_all_workflows_and_docker_images():
    root = Path(__file__).resolve().parents[1]
    provisioned = 0
    for path in (root / ".github" / "workflows").glob("*.yml"):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("astral-sh/setup-uv@"):
                    assert step["with"]["version"] == bootstrap.UV_VERSION, path
                    provisioned += 1
    assert provisioned > 0
    for path in (
        root / ".github" / "docker" / "ijt-browser-ci" / "Dockerfile",
        root / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "Dockerfile",
    ):
        assert f"ghcr.io/astral-sh/uv:{bootstrap.UV_VERSION}@sha256:" in path.read_text()


@pytest.mark.parametrize("strict", [False, True])
def test_audit_system_tools_policy(tmp_path, monkeypatch, strict):
    spec = importlib.util.spec_from_file_location(
        "audit_policy", Path(__file__).resolve().parents[1] / "run_precommit_all.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ensure_python_package", lambda *a, **kw: True)
    monkeypatch.setattr(module, "ensure_uv", lambda project: "uv")
    monkeypatch.setattr(module, "find_cmd", lambda *a: None)
    monkeypatch.setattr(module, "_python_client_dirs", lambda: ())
    monkeypatch.setattr(module, "_run_python_requirements_audit", lambda **kw: 0)
    results = module._run_all_audits_concurrently(strict=strict)
    assert [r.returncode for r in results] == [int(strict), int(strict), 0]
    assert [r.skipped for r in results] == [not strict, not strict, False]
