from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_csharp_runner():
    root = Path(__file__).resolve().parents[1]
    runner_path = root / "OPC_UA_Clients" / "Release2" / "IJT_CSharp_Client" / "run_all_tests.py"
    spec = importlib.util.spec_from_file_location("ijt_csharp_run_all_tests", runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dotnet_prerequisite_reports_missing_dotnet(monkeypatch):
    runner = _load_csharp_runner()
    monkeypatch.setattr(runner, "_dotnet_available", lambda: False)

    ok, detail = runner._check_prerequisites()

    assert not ok
    assert "not found" in detail


def test_dotnet_prerequisite_reports_old_major_version(monkeypatch):
    runner = _load_csharp_runner()
    monkeypatch.setattr(runner, "_dotnet_available", lambda: True)
    monkeypatch.setattr(runner, "_dotnet_version", lambda: "10.0.100")
    monkeypatch.setattr(runner, "_required_dotnet_major", lambda: 11)

    ok, detail = runner._check_prerequisites()

    assert not ok
    assert ">= 11 is required" in detail
    assert "TargetFramework" in detail


def test_dotnet_prerequisite_requirement_comes_from_project_target_frameworks(tmp_path):
    runner = _load_csharp_runner()
    app_project = tmp_path / "App.csproj"
    tests_project = tmp_path / "Tests.csproj"
    app_project.write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net11.0</TargetFramework>
  </PropertyGroup>
</Project>
""",
        encoding="utf-8",
    )
    tests_project.write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net10.0;net12.0</TargetFrameworks>
  </PropertyGroup>
</Project>
""",
        encoding="utf-8",
    )

    assert runner._required_dotnet_major((app_project, tests_project)) == 12


def test_main_skips_local_run_when_dotnet_is_missing(monkeypatch, tmp_path):
    runner = _load_csharp_runner()
    args = SimpleNamespace(
        clean=False,
        phase1=False,
        phase2=False,
        opcua_security=False,
        opcua_security_build_contract=False,
        junit_xml="test-results/run_all_tests.xml",
    )
    written: dict[str, object] = {}

    monkeypatch.setattr(runner, "_parse_args", lambda: args)
    monkeypatch.setattr(runner, "_preserve_test_artifacts", lambda: True)
    monkeypatch.setattr(runner, "_cleanup_legacy_project_dotnet_artifacts", lambda: None)
    monkeypatch.setattr(runner, "_cleanup_caches", lambda *_, **__: None)
    monkeypatch.setattr(runner, "_check_prerequisites", lambda: (False, "dotnet missing"))
    monkeypatch.setattr(runner, "_is_github_actions_environment", lambda: False)
    monkeypatch.setattr(runner, "_strict_dotnet_prerequisites", lambda: False)
    monkeypatch.setattr(runner, "_banner", lambda *_: None)
    monkeypatch.setattr(runner, "_row", lambda *_: None)
    monkeypatch.setattr(runner, "_footer", lambda *_: None)

    def fake_write_junit(path, results):
        written["path"] = path
        written["results"] = results

    monkeypatch.setattr(runner, "_write_junit_xml", fake_write_junit)

    rc = runner.main()

    assert rc == 0
    assert "results" in written
    results = written["results"]
    assert len(results) == 1
    assert results[0].status == "SKIP"


def test_main_skips_local_ci_mode_when_dotnet_is_missing(monkeypatch):
    runner = _load_csharp_runner()
    args = SimpleNamespace(
        clean=False,
        phase1=False,
        phase2=False,
        opcua_security=False,
        opcua_security_build_contract=False,
        junit_xml="test-results/run_all_tests.xml",
    )
    written: dict[str, object] = {}

    monkeypatch.setenv("CI", "1")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(runner, "_parse_args", lambda: args)
    monkeypatch.setattr(runner, "_preserve_test_artifacts", lambda: True)
    monkeypatch.setattr(runner, "_cleanup_legacy_project_dotnet_artifacts", lambda: None)
    monkeypatch.setattr(runner, "_cleanup_caches", lambda *_, **__: None)
    monkeypatch.setattr(runner, "_check_prerequisites", lambda: (False, "dotnet missing"))
    monkeypatch.setattr(runner, "_banner", lambda *_: None)
    monkeypatch.setattr(runner, "_row", lambda *_: None)
    monkeypatch.setattr(runner, "_footer", lambda *_: None)
    monkeypatch.setattr(
        runner,
        "_write_junit_xml",
        lambda path, results: written.setdefault("results", results),
    )

    rc = runner.main()

    assert rc == 0
    assert written["results"][0].status == "SKIP"


def test_main_keeps_github_actions_prerequisites_strict(monkeypatch):
    runner = _load_csharp_runner()
    args = SimpleNamespace(
        clean=False,
        phase1=False,
        phase2=False,
        opcua_security=False,
        opcua_security_build_contract=False,
        junit_xml="test-results/run_all_tests.xml",
    )

    monkeypatch.setattr(runner, "_parse_args", lambda: args)
    monkeypatch.setattr(runner, "_preserve_test_artifacts", lambda: True)
    monkeypatch.setattr(runner, "_cleanup_legacy_project_dotnet_artifacts", lambda: None)
    monkeypatch.setattr(runner, "_cleanup_caches", lambda *_, **__: None)
    monkeypatch.setattr(runner, "_check_prerequisites", lambda: (False, "dotnet missing"))
    monkeypatch.setattr(runner, "_is_github_actions_environment", lambda: True)
    monkeypatch.setattr(runner, "_strict_dotnet_prerequisites", lambda: False)
    monkeypatch.setattr(runner, "_banner", lambda *_: None)

    rc = runner.main()

    assert rc == 1
