#!/usr/bin/env bash
set -euo pipefail

# Default: resolve relative to this script so it works in any clone location.
# Override by setting PROJECT_DIR in the environment before calling this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_DIR_DEFAULT}"
RUN_PROJECT_SETUP="${RUN_PROJECT_SETUP:-0}"

log() {
  echo "[bootstrap_wsl] $*"
}

require_sudo() {
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required but not available."
    exit 1
  fi
}

disable_puppet_repo_if_present() {
  local puppet_list
  puppet_list="$(grep -R -l 'apt.puppet.com' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null || true)"
  if [[ -z "${puppet_list}" ]]; then
    return 0
  fi

  log "Disabling Puppet apt repository entries with expired key (if enabled)."
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    sudo sed -i 's|^deb .*apt.puppet.com.*|# &|' "$file"
  done <<<"$puppet_list"
}

fix_system_python_for_apt() {
  if [[ -x /usr/bin/python3.12 ]]; then
    local current
    current="$(readlink -f /usr/bin/python3 || true)"
    if [[ "$current" != "/usr/bin/python3.12" ]]; then
      log "Restoring /usr/bin/python3 -> /usr/bin/python3.12 for apt tooling."
      sudo ln -sf /usr/bin/python3.12 /usr/bin/python3
    fi
  fi
}

install_base_packages() {
  log "Updating apt indexes."
  sudo apt update

  log "Installing base packages."
  sudo apt install -y \
    software-properties-common \
    curl \
    ca-certificates \
    build-essential \
    git \
    gnupg
}

ensure_deadsnakes() {
  if ! grep -Rqs "deadsnakes/ppa" /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then
    log "Adding deadsnakes PPA."
    sudo add-apt-repository -y ppa:deadsnakes/ppa
  fi
}

install_python_314() {
  log "Installing Python 3.14 toolchain."
  sudo apt update
  sudo apt install -y \
    python3.14 \
    python3.14-venv \
    python3.14-dev \
    python3-apt \
    command-not-found
}

install_node_24() {
  log "Installing Node.js 24.x."
  curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
  sudo apt install -y nodejs
}

verify_runtime() {
  log "Verifying runtime versions."
  python3 --version
  python3 -c "import apt_pkg; print('apt_pkg OK')"
  python3.14 --version
  node -v
  npm -v
  npx --version
}

run_project_setup_if_requested() {
  if [[ "$RUN_PROJECT_SETUP" != "1" ]]; then
    return 0
  fi

  if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "PROJECT_DIR does not exist: $PROJECT_DIR"
    exit 1
  fi

  log "Running project setup in: $PROJECT_DIR"
  (
    cd "$PROJECT_DIR"
    python3 setup_project.py
  )
}

print_next_steps() {
  cat <<EOF

Completed WSL bootstrap.

Next steps:
1. cd "$PROJECT_DIR"
2. python3 setup_project.py
3. python3 scripts/run_tests.py
4. python3 scripts/run_regression.py
5. python3 scripts/run_cross_client_regression.py

Optional:
- Run setup automatically in this script:
  RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh
- Use custom repo path:
  PROJECT_DIR=/mnt/c/.../IJT_Web_Client bash scripts/bootstrap_wsl.sh
EOF
}

main() {
  require_sudo
  fix_system_python_for_apt
  disable_puppet_repo_if_present
  install_base_packages
  ensure_deadsnakes
  install_python_314
  install_node_24
  verify_runtime
  run_project_setup_if_requested
  print_next_steps
}

main "$@"
