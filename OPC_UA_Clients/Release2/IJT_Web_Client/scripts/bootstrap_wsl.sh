#!/usr/bin/env bash
# Thin WSL wrapper — all OS-provisioning logic lives in setup_project.py.
# This script detects WSL, then delegates to Python immediately.
#
# Usage:
#   bash scripts/bootstrap_wsl.sh
#   RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh
#   PROJECT_DIR=/mnt/c/.../IJT_Web_Client bash scripts/bootstrap_wsl.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
RUN_PROJECT_SETUP="${RUN_PROJECT_SETUP:-0}"

# Verify this is running inside WSL.
if ! grep -qi "microsoft" /proc/version 2>/dev/null; then
  echo "[bootstrap_wsl] ERROR: This script must be run inside WSL (Linux)." >&2
  exit 1
fi

# Build extra args for setup_project.py.
_extra=""
if [[ "$RUN_PROJECT_SETUP" == "1" ]]; then
  _extra="--run-project-setup"
fi

# Delegate entirely to Python.  system python3 is available on all WSL Ubuntu
# images before Python 3.14 is installed — that is intentional.
exec python3 "$PROJECT_DIR/setup_project.py" --bootstrap-wsl ${_extra}
