# ── base: shared system + Python deps ────────────────────────────────────────
FROM nikolaik/python-nodejs:python3.14-nodejs24 AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY constraints.txt /tmp/constraints.txt
COPY constraints.txt ./constraints.txt

# Upgrade pip and install Python bootstrap deps
# asyncua >=1.2b2 requires --pre for Python 3.14 compat;
# once 1.2.x stable ships pip will prefer it automatically.
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir --pre -c /tmp/constraints.txt \
        "asyncua>=1.2b2,<2" \
        python-dotenv \
        websockets \
        packaging

ENV IS_DOCKER=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    npm_config_update_notifier=false

# Copy dependency manifests first for better layer caching.
# Docker builds use the repo root as context so the same constraints.txt is
# shared by local runners, CI, and images.
COPY OPC_UA_Clients/Release2/IJT_Web_Client/requirements.txt \
     OPC_UA_Clients/Release2/IJT_Web_Client/requirements-dev.txt* ./
RUN pip install --no-cache-dir --pre -c /tmp/constraints.txt -r requirements.txt

COPY OPC_UA_Clients/Release2/IJT_Web_Client/package.json \
     OPC_UA_Clients/Release2/IJT_Web_Client/package-lock.json* ./

# ── test: includes all dev deps (pytest, vitest) ─────────────────────────────
FROM base AS test

ENV NODE_ENV=development

RUN pip install --no-cache-dir -c /tmp/constraints.txt -r requirements-dev.txt && \
    (npm ci --no-audit --no-fund || npm install --legacy-peer-deps --no-audit --no-fund)

COPY OPC_UA_Clients/Release2/IJT_Web_Client/. .

CMD ["python", "-m", "pytest", "tests/python/unit/", "-v", "--tb=short", "--no-header"]

# ── production: lean image, no dev tools ─────────────────────────────────────
FROM base AS production

ENV NODE_ENV=production

RUN npm ci --omit=dev --no-audit --no-fund || npm install --legacy-peer-deps --omit=dev --no-audit --no-fund

# Copy the rest of the project
COPY OPC_UA_Clients/Release2/IJT_Web_Client/. .

# Create a non-root user and transfer ownership
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

CMD ["python", "setup_project.py"]
