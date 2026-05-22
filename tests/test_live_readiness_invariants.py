"""
Live-test readiness contract checks.

Preamble
========

    No external waits. No inferred identity. No timeout-as-sync.
    Producer and consumer must share a dependency edge with a passed-forward
    output. For live tests, the producer is whatever launches the OPC UA
    server / Web Client stack (start_server_on_port.py, docker compose up,
    native simulator EXE) and the consumer is the test process. The
    dependency edge is either the compose healthcheck or a real binary
    protocol probe (OPC UA HELLO/ACK or asyncua session). Plain TCP-port
    liveness is never sufficient.

Each test below protects a CI readiness rule that cannot be enforced by normal
unit tests alone. Failures mean a live test path has drifted back toward
unreliable startup synchronization.

Status-function note
====================

Some workflow checks intentionally allow ``status() == 'success'`` checks via
``always()`` / ``!cancelled()`` only when paired with an explicit needs-
result assertion, matching the dependency-check pattern in
``test_ci_synchronization_invariants.py``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SHARED_MODULE = SCRIPTS_DIR / "ijt_live_readiness.py"
START_SERVER_SCRIPT = SCRIPTS_DIR / "start_server_on_port.py"
WEB_CLIENT_DOCKERFILE = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
WEB_CLIENT_READINESS_HELPER = (
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Web_Client"
    / "tests"
    / "python"
    / "_live_server_readiness.py"
)

# Every workflow that invokes scripts/start_server_on_port.py. Adding a new
# workflow-level caller requires adding it here so diagnostics capture and
# artifact upload stay guarded by the same test.
START_SERVER_WORKFLOWS = (
    REPO_ROOT / ".github" / "workflows" / "ci.yml",
    REPO_ROOT / ".github" / "workflows" / "integration.yml",
)

# Allowed compose --wait-timeout values, in seconds. Anything else is a
# regression: the warm budget must cover the slowest compose healthcheck
# (~110s for Web Client) and the cold budget must additionally cover image
# build. Use the named constants in ``scripts/ijt_live_readiness.py``.
ALLOWED_WAIT_TIMEOUTS = {"120", "300"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_workflow(path: Path) -> dict:
    return yaml.safe_load(_read(path))


def _iter_workflow_run_steps(workflow: dict):
    """Yield (job_id, step_name, run_str) for every ``run:`` step."""

    for job_id, job in (workflow.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            run = step.get("run")
            if run:
                yield job_id, step.get("name") or step.get("id") or "<unnamed>", run


def _extract_wait_timeouts(text: str) -> list[str]:
    """Return every value passed to ``--wait-timeout`` in ``text`` (regex)."""

    return re.findall(r"--wait-timeout\s+(?:[\"']?)(\d+)(?:[\"']?)", text)


# ─────────────────────────────────────────────────────────────────────────────
# start_server_on_port.py must use the shared OPC UA readiness probe rather
# than a private TCP-only wait loop.
# ─────────────────────────────────────────────────────────────────────────────


def test_start_server_uses_shared_readiness_module() -> None:
    source = _read(START_SERVER_SCRIPT)
    tree = ast.parse(source)

    imports_shared = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "ijt_live_readiness"
        and any(alias.name == "wait_for_opcua_hello" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert imports_shared, (
        "start_server_on_port.py must import wait_for_opcua_hello from "
        "ijt_live_readiness; the script is the single CI entrypoint that "
        "runs before pip install, so it must use the shared stdlib-only "
        "readiness primitive instead of a private TCP loop."
    )

    # Forbid a "create_connection in a poll loop" shape from re-appearing.
    # ``socket.create_connection`` itself is fine in stop-mode / port-cleanup
    # helpers if needed, but not as the primary readiness wait.
    assert "socket.create_connection" not in source, (
        "start_server_on_port.py must not use socket.create_connection "
        "directly — readiness MUST go through ijt_live_readiness.wait_for_* "
        "so the OPC UA HELLO probe is the single source of truth."
    )


# ─────────────────────────────────────────────────────────────────────────────
# The shared readiness module must be importable before client dependencies
# are installed.
# ─────────────────────────────────────────────────────────────────────────────


_STDLIB_ALLOWLIST = frozenset(
    {
        "__future__",
        "contextlib",
        "dataclasses",
        "datetime",
        "json",
        "os",
        "socket",
        "subprocess",
        "sys",
        "time",
        "pathlib",
        "typing",
    }
)


def test_shared_module_top_level_imports_are_stdlib_only() -> None:
    tree = ast.parse(_read(SHARED_MODULE))
    bad: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in _STDLIB_ALLOWLIST:
                    bad.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            root = node.module.split(".")[0]
            if root not in _STDLIB_ALLOWLIST:
                bad.append(f"from {node.module} import ...")

    assert not bad, (
        "scripts/ijt_live_readiness.py top-level imports must be stdlib-only "
        "because start_server_on_port.py loads it in the C# Live job before "
        "actions/setup-dotnet runs and no pip install is performed. Move "
        "third-party imports (asyncua, websockets) inside the function "
        "bodies that need them. Offenders: " + ", ".join(bad)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Client-side readiness helpers must reuse the shared readiness module.
# ─────────────────────────────────────────────────────────────────────────────


_READINESS_HELPER_FILES = (
    WEB_CLIENT_READINESS_HELPER,
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Test_Client" / "helpers" / "server_manager.py",
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Console_Client"
    / "tests"
    / "live"
    / "conftest.py",
)


@pytest.mark.parametrize("path", _READINESS_HELPER_FILES, ids=lambda p: p.name)
def test_client_helpers_delegate_to_shared_readiness(path: Path) -> None:
    assert path.is_file(), f"Expected readiness helper at {path}"
    source = _read(path)
    assert "from ijt_live_readiness import" in source, (
        f"{path.relative_to(REPO_ROOT)} must import from ijt_live_readiness so "
        "the readiness contract is defined in exactly one place. Add the "
        "shared module's scripts/ directory to sys.path and import the "
        "wait_for_* primitives instead of reimplementing them locally."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Every individual ``docker compose up`` callsite must wait for compose
# healthchecks and use a bounded outer process timeout. Pin by callsite count,
# not by file containment: a future second compose-up in the same file must not
# be allowed to slip in unguarded.
# ─────────────────────────────────────────────────────────────────────────────

# Number of distinct ``docker compose up`` callsites expected per tracked
# file. The Web Client runner has two (auto-launch helper for the OPC UA
# server + docker-smoke stage); every other file has one. Adding a callsite
# requires bumping the count here so the architectural review is explicit.
COMPOSE_UP_EXPECTED_CALLSITES: dict[Path, int] = {
    REPO_ROOT / ".github" / "workflows" / "ci.yml": 1,
    REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "run_all_tests.py": 2,
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "run_all_tests.py": 1,
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Console_Client"
    / "tests"
    / "live"
    / "conftest.py": 1,
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_CSharp_Client"
    / "Tests"
    / "IJT_CSharp_Client.Tests"
    / "OpcUaServerFixture.cs": 1,
}


_COMPOSE_UP_PATTERNS_YAML: tuple[re.Pattern[str], ...] = (
    # Workflow YAML: shell ``docker compose up`` in a ``run:`` block.
    re.compile(r"\bdocker\s+compose\s+up\b"),
)

_COMPOSE_UP_PATTERNS_PYTHON: tuple[re.Pattern[str], ...] = (
    # Argv list: ``"compose", "up"`` (or ``"compose",\n    "up"``). Captures
    # both ``["docker", "compose", "up", ...]`` (literal docker) and
    # ``[docker_var, "compose", "up", ...]`` (variable-bound docker).
    re.compile(r"""['"]compose['"]\s*,\s*['"]up['"]"""),
    # Concatenated form: ``compose_cmd + ["up", ...]`` where compose_cmd is
    # a pre-built ``[docker, "compose"]`` list. Matches any list-named
    # variable ending in ``_cmd`` (or named ``compose_cmd``) concatenated
    # with a literal list whose first element is ``"up"``.
    re.compile(r"""\b\w*compose\w*_?(?:cmd|args)?\s*\+\s*\[\s*['"]up['"]"""),
    # Builder pattern: ``compose_args.extend(["up", ...])``.
    re.compile(r"""\bcompose_args\.extend\(\s*\[\s*['"]up['"]"""),
)

# C# fixture: anchor on ``ArgumentList.Add("up")`` because the file may
# insert several Add() calls between ``Add("compose")`` and ``Add("up")``
# (e.g. ``-f overrideFile``). The required ``--wait`` / ``--wait-timeout``
# Add() calls always come after ``Add("up")``.
_COMPOSE_UP_PATTERN_CSHARP = re.compile(r'ArgumentList\.Add\("up"\)')


def _patterns_for(path: Path) -> tuple[re.Pattern[str], ...]:
    suffix = path.suffix.lower()
    if suffix in (".yml", ".yaml"):
        return _COMPOSE_UP_PATTERNS_YAML
    if suffix == ".py":
        return _COMPOSE_UP_PATTERNS_PYTHON
    if suffix == ".cs":
        return (_COMPOSE_UP_PATTERN_CSHARP,)
    raise AssertionError(f"No compose-up callsite patterns defined for {path.suffix} files")


def _enumerate_compose_up_callsites(path: Path, text: str) -> list[tuple[int, str]]:
    """Return (offset, matched_substring) for every distinct compose-up callsite.

    Patterns are selected per file suffix so that shell-form strings inside
    Python log messages (e.g. ``"docker compose up failed"``) are NOT
    counted — only real subprocess.run argv literals are.
    """

    hits: list[tuple[int, str]] = []
    seen_offsets: set[int] = set()
    for pattern in _patterns_for(path):
        for match in pattern.finditer(text):
            offset = match.start()
            if any(abs(offset - existing) < 80 for existing in seen_offsets):
                continue
            seen_offsets.add(offset)
            hits.append((offset, match.group(0)))
    hits.sort(key=lambda item: item[0])
    return hits


def _callsite_is_gated_by_wait(text: str, offset: int, window: int = 1500) -> bool:
    """Return True iff a ``--wait`` argument appears within ``window`` chars of ``offset``."""
    return "--wait" in text[max(0, offset - 50) : offset + window]


# Maps named constants used in argv positions to their numeric values so
# the invariant can validate non-literal timeouts:
#   - C# fixture uses DockerCompose(Warm|Cold)WaitTimeoutSeconds.
#   - Python runners use COMPOSE_WAIT_TIMEOUT_(WARM|COLD)_SECONDS imported
#     from ijt_live_readiness.
_NAMED_TIMEOUT_CONSTANTS = {
    "DockerComposeWarmWaitTimeoutSeconds": "120",
    "DockerComposeColdWaitTimeoutSeconds": "300",
    "COMPOSE_WAIT_TIMEOUT_WARM_SECONDS": "120",
    "COMPOSE_WAIT_TIMEOUT_COLD_SECONDS": "300",
}


def _callsite_wait_timeout(text: str, offset: int, window: int = 1500) -> str | None:
    """Return the ``--wait-timeout`` value adjacent to a callsite, or None.

    Accepts numeric literals (Python argv lists, YAML shell args) and the
    named Python / C# constants documented in ``_NAMED_TIMEOUT_CONSTANTS``.
    Returns the resolved numeric value as a string.
    """
    blob = text[max(0, offset - 50) : offset + window]
    numeric = re.search(
        r"""--wait-timeout(?:["']?(?:\s*[,=]\s*|\s+)["']?)(\d+)""",
        blob,
    )
    if numeric:
        return numeric.group(1)
    if "--wait-timeout" in blob:
        for name, value in _NAMED_TIMEOUT_CONSTANTS.items():
            if name in blob:
                return value
    return None


def test_every_compose_up_caller_uses_compose_wait() -> None:
    failures: list[str] = []
    for path, expected_count in COMPOSE_UP_EXPECTED_CALLSITES.items():
        assert path.is_file(), f"Missing tracked compose caller: {path}"
        text = _read(path)
        callsites = _enumerate_compose_up_callsites(path, text)
        rel = path.relative_to(REPO_ROOT)
        if len(callsites) != expected_count:
            failures.append(
                f"{rel}: expected {expected_count} ``docker compose up`` "
                f"callsite(s), found {len(callsites)} at offsets "
                f"{[o for o, _ in callsites]}. Update "
                "COMPOSE_UP_EXPECTED_CALLSITES in this test so the change is "
                "explicit and gate every new callsite with ``--wait``."
            )
            continue
        for index, (offset, snippet) in enumerate(callsites, start=1):
            if not _callsite_is_gated_by_wait(text, offset):
                failures.append(
                    f"{rel} (callsite #{index} @ offset {offset}, "
                    f"{snippet!r}): missing ``--wait`` in the surrounding "
                    "argument window. Every individual compose-up MUST be "
                    "gated by ``--wait --wait-timeout <N>`` so compose itself "
                    "is the synchronization primitive — no external poll loops."
                )
                continue
            timeout_value = _callsite_wait_timeout(text, offset)
            if timeout_value is None:
                failures.append(
                    f"{rel} (callsite #{index} @ offset {offset}): ``--wait`` "
                    "present but no numeric ``--wait-timeout <N>`` value "
                    "could be parsed from the adjacent argument window."
                )
            elif timeout_value not in ALLOWED_WAIT_TIMEOUTS:
                failures.append(
                    f"{rel} (callsite #{index} @ offset {offset}): "
                    f"``--wait-timeout {timeout_value}`` is not in the "
                    f"allowed set {sorted(ALLOWED_WAIT_TIMEOUTS)}. Use the "
                    "named constants COMPOSE_WAIT_TIMEOUT_WARM_SECONDS=120 "
                    "or COMPOSE_WAIT_TIMEOUT_COLD_SECONDS=300."
                )
    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────────────────────────────────────
# The C# live-test fixture must use protocol readiness, not a port-open sleep
# loop.
# ─────────────────────────────────────────────────────────────────────────────


def test_csharp_fixture_has_no_thread_sleep_port_wait() -> None:
    fixture_path = (
        REPO_ROOT
        / "OPC_UA_Clients"
        / "Release2"
        / "IJT_CSharp_Client"
        / "Tests"
        / "IJT_CSharp_Client.Tests"
        / "OpcUaServerFixture.cs"
    )
    source = _read(fixture_path)
    # WaitForPort (the readiness variant) MUST be gone. WaitForPortClosed is
    # for stale-process cleanup and is explicitly allowlisted.
    assert "private static bool WaitForPort(" not in source, (
        "OpcUaServerFixture.cs must not define a Thread.Sleep-based "
        "WaitForPort happy-path wait. Use ProbeOpcUaReady (which retries "
        "internally) for readiness, and let ``docker compose up --wait`` "
        "synchronize on the compose healthcheck for the Docker path."
    )
    assert "WaitForPort(_port" not in source, (
        "OpcUaServerFixture.cs must not call WaitForPort(_port, ...) for "
        "readiness gating. The protocol probe is the single readiness "
        "contract."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Every workflow job that runs start_server_on_port.py must upload readiness
# diagnostics.
# ─────────────────────────────────────────────────────────────────────────────


_DIAG_DIR_RE = re.compile(r"--diagnostics-dir\s+([^\s\\`]+)")


def test_workflow_jobs_pass_diagnostics_dir_and_upload_it() -> None:
    failures: list[str] = []

    for workflow_path in START_SERVER_WORKFLOWS:
        workflow = _load_workflow(workflow_path)
        workflow_rel = workflow_path.relative_to(REPO_ROOT)
        jobs = workflow.get("jobs") or {}

        for job_id, job in jobs.items():
            diag_dirs: list[str] = []
            runs_script = False
            for step in job.get("steps") or []:
                run = step.get("run") or ""
                if "start_server_on_port.py" in run:
                    runs_script = True
                    # Allow `--stop` invocations to skip the diag flag.
                    if "--stop" in run:
                        continue
                    matches = _DIAG_DIR_RE.findall(run)
                    if not matches:
                        failures.append(
                            f"{workflow_rel} job '{job_id}' invokes start_server_on_port.py "
                            "without ``--diagnostics-dir <PATH>``; readiness failures "
                            "will be undiagnosable in CI."
                        )
                    else:
                        diag_dirs.extend(matches)

            if not runs_script:
                continue

            # Each diagnostics dir must appear inside at least one upload-artifact
            # step's ``path:`` block.
            upload_paths_blobs: list[str] = []
            for step in job.get("steps") or []:
                uses = step.get("uses") or ""
                if uses.startswith("actions/upload-artifact@"):
                    with_block = step.get("with") or {}
                    path_val = with_block.get("path") or ""
                    upload_paths_blobs.append(str(path_val))

            if not upload_paths_blobs:
                failures.append(
                    f"{workflow_rel} job '{job_id}' invokes start_server_on_port.py "
                    "but has no upload-artifact step. Diagnostics manifests would be lost."
                )
                continue

            upload_paths_joined = "\n".join(upload_paths_blobs)
            for diag_dir in diag_dirs:
                covered = (
                    diag_dir in upload_paths_joined
                    or any(
                        diag_dir.startswith(p.rstrip("/"))
                        for p in re.split(r"\s+", upload_paths_joined)
                        if p
                    )
                    or any(
                        p.rstrip("/").startswith(diag_dir.split("/readiness")[0])
                        for p in re.split(r"\s+", upload_paths_joined)
                        if p
                    )
                )
                if not covered:
                    failures.append(
                        f"{workflow_rel} job '{job_id}': diagnostics-dir {diag_dir!r} "
                        "is not covered by any upload-artifact path. Existing "
                        f"upload paths:\n{upload_paths_joined}"
                    )

    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────────────────────────────────────
# Compose wait budgets must use the documented warm and cold values.
# ─────────────────────────────────────────────────────────────────────────────


def test_compose_wait_timeouts_use_allowed_values_only() -> None:
    failures: list[str] = []
    for path in COMPOSE_UP_EXPECTED_CALLSITES:
        text = _read(path)
        rel = path.relative_to(REPO_ROOT)
        for value in _extract_wait_timeouts(text):
            if value not in ALLOWED_WAIT_TIMEOUTS:
                failures.append(
                    f"{rel}: --wait-timeout {value!r} is not in the "
                    f"allowlist {sorted(ALLOWED_WAIT_TIMEOUTS)}. "
                    "Use 120 for warm/cached paths and 300 for cold-build paths. "
                    "Add a new value here only after raising the compose "
                    "healthcheck budget AND updating this test."
                )
    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────────────────────────────────────
# Direct OPC UA live-server start paths must use OPC UA HELLO readiness.
#
# These direct, non-compose server-start surfaces previously used raw port-open
# loops as the consumer synchronization contract. They must stay on the shared
# OPC UA HELLO probe instead.
# ─────────────────────────────────────────────────────────────────────────────

_TCP_ONLY_OPCUA_READINESS_FORBIDDEN: dict[Path, tuple[str, ...]] = {
    REPO_ROOT / ".github" / "workflows" / "ci.yml": (
        "Test-NetConnection -ComputerName localhost -Port 40451",
        "Wait for OPC UA port 40451",
        "Start-Sleep -Seconds 3",
    ),
    REPO_ROOT / "OPC_UA_Servers" / "Release2" / "run_all_tests.py": (
        "def _wait_for_port(",
        "_wait_for_port(host, port",
        "server did not open port",
    ),
    REPO_ROOT
    / "OPC_UA_Clients"
    / "Release2"
    / "IJT_Console_Client"
    / "tests"
    / "live"
    / "conftest.py": (
        "def _wait_for_port(",
        "_wait_for_port(host, port",
        "port {port} did not open within",
    ),
}


def test_direct_opcua_server_start_paths_use_hello_not_tcp_only() -> None:
    failures: list[str] = []
    for path, forbidden_snippets in _TCP_ONLY_OPCUA_READINESS_FORBIDDEN.items():
        assert path.is_file(), f"Missing tracked OPC UA readiness caller: {path}"
        source = _read(path)
        rel = path.relative_to(REPO_ROOT)
        for snippet in forbidden_snippets:
            if snippet in source:
                failures.append(
                    f"{rel}: found TCP-only OPC UA readiness snippet {snippet!r}. "
                    "Use scripts/ijt_live_readiness.wait_for_opcua_hello or "
                    "scripts/start_server_on_port.py instead."
                )
    assert not failures, "\n".join(failures)


# ─────────────────────────────────────────────────────────────────────────────
# The Web Docker unit-test image must be able to import the shared readiness
# module.
#
# The Web Client Docker test target copies only the Web subtree into /app. A
# fixed repo-root depth lookup works in a normal checkout but crashes in that
# flattened Docker layout, so the helper must discover the shared script by
# walking ancestors and the Dockerfile must vendor the script into /app/scripts.
# ─────────────────────────────────────────────────────────────────────────────


def test_web_docker_test_image_vendors_shared_readiness_module() -> None:
    dockerignore = _read(DOCKERIGNORE)
    dockerfile = _read(WEB_CLIENT_DOCKERFILE)
    helper = _read(WEB_CLIENT_READINESS_HELPER)

    assert "COPY scripts/ijt_live_readiness.py /app/scripts/ijt_live_readiness.py" in dockerfile, (
        "The Web Client Docker test target must vendor scripts/ijt_live_readiness.py "
        "into /app/scripts so tests/python/_live_server_readiness.py can import "
        "the shared module inside the flattened /app Docker layout."
    )
    assert "parents[5]" not in helper, (
        "The Web Client readiness helper must not assume the full repository path "
        "depth. Docker unit tests run from a flattened /app tree, where parents[5] "
        "raises IndexError during test collection."
    )
    assert "def _find_shared_readiness_scripts_dir()" in helper, (
        "The Web Client readiness helper must locate scripts/ijt_live_readiness.py "
        "by discovery rather than by hard-coded path depth."
    )
    assert "!scripts/" in dockerignore and "!scripts/ijt_live_readiness.py" in dockerignore, (
        ".dockerignore must allowlist scripts/ijt_live_readiness.py. The Web "
        "Client test Dockerfile uses the repo root as build context, and the "
        "root .dockerignore excludes everything by default."
    )
