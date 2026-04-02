# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# OPC UA IJT Server Simulator — Docker Image
#
# The server is a Windows x64 console application (single self-contained EXE):
#   - Built with VS 2022 toolset (v145), C++17, Release|x64
#   - All libraries statically linked (mbedTLS, OPC UA SDK, WolfMQTT)
#   - Dynamic CRT (/MD) — requires msvcp140.dll + vcruntime140.dll at runtime
#     (installed via winetricks vcrun2022 during this build)
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

FROM scottyhardy/docker-wine:stable

# ── System utilities ──────────────────────────────────────────────────────────
# iproute2 / net-tools  : IP address detection for OPCUA_HOSTNAME auto-resolve
# netcat-openbsd        : TCP probe used in HEALTHCHECK
# xvfb                  : virtual display required by the winetricks installer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        iproute2 \
        net-tools \
        netcat-openbsd \
        xvfb && \
    rm -rf /var/lib/apt/lists/*

# ── Wine: 64-bit prefix + VC++ 2015-2022 runtime ─────────────────────────────
# The EXE is x64, so WINEARCH must be win64.
# vcrun2022 installs the genuine Microsoft msvcp140.dll + vcruntime140.dll —
# the same DLLs shipped in the VC++ 2015-2022 Redistributable package.
# Pre-initialising the Wine prefix here avoids a 15-20 s cold-start penalty
# on every container launch.
ENV WINEARCH=win64 \
    WINEPREFIX=/root/.wine

RUN wineboot --init 2>/dev/null || true && \
    xvfb-run --auto-servernum winetricks --unattended vcrun2022 && \
    rm -rf /tmp/.wine-* /root/.wine/drive_c/windows/Temp/*

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

# pki/ is created at runtime by the server on first launch (certificates are
# auto-generated).  Do not bake them into the image.
RUN mkdir -p /app/pki

# ── Entrypoint — inline shell script written to /entrypoint.sh ───────────────
# Kept inline (heredoc) so the entire Docker configuration lives in one file.
# Shell is the right choice here: bash is guaranteed in every Linux container,
# and the script only does hostname detection + exec — no need for Python.
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
    'exec wine opcua_ijt_demo_application.exe' \
    > /entrypoint.sh && chmod +x /entrypoint.sh

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 40451

ENV RUNNING_IN_DOCKER=1 \
    WINEDEBUG=-all \
    DISPLAY=nonexistent:0 \
    OPCUA_HOSTNAME=""

# TCP readiness probe. start-period covers Wine JIT + server init (~40 s total).
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=6 \
    CMD nc -z localhost 40451 || exit 1

ENTRYPOINT ["/entrypoint.sh"]
