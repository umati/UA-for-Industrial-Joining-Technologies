# ─────────────────────────────────────────────────────────────────────────────
# OPC UA IJT Server Simulator — Docker Image (Linux native)
#
# The server is a Linux x64 ELF binary (statically linked C++ runtime):
#   - Built with CMake/WSL2 toolset on Ubuntu 24.04, C++17, Release|x64
#   - Requires glibc 2.38+ (built on Ubuntu 24.04 / glibc 2.39)
#   - No Wine, no Xvfb, no DISPLAY needed
#
# Base image: ubuntu:24.04 — matches build machine glibc (2.39)
#
# Build (from this Release2/ directory):
#   docker build -t opcua-ijt-server .
#
# Run:
#   docker run --rm -p 40451:40451 opcua-ijt-server
#   docker compose up                                   # recommended
#
# Override advertised hostname for remote OPC UA clients:
#   docker run --rm -p 40451:40451 -e OPCUA_HOSTNAME=192.168.1.10 opcua-ijt-server
# ─────────────────────────────────────────────────────────────────────────────

FROM ubuntu:24.04

WORKDIR /app

# ── Extract server ZIP + install system utilities ─────────────────────────────
# All steps in one layer: install unzip, extract, purge unzip → no size bloat.
# iproute2       : IP address detection for OPCUA_HOSTNAME auto-resolve
# netcat-openbsd : TCP probe used in HEALTHCHECK
# hadolint ignore=DL3008,DL3009
COPY OPC_UA_IJT_Server_Simulator_Linux.zip /tmp/server.zip

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iproute2 \
        netcat-openbsd \
        unzip && \
    unzip -q /tmp/server.zip -d /tmp/ && \
    cp -a /tmp/OPC_UA_IJT_Server_Simulator_Linux/. /app/ && \
    chmod +x /app/opcua_ijt_demo_application && \
    mkdir -p /app/pki && \
    apt-get purge -y unzip && \
    apt-get autoremove -y && \
    rm -rf /tmp/server.zip /tmp/OPC_UA_IJT_Server_Simulator_Linux /var/lib/apt/lists/*

# ── Entrypoint — inline shell script written to /entrypoint.sh ───────────────
# Kept inline (heredoc) so the entire Docker configuration lives in one file.
# Shell is the right choice here: bash is guaranteed in every Linux container,
# and the script only does hostname detection + exec — no need for Python.
# hadolint ignore=SC2016
RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    '' \
    '# Resolve OPCUA_HOSTNAME: explicit env > host.docker.internal > default route > 0.0.0.0' \
    'if [ -z "${OPCUA_HOSTNAME:-}" ]; then' \
    '  OPCUA_HOSTNAME=$(getent hosts host.docker.internal 2>/dev/null | awk "{print \$1}" | head -1) || true' \
    '  if [ -z "$OPCUA_HOSTNAME" ]; then' \
    '    # Extract src IP from: "1.0.0.0 via <gw> dev <if> src <ip> uid 0"' \
    '    OPCUA_HOSTNAME=$(ip route get 1.0.0.0 2>/dev/null | grep -oP "src \K\S+") || true' \
    '  fi' \
    '  OPCUA_HOSTNAME="${OPCUA_HOSTNAME:-0.0.0.0}"' \
    'fi' \
    'export OPCUA_HOSTNAME' \
    '' \
    'echo "[INFO] OPC UA IJT Server Simulator"' \
    'echo "[INFO] Endpoint : opc.tcp://${OPCUA_HOSTNAME}:40451"' \
    '' \
    '[ -f opcua_ijt_demo_application ] || { echo "[ERROR] Binary not found in $(pwd)" >&2; exit 1; }' \
    '' \
    'exec ./opcua_ijt_demo_application' \
    > /entrypoint.sh && chmod +x /entrypoint.sh

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 40451

ENV RUNNING_IN_DOCKER=1 \
    OPCUA_HOSTNAME=""

# TCP readiness probe. start-period covers server init (~3 s; no Wine JIT overhead).
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD nc -z localhost 40451 || exit 1

ENTRYPOINT ["/entrypoint.sh"]
