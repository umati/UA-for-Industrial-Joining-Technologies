#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
VENV_PYTHON = Path("venv") / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tests using the project virtual environment")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (marker=integration)",
    )
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        print(
            "Virtual environment not found. Run 'python setup_project.py --force_full' first.",
            file=sys.stderr,
        )
        return 1

    marker = "integration" if args.integration else "not integration"
    cmd = [str(VENV_PYTHON), "-m", "pytest", "tests", "-m", marker]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
