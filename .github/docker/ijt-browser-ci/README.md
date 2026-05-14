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
  The image-build workflow updates this file through a pull request after a
  verified publish; the file is excluded from image-build path triggers to
  prevent a pin-update loop.

## Image

Published to `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci`
by `.github/workflows/build-browser-ci-image.yml`.

The workflow has three permission-separated jobs:

- `build` — no package write permission; builds and runs the full Phase 0
  smoke path under `--network=none`.
- `publish` — the only job with `packages: write`; pushes the verified image
  to GHCR and pull-verifies the digest. Pushes to `main`, schedules, and
  manual `push=true` dispatches publish the reviewed pin path. Same-repo
  dependency-bot pull requests that change only Web Client dependency inputs
  (`package.json`, `package-lock.json`, `requirements*.txt`) publish a
  PR-scoped tag (`pr-<number>-<head-sha>`) for Integration to resolve to a
  digest before running the offline browser matrix.
- `update-pin` — the only job with `contents: write` and
  `pull-requests: write`; opens or updates the reviewed `image-pin.json` PR
  for non-PR publishes only.

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

Local Web E2E remains native. Neither the root runner nor the Web Client
runner reads `IJT_BROWSER_CI_IMAGE`; the owned image is wired only in the
GitHub Actions Integration workflow.

## Dependency-update PRs

Renovate/Dependabot same-repo dependency PRs can update the Web Client lockfile
before `image-pin.json` has been refreshed on `main`. For that case, the image
build workflow publishes a PR-scoped image after Phase 0 smoke, and
`integration.yml` resolves that tag to an immutable digest before the browser
suites run under `--network=none`. This keeps PR validation automatic without
allowing live npm/pip/Playwright fetches during the browser test job.

PR-scoped publish is intentionally disabled when the PR also changes the image
build logic (`.github/docker/ijt-browser-ci/**`,
`.github/scripts/update_browser_ci_image_pin.py`, or
`.github/workflows/build-browser-ci-image.yml`). Those changes must be reviewed
through the normal image-build path instead of auto-publishing a modified image
builder from the PR.

## Reviewing an auto pin PR

After a successful build + publish, the `update-pin` job opens (or
force-updates) a PR on branch `automation/ijt-browser-ci-image-pin`
that touches **only** `image-pin.json`. To accept or reject quickly:

1. **Diff must be `image-pin.json` only.** Any other touched file means
   the automation drifted; investigate before merging.
2. **Verify the upstream Build Browser CI Image run.** PR body links the
   workflow run; both `build` (Phase 0 smoke under `--network=none`) and
   `publish` (digest pull-verify) must be green.
3. **Confirm exact versions captured.** The new pin should carry exact
   `playwright_version`, `node_version`, `python_version`, and
   `base_digests` from the in-image `/opt/ijt-browser-ci/metadata.json`,
   not the loose `24.x` / `3.14.x` form.
4. **Required checks may be absent.** PRs opened by `GITHUB_TOKEN` do
   not trigger Integration / CodeQL / pre-commit / actionlint / zizmor /
   workflow-policy-guard. This is expected. To unblock: `gh pr close`
   then `gh pr reopen` on the PR (or push an empty user commit). Both
   re-fire the required-check set.
5. **A new digest with no Dockerfile change is normal.** Docker rebuilds
   are not byte-reproducible; identical inputs typically produce a new
   digest. Accept the new digest unless the metadata block shows an
   unexpected version drift.
6. **Loop-prevention is automatic.** Merging the pin PR must NOT
   re-trigger the Build Browser CI Image workflow because `image-pin.json`
   is path-excluded from its own triggers. If a new build-image run
   appears for the pin-only merge, the loop-prevention exclusion has
   regressed; treat it as a stop-the-line bug.
