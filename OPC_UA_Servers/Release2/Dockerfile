# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# OPC UA IJT Server Simulator — Docker Image
#
# The server is a Windows x64 console application (single self-contained EXE):
#   - Built with VS 2022 toolset (v145), C++17, Release|x64
#   - All libraries statically linked (mbedTLS, OPC UA SDK, WolfMQTT)
#   - Dynamic CRT (/MD) — requires msvcp140.dll + vcruntime140.dll at runtime
#
# Uses a pre-built Wine base image from GHCR so that Wine + winetricks never
# run in regular CI (build time: ~30 s instead of ~20 min).
# The base image is rebuilt monthly and on changes to Dockerfile.wine-base
# via .github/workflows/build-wine-base.yml.
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

# Wine + VC++ 2022 runtime pre-installed. Rebuilt monthly via build-wine-base.yml.
# hadolint ignore=DL3007
FROM ghcr.io/umati/ua-for-industrial-joining-technologies/opcua-wine-base:latest

# ── Application files ─────────────────────────────────────────────────────────
# Copy only what the server needs at runtime.
# Zip archives, PDFs, and docs are excluded by .dockerignore.
WORKDIR /app

COPY OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe      ./
COPY OPC_UA_IJT_Server_Simulator/server_configuration.json           ./
COPY OPC_UA_IJT_Server_Simulator/simulated_asset_data.json           ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.NodeSet2.xml                 ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Di.NodeSet2.xml              ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.AMB.NodeSet2.xml             ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.IA.NodeSet2.xml              ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Machinery.NodeSet2.xml       ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Machinery.Result.NodeSet2.xml ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Ijt.Base.NodeSet2.xml        ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Ijt.Tightening.NodeSet2.xml  ./
COPY OPC_UA_IJT_Server_Simulator/Opc.Ua.Ijt.Tightening.Server.xml    ./

# ── Pre-generate PKI certificates at build time ──────────────────────────────
# Wine 11+ on some Linux kernels (e.g. Azure CI) crashes (ucrtbase memset fault)
# when the server generates self-signed certificates on first launch.
# Pre-baking the PKI at image build time avoids the crash: the server finds
# existing certificates and skips generation entirely on every subsequent run.
# Docker BuildKit runs in a less-restricted context than a plain docker run,
# so the same cert generation that crashes at runtime succeeds here.
# hadolint ignore=DL4006
RUN mkdir -p /app/pki && \
    printf '%s\n' \
        'Xvfb :98 -screen 0 1024x768x24 -nolisten tcp &>/dev/null &' \
        'sleep 3' \
        'export DISPLAY=:98' \
        'wine opcua_ijt_demo_application.exe &>/tmp/pregen.log &' \
        'APP_PID=$!' \
        'CERT_FOUND=0' \
        'for i in $(seq 1 90); do' \
        '  if find /app/pki -name "*.der" 2>/dev/null | grep -q .; then' \
        '    CERT_FOUND=1; echo "PKI cert ready after ${i}s"; break' \
        '  fi' \
        '  sleep 1' \
        'done' \
        'kill "$APP_PID" 2>/dev/null || true' \
        'wineserver -k 2>/dev/null || true' \
        'pkill -f "Xvfb :98" 2>/dev/null || true' \
        'rm -f /tmp/.X98-lock' \
        'echo "=== Build-time server log ===" && cat /tmp/pregen.log || true' \
        'find /app/pki -type f 2>/dev/null || true' \
        '[ "$CERT_FOUND" = "1" ] || { echo "ERROR: No PKI certs generated at build time"; exit 1; }' \
        > /tmp/prebake_certs.sh && \
    bash /tmp/prebake_certs.sh && \
    rm /tmp/prebake_certs.sh

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
    '  OPCUA_HOSTNAME=$(getent hosts host.docker.internal 2>/dev/null | awk "{ print \$1; exit }") || true' \
    '  if [ -z "$OPCUA_HOSTNAME" ]; then' \
    '    OPCUA_HOSTNAME=$(ip route get 1.0.0.0 2>/dev/null | awk "/src/{for(i=1;i<=NF;i++) if(\$i==\"src\") print \$(i+1)}") || true' \
    '  fi' \
    '  OPCUA_HOSTNAME="${OPCUA_HOSTNAME:-0.0.0.0}"' \
    'fi' \
    'export OPCUA_HOSTNAME' \
    '' \
    'export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"' \
    'mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"' \
    '' \
    'echo "[INFO] OPC UA IJT Server Simulator"' \
    'echo "[INFO] Endpoint : opc.tcp://${OPCUA_HOSTNAME}:40451"' \
    '' \
    '[ -f opcua_ijt_demo_application.exe ] || { echo "[ERROR] EXE not found in $(pwd)" >&2; exit 1; }' \
    '' \
    '# PKI certs were pre-baked at image build time; no cert generation needed at runtime.' \
    '# Wine 11+ requires a real X11 display; start Xvfb before running Wine.' \
    'Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &>/dev/null &' \
    'sleep 5' \
    'export DISPLAY=:99' \
    '' \
    'exec wine opcua_ijt_demo_application.exe' \
    > /entrypoint.sh && chmod +x /entrypoint.sh

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 40451

ENV RUNNING_IN_DOCKER=1 \
    WINEDEBUG=-all \
    OPCUA_HOSTNAME=""

# TCP readiness probe. start-period covers Wine JIT + server init (~40 s total).
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=6 \
    CMD nc -z localhost 40451 || exit 1

ENTRYPOINT ["/entrypoint.sh"]
