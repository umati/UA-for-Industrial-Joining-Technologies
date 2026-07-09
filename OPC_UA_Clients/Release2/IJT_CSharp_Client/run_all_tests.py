#!/usr/bin/env python3
"""
run_all_tests.py — IJT C# Client test runner.

Usage:
    python run_all_tests.py              # full run (Phase 1 + Phase 2 if server reachable)
    python run_all_tests.py --phase1     # build + unit tests only (no server)
    python run_all_tests.py --phase2     # live integration tests only
    python run_all_tests.py --opcua-security-build-contract
    python run_all_tests.py --opcua-security \
        --opcua-security-target csharp-client-opcua-security-windows
    python run_all_tests.py --help

Environment variables:
    OPCUA_SERVER_URL         OPC UA server endpoint (default: opc.tcp://localhost:40451)
    OPCUA_SERVER_PORT        Alt: port only — constructs opc.tcp://localhost:PORT
    OPCUA_SIMULATOR_EXE      Path to OPC UA simulator EXE (auto-launched if server unreachable)
    IJT_OPCUA_SECURITY_SUT   OPC UA security SUT selector: windows | linux
    IJT_OPCUA_SECURITY_TARGET
                             OPC UA security target:
                             csharp-client-opcua-security-windows |
                             csharp-client-opcua-security-linux
    SKIP_DOTNET_RESTORE=1    Skip `dotnet restore` (deps already restored in CI)
    IJT_CSHARP_CLEAN=1       Remove build artifacts (`bin/`, `obj/`) before and after run
    IJT_PRESERVE_TEST_ARTIFACTS=1
                             Preserve generated test artifacts and skip runner cleanup

Flags:
    --junit-xml=PATH         Write combined JUnit XML (default: test-results/run_all_tests.xml)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & shared utilities
# ---------------------------------------------------------------------------

_PROJECT_DIR: Path = Path(__file__).resolve().parent
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_SLN = _PROJECT_DIR / "IJT_CSharp_Client.sln"
_TEST_PROJ = _PROJECT_DIR / "Tests" / "IJT_CSharp_Client.Tests" / "IJT_CSharp_Client.Tests.csproj"
_RESULTS_DIR = _PROJECT_DIR / "test-results"
_DEFAULT_SERVER_URL = "opc.tcp://localhost:40451"
_COVERAGE_THRESHOLD = 95.0
_PHASE1_TEST_FILTER = (
    "(FullyQualifiedName!~LiveIntegration)&(Category!=Live)&(Category!=OpcUaSecurity)"
)
_PHASE2_TEST_FILTER = "FullyQualifiedName~LiveIntegration"
_OPCUA_SECURITY_TEST_FILTER = "Category=OpcUaSecurity"
_TRX_FAILURE_OUTCOMES = {"Error", "Failed"}
_TRX_SKIPPED_OUTCOMES = {"NotExecuted", "NotRunnable", "Skipped"}

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SERVER_NATIVE_PORT = 40451  # server binary default — used for fallback pre-flight
_OPCUA_SERVER_PORT = 40464  # dedicated port for C# client test isolation (copy-and-patch)
_OPCUA_SECURITY_TARGETS = {
    "csharp-client-opcua-security-windows": ("windows", 40475),
    "csharp-client-opcua-security-linux": ("linux", 40476),
}
_OPCUA_SECURITY_BUILD_CONTRACT_TARGET = "csharp-client-opcua-security-build-contract"
_OPCUA_SECURITY_BUILD_CONTRACT_PROJECTS = (
    "IJT_CSharp_Client.Tests",
    "IJT_CSharp_Client",
    "UAModel.IJTTightening",
    "UAModel.IJTBase",
    "UAModel.MachineryResult",
)
_WELL_KNOWN_SIMULATOR_PATHS = [
    _REPO_ROOT
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator"
    / "opcua_ijt_demo_application.exe",
    _REPO_ROOT
    / "OPC_UA_Servers"
    / "Release2"
    / "OPC_UA_IJT_Server_Simulator_Linux"
    / "opcua_ijt_demo_application",
]


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_opcua_endpoint(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    stripped = url.strip()
    if "://" in stripped:
        parsed = urlparse(stripped)
        return (parsed.hostname or "localhost"), (parsed.port or 40451)
    if ":" in stripped:
        host, _, port_str = stripped.rpartition(":")
        try:
            return host, int(port_str)
        except ValueError:
            return stripped, 40451
    return stripped, 40451


def _dotnet_available() -> bool:
    return shutil.which("dotnet") is not None


def _is_github_actions_environment() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _strict_dotnet_prerequisites() -> bool:
    return os.environ.get("IJT_CSHARP_STRICT_DOTNET_PREREQS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


# ---------------------------------------------------------------------------
# Per-target MSBuild output isolation (parallel matrix runs)
# ---------------------------------------------------------------------------
#
# When the IJT root runner launches both csharp-client-opcua-security-windows
# and csharp-client-opcua-security-linux concurrently in Phase 2, both
# invocations build the same csproj. Without isolation, MSBuild writes to a
# shared bin/Release/net10.0/ and obj/Release/... and races on files like
# IJT_CSharp_Client.Tests.deps.json (MSB4018: GenerateDepsFile — file in use).
#
# Implementation: use the .NET SDK 8+ "artifacts output" layout via
# UseArtifactsOutput=true plus an ArtifactsPath under the C# project's obj/
# build-artifact tree. The artifacts layout writes every project (including
# transitively walked ProjectReferences such as UAModel.IJTBase,
# UAModel.MachineryResult and IJT_CSharp_Client) into its OWN subfolder of the
# artifacts root:
#
#   obj/opcua-security-artifacts/<target>/bin/<ProjectName>/<pivot>/
#   obj/opcua-security-artifacts/<target>/obj/<ProjectName>/<pivot>/
#
# This is the Microsoft-supported way to share an output root across multiple
# projects without their project.assets.json / deps.json files clobbering each
# other. The earlier BaseOutputPath / BaseIntermediateOutputPath approach
# propagated as MSBuild global properties to every ProjectReference and made
# all referenced projects share a single obj folder — the last restored
# project's project.assets.json won, and subsequent builds failed with
# CS0234 ('Opc.Ua.Client', 'UAModel.IJTBase', 'UAModel.MachineryResult'
# missing). See run 26212631852 on 8ab8404b for the original symptom.
#
# Properties are passed only via the runner (not via Directory.Build.props),
# so day-to-day developer builds and IDE workflows keep the classic bin/obj
# layout; only the OPC UA Security CI path opts in. Keep the artifacts root
# under obj/ (or outside _PROJECT_DIR if this ever moves): generated *.cs files
# under a project-local tmp/ folder are picked up by SDK default Compile globs
# during a later classic build.
def _opcua_security_artifacts_dir(target: str) -> Path:
    return _PROJECT_DIR / "obj" / "opcua-security-artifacts" / target


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _is_safe_opcua_security_artifacts_dir(path: Path) -> bool:
    return _is_relative_to(path, _PROJECT_DIR / "obj") or not _is_relative_to(path, _PROJECT_DIR)


def _opcua_security_msbuild_props(target: str | None) -> list[str]:
    """Return MSBuild artifacts-output args for per-target build isolation.

    Returns an empty list when no target is provided (preserves legacy
    behavior for Phase 1 / Phase 2 paths that share the default bin/obj).
    """
    if not target:
        return []
    artifacts = _opcua_security_artifacts_dir(target)
    artifacts.mkdir(parents=True, exist_ok=True)
    return [
        "-p:UseArtifactsOutput=true",
        f"-p:ArtifactsPath={artifacts}",
    ]


def _opcua_security_results_dir(target: str | None) -> Path:
    """Per-target results directory; falls back to the shared dir if no target."""
    if not target:
        return _RESULTS_DIR
    sub = _RESULTS_DIR / "opcua-security" / target
    sub.mkdir(parents=True, exist_ok=True)
    return sub


def _is_https_reachable(host: str, timeout: float = 5.0) -> bool:
    """Fast preflight: return True only if a verified HTTPS connection to host succeeds.

    Prefer requests when available because Semgrep and pip-audit use the
    requests/certifi trust path. Returns False immediately on SSL cert errors,
    connection refused, or timeout, avoiding the multi-minute retry delays that
    advisory tools impose on failure.
    """
    path = {
        "pypi.org": "/pypi/pip/json",
        "semgrep.dev": "/c/p/default",
    }.get(host, "/")
    url = f"https://{host}{path}"
    try:
        try:
            import requests  # type: ignore[import-untyped]
        except Exception:
            import urllib.request

            # safe: always https; host is a known constant (pypi.org, semgrep.dev)
            urllib.request.urlopen(url, timeout=timeout)  # noqa: S310  # nosec B310
        else:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        return True
    except Exception:
        return False


def _dotnet_version() -> str:
    result = subprocess.run(["dotnet", "--version"], capture_output=True, text=True, check=False)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    label: str
    phase: str
    status: str  # "PASS", "FAIL", "SKIP", "WARN", "ERROR"
    detail: str = ""
    duration: float = 0.0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    trx_path: Path | None = None


@dataclass
class TrxTestCase:
    name: str
    classname: str
    outcome: str
    duration: float = 0.0
    message: str = ""
    stack_trace: str = ""


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_W = 58


def _banner(title: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"{title}   {ts}"
    print("\n" + "=" * _W)
    print(header)
    print("=" * _W)


def _footer(ok: bool, elapsed: float, results: list[StepResult]) -> None:
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status in {"FAIL", "ERROR"})
    n_skip = sum(1 for r in results if r.status == "SKIP")
    status = "PASS" if ok else "FAIL"
    print("-" * _W)
    print(f"Result: {status}   Checks: {n_pass} passed, {n_fail} failed, {n_skip} skipped")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * _W + "\n")


def _row(phase: str, label: str, status: str, detail: str = "") -> None:
    tag = f"[{phase}] {label}"
    pad = max(1, 52 - len(tag))
    dots = "." * pad
    suffix = f" ({detail})" if detail else ""
    print(f"{tag} {dots} {status}{suffix}")


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def _run(
    cmd: list[str],
    *,
    cwd: Path = _PROJECT_DIR,
    env: dict | None = None,
    capture_stdout: bool = False,
) -> tuple[int, str]:
    """Run *cmd* and return (returncode, stdout_text).

    stderr is inherited (visible in terminal).
    """
    merged_env = {**os.environ, **(env or {})}
    merged_env.setdefault("DOTNET_SKIP_FIRST_TIME_EXPERIENCE", "1")
    merged_env.setdefault("DOTNET_CLI_TELEMETRY_OPTOUT", "1")
    merged_env.setdefault("DOTNET_NOLOGO", "1")
    merged_env.setdefault("DOTNET_ADD_GLOBAL_TOOLS_TO_PATH", "0")
    merged_env.setdefault("DOTNET_GENERATE_ASPNET_CERTIFICATE", "false")
    merged_env.setdefault("MSBUILDDISABLENODEREUSE", "1")
    merged_env.setdefault("UseSharedCompilation", "false")
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        check=False,
        stdout=subprocess.PIPE if capture_stdout else None,
        text=True,
    )
    return result.returncode, (result.stdout or "")


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------


def _xml_namespace(root: ET.Element) -> str:
    ns_match = re.match(r"\{[^}]+\}", root.tag)
    return ns_match.group(0) if ns_match else ""


def _parse_trx(path: Path) -> tuple[int, int, int, int]:
    """Return (passed, failed, skipped, total) from a dotnet TRX file."""
    if not path.exists():
        return 0, 0, 0, 0
    try:
        # Local TRX XML produced by dotnet test in `test-results/` during this
        # same CI run — no network, no foreign DTDs. Stdlib ET is fine here
        # under the repo's central XML-parser policy (see [tool.bandit] in
        # the root pyproject.toml). Switch to defusedxml if this ever parses
        # network-fetched or foreign-CI XML.
        tree = ET.parse(str(path))  # nosec B314
        root = tree.getroot()
        ns = _xml_namespace(root)
        counters = root.find(f".//{ns}Counters")
        if counters is None:
            return 0, 0, 0, 0
        total = int(counters.get("total", "0"))
        executed = int(counters.get("executed", "0"))
        passed = int(counters.get("passed", "0"))
        failed = int(counters.get("failed", "0"))
        skipped = total - executed
        return passed, failed, skipped, total
    except Exception:
        return 0, 0, 0, 0


def _trx_duration_seconds(value: str) -> float:
    match = re.fullmatch(
        r"(?:(?P<days>\d+)\.)?(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)",
        value or "",
    )
    if not match:
        return 0.0
    days = int(match.group("days") or "0")
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = float(match.group("seconds"))
    return (((days * 24) + hours) * 60 + minutes) * 60 + seconds


def _trx_result_text(
    result: ET.Element,
    ns: str,
    element_name: str,
    include_output_fallbacks: bool = False,
) -> str:
    paths = [f"./{ns}Output/{ns}ErrorInfo/{ns}{element_name}"]
    if include_output_fallbacks:
        paths.extend((f"./{ns}Output/{ns}StdErr", f"./{ns}Output/{ns}StdOut"))
    for path in paths:
        node = result.find(path)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return ""


def _trx_classname(test_name: str) -> str:
    method_name = test_name.split("(", 1)[0]
    if "." not in method_name:
        return "IJT C# Client"
    return method_name.rsplit(".", 1)[0]


def _parse_trx_test_cases(path: Path) -> list[TrxTestCase]:
    """Return per-test TRX outcomes for JUnit drill-down reporting."""
    if not path.exists():
        return []
    try:
        # Local TRX XML produced by dotnet test in `test-results/` during this
        # same CI run — no network, no foreign DTDs. Stdlib ET is fine here
        # under the repo's central XML-parser policy (see [tool.bandit] in
        # the root pyproject.toml). Switch to defusedxml if this ever parses
        # network-fetched or foreign-CI XML.
        tree = ET.parse(str(path))  # nosec B314
        root = tree.getroot()
        ns = _xml_namespace(root)
        cases: list[TrxTestCase] = []
        for result in root.findall(f".//{ns}UnitTestResult"):
            name = result.get("testName") or "unknown"
            cases.append(
                TrxTestCase(
                    name=name,
                    classname=_trx_classname(name),
                    outcome=result.get("outcome") or "Unknown",
                    duration=_trx_duration_seconds(result.get("duration") or ""),
                    message=_trx_result_text(result, ns, "Message", True),
                    stack_trace=_trx_result_text(result, ns, "StackTrace"),
                )
            )
        return cases
    except Exception:
        return []


def _parse_build_warnings(stdout: str) -> int:
    """Extract warning count from `dotnet build` output."""
    match = re.search(r"(\d+)\s+Warning\(s\)", stdout, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def _parse_nuget_vulnerabilities(stdout: str) -> tuple[int, int]:
    """Return (critical_count, high_count) from `dotnet list package --vulnerable` output."""
    if "has the following vulnerable packages" not in stdout:
        return 0, 0
    critical = len(re.findall(r"\bCritical\b", stdout, re.IGNORECASE))
    high = len(re.findall(r"\bHigh\b", stdout, re.IGNORECASE))
    return critical, high


def _find_cobertura_file() -> Path | None:
    """Search test-results/ for a Cobertura coverage XML produced by coverlet."""
    for candidate in [
        _RESULTS_DIR / "coverage.xml",
        _RESULTS_DIR / "coverage.cobertura.xml",
    ]:
        if candidate.exists():
            return candidate
    for found in _RESULTS_DIR.rglob("coverage.cobertura.xml"):
        return found
    return None


def _parse_cobertura_coverage(path: Path) -> float | None:
    """Return line coverage % (0-100) for IJT_CSharp_Client.* classes only.

    Auto-generated UAModel.* type bindings and the Program entry point are
    excluded — they skew the overall rate to ~30% despite good coverage of the
    actual application code.
    """
    if not path.exists():
        return None
    with contextlib.suppress(Exception):
        # Local Cobertura XML produced by coverlet in `test-results/` during
        # this same CI run — no network, no foreign DTDs. Stdlib ET is fine
        # here under the repo's central XML-parser policy (see [tool.bandit]
        # in the root pyproject.toml). Switch to defusedxml if this ever
        # parses network-fetched or foreign-CI XML.
        tree = ET.parse(str(path))  # nosec B314
        root = tree.getroot()
        total_lines = 0
        covered_lines = 0
        for cls in root.iter("class"):
            name = cls.get("name", "")
            # Only count application code, not generated type bindings
            if not name.startswith("IJT_CSharp_Client."):
                continue
            for line in cls.iter("line"):
                total_lines += 1
                if int(line.get("hits", "0")) > 0:
                    covered_lines += 1
        if total_lines > 0:
            return (covered_lines / total_lines) * 100.0
        # Fallback to top-level rate if no matching classes found
        rate_str = root.get("line-rate")
        if rate_str is not None:
            return float(rate_str) * 100.0
    return None


# ---------------------------------------------------------------------------
# JUnit XML writer (combined summary)
# ---------------------------------------------------------------------------


def _write_junit_xml(path: Path, results: list[StepResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suites = ET.Element("testsuites", name="IJT C# Client")
    for r in results:
        trx_cases = _parse_trx_test_cases(r.trx_path) if r.trx_path else []
        if trx_cases:
            failures = sum(1 for case in trx_cases if case.outcome in _TRX_FAILURE_OUTCOMES)
            skipped = sum(1 for case in trx_cases if case.outcome in _TRX_SKIPPED_OUTCOMES)
            suite = ET.SubElement(
                suites,
                "testsuite",
                name=r.label,
                tests=str(len(trx_cases)),
                failures=str(failures),
                skipped=str(skipped),
                time=f"{r.duration:.3f}",
            )
            for case in trx_cases:
                tc = ET.SubElement(
                    suite,
                    "testcase",
                    classname=case.classname,
                    name=case.name,
                    time=f"{case.duration:.3f}",
                )
                if case.outcome in _TRX_FAILURE_OUTCOMES:
                    failure = ET.SubElement(tc, "failure", message=case.message)
                    if case.stack_trace:
                        failure.text = case.stack_trace
                elif case.outcome in _TRX_SKIPPED_OUTCOMES:
                    skipped_el = ET.SubElement(tc, "skipped")
                    if case.message:
                        skipped_el.set("message", case.message)
            continue

        suite = ET.SubElement(
            suites,
            "testsuite",
            name=r.label,
            tests=str(max(r.total, 1)),
            failures=str(r.failed),
            skipped=str(r.skipped),
            time=f"{r.duration:.3f}",
        )
        tc = ET.SubElement(suite, "testcase", name=r.label, time=f"{r.duration:.3f}")
        if r.status == "FAIL":
            ET.SubElement(tc, "failure", message=r.detail)
        elif r.status == "SKIP":
            ET.SubElement(tc, "skipped")
    tree = ET.ElementTree(suites)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# Prerequisite check
# ---------------------------------------------------------------------------


def _dotnet_major(version: str) -> int:
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return 0


def _target_framework_major(target_framework: str) -> int:
    match = re.match(r"^net(?P<major>\d+)(?:\.\d+)?(?:-.+)?$", target_framework.strip())
    if not match:
        return 0
    return int(match.group("major"))


def _iter_source_csharp_projects() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _PROJECT_DIR.rglob("*.csproj")
            if not {"bin", "obj"}.intersection(path.relative_to(_PROJECT_DIR).parts)
        )
    )


def _target_frameworks(project_path: Path) -> tuple[str, ...]:
    text = project_path.read_text(encoding="utf-8")
    frameworks: list[str] = []
    for tag in ("TargetFramework", "TargetFrameworks"):
        for match in re.finditer(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", text):
            frameworks.extend(part.strip() for part in match.group(1).split(";") if part.strip())
    return tuple(frameworks)


def _required_dotnet_major(projects: tuple[Path, ...] | None = None) -> int:
    majors: list[int] = []
    for project in projects or _iter_source_csharp_projects():
        majors.extend(
            major
            for major in (
                _target_framework_major(framework) for framework in _target_frameworks(project)
            )
            if major
        )
    return max(majors, default=0)


def _check_prerequisites() -> tuple[bool, str]:
    if not _dotnet_available():
        return (
            False,
            "'dotnet' was not found in PATH. Install the .NET SDK and ensure it is on PATH.",
        )
    required_major = _required_dotnet_major()
    ver = _dotnet_version()
    major = _dotnet_major(ver)
    if required_major and major < required_major:
        return (
            False,
            f"dotnet {ver or 'unknown'} found, but >= {required_major} is required "
            "by the C# project TargetFramework.",
        )
    print(f"dotnet {ver}")
    return True, ""


# ---------------------------------------------------------------------------
# Phase 1 steps
# ---------------------------------------------------------------------------


def _step_restore(target: str | None = None) -> StepResult:
    label = "dotnet restore"
    t0 = time.monotonic()
    lock_files = list(_PROJECT_DIR.rglob("packages.lock.json"))
    cmd = ["dotnet", "restore", str(_TEST_PROJ)]
    if lock_files:
        cmd.append("--locked-mode")
    cmd.extend(_opcua_security_msbuild_props(target))
    rc, _ = _run(cmd)
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", f"exit {rc}", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_build() -> StepResult:
    label = "dotnet build"
    t0 = time.monotonic()
    rc, stdout = _run(
        [
            "dotnet",
            "build",
            str(_SLN),
            "--no-restore",
            "-warnaserror",
            "--configuration",
            "Release",
        ],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    warnings = _parse_build_warnings(stdout)
    detail = f"{warnings} warnings"
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", detail, dur)


def _step_build_test_project(phase: str = "MATRIX", target: str | None = None) -> StepResult:
    label = "dotnet build (tests)"
    t0 = time.monotonic()
    rc, stdout = _run(
        [
            "dotnet",
            "build",
            str(_TEST_PROJ),
            "--no-restore",
            "--configuration",
            "Release",
            *_opcua_security_msbuild_props(target),
        ],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    warnings = _parse_build_warnings(stdout)
    detail = f"{warnings} warnings"
    if rc != 0:
        return StepResult(label, phase, "FAIL", detail, dur)
    return StepResult(label, phase, "PASS", detail, dur)


def _missing_opcua_security_contract_artifacts(artifacts: Path) -> list[str]:
    missing: list[str] = []
    for project in _OPCUA_SECURITY_BUILD_CONTRACT_PROJECTS:
        obj_project_dir = artifacts / "obj" / project
        bin_project_dir = artifacts / "bin" / project
        if not obj_project_dir.exists() or not any(obj_project_dir.rglob("project.assets.json")):
            missing.append(f"obj/{project}/project.assets.json")
        if not bin_project_dir.exists() or not any(bin_project_dir.rglob(f"{project}.dll")):
            missing.append(f"bin/{project}/{project}.dll")
    return missing


def _step_opcua_security_build_contract(phase: str = "PHASE 1") -> StepResult:
    """Restore and build the real test graph with OPC UA Security artifacts props.

    This catches regressions where output-isolation props are safe for one
    project but break ProjectReference restore/build resolution.
    """
    label = "OPC UA Security build contract"
    target = _OPCUA_SECURITY_BUILD_CONTRACT_TARGET
    artifacts = _opcua_security_artifacts_dir(target)
    t0 = time.monotonic()

    if not _is_safe_opcua_security_artifacts_dir(artifacts):
        return StepResult(
            label,
            phase,
            "FAIL",
            "ArtifactsPath must stay under obj/ or outside IJT_CSharp_Client "
            "to avoid Compile glob leaks",
            time.monotonic() - t0,
        )

    if not _preserve_test_artifacts():
        shutil.rmtree(artifacts, ignore_errors=True)

    lock_files = list(_PROJECT_DIR.rglob("packages.lock.json"))
    restore_cmd = ["dotnet", "restore", str(_TEST_PROJ)]
    if lock_files:
        restore_cmd.append("--locked-mode")
    restore_cmd.extend(_opcua_security_msbuild_props(target))

    rc, _ = _run(restore_cmd)
    if rc != 0:
        return StepResult(label, phase, "FAIL", f"restore exit {rc}", time.monotonic() - t0)

    rc, stdout = _run(
        [
            "dotnet",
            "build",
            str(_TEST_PROJ),
            "--no-restore",
            "--configuration",
            "Release",
            *_opcua_security_msbuild_props(target),
        ],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    warnings = _parse_build_warnings(stdout)
    if rc != 0:
        return StepResult(label, phase, "FAIL", f"build exit {rc}; {warnings} warnings", dur)

    missing = _missing_opcua_security_contract_artifacts(artifacts)
    if missing:
        sample = ", ".join(missing[:4])
        suffix = "" if len(missing) <= 4 else f", +{len(missing) - 4} more"
        return StepResult(
            label,
            phase,
            "FAIL",
            f"missing isolated artifacts: {sample}{suffix}",
            dur,
        )

    detail = f"{warnings} warnings; isolated artifacts verified"
    return StepResult(label, phase, "PASS", detail, dur)


def _step_format() -> StepResult:
    label = "dotnet format"
    t0 = time.monotonic()
    rc, _ = _run(
        ["dotnet", "format", str(_SLN), "--verify-no-changes", "--no-restore"],
    )
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", "formatting changes needed", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_nuget_cve() -> StepResult:
    label = "NuGet CVE scan"
    t0 = time.monotonic()
    rc, stdout = _run(
        ["dotnet", "list", str(_SLN), "package", "--vulnerable", "--include-transitive"],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    critical, high = _parse_nuget_vulnerabilities(stdout)
    if critical > 0 or high > 0:
        detail = f"{critical} critical, {high} high"
        return StepResult(label, "PHASE 1", "FAIL", detail, dur)
    return StepResult(label, "PHASE 1", "PASS", "0 vulnerable", dur)


def _step_nuget_outdated() -> StepResult:
    """Informational check — never fails the suite."""
    label = "NuGet outdated"
    t0 = time.monotonic()
    rc, stdout = _run(
        ["dotnet", "list", str(_SLN), "package", "--outdated"],
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    outdated = len(re.findall(r"^\s*>", stdout, re.MULTILINE))
    if outdated > 0:
        return StepResult(label, "PHASE 1", "WARN", f"{outdated} outdated", dur)
    return StepResult(label, "PHASE 1", "PASS", "all up-to-date", dur)


def _step_detect_secrets() -> StepResult:
    label = "detect-secrets"
    if not shutil.which("detect-secrets"):
        return StepResult(label, "PHASE 1", "SKIP", "not installed", 0.0)
    t0 = time.monotonic()
    rc, stdout = _run(
        ["detect-secrets", "scan"],
        capture_stdout=True,
    )
    dur = time.monotonic() - t0
    if rc != 0:
        return StepResult(label, "PHASE 1", "FAIL", f"exit {rc}", dur)
    with contextlib.suppress(Exception):
        import json as _json

        data = _json.loads(stdout)
        secrets_found = sum(len(v) for v in data.get("results", {}).values())
        if secrets_found > 0:
            return StepResult(label, "PHASE 1", "FAIL", f"{secrets_found} secrets found", dur)
    return StepResult(label, "PHASE 1", "PASS", "", dur)


def _step_test_unit(verbose: bool = False) -> StepResult:
    """Run dotnet test with XPlat Code Coverage — live tests skip via IJT_PHASE1_ONLY=true."""
    label = "dotnet test (unit)"
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    trx_path = _RESULTS_DIR / "tests.trx"
    t0 = time.monotonic()
    verbosity = ["--verbosity", "normal"] if verbose else ["--verbosity", "minimal"]
    rc, _ = _run(
        [
            "dotnet",
            "test",
            str(_TEST_PROJ),
            "--no-build",
            "--no-restore",
            "--configuration",
            "Release",
            *verbosity,
            "--filter",
            _PHASE1_TEST_FILTER,
            "--logger",
            "trx;LogFileName=tests.trx",
            "--results-directory",
            str(_RESULTS_DIR),
            "--collect",
            "XPlat Code Coverage",
            "--settings",
            str(_PROJECT_DIR / "coverlet.runsettings"),
            "--blame-hang",
            "--blame-hang-timeout",
            "60s",
        ],
        env={"IJT_AUTO_ACCEPT": "true", "IJT_PHASE1_ONLY": "true"},
    )
    dur = time.monotonic() - t0
    passed, failed, skipped, total = _parse_trx(trx_path)
    detail = f"{passed}/{total}, {skipped} skipped" if skipped else f"{passed}/{total}"
    if rc != 0 or failed > 0:
        return StepResult(
            label, "PHASE 1", "FAIL", detail, dur, passed, failed, skipped, total, trx_path
        )
    return StepResult(
        label, "PHASE 1", "PASS", detail, dur, passed, failed, skipped, total, trx_path
    )


def _step_coverage_check() -> StepResult:
    """Parse Cobertura coverage produced by coverlet; warn if below threshold."""
    label = "Coverage"
    cov_file = _find_cobertura_file()
    if cov_file is None:
        return StepResult(label, "PHASE 1", "SKIP", "coverage.cobertura.xml not found", 0.0)
    pct = _parse_cobertura_coverage(cov_file)
    if pct is None:
        return StepResult(label, "PHASE 1", "SKIP", "could not parse coverage", 0.0)
    detail = f"{pct:.1f}% (threshold: {_COVERAGE_THRESHOLD:.0f}%)"
    if pct < _COVERAGE_THRESHOLD:
        return StepResult(label, "PHASE 1", "WARN", detail, 0.0)
    return StepResult(label, "PHASE 1", "PASS", detail, 0.0)


def _step_semgrep() -> StepResult:
    """Run Semgrep AI code review (supports C# rules); skip if not installed."""
    label = "Semgrep (AI review)"
    if not shutil.which("semgrep"):
        return StepResult(label, "PHASE 1", "SKIP", "Install: pip install semgrep", 0.0)
    if not _is_https_reachable("semgrep.dev"):
        return StepResult(
            label,
            "PHASE 1",
            "WARN",
            "semgrep produced no output (rc=N/A) — network/TLS unavailable (preflight)",
            0.0,
        )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    json_file = _RESULTS_DIR / "semgrep.json"
    proc = subprocess.run(
        [
            "semgrep",
            "--config=p/default",
            "--json",
            "--output",
            str(json_file),
            ".",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_DIR),
    )
    dur = time.monotonic() - t0
    if not json_file.exists():
        # Semgrep exited without writing output — typically a network or auth failure
        # when downloading cloud rules (p/default requires internet + optional login).
        return StepResult(
            label,
            "PHASE 1",
            "WARN",
            f"semgrep produced no output (rc={proc.returncode}) — network/auth unavailable",
            dur,
        )
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        findings = data.get("results", [])
        errors = [f for f in findings if f.get("extra", {}).get("severity") == "ERROR"]
        warns = [f for f in findings if f.get("extra", {}).get("severity") == "WARNING"]
        if errors:
            return StepResult(
                label, "PHASE 1", "FAIL", f"{len(errors)} error(s), {len(warns)} warning(s)", dur
            )
        if warns:
            return StepResult(label, "PHASE 1", "WARN", f"0 errors, {len(warns)} warning(s)", dur)
        return StepResult(
            label, "PHASE 1", "PASS", f"{len(findings)} finding(s), none critical", dur
        )
    except Exception as exc:
        return StepResult(
            label,
            "PHASE 1",
            "WARN",
            f"semgrep.json parse failed (rc={proc.returncode}): {exc!s:.120}",
            dur,
        )


# ---------------------------------------------------------------------------
# Phase 2 steps
# ---------------------------------------------------------------------------


def _resolve_server_url() -> str:
    port_env = os.environ.get("OPCUA_SERVER_PORT", "").strip()
    if port_env:
        with contextlib.suppress(ValueError):
            return f"opc.tcp://localhost:{int(port_env)}"
    return os.environ.get("OPCUA_SERVER_URL", "").strip() or _DEFAULT_SERVER_URL


def _try_launch_simulator() -> subprocess.Popen | None:
    """Launch the OPC UA simulator and wait up to 30s for it to open its port.

    Checks OPCUA_SIMULATOR_EXE first, then well-known paths.
    Sets os.environ["OPCUA_SERVER_URL"] to the server's native port when launched.
    Returns a Popen handle on success, None on failure.
    """
    exe: str | None = os.environ.get("OPCUA_SIMULATOR_EXE", "").strip() or None
    if not exe:
        for candidate in _WELL_KNOWN_SIMULATOR_PATHS:
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        return None
    exe_path = Path(exe)
    if not exe_path.exists():
        print(f"[PHASE 2] Simulator not found: {exe}", file=sys.stderr)
        return None
    print(f"[PHASE 2] Launching simulator: {exe}")
    try:
        proc = subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
    except OSError as exc:
        print(f"[PHASE 2] Failed to launch simulator: {exc}", file=sys.stderr)
        return None
    for _ in range(30):
        time.sleep(1)
        if _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
            print(f"[PHASE 2] Simulator ready on port {_SERVER_NATIVE_PORT}.")
            os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
            return proc
    print("[PHASE 2] Simulator did not become ready within 30s.", file=sys.stderr)
    proc.terminate()
    return None


def _step_live_tests(server_url: str, verbose: bool = False) -> StepResult:
    label = "Live Tests"
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    trx_path = _RESULTS_DIR / "live-tests.trx"
    t0 = time.monotonic()
    verbosity = ["--verbosity", "normal"] if verbose else ["--verbosity", "minimal"]
    rc, stdout = _run(
        [
            "dotnet",
            "test",
            str(_TEST_PROJ),
            "--no-build",
            "--no-restore",
            "--configuration",
            "Release",
            *verbosity,
            "--filter",
            _PHASE2_TEST_FILTER,
            "--logger",
            "trx;LogFileName=live-tests.trx",
            "--results-directory",
            str(_RESULTS_DIR),
            "--blame-hang",
            "--blame-hang-timeout",
            "60s",
        ],
        env={
            "IJT_AUTO_ACCEPT": "true",
            "IJT_PHASE1_ONLY": "false",
            "OPCUA_SERVER_URL": server_url,
        },
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    passed, failed, skipped, total = _parse_trx(trx_path)
    detail = f"{passed}/{total}" if not skipped else f"{passed}/{total}, {skipped} skipped"
    if rc != 0 or failed > 0:
        return StepResult(
            label, "PHASE 2", "FAIL", detail, dur, passed, failed, skipped, total, trx_path
        )
    return StepResult(
        label, "PHASE 2", "PASS", detail, dur, passed, failed, skipped, total, trx_path
    )


def _step_opcua_security_tests(
    target: str,
    sut: str,
    port: int,
    verbose: bool = False,
) -> StepResult:
    label = f"OPC UA Security {target} ({sut})"
    results_dir = _opcua_security_results_dir(target)
    trx_path = results_dir / "opcua-security.trx"
    server_url = f"opc.tcp://localhost:{port}"
    t0 = time.monotonic()
    verbosity = ["--verbosity", "normal"] if verbose else ["--verbosity", "minimal"]
    rc, stdout = _run(
        [
            "dotnet",
            "test",
            str(_TEST_PROJ),
            "--no-build",
            "--no-restore",
            "--configuration",
            "Release",
            *verbosity,
            *_opcua_security_msbuild_props(target),
            "--filter",
            _OPCUA_SECURITY_TEST_FILTER,
            "--logger",
            "trx;LogFileName=opcua-security.trx",
            "--logger",
            "console;verbosity=normal",
            "--results-directory",
            str(results_dir),
            "--blame-hang",
            "--blame-hang-timeout",
            "120s",
        ],
        env={
            "IJT_AUTO_ACCEPT": "true",
            "IJT_PHASE1_ONLY": "false",
            "IJT_OPCUA_SECURITY_SUT": sut,
            "IJT_OPCUA_SECURITY_TARGET": target,
            "OPCUA_SERVER_PORT": str(port),
            "OPCUA_SERVER_URL": server_url,
            "IJT_SERVER_URL": server_url,
        },
        capture_stdout=True,
    )
    if stdout:
        print(stdout, end="")
    dur = time.monotonic() - t0
    passed, failed, skipped, total = _parse_trx(trx_path)
    detail = f"{passed}/{total}" if not skipped else f"{passed}/{total}, {skipped} skipped"
    if rc != 0 or failed > 0:
        return StepResult(
            label, "MATRIX", "FAIL", detail, dur, passed, failed, skipped, total, trx_path
        )
    if passed == 0:
        return StepResult(
            label,
            "MATRIX",
            "FAIL",
            f"{detail} (no OPC UA security tests executed)",
            dur,
            passed,
            failed,
            skipped,
            total,
            trx_path,
        )
    return StepResult(
        label, "MATRIX", "PASS", detail, dur, passed, failed, skipped, total, trx_path
    )


def _enforce_managed_live_coverage(result: StepResult, port_override: str) -> StepResult:
    """Fail runner-managed live testing when the fixture skipped every test."""
    if port_override and result.status == "PASS" and result.passed == 0 and result.total > 0:
        detail = (
            f"{result.passed}/{result.total}, {result.skipped} skipped (managed server unavailable)"
        )
        return StepResult(
            result.label,
            result.phase,
            "FAIL",
            detail,
            result.duration,
            result.passed,
            result.failed,
            result.skipped,
            result.total,
            result.trx_path,
        )
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_all_tests.py",
        description="IJT C# Client — test runner",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument("--phase1", action="store_true", help="Build + unit tests only (no server)")
    group.add_argument("--phase2", action="store_true", help="Live integration tests only")
    group.add_argument(
        "--opcua-security",
        action="store_true",
        help="Run one C# OPC UA security target",
    )
    group.add_argument(
        "--opcua-security-build-contract",
        action="store_true",
        help="Restore/build the C# test graph with OPC UA Security artifacts-output props",
    )
    p.add_argument(
        "--opcua-security-target",
        choices=sorted(_OPCUA_SECURITY_TARGETS),
        help="OPC UA security target to run",
    )
    p.add_argument(
        "--opcua-security-sut",
        choices=["windows", "linux"],
        help="SUT override for --opcua-security; defaults from the selected target",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose dotnet test output (--verbosity normal)",
    )
    p.add_argument(
        "--junit-xml",
        default="test-results/run_all_tests.xml",
        metavar="PATH",
        help="Combined JUnit XML output path (default: test-results/run_all_tests.xml)",
    )
    p.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts (`bin/`, `obj/`) before and after run",
    )
    return p.parse_args()


def _resolve_opcua_security_target(args: argparse.Namespace) -> tuple[str, str, int]:
    target = (
        (args.opcua_security_target or os.environ.get("IJT_OPCUA_SECURITY_TARGET", ""))
        .strip()
        .lower()
    )
    sut = (args.opcua_security_sut or os.environ.get("IJT_OPCUA_SECURITY_SUT", "")).strip().lower()

    if not target:
        target = (
            "csharp-client-opcua-security-linux"
            if sut == "linux"
            else "csharp-client-opcua-security-windows"
        )

    if target not in _OPCUA_SECURITY_TARGETS:
        raise ValueError(f"Unsupported OPC UA security target: {target}")

    default_sut, default_port = _OPCUA_SECURITY_TARGETS[target]
    if not sut:
        sut = default_sut
    if sut not in {"windows", "linux"}:
        raise ValueError(f"Unsupported OPC UA security SUT: {sut}")

    port_env = os.environ.get("OPCUA_SERVER_PORT", "").strip()
    port = default_port
    if port_env:
        with contextlib.suppress(ValueError):
            port = int(port_env)

    return target, sut, port


def _cleanup_legacy_project_dotnet_artifacts() -> None:
    legacy = _PROJECT_DIR / "tmp" / "dotnet"
    if legacy.exists():
        _force_rmtree(legacy)


def main() -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    args = _parse_args()
    clean_build_artifacts = args.clean or (
        os.environ.get("IJT_CSHARP_CLEAN", "0").strip().lower() in {"1", "true", "yes"}
    )
    preserve_artifacts = _preserve_test_artifacts()
    if not preserve_artifacts:
        _cleanup_legacy_project_dotnet_artifacts()
        _cleanup_caches(
            _PROJECT_DIR, include_build_artifacts=clean_build_artifacts
        )  # pre-run: clear stale caches from interrupted runs

    run_opcua_security = args.opcua_security
    run_opcua_security_build_contract = args.opcua_security_build_contract
    run_phase1 = (
        not args.phase2 and not run_opcua_security and not run_opcua_security_build_contract
    )
    run_phase2 = (
        not args.phase1 and not run_opcua_security and not run_opcua_security_build_contract
    )
    results: list[StepResult] = []
    t_start = time.monotonic()
    junit_xml_path = _PROJECT_DIR / args.junit_xml

    _banner("IJT C# Client — Test Suite")

    prereq_ok, prereq_detail = _check_prerequisites()
    if not prereq_ok:
        if _is_github_actions_environment() or _strict_dotnet_prerequisites():
            print(
                f"ERROR: {prereq_detail}\n"
                "  Install a newer .NET SDK from https://dotnet.microsoft.com/download",
                file=sys.stderr,
            )
            return 1
        print(
            f"WARN: {prereq_detail}\n"
            "  Skipping IJT C# Client tests in local mode (install .NET SDK 10+ to run).",
            file=sys.stderr,
        )
        skipped = StepResult(
            "dotnet prerequisites",
            "BOOTSTRAP",
            "SKIP",
            prereq_detail,
            total=1,
            skipped=1,
        )
        results.append(skipped)
        _row(skipped.phase, skipped.label, skipped.status, skipped.detail)
        _footer(True, time.monotonic() - t_start, results)
        junit_xml_path.parent.mkdir(parents=True, exist_ok=True)
        _write_junit_xml(junit_xml_path, results)
        if not preserve_artifacts:
            _cleanup_caches(_PROJECT_DIR, include_build_artifacts=clean_build_artifacts)
        return 0

    # In matrix (--opcua-security) mode the shared _RESULTS_DIR is populated by
    # both targets running concurrently; wiping it would clobber a sibling
    # target's just-written report. Per-target subdirectories are wiped below
    # once the target is resolved.
    if not preserve_artifacts and not args.opcua_security:
        shutil.rmtree(_RESULTS_DIR, ignore_errors=True)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    skip_restore = os.environ.get("SKIP_DOTNET_RESTORE", "0").strip() in {"1", "true", "yes"}

    # Default junit path; overridden below for matrix mode.

    # -- OPC UA security build contract --------------------------------------
    if run_opcua_security_build_contract:
        r = _step_opcua_security_build_contract(phase="CONTRACT")
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- OPC UA security ------------------------------------------------------
    if run_opcua_security:
        try:
            target, sut, port = _resolve_opcua_security_target(args)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        # Per-target junit XML so concurrent matrix runs don't race on the
        # same default path (test-results/run_all_tests.xml).
        if args.junit_xml == "test-results/run_all_tests.xml":
            junit_xml_path = (
                _PROJECT_DIR / "test-results" / "opcua-security" / target / "run_all_tests.xml"
            )
        else:
            junit_xml_path = _PROJECT_DIR / args.junit_xml
        junit_xml_path.parent.mkdir(parents=True, exist_ok=True)

        # Per-target results subdir wipe (safe — only this target writes here).
        if not preserve_artifacts:
            target_results_dir = _RESULTS_DIR / "opcua-security" / target
            shutil.rmtree(target_results_dir, ignore_errors=True)

        if not skip_restore:
            r = _step_restore(target=target)
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)
            if r.status == "FAIL":
                _footer(False, time.monotonic() - t_start, results)
                _write_junit_xml(junit_xml_path, results)
                return 1

        r = _step_build_test_project(target=target)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)
        if r.status == "FAIL":
            _footer(False, time.monotonic() - t_start, results)
            _write_junit_xml(junit_xml_path, results)
            return 1

        r = _step_opcua_security_tests(target, sut, port, verbose=args.verbose)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Phase 1 --------------------------------------------------------------
    if run_phase1:
        if not skip_restore:
            r = _step_restore()
            results.append(r)
            _row(r.phase, r.label, r.status, r.detail)
            if r.status == "FAIL":
                _footer(False, time.monotonic() - t_start, results)
                _write_junit_xml(junit_xml_path, results)
                return 1

        r = _step_build()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)
        if r.status == "FAIL":
            _footer(False, time.monotonic() - t_start, results)
            _write_junit_xml(junit_xml_path, results)
            return 1

        r = _step_format()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_nuget_cve()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_nuget_outdated()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_detect_secrets()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_test_unit(verbose=args.verbose)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_coverage_check()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

        r = _step_semgrep()
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Phase 2 --------------------------------------------------------------
    if run_phase2:
        sim_proc: subprocess.Popen | None = None
        port_override = os.environ.get("OPCUA_SERVER_PORT", "").strip()
        user_url_was_set = bool(os.environ.get("OPCUA_SERVER_URL"))

        if port_override:
            # OPCUA_SERVER_PORT is set → OpcUaServerFixture.cs manages the server
            # lifecycle (copy-and-patch mechanism).  Skip the Python pre-flight;
            # passing the resolved URL to dotnet test is sufficient.
            server_url = _resolve_server_url()
            server_ready = True
        elif not user_url_was_set:
            server_url = _resolve_server_url()
            host, port = _parse_opcua_endpoint(server_url)
            server_ready = _is_port_reachable(host, port)
            if not server_ready and not _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
                sim_proc = _try_launch_simulator()
                server_ready = sim_proc is not None
            elif not server_ready and _is_port_reachable("localhost", _SERVER_NATIVE_PORT):
                os.environ["OPCUA_SERVER_URL"] = f"opc.tcp://localhost:{_SERVER_NATIVE_PORT}"
                server_ready = True
        else:
            server_url = _resolve_server_url()
            host, port = _parse_opcua_endpoint(server_url)
            server_ready = _is_port_reachable(host, port)
        try:
            # Re-read URL in case _try_launch_simulator updated it
            server_url = _resolve_server_url()
            if server_ready:
                if port_override:
                    print(
                        f"[PHASE 2] OpcUaServerFixture.cs will manage server on port"
                        f" {port_override}"
                    )
                else:
                    print(f"[PHASE 2] OPC UA server reachable at {server_url}")
                r = _step_live_tests(server_url, verbose=args.verbose)
                # If fixture silently set IsAvailable=false, all tests skip — surface that.
                enforced = _enforce_managed_live_coverage(r, port_override)
                if enforced.status == "FAIL" and enforced is not r:
                    print(
                        f"[PHASE 2] ERROR: all {r.total} C# live tests were skipped (0 passed). "
                        f"The runner-managed server on port {port_override} was unavailable. "
                        f"Check fixture diagnostics above for [OpcUaServerFixture] lines.",
                        flush=True,
                    )
                r = enforced
            else:
                print(
                    f"[PHASE 2] OPC UA server not reachable at {server_url} — skipping live tests"
                )
                r = StepResult(
                    "Live Tests",
                    "PHASE 2",
                    "SKIP",
                    f"server not reachable ({server_url})",
                )
        finally:
            if sim_proc is not None:
                sim_proc.terminate()
                try:
                    sim_proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    sim_proc.kill()
                if not user_url_was_set:
                    os.environ.pop("OPCUA_SERVER_URL", None)
        results.append(r)
        _row(r.phase, r.label, r.status, r.detail)

    # -- Summary --------------------------------------------------------------
    elapsed = time.monotonic() - t_start
    any_fail = any(r.status in {"FAIL", "ERROR"} for r in results)
    _footer(not any_fail, elapsed, results)

    _write_junit_xml(junit_xml_path, results)

    if not preserve_artifacts:
        _cleanup_caches(_PROJECT_DIR, include_build_artifacts=clean_build_artifacts)
    return 1 if any_fail else 0


def _preserve_test_artifacts() -> bool:
    return os.environ.get("IJT_PRESERVE_TEST_ARTIFACTS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _force_rmtree(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only / locked files."""
    import stat as _stat

    def _on_exc(func, fpath, exc):
        try:
            os.chmod(fpath, _stat.S_IWRITE)
            func(fpath)
        except OSError:
            time.sleep(0.05)
            with contextlib.suppress(OSError):
                func(fpath)

    shutil.rmtree(path, onexc=_on_exc)


def _cleanup_caches(root: Path, include_build_artifacts: bool = False) -> None:
    """Remove cache/bytecode artifacts after run. Reports in test-results/ are preserved."""
    _SKIP = {
        "node_modules",
        ".git",
        "test-results",
        "TestResults",
    }  # "tmp" intentionally removed — now cleaned
    _CACHE_DIRS = {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "htmlcov",
    }
    if include_build_artifacts:
        _CACHE_DIRS.update({"bin", "obj"})
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if d not in _SKIP and not d.startswith(".venv") and not d.startswith("venv")
        ]
        for d in list(dirs):
            if d in _CACHE_DIRS or d.startswith("pytest-cache-files-") or d.startswith(".dotnet"):
                _force_rmtree(Path(dirpath) / d)
                dirs.remove(d)
        for f in files:
            if f == ".coverage" or f.startswith(".coverage.") or f.endswith(".pyc"):
                with contextlib.suppress(OSError):
                    (Path(dirpath) / f).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
