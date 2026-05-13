"""Contract test for .github/docker/ijt-browser-ci/image-pin.json.

The integration.yml live-webclient-browser job constructs IJT_BROWSER_CI_IMAGE
as `${image}@${digest}` at runtime and refuses any tag-only reference. This
test catches malformed pin files at PR time (faster feedback than a CI workflow
syntax/regex failure on Linux runners).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIN_PATH = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "image-pin.json"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DIGEST_REF_SUFFIX_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
_IMAGE_RE = re.compile(r"^ghcr\.io/[a-z0-9._/-]+$")


@pytest.fixture(scope="module")
def pin() -> dict:
    assert _PIN_PATH.is_file(), f"missing image-pin.json: {_PIN_PATH}"
    with _PIN_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_image_pin_required_keys(pin: dict) -> None:
    for key in ("image", "digest", "playwright_version", "node_version", "python_version"):
        assert key in pin, f"image-pin.json missing required key: {key}"


def test_image_pin_digest_is_sha256_64hex(pin: dict) -> None:
    assert _SHA256_RE.match(pin["digest"]), (
        f"image-pin.json digest must match ^sha256:[0-9a-f]{{64}}$, got: {pin['digest']!r}"
    )


def test_image_pin_image_is_ghcr_lowercase(pin: dict) -> None:
    assert _IMAGE_RE.match(pin["image"]), (
        f"image-pin.json image must be a lowercase ghcr.io reference, got: {pin['image']!r}"
    )


def test_image_pin_reference_is_digest_qualified(pin: dict) -> None:
    ref = f"{pin['image']}@{pin['digest']}"
    assert _DIGEST_REF_SUFFIX_RE.search(ref), (
        f"constructed IJT_BROWSER_CI_IMAGE is not digest-qualified: {ref!r}"
    )


def test_image_pin_no_floating_tag(pin: dict) -> None:
    assert ":" not in pin["image"].split("/")[-1], (
        "image-pin.json 'image' must not contain a tag (':') in the final segment, "
        f"got: {pin['image']!r}"
    )


def test_image_pin_playwright_version_matches_package_lock(pin: dict) -> None:
    """The pinned CI image must track the Web Client's locked Playwright version."""
    lock_path = _IJT_WEB_CLIENT_DIR / "package-lock.json"
    assert lock_path.is_file(), f"missing Web Client package-lock.json: {lock_path}"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    package = lock.get("packages", {}).get("node_modules/@playwright/test")
    assert package, "package-lock.json is missing node_modules/@playwright/test"
    assert pin["playwright_version"] == package["version"], (
        "image-pin.json playwright_version must match package-lock.json "
        "node_modules/@playwright/test. Rebuild/publish ijt-browser-ci and "
        "update image-pin.json in the same Playwright bump."
    )


# ---------------------------------------------------------------------------
# Local/CI separation contracts
# ---------------------------------------------------------------------------
#
# The owned ijt-browser-ci image is a CI-only concern: only the GitHub Actions
# workflow that runs `live-webclient-browser` in `integration.yml` should
# reference IJT_BROWSER_CI_IMAGE / the ijt-browser-ci GHCR image. Local
# developer execution of Web E2E (root runner + Web Client runner) must NOT
# require GHCR access for the browser image; it must keep using the locked
# `@playwright/test` version directly. (The root runner does legitimately use
# `docker run` for the Linux server-simulator package smoke against a
# different image — that path is unrelated and remains allowed.)
# These contract tests guard that separation at PR time.

_IJT_WEB_CLIENT_DIR = _REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
_ROOT_RUNNER = _REPO_ROOT / "run_all_tests.py"
_WEB_CLIENT_RUNNER = _IJT_WEB_CLIENT_DIR / "run_all_tests.py"

_FORBIDDEN_CI_TOKENS_IN_PRODUCTION_RUNNERS = (
    "IJT_BROWSER_CI_IMAGE",
    "ijt-browser-ci",
    "ghcr.io/umati",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"expected production runner script at {path}"
    return path.read_text(encoding="utf-8")


def _tracked_files() -> list[Path]:
    git = shutil.which("git")
    assert git, "git executable is required for repo-wide image-pin boundary checks"
    result = subprocess.run(
        [git, "ls-files"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [_REPO_ROOT / line for line in result.stdout.splitlines() if line]


@pytest.mark.parametrize(
    "runner_path",
    [_ROOT_RUNNER, _WEB_CLIENT_RUNNER],
    ids=["root_runner", "web_client_runner"],
)
def test_python_runners_do_not_reference_ci_image(runner_path: Path) -> None:
    """Production Python runners must not embed IJT_BROWSER_CI_IMAGE / GHCR image.

    The CI image is wired in `.github/workflows/integration.yml` only. If a
    Python runner ever started reading IJT_BROWSER_CI_IMAGE or calling
    `docker pull` / `docker run`, local developer execution would gain a
    hidden CI dependency. This test catches that regression at PR time.
    """
    source = _read(runner_path)
    for token in _FORBIDDEN_CI_TOKENS_IN_PRODUCTION_RUNNERS:
        assert token not in source, (
            f"{runner_path.name} must not reference {token!r}: the ijt-browser-ci "
            "image is a CI-only concern wired in `.github/workflows/integration.yml`. "
            "Embedding it in a Python runner forces local developers onto Docker/GHCR."
        )


def test_ijt_browser_ci_image_env_var_is_workflow_or_image_config_only() -> None:
    """The CI image env var must stay out of product/runtime code."""
    token = "IJT_" + "BROWSER_CI_" + "IMAGE"
    allowed_prefixes = (
        Path(".github/workflows"),
        Path(".github/docker/ijt-browser-ci"),
    )
    allowed_exact = {Path("tests/test_image_pin.py")}
    offenders: list[str] = []

    for path in _tracked_files():
        rel = path.relative_to(_REPO_ROOT)
        if rel in allowed_exact or any(rel.is_relative_to(prefix) for prefix in allowed_prefixes):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if token in text:
            offenders.append(rel.as_posix())

    assert not offenders, (
        "IJT_BROWSER_CI_IMAGE is workflow/image-config only. It must not leak "
        "into Python runners, product code, or general docs: " + ", ".join(sorted(offenders))
    )


def test_local_web_e2e_does_not_require_docker_or_ghcr() -> None:
    """Web Client runner module + package.json must not require Docker or GHCR for local E2E.

    Browser e2e is a local-friendly target: ``cd OPC_UA_Clients/Release2/IJT_Web_Client``
    then ``python run_all_tests.py --suite web-client-e2e-smoke`` must work
    against the locked ``@playwright/test`` Chromium without Docker, without
    GHCR credentials, and without any reference to the ijt-browser-ci image.
    """
    web_client_runner = _read(_WEB_CLIENT_RUNNER)
    for token in _FORBIDDEN_CI_TOKENS_IN_PRODUCTION_RUNNERS:
        assert token not in web_client_runner, (
            f"Web Client runner references {token!r}; local E2E must not require "
            "Docker or GHCR. Move any CI-specific logic into "
            "`.github/workflows/integration.yml` instead."
        )

    package_json_path = _IJT_WEB_CLIENT_DIR / "package.json"
    assert package_json_path.is_file(), f"missing {package_json_path}"
    package_json_text = package_json_path.read_text(encoding="utf-8")
    for token in ("ijt-browser-ci", "ghcr.io/umati"):
        assert token not in package_json_text, (
            f"Web Client package.json references {token!r}; the locked "
            "`@playwright/test` version is the single source of truth for the "
            "local browser bundle. CI image references belong in the workflow."
        )
