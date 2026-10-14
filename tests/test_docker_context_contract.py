"""Repo-root Docker build-context contract.

The Web Client (and browser-CI) images are built with the repo root as context, so the ROOT
``.dockerignore`` is the only ignore file that applies. Every ``COPY scripts/<file>`` in those
Dockerfiles must have a matching ``!scripts/<file>`` allowlist line, otherwise the build fails
with ``not found`` (the exact regression this guards). The converse holds too: stale allowlist
entries are rejected so the file stays the exact inventory.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_DOCKERIGNORE = REPO_ROOT / ".dockerignore"
WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
WEB_DOCKERFILE = WEB_CLIENT_DIR / "Dockerfile"
# Dockerfiles built with the repo root as context (governed by the root .dockerignore).
ROOT_CONTEXT_DOCKERFILES = (
    WEB_DOCKERFILE,
    REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "Dockerfile",
)


def _copy_sources(dockerfile: Path) -> list[str]:
    text = dockerfile.read_text(encoding="utf-8")
    joined = re.sub(r"\\[ \t]*\r?\n", " ", text)
    sources: list[str] = []
    for line in joined.splitlines():
        stripped = line.strip()
        if not re.match(r"^(COPY|ADD)\b", stripped, re.IGNORECASE):
            continue
        tokens = [t for t in stripped.split()[1:] if not t.startswith("--")]
        sources.extend(tokens[:-1])
    return sources


def _copied_scripts() -> set[str]:
    return {
        source
        for dockerfile in ROOT_CONTEXT_DOCKERFILES
        for source in _copy_sources(dockerfile)
        if source.startswith("scripts/")
    }


def _dockerignore_lines() -> list[str]:
    return [
        line.strip()
        for line in ROOT_DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _allowlisted_scripts() -> set[str]:
    return {
        line[1:]
        for line in _dockerignore_lines()
        if line.startswith("!scripts/") and line != "!scripts/"
    }


def test_copy_source_parser_handles_continuations_and_flags(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text(
        "FROM x\n"
        "COPY --from=y /uv /bin/\n"
        "COPY scripts/a.py \\\n"
        "     scripts/b.py \\\n"
        "     other/c.txt /app/\n",
        encoding="utf-8",
    )
    assert _copy_sources(dockerfile) == ["/uv", "scripts/a.py", "scripts/b.py", "other/c.txt"]


def test_every_dockerfile_copied_script_is_allowlisted_in_root_dockerignore():
    copied = _copied_scripts()
    assert "scripts/simulator_extract.py" in copied
    lines = _dockerignore_lines()
    assert "!scripts/" in lines and "scripts/*" in lines
    missing = sorted(src for src in copied if f"!{src}" not in lines)
    assert not missing, (
        f"COPY scripts/* without a '!' allowlist line in root .dockerignore: {missing}"
    )


def test_root_dockerignore_has_no_stale_script_allowlist_entries():
    stale = sorted(_allowlisted_scripts() - _copied_scripts())
    assert not stale, f"root .dockerignore allowlists scripts no Dockerfile COPYs: {stale}"


def test_allowlisted_and_copied_scripts_exist():
    missing = sorted(
        s for s in _copied_scripts() | _allowlisted_scripts() if not (REPO_ROOT / s).is_file()
    )
    assert not missing, f"scripts referenced by Dockerfile/.dockerignore but absent: {missing}"


def test_no_web_client_dockerignore_files():
    """Context is the repo root; a Web Client .dockerignore would be dead (BuildKit ignores it)."""
    assert not (WEB_CLIENT_DIR / ".dockerignore").exists()
    assert not (WEB_CLIENT_DIR / "Dockerfile.dockerignore").exists()
    assert not (WEB_DOCKERFILE.parent / f"{WEB_DOCKERFILE.name}.dockerignore").exists()


def _ci_workflow() -> dict:
    import yaml

    return yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )


def test_ci_docker_smoke_builds_and_runs_test_target_before_production_smoke():
    steps = _ci_workflow()["jobs"]["docker-smoke"]["steps"]
    names = [step.get("name", "") for step in steps]
    build_test = names.index("Build test image (target test)")
    run_pytest = names.index("Run in-image Python unit tests")
    run_vitest = names.index("Run in-image JS unit tests (vitest)")
    build_production = names.index("Build Docker Image")
    start_stack = names.index("Start Compose Stack")
    assert build_test < run_pytest < run_vitest < build_production < start_stack

    build_run = steps[build_test]["run"]
    assert "--target test" in build_run and "ijt_web_client:test" in build_run
    assert '"$GITHUB_WORKSPACE"' in build_run, (
        "context must be the repo root, not the job working-directory"
    )

    pytest_run = steps[run_pytest]["run"]
    assert "-e IS_DOCKER=true" in pytest_run
    assert "tests/python/unit/" in pytest_run
    assert "not checkout_hygiene" in pytest_run

    vitest_run = steps[run_vitest]["run"]
    assert "vitest run" in vitest_run
    assert "vitest.xml" in vitest_run
    assert "--maxWorkers=4" in vitest_run

    # Production smoke build stays: repo-root context, exactly one build-push-action step.
    production = steps[build_production]
    assert production["with"]["context"] == "."
    assert production["with"]["file"] == "OPC_UA_Clients/Release2/IJT_Web_Client/Dockerfile"
    assert (
        sum(
            1 for step in steps if str(step.get("uses", "")).startswith("docker/build-push-action@")
        )
        == 1
    )


def test_docker_unit_pytest_and_vitest_lockstep_across_local_ci_and_system_tests():
    """Local --docker-unit-only, CI docker-smoke, and System Tests webclient-docker stay aligned."""
    import yaml

    web_runner = (WEB_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    assert '_DOCKER_UNIT_PYTEST_PATH = "tests/python/unit/"' in web_runner
    assert '_DOCKER_UNIT_PYTEST_MARKER = "not checkout_hygiene"' in web_runner
    assert '"npx",' in web_runner and '"vitest",' in web_runner and '"run",' in web_runner

    # Host npm scripts and in-image `npx vitest run` must both skip the private
    # Envelope performance fixture (needs data/itbp.json; Phase 1b only).
    vitest_cfg = (WEB_CLIENT_DIR / "vitest.config.mjs").read_text(encoding="utf-8")
    assert "automatic-stepwise-performance.test.mjs" in vitest_cfg
    pkg = (WEB_CLIENT_DIR / "package.json").read_text(encoding="utf-8")
    assert "automatic-stepwise-performance.test.mjs" in pkg

    ci_steps = _ci_workflow()["jobs"]["docker-smoke"]["steps"]
    ci_by_name = {step.get("name", ""): step.get("run", "") for step in ci_steps}
    assert "tests/python/unit/" in ci_by_name["Run in-image Python unit tests"]
    assert "not checkout_hygiene" in ci_by_name["Run in-image Python unit tests"]
    assert "vitest run" in ci_by_name["Run in-image JS unit tests (vitest)"]
    assert "--maxWorkers=4" in ci_by_name["Run in-image JS unit tests (vitest)"]

    integration = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "integration.yml").read_text(encoding="utf-8")
    )
    int_steps = integration["jobs"]["webclient-docker"]["steps"]
    int_runs = "\n".join(
        step.get("run", "") for step in int_steps if isinstance(step.get("run"), str)
    )
    assert "tests/python/unit/" in int_runs
    assert "not checkout_hygiene" in int_runs
    assert "vitest run" in int_runs
    assert "--maxWorkers=4" in int_runs

    root_runner = (REPO_ROOT / "run_all_tests.py").read_text(encoding="utf-8")
    assert '"web-client-docker-unit"' in root_runner
    assert '["--docker-unit-only"]' in root_runner
    assert "--maxWorkers=4" in web_runner


def test_ci_all_required_depends_on_and_aggregates_changes_result():
    jobs = _ci_workflow()["jobs"]
    gate = jobs["all-required"]
    assert "changes" in gate["needs"]
    assert "${{ needs.changes.result }}" in gate["steps"][0]["env"]["RESULTS"]
    assert "changes" in jobs["report"]["needs"]


def test_compose_builds_use_repo_root_context_and_same_dockerfile():
    import yaml

    compose = yaml.safe_load((WEB_CLIENT_DIR / "docker-compose.yml").read_text(encoding="utf-8"))
    for name in ("ijt_web_client", "ijt_tests"):
        build = compose["services"][name]["build"]
        assert (WEB_CLIENT_DIR / build["context"]).resolve() == REPO_ROOT
        assert build["dockerfile"] == "OPC_UA_Clients/Release2/IJT_Web_Client/Dockerfile"
