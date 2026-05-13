# IJT Browser CI image

Owned runtime image for the `live-webclient-browser` matrix job in
`.github/workflows/integration.yml`. Replaces live `playwright install
chromium --with-deps` on stock `ubuntu-latest`, which caused the
apt-mirror-dependent failure observed in Integration run `25817063931` on
commit `4ad418b5`.

## Files

- `Dockerfile` — image definition (Python 3.14, Node 24, Playwright 1.60.0
  + Chromium + Linux system libs; wheelhouse + npm cache pre-warmed).

## Image

Published to `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci`
by `.github/workflows/build-browser-ci-image.yml`.

## Runtime contract

The image is consumed at runtime via a step-level `docker run` (NOT
`jobs.<job>.container:`) in the `live-webclient-browser` matrix job. The
container is invoked with:

- `--network=none` — permanent offline contract; any silent live fetch fails.
- `--user "$(id -u):$(id -g)"` — host runner UID for artifact ownership.
- `-w /workspace` — repo root; the ROOT runner is invoked.
- env: `HOME=/opt/ijt-browser-ci/home`, `npm_config_cache=...`,
  `npm_config_offline=true`, `PIP_NO_INDEX=1`,
  `PIP_FIND_LINKS=/opt/ijt-browser-ci/pip-wheelhouse`,
  `PIP_CACHE_DIR=...`, `SKIP_VENV_INSTALL=1`, plus the `GITHUB_*` whitelist.

PR A (this PR) introduces only the image build and publish path. PR B will
wire the image into `integration.yml`.
