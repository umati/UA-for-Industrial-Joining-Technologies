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
import re
from pathlib import Path

import pytest

_YAML_AVAILABLE = importlib.util.find_spec("yaml") is not None

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DOCKERFILE = _PROJECT_ROOT / "Dockerfile"
_COMPOSE_FILE = _PROJECT_ROOT / "docker-compose.yml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dockerfile_lines() -> list[str]:
    if not _DOCKERFILE.exists():
        pytest.skip(f"Dockerfile not found at {_DOCKERFILE}")
    return _DOCKERFILE.read_text(encoding="utf-8").splitlines()


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

    def test_multi_stage_build_has_test_and_production_stages(self):
        """Multi-stage build must have both 'test' and 'production' stages."""
        froms = _get_instructions("FROM")
        stages_text = " ".join(froms).lower()
        assert "test" in stages_text, "No 'test' stage found in multi-stage build"
        assert "production" in stages_text, "No 'production' stage found in multi-stage build"


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
