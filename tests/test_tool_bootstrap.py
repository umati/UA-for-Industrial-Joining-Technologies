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


def test_create_environment_recreates_when_pyvenv_cfg_missing(tmp_path, monkeypatch):
    directory = tmp_path / "broken-venv"
    python = bootstrap.environment_python(directory)
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    assert not (directory / "pyvenv.cfg").exists()
    calls: list[list[str]] = []

    def run(command, project):
        calls.append(list(command))
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")
        python_path = bootstrap.environment_python(directory)
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_text("", encoding="utf-8")
        return __import__("subprocess").CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(bootstrap, "_run", run)
    result = bootstrap._create_environment(directory, tmp_path)
    assert result == bootstrap.environment_python(directory)
    assert (directory / "pyvenv.cfg").is_file()
    assert calls and calls[0][:3] == [sys.executable, "-m", "venv"]


def test_create_environment_refuses_paths_outside_project(tmp_path, monkeypatch):
    outside = tmp_path.parent / f"ijt-bootstrap-outside-{tmp_path.name}"
    python = bootstrap.environment_python(outside)
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("", encoding="utf-8")
    try:
        with pytest.raises(RuntimeError, match="outside project tree"):
            bootstrap._create_environment(outside, tmp_path)
    finally:
        if outside.exists():
            bootstrap.shutil.rmtree(outside, ignore_errors=True)


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


def test_bootstrap_uv_pin_matches_ssot_and_docker_images():
    root = Path(__file__).resolve().parents[1]
    pin_file = root / ".uv-version"
    assert pin_file.is_file(), "repo-root .uv-version is the uv SSoT"
    assert pin_file.read_text(encoding="utf-8").strip() == bootstrap.UV_VERSION
    assert (root / ".github" / "actions" / "setup-uv-pypi" / "action.yml").is_file()
    provisioned = 0
    for path in (root / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "astral-sh/setup-uv@" not in text, path
        workflow = yaml.safe_load(text)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if step.get("uses") == "$/.github/actions/setup-uv-pypi":
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


# --- running_in_docker / import_simulator_extract policy -------------------------------------


@pytest.fixture
def isolated_simulator_extract_import(monkeypatch):
    """Restore sys.path / sys.modules so throw-away ``simulator_extract`` stubs never leak."""
    saved_path = list(sys.path)
    saved_module = sys.modules.pop("simulator_extract", None)
    monkeypatch.setattr(bootstrap, "_DOCKERENV_MARKER", Path("/nonexistent-ijt/.dockerenv"))
    yield
    sys.path[:] = saved_path
    sys.modules.pop("simulator_extract", None)
    if saved_module is not None:
        sys.modules["simulator_extract"] = saved_module


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", " yes "])
def test_running_in_docker_accepts_truthy_is_docker(monkeypatch, value):
    monkeypatch.setattr(bootstrap, "_DOCKERENV_MARKER", Path("/nonexistent-ijt/.dockerenv"))
    monkeypatch.setenv("IS_DOCKER", value)
    assert bootstrap.running_in_docker() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "maybe"])
def test_running_in_docker_rejects_other_is_docker_values(monkeypatch, value):
    monkeypatch.setattr(bootstrap, "_DOCKERENV_MARKER", Path("/nonexistent-ijt/.dockerenv"))
    monkeypatch.setenv("IS_DOCKER", value)
    assert bootstrap.running_in_docker() is False


def test_running_in_docker_detects_dockerenv_marker(tmp_path, monkeypatch):
    marker = tmp_path / ".dockerenv"
    monkeypatch.setattr(bootstrap, "_DOCKERENV_MARKER", marker)
    assert bootstrap.running_in_docker() is False
    marker.write_text("", encoding="utf-8")
    assert bootstrap.running_in_docker() is True


def test_import_simulator_extract_soft_skips_on_host_when_absent(
    tmp_path, isolated_simulator_extract_import
):
    assert bootstrap.import_simulator_extract(tmp_path) is None


@pytest.mark.parametrize("via", ["env", "dockerenv"])
def test_import_simulator_extract_fails_hard_in_docker_when_absent(
    tmp_path, monkeypatch, isolated_simulator_extract_import, via
):
    if via == "env":
        monkeypatch.setenv("IS_DOCKER", "true")
    else:
        marker = tmp_path / "dockerenv-marker"
        marker.write_text("", encoding="utf-8")
        monkeypatch.setattr(bootstrap, "_DOCKERENV_MARKER", marker)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    with pytest.raises(RuntimeError, match=r"simulator_extract\.py is missing inside Docker"):
        bootstrap.import_simulator_extract(scripts)


def test_import_simulator_extract_imports_real_module_and_prepends_path(
    isolated_simulator_extract_import,
):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    module = bootstrap.import_simulator_extract(scripts)
    assert module is not None and module.__name__ == "simulator_extract"
    assert Path(module.__file__).resolve() == scripts / "simulator_extract.py"
    assert str(scripts) in sys.path


@pytest.mark.parametrize("docker", [False, True])
def test_import_simulator_extract_reraises_when_present_but_broken(
    tmp_path, monkeypatch, isolated_simulator_extract_import, docker
):
    if docker:
        monkeypatch.setenv("IS_DOCKER", "true")
    (tmp_path / "simulator_extract.py").write_text(
        "import module_that_does_not_exist_ijt\n", encoding="utf-8"
    )
    with pytest.raises(ImportError, match="module_that_does_not_exist_ijt"):
        bootstrap.import_simulator_extract(tmp_path)


def _repo_python_files():
    root = Path(__file__).resolve().parents[1]
    skip = {
        ".git",
        ".venv",
        ".venv_test",
        ".venv_ci",
        "venv",
        "node_modules",
        ".state",
        "__pycache__",
        "tmp",
    }
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if skip.intersection(relative.parts):
            continue
        if relative.parts[0] == "tests" or "tests" in relative.parts:
            continue
        yield path


def _imports_simulator_extract(tree):
    import ast

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] == "simulator_extract"
        ):
            yield node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "simulator_extract":
                    yield node


def test_production_code_never_imports_simulator_extract_directly():
    """Runners must use ``import_simulator_extract`` (host soft-skip, Docker hard-fail)."""
    import ast

    offenders = []
    for path in _repo_python_files():
        source = path.read_text(encoding="utf-8", errors="replace")
        if "simulator_extract" not in source:
            continue  # also skips generated sources that are not valid Python
        tree = ast.parse(source, filename=str(path))
        if any(_imports_simulator_extract(tree)):
            offenders.append(str(path.relative_to(Path(__file__).resolve().parents[1])))
    assert not offenders, (
        f"direct simulator_extract import (use import_simulator_extract): {offenders}"
    )


def test_all_simulator_extract_runners_use_the_policy_helper():
    import ast

    root = Path(__file__).resolve().parents[1]
    clients = root / "OPC_UA_Clients" / "Release2"
    runners = [
        root / "run_all_tests.py",
        clients / "IJT_Web_Client" / "run_all_tests.py",
        clients / "IJT_Web_Client" / "setup_project.py",
        clients / "IJT_Test_Client" / "run_all_tests.py",
        clients / "IJT_Performance_Client" / "run_all_tests.py",
        clients / "IJT_Console_Client" / "run_all_tests.py",
        clients / "IJT_CSharp_Client" / "run_all_tests.py",
    ]
    for runner in runners:
        tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
        called = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "import_simulator_extract")
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "import_simulator_extract"
                )
            )
            for node in ast.walk(tree)
        )
        assert called, f"{runner} must call tool_bootstrap.import_simulator_extract"
