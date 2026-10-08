# ── base: shared system + Python deps ────────────────────────────────────────
FROM nikolaik/python-nodejs:python3.14-nodejs24 AS base

# Install uv pinned by image digest
COPY --from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY scripts/opcua_session_policy.py \
     scripts/opcua_session_policy_loader.py \
     scripts/tool_bootstrap.py /app/scripts/

ENV IS_DOCKER=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    npm_config_update_notifier=false \
    UV_PROJECT_ENVIRONMENT=/opt/ijt_venv \
    PATH="/opt/ijt_venv/bin:$PATH"

# Copy dependency manifests first for better layer caching.
COPY OPC_UA_Clients/Release2/IJT_Web_Client/pyproject.toml \
     OPC_UA_Clients/Release2/IJT_Web_Client/uv.lock ./

RUN uv sync --locked --no-dev

COPY OPC_UA_Clients/Release2/IJT_Web_Client/package.json \
     OPC_UA_Clients/Release2/IJT_Web_Client/package-lock.json* ./

# ── test: includes all dev deps (pytest, vitest) ─────────────────────────────
FROM base AS test

ENV NODE_ENV=development

RUN uv sync --locked && \
    (npm ci --ignore-scripts --no-audit --no-fund || npm install --legacy-peer-deps --ignore-scripts --no-audit --no-fund)

# Vendor the shared readiness module so tests/python/_live_server_readiness.py
# can import ``ijt_live_readiness`` inside the Docker test container. The
# build context is the repo root (see CI step), so the source path is
# scripts/ijt_live_readiness.py and the target matches the helper's Docker
# fallback path at /app/scripts/ijt_live_readiness.py.
COPY scripts/ijt_live_readiness.py /app/scripts/ijt_live_readiness.py

COPY OPC_UA_Clients/Release2/IJT_Web_Client/. .

CMD ["python", "-m", "pytest", "tests/python/unit/", "-v", "--tb=short", "--no-header"]


# ── production: lean image, no dev tools ─────────────────────────────────────
FROM base AS production

ENV NODE_ENV=production

RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund || npm install --legacy-peer-deps --omit=dev --ignore-scripts --no-audit --no-fund

# Copy the rest of the project
COPY OPC_UA_Clients/Release2/IJT_Web_Client/. .

# Create a non-root user and transfer ownership
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app /opt/ijt_venv

USER appuser

EXPOSE 3000 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

CMD ["python", "setup_project.py"]
