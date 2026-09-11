# ─────────────────────────────────────────────────────────────────────────────
# OPC UA IJT Server Simulator — Docker Image (Linux native)
#
# The server is a Linux x64 ELF binary (statically linked C++ runtime):
#   - Built with CMake/WSL2 toolset on Ubuntu 24.04, C++17, Release|x64
#   - Requires glibc 2.38+ (built on Ubuntu 24.04 / glibc 2.39)
#   - No Wine, no Xvfb, no DISPLAY needed
#
# Base image: ubuntu:26.04 (latest LTS)
#   glibc is strictly backward-compatible; a binary built on 24.04/glibc-2.39
#   runs correctly on 26.04/glibc-2.41. No binary rebuild is required for an
#   OS base-image bump. Rebuild the binary from source only when moving to a
#   newer compiler toolchain or to pick up new library features.
#
# Default port: 40451 — always used when launching normally.
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
#
# Port override (automated testing ONLY — do NOT use for normal operation):
#   OPCUA_SERVER_PORT=40452 docker compose up
# ─────────────────────────────────────────────────────────────────────────────

# Multi-stage build: stage 1 extracts the Linux simulator ZIP using minimal BusyBox.
FROM busybox:stable-musl AS extractor
WORKDIR /tmp
COPY OPC_UA_IJT_Server_Simulator_Linux.zip server.zip
RUN unzip -q server.zip

FROM ubuntu:26.04

WORKDIR /app

# Run as dedicated non-root user with deterministic UID/GID (CIS Benchmark 4.1 / 4.2)
RUN groupadd -g 10001 opcua && \
    useradd -u 10001 -g opcua -d /app -s /bin/false opcua

# Copy the extracted simulator from the extractor stage.
# No package installation (apt-get) is needed: the Linux binary is statically
# linked (requiring only glibc from the base image), IP detection uses standard
# GNU hostname -I, and the TCP healthcheck uses native bash /dev/tcp.
# Setting ownership on COPY avoids duplicate layer storage overhead in OverlayFS.
COPY --chown=10001:10001 --from=extractor /tmp/OPC_UA_IJT_Server_Simulator_Linux/. /app/
RUN chmod +x /app/opcua_ijt_demo_application && \
    mkdir -p /app/pki && \
    chown -R opcua:opcua /app

# ── Entrypoint — inline shell script written to /entrypoint.sh ───────────────
# Kept inline (heredoc) so the entire Docker configuration lives in one file.
# Shell is the right choice here: bash is guaranteed in every Linux container,
# and the script only does hostname detection + exec — no need for Python.
# hadolint ignore=SC2016
RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    '' \
    '# Resolve OPCUA_HOSTNAME: explicit env > default route egress > local interface IP > localhost' \
    'if [ -z "${OPCUA_HOSTNAME:-}" ]; then' \
    '  if command -v ip >/dev/null 2>&1; then' \
    '    OPCUA_HOSTNAME=$(ip route get 1.0.0.0 2>/dev/null | awk "{for(i=1;i<=NF;i++) if(\$i==\"src\") print \$(i+1); exit}") || true' \
    '  fi' \
    '  if [ -z "$OPCUA_HOSTNAME" ]; then' \
    '    OPCUA_HOSTNAME=$(hostname -I 2>/dev/null | awk "{print \$1}") || true' \
    '  fi' \
    '  OPCUA_HOSTNAME="${OPCUA_HOSTNAME:-localhost}"' \
    'fi' \
    'export OPCUA_HOSTNAME' \
    '' \
    '# Resolve OPCUA_SERVER_PORT: override serverEndpointTCPPort in server_configuration.json' \
    'OPCUA_SERVER_PORT="${OPCUA_SERVER_PORT:-40451}"' \
    'export OPCUA_SERVER_PORT' \
    'if [ -f server_configuration.json ]; then' \
    '  sed -i "s/\"serverEndpointTCPPort\": [0-9]*/\"serverEndpointTCPPort\": ${OPCUA_SERVER_PORT}/" server_configuration.json' \
    'fi' \
    '' \
    'echo "[INFO] OPC UA IJT Server Simulator"' \
    'echo "[INFO] Endpoint : opc.tcp://${OPCUA_HOSTNAME}:${OPCUA_SERVER_PORT}"' \
    '' \
    '[ -f opcua_ijt_demo_application ] || { echo "[ERROR] Binary not found in $(pwd)" >&2; exit 1; }' \
    '' \
    'exec ./opcua_ijt_demo_application' \
    > /entrypoint.sh && chmod +x /entrypoint.sh

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 40451

ENV RUNNING_IN_DOCKER=1 \
    OPCUA_HOSTNAME="" \
    OPCUA_SERVER_PORT="40451"

USER opcua

# TCP readiness probe via native bash /dev/tcp (zero external tools required).
# Wrapped with timeout 3 to prevent blocking socket hangs.
# start-period covers server init (~3 s; no Wine JIT overhead).
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD timeout 3 bash -c "</dev/tcp/127.0.0.1/${OPCUA_SERVER_PORT:-40451}" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
