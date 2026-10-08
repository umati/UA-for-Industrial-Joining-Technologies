from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture(autouse=True)
def audit_temp_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    import tool_bootstrap

    monkeypatch.setattr(tool_bootstrap, "ensure_uv", lambda project: "uv")


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "run_precommit_all.py"
    spec = importlib.util.spec_from_file_location("ijt_run_precommit_all", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _client_fixtures(module, tmp_path, monkeypatch):
    clients = tuple(tmp_path / name for name in ("Console", "Performance", "Test", "Web"))
    for client in clients:
        client.mkdir()
        (client / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_python_client_dirs", lambda: clients)
    return clients


def test_runs_root_then_envelope_when_config_exists(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    envelope = (
        root
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "src"
        / "javascripts"
        / "views"
        / "envelope"
    )
    envelope.mkdir(parents=True)
    (envelope / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 0)
    monkeypatch.setattr(module, "_run_all_audits_concurrently", lambda **kwargs: [])
    calls = []

    def _run(cmd, cwd):
        calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(module.subprocess, "run", _run)
    assert module.main([]) == 0
    assert calls == [
        (["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"], root),
        (
            ["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"],
            envelope,
        ),
    ]


def test_skips_envelope_when_config_missing(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    envelope = (
        root
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_Web_Client"
        / "src"
        / "javascripts"
        / "views"
        / "envelope"
    )
    envelope.mkdir(parents=True)
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 0)
    monkeypatch.setattr(module, "_run_all_audits_concurrently", lambda **kwargs: [])
    calls = []

    def _run(cmd, cwd):
        calls.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(module.subprocess, "run", _run)
    assert module.main([]) == 0
    assert calls == [
        (["pre-commit", "run", "--all-files", "--show-diff-on-failure", "--color=always"], root),
    ]


def test_npm_lock_audit_retries_on_network_error(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(module.time, "sleep", lambda *args: None)

    attempts = 0

    def mock_run(cmd, cwd, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="npm warn audit request failed, reason: read ECONNRESET"
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(module.subprocess, "run", mock_run)
    monkeypatch.delenv("IJT_NPM_AUDIT_MODE", raising=False)
    assert module._run_npm_lock_audit(d, "test-label", retries=3) == 0
    assert attempts == 2


def test_npm_lock_audit_fails_on_network_error_in_strict_mode(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, cwd, **kwargs: subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="ETIMEDOUT"
        ),
    )
    monkeypatch.setenv("IJT_NPM_AUDIT_MODE", "strict")
    assert module._run_npm_lock_audit(d, "test-label", retries=1) == 1


def test_npm_lock_audit_allows_network_error_in_offline_mode(tmp_path, monkeypatch):
    module = _load_module()
    d = tmp_path / "proj"
    d.mkdir()
    (d / "package.json").write_text("{}", encoding="utf-8")
    (d / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda cmd, cwd, **kwargs: subprocess.CompletedProcess(
            cmd, 1, stdout="", stderr="ETIMEDOUT"
        ),
    )
    monkeypatch.setenv("IJT_NPM_AUDIT_MODE", "offline")
    assert module._run_npm_lock_audit(d, "test-label", retries=1) == 0


def test_audit_failure_returns_non_zero(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", root / "missing_envelope")
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", ())
    monkeypatch.setattr(module, "_precommit_command", lambda: ["pre-commit"])
    monkeypatch.setattr(
        module.subprocess, "run", lambda cmd, cwd: subprocess.CompletedProcess(cmd, 0)
    )
    monkeypatch.setattr(module, "_run_npm_lock_audit", lambda *args: 1)
    monkeypatch.setattr(
        module,
        "_run_all_audits_concurrently",
        lambda **kwargs: [module.AuditResult("npm", 1)],
    )
    assert module.main([]) != 0


def test_audits_only_runs_every_ecosystem_and_skips_precommit(tmp_path, monkeypatch):
    module = _load_module()
    root = tmp_path / "root"
    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "ENVELOPE_DIR", root / "missing_envelope")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "git")
    monkeypatch.setattr(
        module,
        "_run_precommit",
        lambda *_args: (_ for _ in ()).throw(AssertionError("pre-commit must not run")),
    )
    calls = []

    def audit(name, code):
        def run(**kwargs):
            calls.append(name)
            return code

        return run

    monkeypatch.setattr(module, "_run_csharp_nuget_audit", audit("nuget", 0))
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", audit("npm", 1))
    monkeypatch.setattr(module, "_run_python_requirements_audit", audit("python", 0))
    monkeypatch.setattr(module, "ensure_python_package", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "_python_client_dirs", lambda: ())

    assert module.main(["--audits-only"]) == 1
    assert sorted(calls) == ["npm", "nuget", "python"]


def test_csharp_nuget_audit_fails_when_sln_missing(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    assert module._run_csharp_nuget_audit() == 1


def test_csharp_nuget_audit_runs_when_sln_present(tmp_path, monkeypatch):
    module = _load_module()
    sln_dir = tmp_path / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
    sln_dir.mkdir(parents=True)
    sln = sln_dir / "IJT_CSharp_Client.sln"
    sln.write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dotnet")

    called_cmd = []

    def mock_run(cmd, cwd, capture_output=False, text=False, timeout=None, env=None):
        called_cmd.append(cmd)
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout='{"projects":[{"path":"test.csproj","frameworks":[{"framework":"net10.0"}]}]}',
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", mock_run)
    assert module._run_csharp_nuget_audit() == 0
    assert len(called_cmd) == 1
    assert "package" in called_cmd[0] and "--vulnerable" in called_cmd[0]


def test_run_all_audits_concurrently_bounds_concurrency(tmp_path, monkeypatch):
    module = _load_module()
    clients = _client_fixtures(module, tmp_path, monkeypatch)

    active_count = 0
    max_active = 0
    lock = threading.Lock()
    barrier = threading.Barrier(2)
    call_count = 0

    def slow_audit(*args, **kwargs):
        nonlocal active_count, max_active, call_count
        with lock:
            active_count += 1
            if active_count > max_active:
                max_active = active_count
            call_count += 1
            index = call_count
        if index <= 2:
            barrier.wait(timeout=5)
        with lock:
            active_count -= 1
        return 0

    monkeypatch.setattr(module, "ensure_python_package", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dummy_uv")
    monkeypatch.setattr(module, "_run_csharp_nuget_audit", slow_audit)
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", slow_audit)
    monkeypatch.setattr(module, "_run_python_requirements_audit", slow_audit)
    monkeypatch.setattr(
        module,
        "_run_single_python_client_lock_audit",
        lambda cd, **kwargs: module.AuditResult(f"Python client lock ({cd.name})", slow_audit()),
    )

    results = module._run_all_audits_concurrently(max_workers=2)
    assert [r.label for r in results] == [
        "C# Client",
        "npm audits",
        *[f"Python client lock ({cd.name})" for cd in clients],
        "Python requirements",
    ]
    assert all(r.returncode == 0 for r in results)
    assert call_count == 7
    assert max_active == 2


def test_run_all_audits_aggregates_failures_without_aborting_remaining(tmp_path, monkeypatch):
    module = _load_module()
    clients = _client_fixtures(module, tmp_path, monkeypatch)
    completed = []

    def mock_csharp(**kwargs):
        completed.append("csharp")
        return 1

    def mock_npm(**kwargs):
        completed.append("npm")
        return 0

    def mock_py_req(**kwargs):
        completed.append("py_req")
        return 0

    monkeypatch.setattr(module, "ensure_python_package", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dummy_uv")
    monkeypatch.setattr(module, "_run_csharp_nuget_audit", mock_csharp)
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", mock_npm)
    monkeypatch.setattr(module, "_run_python_requirements_audit", mock_py_req)
    monkeypatch.setattr(
        module,
        "_run_single_python_client_lock_audit",
        lambda cd, *args, **kwargs: completed.append(cd.name) or module.AuditResult(cd.name, 0),
    )

    results = module._run_all_audits_concurrently(max_workers=2)
    assert "csharp" in completed
    assert "npm" in completed
    assert "py_req" in completed
    assert sorted(completed) == sorted(["csharp", "npm", "py_req", *[c.name for c in clients]])
    assert len(results) == 7
    assert any(r.returncode == 1 for r in results)


def test_run_single_python_client_lock_audit_contract(tmp_path, monkeypatch):
    module = _load_module()
    client_dir = tmp_path / "Test_Client"
    client_dir.mkdir()
    (client_dir / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

    commands = []
    tmp_files_seen = []

    def mock_safe_run(cmd, cwd, env=None, timeout=None, capture_output=True):
        commands.append((cmd, cwd))
        if "export" in cmd:
            out_idx = cmd.index("-o") + 1
            tmp_path_out = Path(cmd[out_idx])
            tmp_files_seen.append(tmp_path_out)
            tmp_path_out.write_text("package==1.0.0\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="Audit passed", stderr="")

    monkeypatch.setattr(module, "_safe_subprocess_run", mock_safe_run)

    result = module._run_single_python_client_lock_audit(
        client_dir, uv="mock_uv", timeout_seconds=30.0, cache_dir=tmp_path / "cache"
    )

    assert result.returncode == 0
    assert "Python client lock (Test_Client)" in result.label
    assert len(commands) == 3
    assert set(result.stages) == {"lock", "export", "audit"}
    # 1. uv lock --check
    assert commands[0][0] == ["mock_uv", "lock", "--check"]
    assert commands[0][1] == client_dir
    # 2. uv export --frozen --all-groups --no-emit-project --format requirements-txt -o <tmp>
    export_cmd = commands[1][0]
    assert export_cmd[:6] == [
        "mock_uv",
        "export",
        "--frozen",
        "--all-groups",
        "--no-emit-project",
        "--format",
    ]
    assert export_cmd[6] == "requirements-txt"
    assert export_cmd[7] == "-o"
    # 3. pip-audit --strict --require-hashes --disable-pip
    audit_cmd = commands[2][0]
    assert "-m" in audit_cmd and "pip_audit" in audit_cmd
    assert "--strict" in audit_cmd
    assert "--no-deps" not in audit_cmd
    assert "--disable-pip" in audit_cmd
    assert "--require-hashes" in audit_cmd
    # Assert temp file is unlinked / cleaned up
    assert len(tmp_files_seen) == 1
    assert not tmp_files_seen[0].exists()


def test_run_single_python_client_lock_audit_fallback_on_unrecognized_args(tmp_path, monkeypatch):
    module = _load_module()
    client_dir = tmp_path / "Test_Client"
    client_dir.mkdir()
    (client_dir / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

    commands = []

    def mock_safe_run(cmd, cwd, env=None, timeout=None, capture_output=True):
        commands.append(cmd)
        if "export" in cmd:
            out_idx = cmd.index("-o") + 1
            Path(cmd[out_idx]).write_text("package==1.0.0\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "--disable-pip" in cmd:
            return subprocess.CompletedProcess(
                cmd, 2, stdout="", stderr="error: unrecognized arguments: --disable-pip"
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="Audit passed with fallback", stderr="")

    monkeypatch.setattr(module, "_safe_subprocess_run", mock_safe_run)

    result = module._run_single_python_client_lock_audit(
        client_dir, uv="mock_uv", timeout_seconds=30.0, cache_dir=tmp_path / "cache"
    )

    assert result.returncode == 0
    assert len(commands) == 4
    fallback_cmd = commands[3]
    assert "--strict" in fallback_cmd
    assert "--disable-pip" not in fallback_cmd
    assert "--no-deps" not in fallback_cmd
    assert "--require-hashes" in fallback_cmd
    assert "pip-based resolution instead" in result.output


@pytest.mark.parametrize("exception", [False, True])
def test_tool_preparation_failure_fails_all_python_tasks(tmp_path, monkeypatch, exception):
    module = _load_module()
    _client_fixtures(module, tmp_path, monkeypatch)
    preparations = []

    def prepare(*args, **kwargs):
        preparations.append(threading.current_thread())
        if exception:
            raise OSError("installation unavailable")
        return False

    monkeypatch.setattr(module, "ensure_python_package", prepare)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "uv")
    monkeypatch.setattr(module, "_run_csharp_nuget_audit", lambda **kwargs: 0)
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", lambda **kwargs: 0)
    results = module._run_all_audits_concurrently()
    assert preparations == [threading.main_thread()]
    assert [r.returncode for r in results] == [0, 0, 1, 1, 1, 1, 1]


def test_worker_exception_does_not_abort_other_tasks(tmp_path, monkeypatch):
    module = _load_module()
    clients = _client_fixtures(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "ensure_python_package", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "uv")
    monkeypatch.setattr(module, "_run_csharp_nuget_audit", lambda **kwargs: 0)
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", lambda **kwargs: 0)
    monkeypatch.setattr(module, "_run_python_requirements_audit", lambda **kwargs: 0)
    seen = []

    def client(cd, **kwargs):
        seen.append(cd)
        if cd == clients[0]:
            raise OSError("worker failed")
        return module.AuditResult(f"Python client lock ({cd.name})", 0)

    monkeypatch.setattr(module, "_run_single_python_client_lock_audit", client)
    results = module._run_all_audits_concurrently()
    assert len(results) == 7
    assert sorted(seen) == sorted(clients)
    assert [r.returncode for r in results] == [0, 0, 1, 0, 0, 0, 0]
    assert "worker failed" in results[2].error


@pytest.mark.parametrize("failure", ["returncode", "exception"])
@pytest.mark.parametrize("envelope_available", [False, True])
def test_npm_group_finishes_all_available_projects(
    tmp_path, monkeypatch, failure, envelope_available
):
    module = _load_module()
    envelope = tmp_path / "envelope"
    envelope.mkdir()
    if envelope_available:
        (envelope / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    seen = []

    def audit(cwd, label, **kwargs):
        seen.append(label)
        if label == "Node Client":
            if failure == "exception":
                raise OSError("npm failed")
            return 1
        return 0

    monkeypatch.setattr(module, "_run_npm_lock_audit", audit)
    assert module._run_all_npm_lock_audits(output=[]) == 1
    assert seen == ["Node Client", "Web Client"] + (["Envelope"] if envelope_available else [])


@pytest.mark.parametrize("failure", ["lock", "export", "empty", "audit", "timeout"])
def test_client_failure_is_nonzero_and_cleans_export(tmp_path, monkeypatch, failure):
    module = _load_module()
    client = tmp_path / "client"
    client.mkdir()
    (client / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    exports = []

    def run(cmd, **kwargs):
        if "export" in cmd:
            path = Path(cmd[cmd.index("-o") + 1])
            exports.append(path)
            if failure != "empty":
                path.write_text("example==1.0\n", encoding="utf-8")
        if failure == "timeout" and "pip_audit" in cmd:
            raise subprocess.TimeoutExpired(cmd, 1)
        failing = (
            (failure == "lock" and "lock" in cmd)
            or (failure == "export" and "export" in cmd)
            or (failure == "audit" and "pip_audit" in cmd)
        )
        return subprocess.CompletedProcess(
            cmd, int(failing), stdout="", stderr="failed" if failing else ""
        )

    monkeypatch.setattr(module, "_safe_subprocess_run", run)
    result = module._run_single_python_client_lock_audit(
        client, uv="uv", cache_dir=tmp_path / "cache"
    )
    assert result.returncode == 1
    assert all(not p.exists() for p in exports)


def test_cache_creation_failure_cleans_temporary_file(tmp_path, monkeypatch):
    module = _load_module()
    client = tmp_path / "client"
    client.mkdir()
    (client / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    bad_cache = tmp_path / "cache-file"
    bad_cache.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )
    before = set(tmp_path.iterdir())
    with pytest.raises(FileExistsError):
        module._run_single_python_client_lock_audit(client, uv="uv", cache_dir=bad_cache)
    assert set(tmp_path.iterdir()) == before


def test_missing_client_manifest_fails(tmp_path):
    module = _load_module()
    result = module._run_single_python_client_lock_audit(tmp_path, uv="uv")
    assert result.returncode == 1
    assert "manifest missing" in result.error


@pytest.mark.parametrize("tool", ["npm", "dotnet"])
def test_missing_required_tool_fails(tmp_path, monkeypatch, tool):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "find_cmd", lambda *args: None)
    if tool == "npm":
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
        assert module._run_npm_lock_audit(tmp_path, "required", output=[]) == 1
    else:
        sln = tmp_path / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
        sln.mkdir(parents=True)
        (sln / "IJT_CSharp_Client.sln").write_text("fixture", encoding="utf-8")
        assert module._run_csharp_nuget_audit(output=[]) == 1


@pytest.mark.parametrize(
    "report",
    [
        '{"projects":[{"frameworks":[{"topLevelPackages":[{"vulnerabilities":[{"severity":"High"}]}]}]}]}',
        '{"projects":[{"frameworks":[{"transitivePackages":[{"vulnerabilities":[{"severity":"High"}]}]}]}]}',
        '{"projects":[]}',
        '{"projects":[{}]}',
        '{"projects":[{"path":"test.csproj","frameworks":null}]}',
        '{"projects":[{"path":"test.csproj","frameworks":[]}]}',
        '{"projects":[{}],"problems":["service unavailable"]}',
        "not JSON",
    ],
)
def test_nuget_zero_exit_is_not_sufficient(tmp_path, monkeypatch, report):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    sln = tmp_path / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
    sln.mkdir(parents=True)
    (sln / "IJT_CSharp_Client.sln").write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dotnet")
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=report, stderr=""),
    )
    output = []
    assert module._run_csharp_nuget_audit(output=output) == 1
    assert report in "".join(output)


def test_nuget_clean_filtered_report_omits_frameworks(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    directory = tmp_path / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client"
    directory.mkdir(parents=True)
    (directory / "IJT_CSharp_Client.sln").write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "dotnet")
    report = module.json.dumps(
        {"version": 1, "projects": [{"path": "client.csproj"}, {"path": "types.csproj"}]}
    )
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=report, stderr=""),
    )
    assert module._run_csharp_nuget_audit(output=[]) == 0


@pytest.mark.parametrize("envelope_available", [False, True])
def test_requirements_audit_optional_envelope(tmp_path, monkeypatch, envelope_available):
    module = _load_module()
    envelope = tmp_path / "envelope"
    envelope.mkdir()
    envelope_req = envelope / "requirements-ci.txt"
    root_req = tmp_path / "requirements.txt"
    root_req.write_text("example>=1\n", encoding="utf-8")
    if envelope_available:
        (envelope / "package.json").write_text("{}", encoding="utf-8")
        envelope_req.write_text("example>=1\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", (root_req, envelope_req))
    monkeypatch.setattr(
        module,
        "ensure_python_package",
        lambda *a, **kw: pytest.fail("worker must not prepare tools"),
    )
    commands = []
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda cmd, **kwargs: (
            commands.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        ),
    )
    assert module._run_python_requirements_audit(prepared=True, output=[]) == 0
    assert (str(envelope_req) in commands[0]) == envelope_available


def test_missing_required_requirements_fails(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", (tmp_path / "missing.txt",))
    monkeypatch.setattr(
        module, "_safe_subprocess_run", lambda *a, **kw: pytest.fail("must fail before subprocess")
    )
    assert module._run_python_requirements_audit(prepared=True, output=[]) == 1


def test_audit_output_is_buffered_and_ordered(tmp_path, monkeypatch, capsys):
    module = _load_module()
    clients = _client_fixtures(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "ensure_python_package", lambda *args, **kwargs: True)
    monkeypatch.setattr(module, "find_cmd", lambda *args: "uv")
    completed = []

    def buffered(name):
        def run(**kwargs):
            kwargs["output"].append(name + " output\n")
            completed.append(name)
            assert capsys.readouterr().out == ""
            return 0

        return run

    monkeypatch.setattr(module, "_run_csharp_nuget_audit", buffered("nuget"))
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", buffered("npm"))
    monkeypatch.setattr(module, "_run_python_requirements_audit", buffered("requirements"))
    monkeypatch.setattr(
        module,
        "_run_single_python_client_lock_audit",
        lambda cd, **kwargs: module.AuditResult(
            f"Python client lock ({cd.name})", 0, output=cd.name + " output\n"
        ),
    )
    results = module._run_all_audits_concurrently()
    text = capsys.readouterr().out
    assert len(results) == 7
    assert all(r.returncode == 0 for r in results)
    lines = text.splitlines()
    assert len(lines) == 7
    assert all("[security]" in line and "Passed" in line for line in lines)
    assert any("C# Client" in line for line in lines)
    assert any("npm package locks" in line for line in lines)
    assert all(any(cd.name in line for line in lines) for cd in clients)
    assert any("Python requirements" in line for line in lines)
    assert sorted(completed) == ["npm", "nuget", "requirements"]


def test_subprocess_typeerror_is_not_retried_without_timeout(tmp_path, monkeypatch):
    module = _load_module()
    calls = []

    def run(cmd, **kwargs):
        calls.append(kwargs)
        raise TypeError("invalid invocation")

    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(TypeError):
        module._safe_subprocess_run(["tool"], tmp_path, env={"KEY": "value"}, timeout=1)
    assert len(calls) == 1
    assert calls[0]["timeout"] == 1
    assert calls[0]["env"] == {"KEY": "value"}


def test_missing_uv_fails_clients_without_hiding_other_tasks(tmp_path, monkeypatch):
    module = _load_module()
    _client_fixtures(module, tmp_path, monkeypatch)
    monkeypatch.setattr(module, "ensure_python_package", lambda *a, **kw: True)
    monkeypatch.setattr(module, "find_cmd", lambda *a: None)
    monkeypatch.setattr(
        module,
        "ensure_uv",
        lambda project: (_ for _ in ()).throw(RuntimeError("uv unavailable")),
    )
    monkeypatch.setattr(module, "_run_csharp_nuget_audit", lambda **kw: 0)
    monkeypatch.setattr(module, "_run_all_npm_lock_audits", lambda **kw: 0)
    monkeypatch.setattr(module, "_run_python_requirements_audit", lambda **kw: 0)
    results = module._run_all_audits_concurrently()
    assert [r.returncode for r in results] == [0, 0, 1, 1, 1, 1, 0]
    assert results[0].skipped and results[1].skipped


@pytest.mark.parametrize("envelope_available", [False, True])
def test_available_envelope_requires_lock_and_requirements(
    tmp_path, monkeypatch, envelope_available
):
    module = _load_module()
    envelope = tmp_path / "envelope"
    envelope.mkdir()
    if envelope_available:
        (envelope / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "ENVELOPE_DIR", envelope)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", (envelope / "requirements-ci.txt",))
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda *a, **kw: pytest.fail("missing inputs must not invoke a subprocess"),
    )
    assert module._run_python_requirements_audit(prepared=True, output=[]) == int(
        envelope_available
    )
    if envelope_available:
        assert module._run_npm_lock_audit(envelope, "Envelope", output=[]) == 1


@pytest.mark.parametrize("failure", ["vulnerability", "timeout", "network"])
def test_required_requirements_audit_failure_is_nonzero(tmp_path, monkeypatch, failure):
    module = _load_module()
    req = tmp_path / "requirements.txt"
    req.write_text("example>=1\n", encoding="utf-8")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "PYTHON_AUDIT_REQUIREMENTS", (req,))
    seen = []

    def run(cmd, **kwargs):
        seen.append(cmd)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd, 1)
        return subprocess.CompletedProcess(
            cmd,
            1,
            stdout="vulnerability" if failure == "vulnerability" else "",
            stderr="ConnectionError" if failure == "network" else "",
        )

    monkeypatch.setattr(module, "_safe_subprocess_run", run)
    assert module._run_python_requirements_audit(retries=1, prepared=True, output=[]) == 1
    assert len(seen) == 1


@pytest.mark.parametrize("returncode", [0, 1])
def test_main_uses_all_required_results(tmp_path, monkeypatch, returncode):
    module = _load_module()
    monkeypatch.setattr(module, "find_cmd", lambda *args: "git")
    results = [module.AuditResult(f"task-{i}", 0) for i in range(7)]
    results[-1].returncode = returncode
    monkeypatch.setattr(module, "_run_all_audits_concurrently", lambda **kwargs: results)
    assert module.main(["--audits-only"]) == returncode


def test_npm_findings_are_buffered_without_interleaving(tmp_path, monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "find_cmd", lambda *args: "npm")
    monkeypatch.setattr(
        module,
        "_safe_subprocess_run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(
            cmd, 1, stdout="High vulnerability", stderr=""
        ),
    )
    output = []
    assert module._run_npm_lock_audit(tmp_path, "fixture", output=output) == 1
    assert "High vulnerability" in "".join(output)
    assert capsys.readouterr().out == ""


def test_npm_audit_offline_unvalidated_reports_warning_and_not_validated(capsys):
    module = _load_module()
    raw_output = (
        "INFO: [security] Node Client: npm audit passed (1.20s)\n"
        "WARNING: [security] Web Client: npm audit registry endpoint unreachable/timed out "
        "(offline or restricted network); offline mode allows continuing.\n"
    )
    result = module.AuditResult("npm audits", 0, duration=2.5, output=raw_output)
    module._render_results([result])
    out = capsys.readouterr().out
    assert "npm package locks (Node, Web - not validated)" in out
    assert "Not Validated" in out
    assert "[security WARNING]" in out
    assert "offline mode allows continuing" in out


def test_npm_audit_names_only_scanned_projects(capsys):
    module = _load_module()
    # Scenario 1: Envelope checkout absent, only Node & Web scanned
    raw_output = (
        "INFO: [security] Node Client: npm audit passed (1.20s)\n"
        "INFO: [security] Web Client: npm audit passed (1.40s)\n"
        "INFO: [security] Envelope: optional checkout absent\n"
    )
    result = module.AuditResult("npm audits", 0, duration=2.6, output=raw_output)
    module._render_results([result])
    out = capsys.readouterr().out
    assert "npm package locks (Node, Web - 0 vulnerabilities)" in out
    assert "Passed" in out
    assert "Envelope" not in out


def test_npm_audit_skipped_does_not_claim_zero_vulnerabilities(capsys):
    module = _load_module()
    result = module.AuditResult(
        "npm audits",
        0,
        duration=0.0,
        error="npm unavailable; skipped",
        skipped=True,
    )
    module._render_results([result])
    out = capsys.readouterr().out
    assert "npm package locks (skipped)" in out
    assert "Skipped" in out
    assert "0 vulnerabilities" not in out
    assert "[security SKIP]" in out
