"""Contract test for .github/docker/ijt-browser-ci/image-pin.json.

The integration.yml live-webclient-browser job constructs IJT_BROWSER_CI_IMAGE
as `${image}@${digest}` at runtime and refuses any tag-only reference. This
test catches malformed pin files at PR time (faster feedback than a CI workflow
syntax/regex failure on Linux runners).
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIN_PATH = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "image-pin.json"
_PIN_UPDATE_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "update_browser_ci_image_pin.py"
_IMAGE_BUILD_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "build-browser-ci-image.yml"

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


# ---------------------------------------------------------------------------
# Drift-guard automation contracts
# ---------------------------------------------------------------------------


def _load_pin_update_module():
    spec = importlib.util.spec_from_file_location("update_browser_ci_image_pin", _PIN_UPDATE_SCRIPT)
    assert spec and spec.loader, f"unable to import {_PIN_UPDATE_SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_browser_ci_image_pin_script_writes_verified_publish_metadata() -> None:
    """The updater must produce a reviewed pin from image metadata, not prose."""
    module = _load_pin_update_module()
    updated = module.build_updated_pin(
        current={
            "image": "ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci",
            "digest": "sha256:" + "0" * 64,
            "playwright_version": "1.60.0",
            "node_version": "24.x",
            "python_version": "3.14.x",
            "image_revision": "old",
            "image_created": "old",
            "image_workflow_run": "old",
            "custom_audit_field": "preserved",
            "_comment": "old manual comment",
        },
        metadata={
            "playwright_version": "1.60.0",
            "node_version": "v24.11.1",
            "python_version": "Python 3.14.0",
            "base_digests": {
                "ubuntu": "sha256:" + "a" * 64,
                "python": "sha256:" + "b" * 64,
                "node": "sha256:" + "c" * 64,
            },
        },
        image="ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci",
        digest="sha256:" + "1" * 64,
        image_revision="abc1234",
        image_created="2026-05-13T22:00:00Z",
        image_workflow_run=(
            "https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/1"
        ),
    )

    assert updated["digest"] == "sha256:" + "1" * 64
    assert updated["node_version"] == "v24.11.1"
    assert updated["python_version"] == "Python 3.14.0"
    assert updated["base_digests"]["ubuntu"] == "sha256:" + "a" * 64
    assert updated["custom_audit_field"] == "preserved"
    assert "opens or updates a reviewable PR" in updated["_comment"]


def test_update_browser_ci_image_pin_script_keeps_current_pin_when_digest_matches() -> None:
    """A scheduled rebuild with the same digest must not churn image-pin PRs."""
    module = _load_pin_update_module()
    current = {
        "image": "ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci",
        "digest": "sha256:" + "1" * 64,
        "playwright_version": "1.60.0",
        "node_version": "24.x",
        "python_version": "3.14.x",
        "image_revision": "old",
        "image_created": "old",
        "image_workflow_run": "old",
        "_comment": "already reviewed",
    }

    updated = module.build_updated_pin(
        current=current,
        metadata={
            "playwright_version": "1.60.0",
            "node_version": "v24.11.1",
            "python_version": "Python 3.14.0",
        },
        image=current["image"],
        digest=current["digest"],
        image_revision="new",
        image_created="2026-05-13T23:00:00Z",
        image_workflow_run="https://github.com/example/repo/actions/runs/2",
    )

    assert updated == current


@pytest.mark.parametrize(
    ("image", "digest", "message"),
    [
        (
            "ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci:latest",
            "sha256:" + "1" * 64,
            "floating tag",
        ),
        (
            "docker.io/umati/ijt-browser-ci",
            "sha256:" + "1" * 64,
            "lowercase ghcr.io",
        ),
        (
            "ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci",
            "sha256:not-a-digest",
            "sha256",
        ),
    ],
)
def test_update_browser_ci_image_pin_script_rejects_unsafe_references(
    image: str,
    digest: str,
    message: str,
) -> None:
    module = _load_pin_update_module()

    with pytest.raises(ValueError, match=message):
        module.build_updated_pin(
            current={},
            metadata={
                "playwright_version": "1.60.0",
                "node_version": "v24.11.1",
                "python_version": "Python 3.14.0",
            },
            image=image,
            digest=digest,
            image_revision="abc1234",
            image_created="2026-05-13T22:00:00Z",
            image_workflow_run="https://github.com/example/repo/actions/runs/1",
        )


def test_build_browser_ci_image_workflow_opens_reviewed_pin_pr_without_loop() -> None:
    """Pin refresh must be automatic but still reviewable and non-self-triggering."""
    import yaml

    workflow = yaml.safe_load(_IMAGE_BUILD_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True, {}))
    for event_name in ("push", "pull_request"):
        paths = triggers[event_name]["paths"]
        docker_glob_index = paths.index(".github/docker/ijt-browser-ci/**")
        pin_exclude_index = paths.index("!.github/docker/ijt-browser-ci/image-pin.json")
        assert docker_glob_index < pin_exclude_index, (
            "image-pin.json must be excluded after the docker directory include; "
            "otherwise the automation branch can publish a fresh image and loop."
        )

    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert jobs["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
    }

    update_pin_job = jobs["update-pin"]
    assert update_pin_job["needs"] == "publish"
    assert update_pin_job["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "packages": "read",
    }
    assert update_pin_job["env"]["PIN_BRANCH"] == "automation/ijt-browser-ci-image-pin"
    assert update_pin_job["env"]["PIN_PATH"] == ".github/docker/ijt-browser-ci/image-pin.json"

    step_names = [step.get("name", "") for step in update_pin_job["steps"]]
    assert "Capture metadata from published digest" in step_names
    assert "Update image-pin.json" in step_names
    assert "Open or update image-pin PR" in step_names

    update_step = next(
        step for step in update_pin_job["steps"] if step.get("name") == "Update image-pin.json"
    )
    assert ".github/scripts/update_browser_ci_image_pin.py" in update_step["run"]
    assert "--metadata" in update_step["run"]
    assert '--digest "$PUBLISHED_DIGEST"' in update_step["run"]

    pr_step = next(
        step
        for step in update_pin_job["steps"]
        if step.get("name") == "Open or update image-pin PR"
    )
    pr_body = pr_step["run"]
    assert "git push --force-with-lease" in pr_body
    assert "gh pr list" in pr_body
    assert "gh pr edit" in pr_body
    assert "gh pr create" in pr_body
    assert "Review focus:" in pr_body
    assert ".github/docker/ijt-browser-ci/image-pin.json" in pr_body
