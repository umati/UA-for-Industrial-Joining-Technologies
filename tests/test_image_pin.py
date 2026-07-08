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
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PIN_PATH = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "image-pin.json"
_IMAGE_DOCKERFILE = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "Dockerfile"
_INPUTS_MANIFEST = _REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "inputs-manifest.json"
_PIN_UPDATE_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "update_browser_ci_image_pin.py"
_FINGERPRINT_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "compute_browser_image_fingerprint.py"
_IMAGE_BUILD_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "build-browser-ci-image.yml"
_INTEGRATION_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "integration.yml"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
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


def test_image_pin_inputs_fingerprint_is_valid_when_present(pin: dict) -> None:
    fingerprint = pin.get("inputs_fingerprint")
    if fingerprint is None:
        return
    assert isinstance(fingerprint, str)
    assert _FINGERPRINT_RE.fullmatch(fingerprint), (
        "image-pin.json inputs_fingerprint must be 64 lowercase hex chars when present"
    )


def test_image_pin_playwright_version_matches_package_lock(pin: dict) -> None:
    """The reviewed pin must be version-current only when it matches current inputs."""
    lock_path = _IJT_WEB_CLIENT_DIR / "package-lock.json"
    assert lock_path.is_file(), f"missing Web Client package-lock.json: {lock_path}"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    package = lock.get("packages", {}).get("node_modules/@playwright/test")
    assert package, "package-lock.json is missing node_modules/@playwright/test"
    current_fingerprint = _load_fingerprint_module().compute_fingerprint()["fingerprint"]
    if pin.get("inputs_fingerprint") != current_fingerprint:
        return
    assert pin["playwright_version"] == package["version"], (
        "image-pin.json playwright_version must match package-lock.json when "
        "image-pin.json inputs_fingerprint already matches the current Browser "
        "CI image inputs. Stale pins are handled by Integration's fingerprint "
        "cache/build path instead of requiring every dependency PR to edit the pin."
    )


def _load_fingerprint_module():
    spec = importlib.util.spec_from_file_location(
        "compute_browser_image_fingerprint",
        _FINGERPRINT_SCRIPT,
    )
    assert spec and spec.loader, f"unable to import {_FINGERPRINT_SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_inputs_manifest() -> dict:
    assert _INPUTS_MANIFEST.is_file(), f"missing inputs manifest: {_INPUTS_MANIFEST}"
    return json.loads(_INPUTS_MANIFEST.read_text(encoding="utf-8"))


def _path_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-3].rstrip("/") + "/")
    return fnmatchcase(path, pattern)


def _workflow_path_includes(path: str, patterns: list[str]) -> bool:
    included = any(
        _path_matches(path, pattern) for pattern in patterns if not pattern.startswith("!")
    )
    excluded = any(
        _path_matches(path, pattern[1:]) for pattern in patterns if pattern.startswith("!")
    )
    return included and not excluded


def test_browser_ci_inputs_manifest_is_canonical_and_fingerprintable() -> None:
    manifest = _load_inputs_manifest()
    assert manifest["schema_version"] == 1
    assert manifest["algorithm"] == "sha256-v1"
    paths = manifest["paths"]
    assert paths == sorted(paths), "manifest paths should stay sorted for reviewable diffs"
    assert len(paths) == len(set(paths)), "manifest paths must be unique"
    for rel in paths:
        assert not rel.startswith("/")
        assert ".." not in Path(rel).parts
        assert (_REPO_ROOT / rel).is_file(), f"manifest path is missing: {rel}"

    module = _load_fingerprint_module()
    result = module.compute_fingerprint(repo_root=_REPO_ROOT, manifest_path=_INPUTS_MANIFEST)
    assert result["algorithm"] == "sha256-v1"
    assert _FINGERPRINT_RE.fullmatch(result["fingerprint"])
    assert result["paths"] == paths


def test_build_workflow_path_filters_cover_browser_ci_inputs_manifest() -> None:
    import yaml

    workflow = yaml.safe_load(_IMAGE_BUILD_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True, {}))
    manifest_paths = _load_inputs_manifest()["paths"]
    # Producer is triggered directly on push to main / schedule / workflow_dispatch /
    # workflow_call. There is intentionally no pull_request trigger: PR-time
    # builds go through integration.yml's prepare-browser-image-plan -> build-
    # browser-image (workflow_call) DAG, so producer and consumer share a
    # single execution graph instead of synchronising through GHCR tag polling.
    assert "pull_request" not in triggers, (
        "build-browser-ci-image.yml must not declare a pull_request trigger; "
        "PR builds go through integration.yml workflow_call so producer and "
        "consumer are one execution graph."
    )
    paths = triggers["push"]["paths"]
    missing = [path for path in manifest_paths if not _workflow_path_includes(path, paths)]
    assert not missing, (
        "build-browser-ci-image.yml push paths must cover every "
        "Browser CI image input manifest path: " + ", ".join(missing)
    )

    assert not _workflow_path_includes(".github/docker/ijt-browser-ci/image-pin.json", paths)
    assert not _workflow_path_includes(".github/docker/ijt-browser-ci/README.md", paths)


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
        [git, "ls-files", "-z"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
    )
    tracked_paths: list[Path] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = _REPO_ROOT / raw_path.decode()
        if path.is_file():
            tracked_paths.append(path)
    return tracked_paths


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
    allowed_exact = {
        Path(".github/scripts/update_browser_ci_image_pin.py"),
        Path("tests/test_image_pin.py"),
        Path("tests/test_ci_synchronization_invariants.py"),
    }
    offenders: list[str] = []

    for path in _tracked_files():
        rel = path.relative_to(_REPO_ROOT)
        if rel in allowed_exact or any(rel.is_relative_to(prefix) for prefix in allowed_prefixes):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
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
            "inputs_fingerprint": "2" * 64,
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
    assert updated["inputs_fingerprint"] == "2" * 64
    assert updated["node_version"] == "v24.11.1"
    assert updated["python_version"] == "Python 3.14.0"
    assert updated["base_digests"]["ubuntu"] == "sha256:" + "a" * 64
    assert updated["custom_audit_field"] == "preserved"
    assert "maintainer opens a normal reviewed PR" in updated["_comment"]


def test_update_browser_ci_image_pin_script_keeps_current_pin_when_digest_matches() -> None:
    """A scheduled rebuild with the same digest must not churn image-pin edits."""
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
        "inputs_fingerprint": "2" * 64,
        "_comment": "already reviewed",
    }

    updated = module.build_updated_pin(
        current=current,
        metadata={
            "inputs_fingerprint": "2" * 64,
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


def test_update_browser_ci_image_pin_script_refreshes_same_digest_stale_fingerprint() -> None:
    """A matching digest must not preserve a stale or manually edited input fingerprint."""
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
        "inputs_fingerprint": "2" * 64,
    }

    updated = module.build_updated_pin(
        current=current,
        metadata={
            "inputs_fingerprint": "3" * 64,
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

    assert updated["digest"] == current["digest"]
    assert updated["inputs_fingerprint"] == "3" * 64
    assert updated["image_revision"] == "new"


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
                "inputs_fingerprint": "2" * 64,
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


def test_build_browser_ci_image_workflow_keeps_pin_updates_manual_without_loop() -> None:
    """Pin refresh is manual; the build workflow must not self-trigger on pin PRs."""
    import yaml

    workflow_text = _IMAGE_BUILD_WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    triggers = workflow.get("on", workflow.get(True, {}))
    paths = triggers["push"]["paths"]
    docker_glob_index = paths.index(".github/docker/ijt-browser-ci/**")
    pin_exclude_index = paths.index("!.github/docker/ijt-browser-ci/image-pin.json")
    readme_exclude_index = paths.index("!.github/docker/ijt-browser-ci/README.md")
    assert docker_glob_index < pin_exclude_index, (
        "image-pin.json must be excluded after the docker directory include; "
        "otherwise the automation branch can publish a fresh image and loop."
    )
    assert docker_glob_index < readme_exclude_index, (
        "README.md must be excluded after the docker directory include; "
        "documentation-only edits must not rebuild and republish the browser image."
    )

    # workflow_call is the producer's PR-time entry point, invoked from
    # integration.yml's build-browser-image job. The expected_fingerprint
    # input is the YAML-visible cache identity contract: planner computes a
    # fingerprint, build job asserts equality, and the published image
    # metadata carries the same fingerprint so the consumer can do a single
    # runtime trust check (fingerprint equality) instead of polling.
    assert "workflow_call" in triggers, (
        "build-browser-ci-image.yml must expose workflow_call so integration.yml "
        "can invoke it as part of one execution graph."
    )
    wc = triggers["workflow_call"]
    assert wc["inputs"]["expected_fingerprint"]["required"] is True
    assert wc["inputs"]["expected_fingerprint"]["type"] == "string"
    wc_outputs = wc["outputs"]
    assert wc_outputs["digest"]["value"] == "${{ jobs.publish.outputs.digest }}"
    assert wc_outputs["source_sha"]["value"] == "${{ jobs.build.outputs.source_sha }}"
    assert (
        wc_outputs["inputs_fingerprint"]["value"] == "${{ jobs.build.outputs.inputs_fingerprint }}"
    )

    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    build_job = jobs["build"]
    assert build_job["outputs"]["publish_mode"] == "${{ steps.decide.outputs.publish_mode }}"
    assert build_job["outputs"]["source_sha"] == "${{ steps.decide.outputs.source_sha }}"
    assert build_job["outputs"]["pr_image_tag"] == "${{ steps.decide.outputs.pr_image_tag }}"
    assert (
        build_job["outputs"]["inputs_fingerprint"]
        == "${{ steps.fingerprint.outputs.inputs_fingerprint }}"
    )
    assert (
        build_job["outputs"]["playwright_version"]
        == "${{ steps.playwright.outputs.playwright_version }}"
    )

    checkout_step = next(step for step in build_job["steps"] if step.get("name") == "Checkout")
    assert "ref" not in checkout_step["with"], (
        "Build context should stay on the workflow checkout default: pull_request "
        "events use the merge tree, while IMAGE_BUILD_SHA records the exact "
        "workflow checkout SHA."
    )

    # Fingerprint guard: when invoked via workflow_call the build step must
    # assert the planner's expected_fingerprint matches what this checkout
    # computes. Drift between planner and build is a hard failure.
    fingerprint_guard = next(
        step
        for step in build_job["steps"]
        if step.get("name") == "Assert caller's expected fingerprint matches this checkout"
    )
    assert "inputs.expected_fingerprint" in (fingerprint_guard.get("if") or "")
    fp_guard_body = fingerprint_guard["run"]
    assert "EXPECTED_FINGERPRINT" in fp_guard_body
    assert "COMPUTED_FINGERPRINT" in fp_guard_body

    decide_step = next(
        step
        for step in build_job["steps"]
        if step.get("name") == "Decide whether to push (carry to publish job)"
    )
    decide_body = decide_step["run"]
    assert "PR_HEAD_REPO" in decide_step["env"]
    assert "EXPECTED_FINGERPRINT" in decide_step["env"]
    assert 'SOURCE_SHA="$GITHUB_SHA"' in decide_body
    assert "trusted_dependency_bot" not in decide_body
    assert 'PUBLISH_MODE="pr"' in decide_body
    assert 'PR_IMAGE_TAG="${IMAGE_NAME}:pr-${PR_NUMBER}-${SHORT_SHA}"' in decide_body
    # The producer no longer inlines a `browser_image_inputs_changed` shell
    # function; integration.yml's planner owns "did inputs change?" via the
    # compute_browser_image_fingerprint.py contract, and only invokes
    # workflow_call when a build is actually needed.
    assert "browser_image_inputs_changed" not in decide_body, (
        "Producer must not re-derive whether inputs changed; the planner in "
        "integration.yml is the single source of truth via inputs-manifest.json + "
        "compute_browser_image_fingerprint.py."
    )

    build_body = "\n".join(str(step.get("run", "")) for step in build_job["steps"])
    assert "compute_browser_image_fingerprint.py --format github-output" in build_body
    assert "inputs_fingerprint" in build_body
    assert "Extract Playwright version from Web Client package-lock.json" in str(build_job)
    assert "node_modules/@playwright/test" in build_body
    assert "IMAGE_INPUTS_FINGERPRINT=${{ steps.fingerprint.outputs.inputs_fingerprint }}" in str(
        build_job
    )
    assert "IMAGE_PLAYWRIGHT_VERSION=${{ steps.playwright.outputs.playwright_version }}" in str(
        build_job
    )
    image_smoke_metadata_step = next(
        step
        for step in build_job["steps"]
        if step.get("name") == "Image smoke - metadata and tool versions"
    )
    assert (
        image_smoke_metadata_step["env"]["EXPECTED_FINGERPRINT"]
        == "${{ steps.fingerprint.outputs.inputs_fingerprint }}"
    )
    assert '"$EXPECTED_FINGERPRINT"' in image_smoke_metadata_step["run"]
    assert (
        "${{ steps.fingerprint.outputs.inputs_fingerprint }}"
        not in image_smoke_metadata_step["run"]
    )
    summary_step = next(step for step in build_job["steps"] if step.get("name") == "Job summary")
    assert (
        summary_step["env"]["INPUTS_FINGERPRINT"]
        == "${{ steps.fingerprint.outputs.inputs_fingerprint }}"
    )
    assert "\\`${INPUTS_FINGERPRINT}\\`" in summary_step["run"]
    assert "${{ steps.fingerprint.outputs.inputs_fingerprint }}" not in summary_step["run"]
    assert "web-client-e2e-regression" not in build_body, (
        "The image publish gate must validate image integrity only. Full browser "
        "behavior belongs in the post-publish offline-e2e job (standalone path) "
        "or in the calling Integration run's live-webclient-browser matrix "
        "(workflow_call path), so product regressions do not prevent publishing "
        "the digest those consumers need."
    )
    assert "npm ci --legacy-peer-deps --offline --no-audit --no-fund" in build_body
    assert "--find-links /opt/ijt-browser-ci/pip-wheelhouse" in build_body
    assert "IS_DOCKER=true" in build_body
    assert "IJT_OPCUA_HOST_REWRITE" not in build_body
    assert 'constraints.txt > "$HOME/runtime-constraints.txt"' in build_body
    assert 'python -m venv "$HOME/ijt-browser-probe"' in build_body
    assert '-c "$HOME/runtime-constraints.txt"' in build_body
    forbidden_probe_python = "/" + "tmp" + "/ijt-browser-probe/bin/python"
    forbidden_runtime_constraints = "/" + "tmp" + "/runtime-constraints.txt"
    assert f'"{forbidden_probe_python}"' not in build_body
    assert forbidden_runtime_constraints not in build_body

    assert jobs["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
    }
    assert "update-pin" not in jobs
    assert "IJT_PIN_UPDATER" not in workflow_text
    assert "ijt-pin-updater" not in workflow_text
    assert "actions/create-github-app-token" not in workflow_text
    assert "automation/ijt-browser-ci-image-pin" not in workflow_text
    assert "gh pr create" not in workflow_text
    assert "pull-requests: write" not in workflow_text
    offline_job = jobs["offline-e2e"]
    assert offline_job["needs"] == ["build", "publish"]
    # The offline-e2e gate runs on the standalone path only (push to main,
    # schedule, workflow_dispatch). When invoked via workflow_call from
    # integration.yml, the calling run's live-webclient-browser matrix is
    # the verification against the same digest, so paying for the full
    # browser regression twice would be redundant.
    offline_if = offline_job["if"]
    assert "needs.build.outputs.should_push == 'true'" in offline_if
    assert "needs.publish.result == 'success'" in offline_if
    assert "inputs.expected_fingerprint == ''" in offline_if, (
        "offline-e2e must be skipped on the workflow_call path; integration.yml's "
        "live-webclient-browser matrix is the verification for that path."
    )
    assert offline_job["permissions"] == {"contents": "read", "packages": "read"}
    assert offline_job["timeout-minutes"] == 45
    offline_body = "\n".join(str(step.get("run", "")) for step in offline_job["steps"])
    assert "${IMAGE_NAME}@${PUBLISHED_DIGEST}" in offline_body
    assert "--network=none" in offline_body
    assert "IS_DOCKER=true" in offline_body
    assert "IJT_OPCUA_HOST_REWRITE" not in offline_body
    assert "SKIP_VENV_INSTALL=1" in offline_body
    assert "python run_all_tests.py --suite web-client-e2e-regression --verbose" in offline_body

    publish_job = jobs["publish"]
    publish_body = "\n".join(str(step.get("run", "")) for step in publish_job["steps"])
    assert "IMAGE_INPUTS_FINGERPRINT=${{ needs.build.outputs.inputs_fingerprint }}" in str(
        publish_job
    )
    assert "IMAGE_PLAYWRIGHT_VERSION=${{ needs.build.outputs.playwright_version }}" in str(
        publish_job
    )
    assert "EXPECTED_INPUTS_FINGERPRINT" in publish_body
    assert "inputs_fingerprint" in publish_body
    publish_checkout_step = next(
        step for step in publish_job["steps"] if step.get("name") == "Checkout"
    )
    assert "ref" not in publish_checkout_step["with"], (
        "Publish must rebuild the same default checkout context that image "
        "integrity validated; only image metadata should use "
        "needs.build.outputs.source_sha."
    )
    publish_tags_step = next(
        step for step in publish_job["steps"] if step.get("name") == "Compute publish tags"
    )
    assert "PUBLISH_MODE" in publish_tags_step["env"]
    assert "PR_IMAGE_TAG" in publish_tags_step["env"]
    assert "INPUTS_FINGERPRINT" in publish_tags_step["env"]
    assert "${PR_IMAGE_TAG}" in publish_tags_step["run"]
    # The fingerprint-<hex> tag is the cache identity used by integration.yml's
    # planner. Repeated Renovate PRs with identical Browser CI image inputs
    # resolve this tag to an existing digest and skip the build entirely.
    assert "${IMAGE_NAME}:fingerprint-${INPUTS_FINGERPRINT}" in publish_tags_step["run"], (
        "Publish must include a fingerprint-<hex> tag so future same-input "
        "builds can short-circuit at the planner."
    )
    publish_verify_step = next(
        step
        for step in publish_job["steps"]
        if step.get("name") == "Verify published image by digest (pull + offline smoke)"
    )
    assert (
        publish_verify_step["env"]["EXPECTED_SOURCE_SHA"] == "${{ needs.build.outputs.source_sha }}"
    )
    assert (
        publish_verify_step["env"]["EXPECTED_INPUTS_FINGERPRINT"]
        == "${{ needs.build.outputs.inputs_fingerprint }}"
    )
    assert "actual_sha" in publish_verify_step["run"]
    assert "actual_fingerprint" in publish_verify_step["run"]


def test_browser_ci_image_smoke_runtime_probe_uses_writable_home_paths() -> None:
    """The non-root runtime probe must not overwrite root-owned /tmp build files."""
    import yaml

    workflow = yaml.safe_load(_IMAGE_BUILD_WORKFLOW.read_text(encoding="utf-8"))
    build_job = workflow["jobs"]["build"]
    probe_step = next(
        step
        for step in build_job["steps"]
        if step.get("name") == "Image smoke - offline dependency closure probe"
    )
    body = probe_step["run"]

    assert "-e HOME=/opt/ijt-browser-ci/home" in body
    assert 'constraints.txt > "$HOME/runtime-constraints.txt"' in body
    assert 'python -m venv "$HOME/ijt-browser-probe"' in body
    assert '"$HOME/ijt-browser-probe/bin/python" -m pip install' in body
    assert '-c "$HOME/runtime-constraints.txt"' in body
    forbidden_probe_python = "/" + "tmp" + "/ijt-browser-probe/bin/python"
    forbidden_runtime_constraints = "/" + "tmp" + "/runtime-constraints.txt"
    assert f'"{forbidden_probe_python}"' not in body
    assert forbidden_runtime_constraints not in body


def test_integration_workflow_runs_for_image_pin_updates() -> None:
    """Pin PRs and merges must exercise the browser Integration workflow, and the
    planner (prepare-browser-image-plan) must read image-pin.json + compute the
    current fingerprint to decide pin / cached / build.
    """
    import yaml

    workflow = yaml.safe_load(_INTEGRATION_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True, {}))
    pin_path = ".github/docker/ijt-browser-ci/image-pin.json"
    assert pin_path in triggers["pull_request"]["paths"], (
        "image-pin PRs must trigger Integration so browser suites validate the new digest "
        "before merge."
    )
    assert pin_path in triggers["push"]["paths"], (
        "image-pin merges to main must trigger Integration so post-merge closure has a "
        "main-branch run for the reviewed digest."
    )

    # The legacy in-job resolver step in live-webclient-browser is gone.
    # Image identity now flows through three explicit jobs: planner (reads
    # pin + computes fingerprint), conditional reusable-workflow build, and
    # resolver (picks pin / cached / build digest and runs the single
    # fingerprint-equality runtime trust check).
    planner_job = workflow["jobs"]["prepare-browser-image-plan"]
    decide_step = next(
        step
        for step in planner_job["steps"]
        if step.get("name") == "Decide image plan (pin -> cached -> build)"
    )
    assert (
        decide_step.get("env", {}).get("PIN_PATH") == ".github/docker/ijt-browser-ci/image-pin.json"
    )
    decide_body = decide_step["run"]
    assert "compute_browser_image_fingerprint.py --format value" in decide_body
    assert "PIN_FP" in decide_body and "CUR_FP" in decide_body
    assert "plan=pin" in decide_body
    assert "plan=cached" in decide_body
    assert "plan=build" in decide_body
    assert "fingerprint-${CUR_FP}" in decide_body, (
        "Planner must look up the fingerprint-<hex> GHCR tag as the cache "
        "identity before falling through to a cold build."
    )

    # live-webclient-browser must consume the planner+resolver chain via
    # needs:, not by re-resolving the image inside its own steps.
    browser_job = workflow["jobs"]["live-webclient-browser"]
    needs = browser_job.get("needs")
    if isinstance(needs, str):
        needs = [needs]
    assert "resolve-browser-image" in (needs or []), (
        "live-webclient-browser must declare `needs: resolve-browser-image` so "
        "image identity is a passed-forward job output, not a tag poll."
    )

    # Resolver pick step performs the SINGLE runtime trust check:
    # image.metadata.inputs_fingerprint == planner.current_fingerprint.
    # build_sha is provenance only; cached cross-PR images with identical
    # fingerprints but different build SHAs are accepted.
    resolve_job = workflow["jobs"]["resolve-browser-image"]
    pick_step = next(
        step
        for step in resolve_job["steps"]
        if step.get("name") == "Pick final image_ref and validate metadata fingerprint"
    )
    pick_body = pick_step["run"]
    assert "CURRENT_FINGERPRINT" in pick_step["env"]
    assert "/opt/ijt-browser-ci/metadata.json" in pick_body
    assert "inputs_fingerprint" in pick_body
    assert "actual_fp" in pick_body
    # No build_sha equality check on the consumer side. Cache hits may have
    # been built from a different GITHUB_SHA with identical inputs. Strip
    # comment lines so a documenting comment can't trip the negative.
    pick_code_only = "\n".join(
        line for line in pick_body.splitlines() if not line.lstrip().startswith("#")
    )
    assert "build_sha" not in pick_code_only, (
        "Resolver code must NOT compare image build_sha to current GITHUB_SHA. "
        "build_sha is provenance only; fingerprint equality is the runtime "
        "trust check for cache reuse to work."
    )


def test_browser_ci_dockerfile_derives_asyncua_runtime_constraint_from_wheel() -> None:
    """Offline verification must not duplicate asyncua's version pin by hand."""
    dockerfile = _IMAGE_DOCKERFILE.read_text(encoding="utf-8")
    assert "asyncua_wheel=" in dockerfile
    assert "asyncua_version=" in dockerfile
    assert "asyncua==" + "1.2b2" not in dockerfile
    assert "runtime-constraints.txt" in dockerfile
    assert "ARG IMAGE_INPUTS_FINGERPRINT=unknown" in dockerfile
    assert "'inputs_fingerprint':'${IMAGE_INPUTS_FINGERPRINT}'" in dockerfile
    assert 'org.umati.ijt.inputs_fingerprint="${IMAGE_INPUTS_FINGERPRINT}"' in dockerfile
    assert "'playwright_version':'1." not in dockerfile
    assert "node_modules/@playwright/test" in dockerfile
    assert (
        "package-lock.json'))['packages']['node_modules/@playwright/test']['version']" in dockerfile
    )
    assert 'org.umati.ijt.playwright_version="${IMAGE_PLAYWRIGHT_VERSION}"' in dockerfile
