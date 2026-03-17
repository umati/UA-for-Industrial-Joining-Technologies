#!/usr/bin/env python3
import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from venv_bootstrap import ensure_test_env, is_current_interpreter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _endpoint_reachable(endpoint: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(endpoint)
    host = parsed.hostname or "localhost"
    port = parsed.port or 40451
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tests using the project virtual environment")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (marker=integration)",
    )
    parser.add_argument(
        "--skip-regression",
        action="store_true",
        help="Skip post-integration regression scenario execution.",
    )
    parser.add_argument(
        "--ws-url",
        default=os.getenv("WS_TEST_URL", "ws://localhost:8001"),
        help="Backend websocket URL used by regression script.",
    )
    parser.add_argument(
        "--regression-out",
        default=str(PROJECT_ROOT / "regression_report.json"),
        help="Output path for regression JSON report.",
    )
    parser.add_argument(
        "--ui-base-url",
        default=os.getenv("UI_TEST_BASE_URL", "http://127.0.0.1:3000"),
        help="Base URL for browser UI assertions.",
    )
    args = parser.parse_args()

    test_python = ensure_test_env(PROJECT_ROOT)
    if not is_current_interpreter(test_python):
        cmd = [str(test_python), str(Path(__file__).resolve()), *sys.argv[1:]]
        return subprocess.call(cmd, cwd=str(PROJECT_ROOT))

    marker = "integration" if args.integration else "not integration"
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
    if not _endpoint_reachable(endpoint):
        print(
            f"[WARN] No OPC UA Server running on {endpoint}. "
            "If clients and simulator are in separate folders/downloads, start the server before running tests.",
            file=sys.stderr,
        )

    cmd = [str(test_python), "-m", "pytest", str(PROJECT_ROOT / "tests"), "-m", marker]
    print("Running:", " ".join(cmd))
    pytest_rc = subprocess.call(cmd)
    if pytest_rc != 0:
        return pytest_rc

    if args.integration and not args.skip_regression:
        regression_script = PROJECT_ROOT / "scripts" / "run_regression.py"
        regression_cmd = [
            str(test_python),
            str(regression_script),
            "--endpoint",
            endpoint,
            "--ws-url",
            args.ws_url,
            "--out",
            args.regression_out,
            "--ui-assertions",
            "--ui-base-url",
            args.ui_base_url,
        ]
        print("Running post-integration regression:", " ".join(regression_cmd))
        return subprocess.call(regression_cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
