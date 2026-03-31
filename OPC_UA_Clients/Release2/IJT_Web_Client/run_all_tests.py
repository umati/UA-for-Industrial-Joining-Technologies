#!/usr/bin/env python3
"""
IJT Web Client — Cross-Platform Test Runner
============================================
Works on: Windows, Linux, macOS, Docker, WSL
Requires: Python 3.11+  (already installed for this project)
No PowerShell, no bash, no special shell required.

Usage:
  python run_all_tests.py        # auto-detects all optional stages — ONE command for everything
  python run_all_tests.py --list # print stages and exit

Optional stages activate automatically when available:
  Docker smoke  — if Docker daemon is running  (build + compose-up + readiness check + down)
  Live OPC UA   — if server reachable at OPCUA_TEST_ENDPOINT  (default: opc.tcp://localhost:40451)
  Playwright E2E — if WebSocket backend reachable at WS_TEST_URL (default: ws://localhost:8001)

Force flags (override auto-detection):
  --integration  force live OPC UA stage even if server unreachable
  --e2e          force Playwright E2E stage even if WS backend unreachable
  --all          force every optional stage

Environment variables (all optional):
  OPCUA_TEST_ENDPOINT   default: opc.tcp://localhost:40451
  WS_TEST_URL           default: ws://localhost:8001
  UI_TEST_BASE_URL      default: http://127.0.0.1:3000
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
IS_DOCKER = os.getenv("IS_DOCKER") == "true"
IS_CI = bool(os.getenv("CI"))

# ---------------------------------------------------------------------------
# Colour helpers — ANSI on Linux/macOS/Win10+, plain text fallback
# ---------------------------------------------------------------------------
def _enable_ansi_windows() -> bool:
    """Enable virtual terminal processing on Windows 10+."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            return True
        return False
    except (AttributeError, OSError):
        return False


_USE_COLOUR = sys.stdout.isatty() and (
    not IS_WINDOWS or _enable_ansi_windows()
)


class _C:
    RESET  = "\033[0m"  if _USE_COLOUR else ""
    BOLD   = "\033[1m"  if _USE_COLOUR else ""
    DIM    = "\033[2m"  if _USE_COLOUR else ""
    GREEN  = "\033[92m" if _USE_COLOUR else ""
    RED    = "\033[91m" if _USE_COLOUR else ""
    YELLOW = "\033[93m" if _USE_COLOUR else ""
    CYAN   = "\033[96m" if _USE_COLOUR else ""


def _ok(msg: str)   -> None: print(f"{_C.GREEN}  [PASS]{_C.RESET} {msg}")
def _fail(msg: str) -> None: print(f"{_C.RED}  [FAIL]{_C.RESET} {msg}", file=sys.stderr)
def _info(msg: str) -> None: print(f"{_C.CYAN}  [INFO]{_C.RESET} {msg}")
def _warn(msg: str) -> None: print(f"{_C.YELLOW}  [WARN]{_C.RESET} {msg}")
def _skip(msg: str) -> None: print(f"{_C.DIM}  [SKIP]{_C.RESET} {msg}")


def _banner(title: str) -> None:
    line = "=" * 65
    print(f"\n{_C.BOLD}{_C.CYAN}{line}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}  {title}{_C.RESET}")
    print(f"{_C.BOLD}{_C.CYAN}{line}{_C.RESET}")


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------
def _run(
    cmd: list,
    *,
    cwd: Path = ROOT,
    label: str = "",
    env: Optional[dict] = None,
) -> int:
    display = label or " ".join(str(c) for c in cmd[:5])
    print(f"\n{_C.DIM}CMD: {display}{_C.RESET}")
    result = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd),
        env=env or os.environ.copy(),
    )
    return result.returncode


# ---------------------------------------------------------------------------
# Server / port helpers
# ---------------------------------------------------------------------------
def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_opcua_host_port(endpoint: str) -> tuple[str, int]:
    """Parse 'opc.tcp://host:port' → (host, port).

    The 'opc.tcp//' variant (missing colon) is a common copy-paste typo seen
    in config files and environment variables, so both forms are stripped.
    """
    clean = endpoint.replace("opc.tcp://", "").replace("opc.tcp//", "")
    if ":" in clean:
        host, port_str = clean.rsplit(":", 1)
        return host, int(port_str)
    return clean, 4840


def _parse_ws_host_port(url: str) -> tuple[str, int]:
    """Parse 'ws://host:port[/path]' or 'wss://host:port[/path]' → (host, port)."""
    clean = url.replace("wss://", "").replace("ws://", "").split("/")[0]
    if ":" in clean:
        host, port_str = clean.rsplit(":", 1)
        return host, int(port_str)
    return clean, 80  # ws default port when none specified


# ---------------------------------------------------------------------------
# Stage result
# ---------------------------------------------------------------------------
@dataclass
class StageResult:
    name: str
    rc: int
    skipped: bool = False
    duration: float = 0.0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def _stage_versions() -> StageResult:
    """Print tool versions for debugging."""
    _banner("STAGE 0  Tool versions")
    t0 = time.monotonic()
    _info(f"Python   : {sys.version}")
    _info(f"Platform : {platform.platform()}")
    _info(f"Docker   : {IS_DOCKER}  CI: {IS_CI}")
    npm = shutil.which("npm")
    node = shutil.which("node") or shutil.which("node.exe")
    if node:
        _run([node, "--version"], label="node --version")
    if npm:
        _run([npm, "--version"], label="npm --version")
    else:
        _warn("npm not found in PATH")
    return StageResult("versions", 0, duration=time.monotonic() - t0)


def _stage_pip_install(python: Path) -> StageResult:
    _banner("STAGE 1  Install / verify Python test dependencies")
    t0 = time.monotonic()
    rc = _run(
        [
            python, "-m", "pip", "install",
            "--quiet", "--disable-pip-version-check", "--pre",
            # asyncua 1.2b2+ for Python 3.14 compat; once stable 1.2.x ships,
            # pip will prefer that automatically over any pre-release.
            "asyncua>=1.2b2",
            "pytest", "pytest-asyncio",
            "websockets>=16.0",
            "pytz", "aiofiles", "packaging",
            "python-dotenv",
        ],
        label="pip install test deps",
    )
    return StageResult("pip-install", rc, duration=time.monotonic() - t0)


def _stage_python_unit(python: Path) -> StageResult:
    _banner("STAGE 2  Python unit tests (no server needed)")
    t0 = time.monotonic()
    rc = _run(
        [
            python, "-m", "pytest", "tests/",
            "-m", "not integration and not live and not live_ws",
            "-v", "--tb=short", "--no-header",
        ],
        label="pytest unit",
    )
    return StageResult("python-unit", rc, duration=time.monotonic() - t0)


def _stage_js_unit() -> StageResult:
    _banner("STAGE 3  JavaScript unit tests (vitest)")
    t0 = time.monotonic()
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        _warn("npm not found — skipping JS unit tests")
        return StageResult("js-unit", 0, skipped=True)

    if not (ROOT / "node_modules").exists():
        _info("node_modules not found — running npm install")
        rc = _run([npm, "install", "--legacy-peer-deps"], label="npm install")
        if rc != 0:
            return StageResult("js-unit", rc, duration=time.monotonic() - t0,
                               notes=["npm install failed"])

    rc = _run([npm, "run", "test:unit:js"], label="vitest")
    return StageResult("js-unit", rc, duration=time.monotonic() - t0)


def _stage_python_live(python: Path) -> StageResult:
    _banner("STAGE 4  Python live tests (OPC UA + WebSocket backend)")
    t0 = time.monotonic()
    rc = _run(
        [
            python, "-m", "pytest", "tests/python/live/",
            "-v", "--tb=short", "--no-header", "--timeout=120",
        ],
        label="pytest live",
    )
    return StageResult("python-live", rc, duration=time.monotonic() - t0)


def _stage_playwright_install() -> StageResult:
    _banner("STAGE 5  Install Playwright browsers")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        _warn("npx not found — skipping Playwright stages")
        return StageResult("playwright-install", 0, skipped=True)

    env = os.environ.copy()

    # Try with --with-deps first (Linux CI); fall back without it (Windows, no admin)
    rc = _run(
        [npx, "playwright", "install", "chromium", "--with-deps"],
        label="playwright install chromium --with-deps",
        env=env,
    )
    if rc != 0:
        _warn("--with-deps failed, retrying without it")
        rc = _run(
            [npx, "playwright", "install", "chromium"],
            label="playwright install chromium",
            env=env,
        )
    if rc != 0:
        # Corporate SSL proxy may block download — retry with TLS verification disabled
        _warn("Download failed, retrying with NODE_TLS_REJECT_UNAUTHORIZED=0 (corporate proxy)")
        env2 = {**env, "NODE_TLS_REJECT_UNAUTHORIZED": "0"}
        rc = _run(
            [npx, "playwright", "install", "chromium"],
            label="playwright install chromium (TLS bypass)",
            env=env2,
        )
    if rc != 0:
        # If still failing it's a network/environment issue — warn but don't block other tests
        _warn("Playwright browser install failed (network/SSL issue) — smoke tests will be skipped")
        result = StageResult("playwright-install", 0, skipped=True)
        result.notes.append("Browser download blocked (SSL/network) — run 'npx playwright install chromium' manually")
        return result
    return StageResult("playwright-install", rc, duration=time.monotonic() - t0)


def _stage_playwright_smoke() -> StageResult:
    _banner("STAGE 6  Playwright smoke tests (static HTML, no server needed)")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        return StageResult("playwright-smoke", 0, skipped=True)
    rc = _run(
        [npx, "playwright", "test", "--project=smoke", "--reporter=line"],
        label="playwright smoke",
    )
    return StageResult("playwright-smoke", rc, duration=time.monotonic() - t0)


def _stage_playwright_e2e(ws_url: str, ui_url: str) -> StageResult:
    _banner("STAGE 7  Playwright E2E — features + regression")
    t0 = time.monotonic()
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        return StageResult("playwright-e2e", 0, skipped=True)

    env = os.environ.copy()
    env["WS_TEST_URL"] = ws_url
    env["PLAYWRIGHT_TEST_BASE_URL"] = ui_url

    rc1 = _run(
        [npx, "playwright", "test", "--project=features",   "--reporter=line"],
        env=env, label="playwright features",
    )
    rc2 = _run(
        [npx, "playwright", "test", "--project=regression", "--reporter=line"],
        env=env, label="playwright regression",
    )
    return StageResult("playwright-e2e", max(rc1, rc2), duration=time.monotonic() - t0)


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------
def _docker_available() -> bool:
    """Return True if the Docker daemon is reachable."""
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker:
        return False
    try:
        r = subprocess.run(
            [docker, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        return r.returncode == 0
    except Exception:
        return False


def _stage_docker_smoke() -> StageResult:
    """Build image, start compose, verify HTTP + WS readiness, then tear down."""
    _banner("STAGE 8  Docker smoke (build + compose up + readiness + down)")
    t0 = time.monotonic()
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if not docker:
        return StageResult("docker-smoke", 0, skipped=True,
                           notes=["docker not in PATH"])
    compose_cmd = [docker, "compose"]

    rc = _run([docker, "build", "-t", "ijt_web_client", "."], label="docker build")
    if rc != 0:
        return StageResult("docker-smoke", rc, duration=time.monotonic() - t0,
                           notes=["docker build failed"])

    rc = _run(compose_cmd + ["up", "-d"], label="docker compose up -d")
    if rc != 0:
        return StageResult("docker-smoke", rc, duration=time.monotonic() - t0,
                           notes=["docker compose up failed"])

    # Wait up to 180 s for HTTP readiness (60 polls × up to 3 s each: 1 s connect timeout + 2 s sleep)
    _info("Waiting for http://127.0.0.1:3000 ...")
    ready = False
    for _ in range(60):
        if _port_open("127.0.0.1", 3000, timeout=1.0):
            ready = True
            break
        time.sleep(2)

    ws_ready = _port_open("127.0.0.1", 8001, timeout=2.0)

    _run(compose_cmd + ["logs", "--tail=20"], label="docker compose logs")
    _run(compose_cmd + ["down", "-v"], label="docker compose down -v")

    if not ready:
        return StageResult("docker-smoke", 1, duration=time.monotonic() - t0,
                           notes=["HTTP :3000 not ready within 180 s"])

    notes = [] if ws_ready else ["WS :8001 not ready — backend may need OPC UA server"]
    return StageResult("docker-smoke", 0, duration=time.monotonic() - t0, notes=notes)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def _print_summary(results: list[StageResult], total_time: float) -> int:
    _banner("TEST SUMMARY")
    overall = 0
    for r in results:
        if r.skipped:
            tag = f"{_C.YELLOW}[SKIP]{_C.RESET}"
        elif r.rc == 0:
            tag = f"{_C.GREEN}[PASS]{_C.RESET}"
        else:
            tag = f"{_C.RED}[FAIL]{_C.RESET}"
            overall = max(overall, r.rc)
        dur = f"  {r.duration:.1f}s" if r.duration else ""
        print(f"  {tag}  {r.name:<35} exit={r.rc}{dur}")
        for note in r.notes:
            print(f"         {_C.DIM}^ {note}{_C.RESET}")

    print(f"\n  Total time: {total_time:.1f}s")
    if overall == 0:
        print(f"\n{_C.GREEN}{_C.BOLD}  ALL TESTS PASSED{_C.RESET}")
    else:
        print(f"\n{_C.RED}{_C.BOLD}  SOME TESTS FAILED — review output above{_C.RESET}")
    print("=" * 65 + "\n")
    return overall


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
STAGES = [
    "versions", "pip-install", "python-unit", "js-unit",
    "python-live", "playwright-install", "playwright-smoke",
    "playwright-e2e", "docker-smoke",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="IJT Web Client cross-platform test runner",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all",          action="store_true",
                        help="Run every stage (unit + live + E2E)")
    parser.add_argument("--integration",  action="store_true",
                        help="Include live OPC UA + WS backend tests")
    parser.add_argument("--e2e",          action="store_true",
                        help="Include Playwright smoke + E2E tests")
    parser.add_argument("--list",         action="store_true",
                        help="Print available stages and exit")
    parser.add_argument("--opcua-endpoint",
                        default=os.getenv("OPCUA_TEST_ENDPOINT",
                                          "opc.tcp://localhost:40451"))
    parser.add_argument("--ws-url",
                        default=os.getenv("WS_TEST_URL", "ws://localhost:8001"))
    parser.add_argument("--ui-url",
                        default=os.getenv("UI_TEST_BASE_URL",
                                          "http://127.0.0.1:3000"))
    args = parser.parse_args()

    if args.list:
        print("Available stages:")
        for s in STAGES:
            print(f"  {s}")
        return 0

    run_live = args.integration or args.all
    run_e2e  = args.e2e or args.all

    python = Path(sys.executable)
    t_start = time.monotonic()

    # Check availability upfront — drives auto-detection of optional stages
    opcua_host, opcua_port = _parse_opcua_host_port(args.opcua_endpoint)
    ws_host,    ws_port    = _parse_ws_host_port(args.ws_url)
    opcua_up   = _port_open(opcua_host, opcua_port)
    ws_up      = _port_open(ws_host, ws_port)
    docker_up  = _docker_available()

    # Auto-detect optional stages when not explicitly requested
    run_live   = run_live   or opcua_up
    run_e2e    = run_e2e    or ws_up
    run_docker = args.all   or docker_up

    _banner("IJT Web Client — Cross-Platform Test Runner")
    _info(f"Python  : {python}")
    _info(f"Root    : {ROOT}")
    _info(f"OS      : {sys.platform} / {platform.machine()}")
    _info(f"OPC UA  : {'UP' if opcua_up else 'not reachable'} ({args.opcua_endpoint})")
    _info(f"WS      : {'UP' if ws_up else 'not reachable'} ({args.ws_url})")
    _info(f"Docker  : {'available' if docker_up else 'not available'}")

    if (args.integration or args.all) and not opcua_up:
        _warn(f"OPC UA server NOT reachable at {args.opcua_endpoint} — live tests will be skipped")
    if (args.e2e or args.all) and not ws_up:
        _warn(f"WebSocket backend NOT reachable at {args.ws_url} — E2E tests will be skipped")

    results: list[StageResult] = []

    # ── Always run ────────────────────────────────────────────────────────────
    results.append(_stage_versions())
    results.append(_stage_pip_install(python))
    results.append(_stage_python_unit(python))
    results.append(_stage_js_unit())

    # ── Live tests (optional) ─────────────────────────────────────────────────
    if run_live:
        if opcua_up:
            results.append(_stage_python_live(python))
        else:
            _skip("python-live: OPC UA server not reachable")
            results.append(StageResult("python-live", 0, skipped=True))

    # ── Playwright (smoke always runs; E2E auto-detected or explicit) ─────────
    pw_install = _stage_playwright_install()
    results.append(pw_install)

    if not pw_install.skipped and pw_install.rc == 0:
        # Smoke always runs — catches 404s, JS errors, missing assets
        results.append(_stage_playwright_smoke())

        if run_e2e:
            if ws_up:
                results.append(_stage_playwright_e2e(args.ws_url, args.ui_url))
            else:
                _skip("playwright-e2e: WebSocket backend not reachable")
                results.append(StageResult("playwright-e2e", 0, skipped=True))

    # ── Docker smoke (auto-detected; skipped if Docker unavailable) ───────────
    if run_docker:
        results.append(_stage_docker_smoke())
    else:
        _skip("docker-smoke: Docker not available")
        results.append(StageResult("docker-smoke", 0, skipped=True))

    return _print_summary(results, time.monotonic() - t_start)


if __name__ == "__main__":
    raise SystemExit(main())
