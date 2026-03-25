#!/usr/bin/env python3
"""
IJT Web Client — Cross-Platform Test Runner
============================================
Works on: Windows, Linux, macOS, Docker, WSL
Requires: Python 3.11+  (already installed for this project)
No PowerShell, no bash, no special shell required.

Usage:
  python run_all_tests.py               # unit tests + smoke only (fast)
  python run_all_tests.py --all         # every stage
  python run_all_tests.py --integration # unit + live OPC UA tests
  python run_all_tests.py --e2e         # unit + Playwright E2E
  python run_all_tests.py --list        # print stages and exit

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
CONSOLE_DIR = ROOT.parent.parent / "IJT_Console_Client"
# Support both flat layout and Release2 layout
if not CONSOLE_DIR.exists():
    CONSOLE_DIR = ROOT.parent / "IJT_Console_Client"
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
    except Exception:
        pass
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
    print(f"\n{_C.DIM}CMD: {' '.join(str(c) for c in cmd)}{_C.RESET}")
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
    """Parse 'opc.tcp://host:port' → (host, port)."""
    clean = endpoint.replace("opc.tcp://", "").replace("opc.tcp//", "")
    if ":" in clean:
        host, port_str = clean.rsplit(":", 1)
        return host, int(port_str)
    return clean, 4840


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


def _stage_console_client(python: Path) -> StageResult:
    _banner("STAGE 8  IJT Console Client tests")
    t0 = time.monotonic()
    if not CONSOLE_DIR.exists():
        _warn(f"Console client not found at {CONSOLE_DIR}")
        return StageResult("console-client", 0, skipped=True)

    req = CONSOLE_DIR / "requirements.txt"
    if req.exists():
        _run(
            [python, "-m", "pip", "install",
             "--quiet", "--disable-pip-version-check", "--pre",
             "-r", str(req)],
            cwd=CONSOLE_DIR,
            label="pip install console deps",
        )

    tests_dir = CONSOLE_DIR / "tests"
    if not tests_dir.exists():
        _warn("Console client has no tests/ directory — skipping")
        return StageResult("console-client", 0, skipped=True)

    rc = _run(
        [python, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
        cwd=CONSOLE_DIR,
        label="pytest console client",
    )
    return StageResult("console-client", rc, duration=time.monotonic() - t0)


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
    "playwright-e2e", "console-client",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="IJT Web Client cross-platform test runner",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--all",          action="store_true",
                        help="Run every stage (unit + live + E2E + console)")
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

    _banner("IJT Web Client — Cross-Platform Test Runner")
    _info(f"Python  : {python}")
    _info(f"Root    : {ROOT}")
    _info(f"OS      : {sys.platform} / {platform.machine()}")
    _info(f"Mode    : {'--all' if args.all else '--integration' if run_live else '--e2e' if run_e2e else 'unit+smoke'}")

    # Check server availability upfront
    opcua_host, opcua_port = _parse_opcua_host_port(args.opcua_endpoint)
    opcua_up = _port_open(opcua_host, opcua_port)
    ws_up    = _port_open("localhost", 8001)

    if run_live and not opcua_up:
        _warn(f"OPC UA server NOT reachable at {args.opcua_endpoint}")
    if run_e2e and not ws_up:
        _warn(f"WebSocket backend NOT reachable at {args.ws_url}")

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

    # ── Playwright (smoke always runs; E2E only when --e2e/--all) ─────────────
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

    # ── Console client ────────────────────────────────────────────────────────
    results.append(_stage_console_client(python))

    return _print_summary(results, time.monotonic() - t_start)


if __name__ == "__main__":
    raise SystemExit(main())
