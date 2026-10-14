"""Docker / container configuration tests.

These tests parse Dockerfile and docker-compose.yml without executing Docker
and verify that key instructions are present and correct:
  - Correct base image stage names
  - WORKDIR is /app
  - EXPOSE includes ports 3000 and 8001
  - USER instruction present (non-root)
  - CMD does not contain --serve (invalid argument from a previous bug)
  - docker-compose ports mapping is correct
  - ijt_web_client service is defined
"""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

import pytest

_YAML_AVAILABLE = importlib.util.find_spec("yaml") is not None

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DOCKERFILE = _PROJECT_ROOT / "Dockerfile"
_COMPOSE_FILE = _PROJECT_ROOT / "docker-compose.yml"
_SMOKE_COMPOSE_FILE = _PROJECT_ROOT / "docker-compose.smoke.yml"
# Image-side location of the shared helpers COPYed from the repo-root ``scripts/``.
_IMAGE_SCRIPTS_DIR = Path("/app/scripts")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dockerfile_lines() -> list[str]:
    if not _DOCKERFILE.exists():
        pytest.fail(f"Dockerfile not found at {_DOCKERFILE}")
    return _DOCKERFILE.read_text(encoding="utf-8").splitlines()


def _repo_root() -> Path | None:
    """Repo root on the host; ``None`` inside the image (no repo above /app)."""
    for parent in _PROJECT_ROOT.parents:
        if (
            (parent / ".dockerignore").is_file()
            and (parent / "scripts" / "tool_bootstrap.py").is_file()
            and (parent / "OPC_UA_Clients").is_dir()
        ):
            return parent
    return None


def _root_dockerignore() -> Path | None:
    """The ONLY .dockerignore for this build (context = repo root).

    ``IJT_ROOT_DOCKERIGNORE`` overrides discovery (e.g. a copy mounted into an image).
    """
    override = os.environ.get("IJT_ROOT_DOCKERIGNORE")
    if override:
        path = Path(override)
        assert path.is_file(), f"IJT_ROOT_DOCKERIGNORE={override!r} is not a file"
        return path
    root = _repo_root()
    return root / ".dockerignore" if root else None


def _dockerignore_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _dockerfile_copy_scripts_sources() -> set[str]:
    """Every ``scripts/*`` source named by a Dockerfile ``COPY`` (continuations joined)."""
    text = _DOCKERFILE.read_text(encoding="utf-8")
    joined = re.sub(r"\\[ \t]*\r?\n", " ", text)
    sources: set[str] = set()
    for line in joined.splitlines():
        stripped = line.strip()
        if not re.match(r"^COPY\b", stripped, re.IGNORECASE):
            continue
        tokens = [t for t in stripped.split()[1:] if not t.startswith("--")]
        sources.update(t for t in tokens[:-1] if t.startswith("scripts/"))
    return sources


def _get_instructions(keyword: str) -> list[str]:
    """Return all Dockerfile lines starting with the given instruction keyword."""
    return [line.strip() for line in _dockerfile_lines() if re.match(rf"^\s*{keyword}\b", line, re.IGNORECASE)]


# ===========================================================================
# 1. Dockerfile structure
# ===========================================================================


class TestDockerfileInstructions:
    def test_dockerfile_exists(self):
        """Dockerfile must exist at the project root."""
        assert _DOCKERFILE.exists(), f"Dockerfile not found at {_DOCKERFILE}"

    def test_from_instruction_present(self):
        """At least one FROM instruction must be present."""
        froms = _get_instructions("FROM")
        assert len(froms) >= 1, "Dockerfile must have at least one FROM instruction"

    def test_workdir_is_app(self):
        """WORKDIR must be set to /app."""
        workdirs = _get_instructions("WORKDIR")
        assert any("/app" in wd for wd in workdirs), f"Expected WORKDIR /app, found: {workdirs}"

    def test_expose_includes_port_3000(self):
        """EXPOSE must include port 3000 (web server)."""
        exposes = _get_instructions("EXPOSE")
        all_ports = " ".join(exposes)
        assert "3000" in all_ports, f"Port 3000 not found in EXPOSE instructions: {exposes}"

    def test_expose_includes_port_8001(self):
        """EXPOSE must include port 8001 (WebSocket server)."""
        exposes = _get_instructions("EXPOSE")
        all_ports = " ".join(exposes)
        assert "8001" in all_ports, f"Port 8001 not found in EXPOSE instructions: {exposes}"

    def test_user_instruction_present_for_non_root(self):
        """USER instruction must be present to run as non-root."""
        users = _get_instructions("USER")
        assert len(users) >= 1, "No USER instruction found in Dockerfile — container would run as root"

    def test_user_is_not_root(self):
        """USER must not be root or UID 0."""
        users = _get_instructions("USER")
        for user_line in users:
            assert "root" not in user_line.lower(), f"USER instruction must not use root: {user_line}"
            assert "uid=0" not in user_line.lower(), f"USER instruction must not use UID 0: {user_line}"

    def test_cmd_does_not_contain_serve_flag(self):
        """CMD must not contain --serve (invalid argument that caused a previous bug)."""
        cmds = _get_instructions("CMD")
        for cmd_line in cmds:
            assert "--serve" not in cmd_line, (
                f"CMD contains --serve (invalid flag): {cmd_line}\nThis was fixed previously — ensure it stays fixed."
            )

    def test_production_stage_uses_setup_project(self):
        """Production CMD must run setup_project.py (the entrypoint)."""
        cmds = _get_instructions("CMD")
        # At least one CMD line should reference setup_project
        has_setup = any("setup_project" in cmd for cmd in cmds)
        assert has_setup, f"No CMD with setup_project.py found. CMDs: {cmds}"

    def test_healthcheck_present(self):
        """HEALTHCHECK must be defined so Docker knows when the container is ready."""
        healthchecks = _get_instructions("HEALTHCHECK")
        assert len(healthchecks) >= 1, "No HEALTHCHECK instruction found — Docker cannot detect container readiness"
        text = _DOCKERFILE.read_text(encoding="utf-8")
        assert "HEALTHCHECK" in text
        assert "docker_healthcheck.py" in text, "HEALTHCHECK must run docker_healthcheck.py (HTTP + WebSocket upgrade)"
        assert (_PROJECT_ROOT / "docker_healthcheck.py").is_file()
        assert "HTTP_PORT" in text and "WS_PORT" in text

    def test_multi_stage_build_has_test_and_production_stages(self):
        """Multi-stage build must have both 'test' and 'production' stages."""
        froms = _get_instructions("FROM")
        stages_text = " ".join(froms).lower()
        assert "test" in stages_text, "No 'test' stage found in multi-stage build"
        assert "production" in stages_text, "No 'production' stage found in multi-stage build"

    def test_npm_installs_suppress_audit_and_funding_noise(self):
        """Docker npm install steps must not emit install-time audit/funding noise."""
        text = _DOCKERFILE.read_text(encoding="utf-8")
        npm_install_lines = [line.strip() for line in text.splitlines() if "npm ci" in line or "npm install" in line]
        assert npm_install_lines, "No npm install step found in Dockerfile"
        for line in npm_install_lines:
            assert "--no-audit" in line, f"Docker npm install must pass --no-audit: {line}"
            assert "--no-fund" in line, f"Docker npm install must pass --no-fund: {line}"

    def test_npm_update_notifier_disabled(self):
        """Docker npm commands must not print update-notifier messages."""
        text = _DOCKERFILE.read_text(encoding="utf-8")
        assert "npm_config_update_notifier=false" in text

    def test_shared_runtime_helpers_are_available_in_all_image_stages(self):
        """Production and test images must include shared session policy and tooling."""
        text = _DOCKERFILE.read_text(encoding="utf-8")
        test_stage = text.index("FROM base AS test")
        for filename in {
            "scripts/opcua_session_policy.py",
            "scripts/opcua_session_policy_loader.py",
            "scripts/tool_bootstrap.py",
            "scripts/simulator_extract.py",
        }:
            assert filename in text
            assert text.index(filename) < test_stage


class TestDockerBuildContext:
    """The build context is the repo root, so the ROOT ``.dockerignore`` governs it.

    There is deliberately no Web Client ``.dockerignore`` (it would be dead: BuildKit only
    reads ``<context>/.dockerignore`` or ``<Dockerfile>.dockerignore``).
    """

    def test_every_copied_script_is_allowlisted_in_root_dockerignore(self):
        """Each ``COPY scripts/<file>`` needs a ``!scripts/<file>`` allowlist line (root file)."""
        sources = _dockerfile_copy_scripts_sources()
        assert sources, "Dockerfile no longer COPYs any scripts/* helpers; update this contract"
        assert "scripts/simulator_extract.py" in sources
        ignore_path = _root_dockerignore()
        assert ignore_path is not None, (
            "root .dockerignore must be discoverable on the host and via IJT_ROOT_DOCKERIGNORE in the test image"
        )
        lines = _dockerignore_lines(ignore_path)
        assert "!scripts/" in lines and "scripts/*" in lines
        missing = sorted(s for s in sources if f"!{s}" not in lines)
        assert not missing, (
            f"Dockerfile COPYs {missing} but {ignore_path} has no matching '!' allowlist line; "
            "the build would fail with 'not found'."
        )
        delivered = sorted(s for s in sources if not (_IMAGE_SCRIPTS_DIR / Path(s).name).is_file())
        if os.environ.get("IS_DOCKER", "").strip().lower() in {"1", "true", "yes"}:
            assert not delivered, f"COPYed scripts missing from image: {delivered}"

    def test_local_runtime_directories_are_excluded_from_build_context(self):
        """Local virtualenvs and generated test output must stay out of Docker context."""
        ignore_path = _root_dockerignore()
        assert ignore_path is not None, (
            "root .dockerignore must be discoverable on the host and via IJT_ROOT_DOCKERIGNORE in the test image"
        )
        ignored = set(_dockerignore_lines(ignore_path))
        for pattern in {
            "**/.venv/",
            "**/.venv_test/",
            "**/.venv_ci/",
            "**/venv/",
            "**/venv_test/",
            "**/node_modules/",
            "**/test-results/",
            "**/tmp/",
        }:
            assert pattern in ignored

    def test_no_dead_web_client_dockerignore(self):
        """A Web Client .dockerignore / Dockerfile.dockerignore would silently be ignored or shadow root."""
        assert not (_PROJECT_ROOT / ".dockerignore").exists()
        assert not (_PROJECT_ROOT / "Dockerfile.dockerignore").exists()


# ===========================================================================
# 2. docker-compose.yml
# ===========================================================================


class TestDockerCompose:
    def test_compose_file_exists(self):
        """docker-compose.yml must exist at the project root."""
        assert _COMPOSE_FILE.exists(), f"docker-compose.yml not found at {_COMPOSE_FILE}"

    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_compose_has_ijt_web_client_service(self):
        """docker-compose.yml must define the ijt_web_client service."""
        import yaml

        content = yaml.safe_load(_COMPOSE_FILE.read_text(encoding="utf-8"))
        services = content.get("services", {})
        assert "ijt_web_client" in services, f"ijt_web_client service not found. Services: {list(services.keys())}"

    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_compose_ijt_web_client_exposes_port_3000(self):
        """ijt_web_client service must map host port 3000."""
        import yaml

        content = yaml.safe_load(_COMPOSE_FILE.read_text(encoding="utf-8"))
        ports = content["services"]["ijt_web_client"].get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "3000" in ports_str, f"Port 3000 not in ijt_web_client service ports: {ports}"

    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_compose_ijt_web_client_exposes_port_8001(self):
        """ijt_web_client service must map host port 8001."""
        import yaml

        content = yaml.safe_load(_COMPOSE_FILE.read_text(encoding="utf-8"))
        ports = content["services"]["ijt_web_client"].get("ports", [])
        ports_str = " ".join(str(p) for p in ports)
        assert "8001" in ports_str, f"Port 8001 not in ijt_web_client service ports: {ports}"

    def test_compose_file_ports_raw_text_includes_3000(self):
        """Raw text of docker-compose.yml must reference port 3000."""
        text = _COMPOSE_FILE.read_text(encoding="utf-8")
        assert "3000" in text, "Port 3000 not found in docker-compose.yml"

    def test_compose_file_ports_raw_text_includes_8001(self):
        """Raw text of docker-compose.yml must reference port 8001."""
        text = _COMPOSE_FILE.read_text(encoding="utf-8")
        assert "8001" in text, "Port 8001 not found in docker-compose.yml"

    def test_compose_file_not_contains_serve_flag(self):
        """docker-compose.yml must not use the --serve flag."""
        text = _COMPOSE_FILE.read_text(encoding="utf-8")
        assert "--serve" not in text, "docker-compose.yml contains --serve (invalid flag from a previous bug)"

    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_compose_opts_into_docker_host_endpoint_rewrite(self):
        """Docker Compose is the host-bridge topology and must opt in explicitly."""
        import yaml

        content = yaml.safe_load(_COMPOSE_FILE.read_text(encoding="utf-8"))
        services = content["services"]

        for service_name in ("ijt_web_client", "ijt_tests"):
            env = services[service_name].get("environment", {})
            assert env.get("IS_DOCKER") == "true"
            assert env.get("IJT_OPCUA_HOST_REWRITE") == "true"

    def test_compose_healthcheck_uses_websocket_script(self):
        """Compose healthcheck must run the real WebSocket upgrade probe."""
        text = _COMPOSE_FILE.read_text(encoding="utf-8")
        assert "docker_healthcheck.py" in text
        assert "IJT_WEB_IMAGE" in text
        assert "IJT_SETUP_ARGS" in text
        assert "HTTP_PORT" in text and "WS_PORT" in text
        smoke = _SMOKE_COMPOSE_FILE.read_text(encoding="utf-8")
        assert "docker_healthcheck.py" in smoke

    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_dev_compose_remounts_shared_scripts_after_project_bind_mount(self):
        """``.:/app`` hides the image's /app/scripts; dev compose must re-mount repo scripts/ after it."""
        import yaml

        content = yaml.safe_load(_COMPOSE_FILE.read_text(encoding="utf-8"))
        volumes = [str(v) for v in content["services"]["ijt_web_client"]["volumes"]]
        assert ".:/app" in volumes
        assert "../../../scripts:/app/scripts:ro" in volumes
        assert volumes.index("../../../scripts:/app/scripts:ro") > volumes.index(".:/app")
        assert "hides the image's /app/scripts" in _COMPOSE_FILE.read_text(encoding="utf-8"), (
            "document why the scripts mount exists"
        )


class TestDockerSmokeCompose:
    @pytest.mark.skipif(
        not _YAML_AVAILABLE,
        reason="PyYAML not installed — skipping docker-compose YAML parsing",
    )
    def test_smoke_stack_runs_only_the_prebuilt_image(self):
        """Smoke checks must not replace the image with host files or reinstall dependencies."""
        import yaml

        content = yaml.safe_load(_SMOKE_COMPOSE_FILE.read_text(encoding="utf-8"))
        service = content["services"]["ijt_web_client"]

        assert "ijt_web_client" in str(service["image"])
        assert "build" not in service
        assert "volumes" not in service
        assert "volumes" not in content
        assert "command" not in service
        assert "/app/scripts" not in _SMOKE_COMPOSE_FILE.read_text(encoding="utf-8")
