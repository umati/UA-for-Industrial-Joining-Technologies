# IJT Browser CI image
#
# Owned runtime image for the live-webclient-browser matrix job in
# .github/workflows/integration.yml. Replaces live
# `playwright install chromium --with-deps` on stock ubuntu-latest, which
# is sensitive to upstream apt-mirror availability and timeout budgets.
#
# Contract:
#   - Python 3.14.x, Node 24.x, Playwright 1.60.0 + Chromium + Linux system
#     libs, all baked at image-build time.
#   - Offline-by-construction at runtime: pip wheelhouse, npm cache, browser
#     cache pre-warmed; intended to be invoked with --network=none.
#   - Cache dirs under /opt/ijt-browser-ci are world-writable so non-root
#     --user UID at runtime can read+write.
#   - All base images are digest-pinned. Refresh procedure: re-pull tag,
#     copy `Docker-Content-Digest` from the registry HEAD response, update
#     the Node, Python, and Ubuntu `FROM` lines and metadata.json
#     `base_digests`.

# ---------------------------------------------------------------------------
# Stage 1: Node 24 source stage (digest-pinned).
#   node:24-bookworm-slim - manifest-list HEAD digest captured 2026-05-13.
# ---------------------------------------------------------------------------
FROM node:24-bookworm-slim@sha256:24dc26ef1e3c3690f27ebc4136c9c186c3133b25563ae4d7f0692e4d1fe5db0e AS node

# ---------------------------------------------------------------------------
# Stage 2: Python 3.14 source stage (digest-pinned).
#   python:3.14-slim-bookworm - manifest-list HEAD digest captured 2026-05-13.
#   Used only as a donor of /usr/local (interpreter, stdlib, pip). The runtime
#   final stage is Ubuntu Noble so the image's glibc matches the IJT Linux
#   simulator binary requirement (GLIBC_2.38). CPython is forward-compatible
#   across glibc versions, so a binary linked on bookworm (glibc 2.36) runs on
#   Noble (glibc 2.39).
# ---------------------------------------------------------------------------
FROM python:3.14-slim-bookworm@sha256:a3974109d36f164ca70024bc0d0828ac706e4ccda849f8638d879e91f79e90ec AS python

# ---------------------------------------------------------------------------
# Stage 3: Ubuntu 24.04 Noble final image (digest-pinned).
#   ubuntu:24.04 - manifest-list HEAD digest captured 2026-05-13.
#   Noble ships glibc 2.39 (the simulator binary needs GLIBC_2.38). Bookworm's
#   glibc 2.36 is too old. Python 3.14 is copied from the official python
#   stage above (no third-party PPA, no source build).
# ---------------------------------------------------------------------------
FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    HOME=/opt/ijt-browser-ci/home \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    npm_config_cache=/opt/ijt-browser-ci/npm-cache \
    PIP_CACHE_DIR=/opt/ijt-browser-ci/pip-cache \
    PIP_FIND_LINKS=/opt/ijt-browser-ci/pip-wheelhouse

# ---------------------------------------------------------------------------
# 1. Install Noble runtime tooling + the shared libraries Python 3.14 needs
#    at runtime. Pulling `python3` as a meta-package brings in the canonical
#    libssl3/libffi8/libsqlite3/etc. set with Noble's correct package names
#    (including the libt64 transition variants); the copied CPython 3.14
#    binary links against the same SONAMEs.
#    build-essential covers any sdists that lack pre-built 3.14 wheels.
# ---------------------------------------------------------------------------
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        build-essential pkg-config \
        git unzip \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 2. Copy Python 3.14 (interpreter, stdlib, pip) from the digest-pinned
#    official python:3.14-slim-bookworm stage. /usr/local/bin/python and
#    /usr/local/bin/pip are created by that image; PATH puts /usr/local/bin
#    first, so `python` resolves to 3.14, not Noble's bundled 3.12.
# ---------------------------------------------------------------------------
COPY --from=python /usr/local /usr/local
RUN getconf GNU_LIBC_VERSION | grep -E '^glibc 2\.(3[89]|[4-9][0-9])' \
 && python --version | grep -E '^Python 3\.14\.' \
 && python -m pip --version \
 && python -m venv /tmp/__venv-probe \
 && /tmp/__venv-probe/bin/python -m pip --version \
 && rm -rf /tmp/__venv-probe

# ---------------------------------------------------------------------------
# 3. Copy Node 24 + npm + npx from the pinned node:24-bookworm-slim stage.
#    Avoids piping a remote setup script (supply-chain pin).
#    Then assert the major matches v24.x (fail-fast in image build).
# ---------------------------------------------------------------------------
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version | grep -E '^v24\.' \
 && npm --version

# ---------------------------------------------------------------------------
# 4. Pre-create cache dirs writable for any --user UID at runtime.
# ---------------------------------------------------------------------------
RUN mkdir -p /opt/ijt-browser-ci/home \
             /opt/ijt-browser-ci/npm-cache \
             /opt/ijt-browser-ci/pip-cache \
             /opt/ijt-browser-ci/pip-wheelhouse \
             /opt/ijt-browser-ci/web-client-deps \
             /ms-playwright \
             /workspace \
 && chmod -R 0777 /opt/ijt-browser-ci /ms-playwright /workspace

# ---------------------------------------------------------------------------
# 5. Bake Python wheelhouse (complete closure, wheels only) from IJT Web
#    Client requirements. PIP_FIND_LINKS at runtime points here, plus
#    PIP_NO_INDEX=1, so the runtime venv-create + pip install is offline.
# ---------------------------------------------------------------------------
COPY OPC_UA_Clients/Release2/IJT_Web_Client/requirements.txt /tmp/requirements.txt
COPY OPC_UA_Clients/Release2/IJT_Web_Client/requirements-dev.txt /tmp/requirements-dev.txt
RUN python -m pip install --upgrade pip \
 && python -m pip wheel --pre \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
        --wheel-dir /opt/ijt-browser-ci/pip-wheelhouse \
 && python -m pip install --pre \
        --no-index \
        --find-links /opt/ijt-browser-ci/pip-wheelhouse \
        -r /tmp/requirements.txt \
        -r /tmp/requirements-dev.txt \
 && python -c "import pytest, pytest_asyncio, pytest_timeout, asyncua, websockets, dotenv, aiofiles, pytz; print('python deps OK')"

# ---------------------------------------------------------------------------
# 6. Bake npm cache from IJT Web Client package-lock + install Playwright
#    Chromium and Linux system deps. The `--with-deps` apt cost happens HERE
#    at image build, never in CI.
# ---------------------------------------------------------------------------
COPY OPC_UA_Clients/Release2/IJT_Web_Client/package.json /opt/ijt-browser-ci/web-client-deps/package.json
COPY OPC_UA_Clients/Release2/IJT_Web_Client/package-lock.json /opt/ijt-browser-ci/web-client-deps/package-lock.json
RUN cd /opt/ijt-browser-ci/web-client-deps \
 && npm ci --legacy-peer-deps --no-audit --no-fund \
 && npx playwright install --with-deps chromium \
 && rm -rf /opt/ijt-browser-ci/web-client-deps/node_modules

# ---------------------------------------------------------------------------
# 7. Post-install permission fixup (build ran as root; runtime --user UID
#    must be able to read+write every cache path).
# ---------------------------------------------------------------------------
RUN chmod -R a+rwX /opt/ijt-browser-ci/npm-cache \
                    /opt/ijt-browser-ci/home \
                    /opt/ijt-browser-ci/pip-cache \
                    /opt/ijt-browser-ci/pip-wheelhouse \
                    /ms-playwright \
 && python --version | grep -E '^Python 3\.14\.' \
 && python -m venv /tmp/__venv-probe \
 && /tmp/__venv-probe/bin/python -m pip --version \
 && rm -rf /tmp/__venv-probe

# ---------------------------------------------------------------------------
# 8. Write metadata.json (durable image self-description for CI assertions).
# ---------------------------------------------------------------------------
ARG IMAGE_BUILD_REF=unknown
ARG IMAGE_BUILD_SHA=unknown
ARG IMAGE_BUILD_CREATED=unknown
RUN python -c "import json,sys,subprocess; \
    py=sys.version.split()[0]; \
    node=subprocess.check_output(['node','--version'],text=True).strip(); \
    npm=subprocess.check_output(['npm','--version'],text=True).strip(); \
    meta={'python_version':py,'node_version':node,'npm_version':npm,\
          'playwright_version':'1.60.0',\
          'build_ref':'${IMAGE_BUILD_REF}','build_sha':'${IMAGE_BUILD_SHA}',\
          'build_created':'${IMAGE_BUILD_CREATED}',\
          'base_digests':{\
            'ubuntu':'sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b',\
            'python':'sha256:a3974109d36f164ca70024bc0d0828ac706e4ccda849f8638d879e91f79e90ec',\
            'node':'sha256:24dc26ef1e3c3690f27ebc4136c9c186c3133b25563ae4d7f0692e4d1fe5db0e'},\
          'cache_paths':{\
            'pip_wheelhouse':'/opt/ijt-browser-ci/pip-wheelhouse',\
            'pip_cache':'/opt/ijt-browser-ci/pip-cache',\
            'npm_cache':'/opt/ijt-browser-ci/npm-cache',\
            'playwright_browsers':'/ms-playwright',\
            'home':'/opt/ijt-browser-ci/home'}}; \
    open('/opt/ijt-browser-ci/metadata.json','w').write(json.dumps(meta,indent=2))" \
 && chmod a+r /opt/ijt-browser-ci/metadata.json \
 && cat /opt/ijt-browser-ci/metadata.json

WORKDIR /workspace
CMD ["bash"]

LABEL org.opencontainers.image.title="ijt-browser-ci" \
      org.opencontainers.image.description="Owned runtime image for IJT Web Client browser E2E suites." \
      org.opencontainers.image.source="https://github.com/umati/UA-for-Industrial-Joining-Technologies" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${IMAGE_BUILD_SHA}" \
      org.opencontainers.image.created="${IMAGE_BUILD_CREATED}" \
      org.opencontainers.image.ref.name="${IMAGE_BUILD_REF}" \
      org.umati.ijt.python_version="3.14" \
      org.umati.ijt.node_version="24.x" \
      org.umati.ijt.playwright_version="1.60.0" \
      org.umati.ijt.base_ubuntu_digest="sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b" \
      org.umati.ijt.base_python_digest="sha256:a3974109d36f164ca70024bc0d0828ac706e4ccda849f8638d879e91f79e90ec" \
      org.umati.ijt.base_node_digest="sha256:24dc26ef1e3c3690f27ebc4136c9c186c3133b25563ae4d7f0692e4d1fe5db0e"
