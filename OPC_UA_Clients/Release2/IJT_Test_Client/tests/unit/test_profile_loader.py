"""
Unit tests for helpers/profile_loader.py

Tests with temporary YAML files — no OPC UA server required.
"""

import logging
import textwrap
import uuid
from pathlib import Path

import pytest

import helpers.profile_loader as _pl_module
from helpers.profile_loader import get_skip_reason, is_cu_supported, load_supported_cus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, content: str) -> None:
    """Write a YAML string to *path*."""
    path.write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture
def profile_tmp_path():
    """Repo-local temp path for environments where pytest tmp_path ACLs are locked."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "profile_loader" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield path


# ---------------------------------------------------------------------------
# is_cu_supported
# ---------------------------------------------------------------------------


class TestIsCuSupported:
    def test_key_present_returns_true(self):
        supported = frozenset({"single_result", "basic_result"})
        assert is_cu_supported("single_result", supported) is True

    def test_key_absent_returns_false(self):
        supported = frozenset({"single_result"})
        assert is_cu_supported("unknown_cu", supported) is False

    def test_empty_set_returns_false(self):
        assert is_cu_supported("anything", frozenset()) is False

    def test_exact_match_required(self):
        supported = frozenset({"single_result"})
        assert is_cu_supported("Single_Result", supported) is False  # case-sensitive


# ---------------------------------------------------------------------------
# get_skip_reason
# ---------------------------------------------------------------------------


class TestGetSkipReason:
    def test_returns_string(self):
        reason = get_skip_reason("single_result")
        assert isinstance(reason, str)

    def test_mentions_cu_key(self):
        reason = get_skip_reason("single_result")
        assert "single_result" in reason

    def test_uses_public_not_supported_label(self):
        reason = get_skip_reason("send_joining_process")
        assert reason.startswith("IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED")

    def test_mentions_config_file(self):
        reason = get_skip_reason("any_key")
        assert "server_capabilities.yaml" in reason or "yaml" in reason.lower()

    def test_with_explicit_path(self, profile_tmp_path):
        caps_path = profile_tmp_path / "caps.yaml"
        reason = get_skip_reason("my_cu", capabilities_path=caps_path)
        assert "my_cu" in reason
        assert "caps.yaml" in reason

    def test_env_var_influences_path(self, profile_tmp_path, monkeypatch):
        caps_file = profile_tmp_path / "custom_caps.yaml"
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_file))
        reason = get_skip_reason("test_cu")
        assert "custom_caps.yaml" in reason


# ---------------------------------------------------------------------------
# load_supported_cus — missing capabilities file
# ---------------------------------------------------------------------------


class TestLoadSupportedCusMissingFile:
    def test_missing_file_returns_all_facets_cus(self, profile_tmp_path, monkeypatch):
        """When capabilities file is absent, all CUs from facets should be returned."""
        caps_file = profile_tmp_path / "nonexistent_caps.yaml"
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_file))
        # The real profiles/facets.yaml is used — result should be a non-empty frozenset
        supported = load_supported_cus()
        assert isinstance(supported, frozenset)
        assert len(supported) > 0

    def test_missing_file_explicit_path(self, profile_tmp_path):
        caps_file = profile_tmp_path / "nonexistent.yaml"
        supported = load_supported_cus(capabilities_path=caps_file)
        assert isinstance(supported, frozenset)
        # Uses real facets.yaml → all CUs
        assert len(supported) > 0


# ---------------------------------------------------------------------------
# load_supported_cus — full_conformance profile
# ---------------------------------------------------------------------------


class TestLoadSupportedCusFullConformance:
    def test_full_conformance_returns_large_set(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(caps_file, "active_profile: full_conformance\n")
        supported = load_supported_cus(capabilities_path=caps_file)
        # full_conformance claims 123 CUs
        assert len(supported) >= 100

    def test_full_conformance_includes_basic_cus(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(caps_file, "active_profile: full_conformance\n")
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "single_result" in supported
        assert "basic_result" in supported
        assert "joining_system_base" in supported

    def test_returns_frozenset(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(caps_file, "active_profile: full_conformance\n")
        supported = load_supported_cus(capabilities_path=caps_file)
        assert isinstance(supported, frozenset)


# ---------------------------------------------------------------------------
# load_supported_cus — cu_overrides: unsupported
# ---------------------------------------------------------------------------


class TestLoadSupportedCusUnsupportedOverride:
    def test_unsupported_override_removes_key(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              single_result: unsupported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "single_result" not in supported

    def test_unsupported_override_leaves_other_keys(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              single_result: unsupported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "basic_result" in supported  # not overridden

    def test_unsupported_nonexistent_key_no_error(self, profile_tmp_path):
        """Discarding a key that doesn't exist should silently pass."""
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              phantom_cu: unsupported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "phantom_cu" not in supported


# ---------------------------------------------------------------------------
# load_supported_cus — cu_overrides: supported
# ---------------------------------------------------------------------------


class TestLoadSupportedCusSupportedOverride:
    def test_supported_override_adds_key(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: basic_joining_system
            cu_overrides:
              custom_vendor_extension: supported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "custom_vendor_extension" in supported

    def test_supported_override_adds_key_not_in_profile(self, profile_tmp_path):
        """A key explicitly declared supported must appear even if not in the profile's facets."""
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              vendor_special_feature: supported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        assert "vendor_special_feature" in supported


# ---------------------------------------------------------------------------
# load_supported_cus — unknown disposition
# ---------------------------------------------------------------------------


class TestLoadSupportedCusUnknownDisposition:
    def test_unknown_disposition_logged_key_unchanged(self, profile_tmp_path, caplog):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              single_result: maybe
            """,
        )
        import logging

        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            supported = load_supported_cus(capabilities_path=caps_file)
        # Key should still be present (neither added nor removed)
        assert "single_result" in supported
        assert any("maybe" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# load_supported_cus — supported_facets
# ---------------------------------------------------------------------------


class TestLoadSupportedCusSupportedFacets:
    def test_extra_facets_added(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: basic_joining_system
            supported_facets:
              - result_management_server_facet
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        # result_management_server_facet includes sync_result, batch_result, etc.
        assert "sync_result" in supported

    def test_unknown_extra_facet_does_not_crash(self, profile_tmp_path, caplog):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: basic_joining_system
            supported_facets:
              - nonexistent_facet_xyz
            """,
        )
        import logging

        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            supported = load_supported_cus(capabilities_path=caps_file)
        assert isinstance(supported, frozenset)


# ---------------------------------------------------------------------------
# load_supported_cus — unknown profile (missing profile file)
# ---------------------------------------------------------------------------


class TestLoadSupportedCusMissingProfile:
    def test_missing_profile_file_returns_overrides_only(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: nonexistent_profile_xyz
            cu_overrides:
              my_cu: supported
            """,
        )
        supported = load_supported_cus(capabilities_path=caps_file)
        # Profile not found → 0 facet keys, but override still applied
        assert "my_cu" in supported

    def test_missing_profile_file_empty_without_overrides(self, profile_tmp_path):
        caps_file = profile_tmp_path / "caps.yaml"
        _write_yaml(caps_file, "active_profile: nonexistent_profile_xyz\n")
        supported = load_supported_cus(capabilities_path=caps_file)
        assert isinstance(supported, frozenset)
        assert len(supported) == 0


# ---------------------------------------------------------------------------
# load_supported_cus — env var integration
# ---------------------------------------------------------------------------


class TestLoadSupportedCusEnvVar:
    def test_env_var_overrides_default_path(self, profile_tmp_path, monkeypatch):
        caps_file = profile_tmp_path / "custom_env_caps.yaml"
        _write_yaml(
            caps_file,
            """\
            active_profile: full_conformance
            cu_overrides:
              env_test_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(caps_file))
        supported = load_supported_cus()
        assert "env_test_cu" in supported

    def test_explicit_path_takes_precedence_over_env_var(self, profile_tmp_path, monkeypatch):
        env_caps = profile_tmp_path / "env_caps.yaml"
        explicit_caps = profile_tmp_path / "explicit_caps.yaml"
        _write_yaml(env_caps, "active_profile: full_conformance\n")
        _write_yaml(
            explicit_caps,
            """\
            active_profile: full_conformance
            cu_overrides:
              explicit_only_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(env_caps))
        supported = load_supported_cus(capabilities_path=explicit_caps)
        assert "explicit_only_cu" in supported


# ---------------------------------------------------------------------------
# _load_facets — missing facets.yaml warns and returns empty dict
# ---------------------------------------------------------------------------


class TestLoadFacetsMissingFile:
    def test_missing_facets_yaml_warns_and_returns_empty(self, profile_tmp_path, monkeypatch, caplog):
        """When profiles/facets.yaml is absent, a WARNING is logged and the result
        is an empty frozenset (no facets to populate from)."""
        monkeypatch.setattr(_pl_module, "_PROFILES_DIR", profile_tmp_path)
        caps_file = profile_tmp_path / "caps.yaml"
        caps_file.write_text("active_profile: full_conformance\n", encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            supported = load_supported_cus(capabilities_path=caps_file)
        assert isinstance(supported, frozenset)
        assert len(supported) == 0
        assert "facets.yaml not found" in caplog.text


# ---------------------------------------------------------------------------
# Coverage gap test — line 129
# ---------------------------------------------------------------------------


class TestLoadSupportedCusUnknownFacetInProfile:
    def test_unknown_facet_in_active_profile_logs_warning(self, monkeypatch, caplog, profile_tmp_path):
        """Line 129: warning logged when profile resolves to a facet not in facets.yaml."""
        caps_file = profile_tmp_path / "caps.yaml"
        caps_file.write_text("active_profile: some_profile\n", encoding="utf-8")

        # Force profile to list a facet that doesn't exist in the facets dict
        monkeypatch.setattr(
            _pl_module,
            "_resolve_profile_facets",
            lambda profile: ["nonexistent_facet_xyz"],
        )
        # No facets defined at all
        monkeypatch.setattr(_pl_module, "_load_facets", lambda: {})

        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            result = load_supported_cus(capabilities_path=caps_file)

        assert isinstance(result, frozenset)
        assert "nonexistent_facet_xyz" in caplog.text
