# IJT Browser CI image

Owned runtime image for the `live-webclient-browser` matrix job in
`.github/workflows/integration.yml`. Replaces live `playwright install
chromium --with-deps` on stock `ubuntu-latest`, which caused the
apt-mirror-dependent failure observed in Integration run `25817063931` on
commit `4ad418b5`.

## Files

- `Dockerfile` — image definition (Python 3.14, Node 24, Playwright 1.60.0
  + Chromium + Linux system libs; wheelhouse + npm cache pre-warmed).
- `image-pin.json` — reviewed digest consumed by the Integration workflow.
  This file is updated by normal reviewed pull requests after a verified
  publish; it is excluded from image-build path triggers to prevent a
  pin-update loop.

## Image

Published to `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci`
by `.github/workflows/build-browser-ci-image.yml`.

The workflow has three permission-separated jobs:

- `build` — no package write permission; builds the image and runs image
  integrity probes under `--network=none` (metadata, tool versions,
  non-root cache permissions, offline pip wheelhouse closure, offline npm
  cache closure, and Playwright/Chromium presence).
- `publish` — the only job with `packages: write`; pushes the verified image
  to GHCR and pull-verifies the digest. Pushes to `main`, schedules, and
  manual `push=true` dispatches publish the reviewed pin path. Same-repo pull
  requests that change browser image inputs (`.dockerignore`, `constraints.txt`,
  Web Client `package*.json`, `requirements*.txt`, the image Dockerfile, the
  image-pin updater, or this build workflow) publish a PR-scoped source-SHA tag
  (`pr-<number>-<checkout-sha>`) for Integration to resolve to a digest before
  running the offline browser matrix.
- `offline-e2e` — runs the full `web-client-e2e-regression` root-runner path
  from the published digest under `--network=none`. This job is the browser
  behavior gate; it may fail the workflow/required check, but it intentionally
  does not block image publication. That separation prevents a product
  regression from cascading into Integration as a missing PR/SHA image.

## Runtime contract

The image is consumed at runtime via a step-level `docker run` (NOT
`jobs.<job>.container:`) in the `live-webclient-browser` matrix job. The
container is invoked with:

- `--network=none` — permanent offline contract; any silent live fetch fails.
- `--user "$(id -u):$(id -g)"` — host runner UID for artifact ownership.
- `-w /workspace` — repo root; the ROOT runner is invoked.
- env: `IS_DOCKER=true`, `HOME=/opt/ijt-browser-ci/home`, `npm_config_cache=...`,
  `npm_config_offline=true`, `PIP_NO_INDEX=1`,
  `PIP_FIND_LINKS=/opt/ijt-browser-ci/pip-wheelhouse`,
  `PIP_CACHE_DIR=...`, `SKIP_VENV_INSTALL=1`, plus the `GITHUB_*` whitelist.
  The offline container intentionally does not set `IJT_OPCUA_HOST_REWRITE`;
  with `--network=none`, rewriting `localhost` to `host.docker.internal` would
  create a DNS dependency that the offline contract forbids.

Local Web E2E remains native. Neither the root runner nor the Web Client
runner reads `IJT_BROWSER_CI_IMAGE`; the owned image is wired only in the
GitHub Actions Integration workflow.

## Browser Image Input PRs

Same-repo PRs can update browser image dependencies or image build logic before
`image-pin.json` has been refreshed on `main`. For that case, the image build
workflow publishes a PR-scoped image after image-integrity smoke, and
`integration.yml` resolves that tag to an immutable digest before the browser
suites run under `--network=none`. The build workflow then runs the full
offline E2E regression as a separate post-publish job. This keeps PR validation
automatic without allowing live npm/pip/Playwright fetches during the browser
test job.

Fork PRs cannot publish GHCR images with the repository token. If a fork needs
to change browser image inputs, a maintainer must replay the branch from this
repository or use the manual image-pin flow below.

## Manual image-pin PR flow

The build workflow publishes and verifies images. It does not open pull
requests or require GitHub App/PAT credentials. To move `main` to a new
reviewed digest:

1. Trigger or wait for a Build Browser CI Image run that completes `build`,
   `publish`, and `offline-e2e` successfully.
2. Use the published digest from the job summary and the image metadata from
   `/opt/ijt-browser-ci/metadata.json` to update `image-pin.json` with
   `.github/scripts/update_browser_ci_image_pin.py`.
3. Open a normal PR that touches **only**
   `.github/docker/ijt-browser-ci/image-pin.json`.
4. Wait for CI Fast Checks, CodeQL, and Integration to pass. Integration
   includes `image-pin.json` in both `push.paths` and `pull_request.paths`,
   so browser suites validate the new digest before and after merge.
5. A new digest with no Dockerfile change is normal. Docker rebuilds are not
   byte-reproducible; identical inputs typically produce a new digest. Accept
   the new digest unless the metadata block shows unexpected version drift.
6. Loop-prevention is structural. Merging the pin PR must NOT re-trigger the
   Build Browser CI Image workflow because `image-pin.json` is path-excluded
   from its own triggers. If a new build-image run appears for the pin-only
   merge, the exclusion has regressed; treat it as a stop-the-line bug.
