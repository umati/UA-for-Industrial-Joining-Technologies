"""
Unit tests for helpers/profile_loader.py

CU claim resolution now reads one SUT manifest (``*.sut.yaml``).
Tests use temporary manifests - no OPC UA server required.
"""

import logging
import textwrap
import uuid
from pathlib import Path

import pytest

import helpers.profile_loader as _pl_module
from helpers.profile_loader import (
    ExplicitManifestError,
    get_skip_reason,
    is_cu_supported,
    load_supported_cus,
    resolve_session_supported_cus,
    selected_manifest_path,
)
from helpers.sut_manifest import LegacyPairedFileError, SutManifestError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MANIFEST_HEAD = """\
schema_version: 1
name: "Claim test SUT"
lifecycle:
  mode: external
authentication:
  source: anonymous
connection:
  endpoint: "opc.tcp://localhost:40451"
"""


def _write_manifest(path: Path, claims: str = "") -> Path:
    """Write a minimal SUT manifest carrying *claims* under capability_claims."""
    body = _MANIFEST_HEAD
    if claims:
        body += "capability_claims:\n" + textwrap.indent(textwrap.dedent(claims), "  ")
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def profile_tmp_path():
    """Repo-local temp path for environments where pytest tmp_path ACLs are locked."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "profile_loader" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield path


@pytest.fixture
def manifest_path(profile_tmp_path):
    return profile_tmp_path / "sut.sut.yaml"


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
        assert "IJT Single Result" in reason

    def test_uses_public_not_supported_label(self):
        reason = get_skip_reason("send_joining_process")
        assert reason.startswith("Method 'SendJoiningProcess' is not supported NOT SUPPORTED")

    def test_omits_config_file_guidance(self):
        reason = get_skip_reason("any_key")
        assert "Config file:" not in reason
        assert "To enable:" not in reason
        assert "server_capabilities.yaml" not in reason

    def test_with_explicit_path(self, manifest_path):
        reason = get_skip_reason("my_cu", manifest_path=manifest_path)
        assert "IJT My Cu" in reason
        assert "sut.sut.yaml" not in reason

    def test_env_var_influences_path(self, profile_tmp_path, monkeypatch):
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(profile_tmp_path / "custom.sut.yaml"))
        reason = get_skip_reason("test_cu")
        assert "custom.sut.yaml" not in reason
        assert "IJT Test Cu" in reason


# ---------------------------------------------------------------------------
# load_supported_cus - missing or legacy manifest
# ---------------------------------------------------------------------------


class TestLoadSupportedCusMissingFile:
    def test_missing_environment_file_fails_fast(self, profile_tmp_path, monkeypatch):
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(profile_tmp_path / "nope.sut.yaml"))
        with pytest.raises(FileNotFoundError, match="SUT manifest not found"):
            load_supported_cus()

    def test_missing_explicit_file_fails_fast(self, profile_tmp_path):
        with pytest.raises(FileNotFoundError, match="SUT manifest not found"):
            load_supported_cus(manifest_path=profile_tmp_path / "nope.sut.yaml")

    def test_legacy_capabilities_file_is_rejected_with_clear_error(self, profile_tmp_path):
        legacy = profile_tmp_path / "old.capabilities.yaml"
        legacy.write_text("active_profile: full_specification_coverage\n", encoding="utf-8")
        with pytest.raises(LegacyPairedFileError, match="capability_claims"):
            load_supported_cus(manifest_path=legacy)

    def test_no_manifest_selected_claims_every_cu(self, monkeypatch, caplog):
        monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
        with caplog.at_level(logging.INFO, logger="helpers.profile_loader"):
            supported = load_supported_cus()
        assert len(supported) == 123
        assert "full specification coverage mode" in caplog.text


# ---------------------------------------------------------------------------
# load_supported_cus - full_specification_coverage profile
# ---------------------------------------------------------------------------


class TestLoadSupportedCusFullSpecificationCoverage:
    def test_full_specification_coverage_returns_large_set(self, manifest_path):
        _write_manifest(manifest_path, "active_profile: full_specification_coverage\n")
        supported = load_supported_cus(manifest_path=manifest_path)
        assert len(supported) >= 100

    def test_full_specification_coverage_includes_basic_cus(self, manifest_path):
        _write_manifest(manifest_path, "active_profile: full_specification_coverage\n")
        supported = load_supported_cus(manifest_path=manifest_path)
        assert "single_result" in supported
        assert "basic_result" in supported
        assert "joining_system_base" in supported

    def test_returns_frozenset(self, manifest_path):
        _write_manifest(manifest_path, "active_profile: full_specification_coverage\n")
        assert isinstance(load_supported_cus(manifest_path=manifest_path), frozenset)

    def test_full_specification_coverage_profile_declares_all_cus(self, manifest_path):
        _write_manifest(manifest_path, "active_profile: full_specification_coverage\n")
        assert len(load_supported_cus(manifest_path=manifest_path)) == 123


# ---------------------------------------------------------------------------
# Checked-in SUT manifests
# ---------------------------------------------------------------------------


class TestCheckedInManifests:
    @staticmethod
    def _manifests():
        manifest_dir = Path(_pl_module.__file__).resolve().parents[1] / "target_server_cu_profiles"
        return sorted(manifest_dir.glob("*.sut.yaml"))

    def test_checked_in_manifests_are_discovered(self):
        names = {path.name for path in self._manifests()}
        assert "template.sut.yaml" in names
        assert "simulator.sut.yaml" in names

    def test_active_profiles_exist_for_all_checked_in_manifests(self):
        from helpers.sut_manifest import load_sut_manifest

        for path in self._manifests():
            claims = load_sut_manifest(path).capability_claims
            assert claims.active_profile, f"{path.name} must declare an active profile"
            profile_path = _pl_module._PROFILES_DIR / f"{claims.active_profile}.yaml"
            assert profile_path.exists(), f"{path.name} references missing profile {profile_path.name}"

    def test_checked_in_manifests_resolve_non_empty_cu_scope(self):
        for path in self._manifests():
            supported = load_supported_cus(manifest_path=path)
            assert supported, f"{path.name} resolved to 0 claimed CUs"

    def test_simulator_manifest_keeps_expected_claimed_cu_count(self):
        simulator = Path(_pl_module.__file__).resolve().parents[1] / "target_server_cu_profiles" / "simulator.sut.yaml"
        assert len(load_supported_cus(manifest_path=simulator)) == 98


# ---------------------------------------------------------------------------
# load_supported_cus - cu_overrides
# ---------------------------------------------------------------------------


class TestLoadSupportedCusOverrides:
    def test_unsupported_override_removes_key(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              single_result: unsupported
            """,
        )
        supported = load_supported_cus(manifest_path=manifest_path)
        assert "single_result" not in supported

    def test_unsupported_override_leaves_other_keys(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              single_result: unsupported
            """,
        )
        assert "basic_result" in load_supported_cus(manifest_path=manifest_path)

    def test_unsupported_nonexistent_key_no_error(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              phantom_cu: unsupported
            """,
        )
        assert "phantom_cu" not in load_supported_cus(manifest_path=manifest_path)

    def test_supported_override_adds_key(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: basic_joining_system
            cu_overrides:
              custom_vendor_extension: supported
            """,
        )
        assert "custom_vendor_extension" in load_supported_cus(manifest_path=manifest_path)

    def test_manual_required_override_stays_claimed(self, manifest_path):
        """manual_required is still a claim: the CU applies, an operator triggers it."""
        _write_manifest(
            manifest_path,
            """\
            active_profile: basic_joining_system
            cu_overrides:
              start_selected_joining: manual_required
            """,
        )
        assert "start_selected_joining" in load_supported_cus(manifest_path=manifest_path)

    def test_unknown_disposition_is_rejected(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              single_result: maybe
            """,
        )
        with pytest.raises(SutManifestError, match="invalid value 'maybe'"):
            load_supported_cus(manifest_path=manifest_path)


# ---------------------------------------------------------------------------
# load_supported_cus - supported_facets
# ---------------------------------------------------------------------------


class TestLoadSupportedCusSupportedFacets:
    def test_extra_facets_added(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: basic_joining_system
            supported_facets:
              - sync_result_server_facet
            """,
        )
        assert "sync_result" in load_supported_cus(manifest_path=manifest_path)

    def test_unknown_extra_facet_does_not_crash(self, manifest_path, caplog):
        _write_manifest(
            manifest_path,
            """\
            active_profile: basic_joining_system
            supported_facets:
              - nonexistent_facet_xyz
            """,
        )
        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            supported = load_supported_cus(manifest_path=manifest_path)
        assert isinstance(supported, frozenset)
        assert "nonexistent_facet_xyz" in caplog.text


# ---------------------------------------------------------------------------
# load_supported_cus - unknown profile (missing profile file)
# ---------------------------------------------------------------------------


class TestLoadSupportedCusMissingProfile:
    def test_missing_profile_file_returns_overrides_only(self, manifest_path):
        _write_manifest(
            manifest_path,
            """\
            active_profile: nonexistent_profile_xyz
            cu_overrides:
              my_cu: supported
            """,
        )
        assert "my_cu" in load_supported_cus(manifest_path=manifest_path)

    def test_missing_profile_file_empty_without_overrides(self, manifest_path):
        _write_manifest(manifest_path, "active_profile: nonexistent_profile_xyz\n")
        supported = load_supported_cus(manifest_path=manifest_path)
        assert isinstance(supported, frozenset)
        assert len(supported) == 0


# ---------------------------------------------------------------------------
# load_supported_cus - env var integration
# ---------------------------------------------------------------------------


class TestLoadSupportedCusEnvVar:
    def test_env_var_selects_the_manifest(self, manifest_path, monkeypatch):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              env_test_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(manifest_path))
        assert "env_test_cu" in load_supported_cus()

    def test_explicit_path_takes_precedence_over_env_var(self, profile_tmp_path, monkeypatch):
        env_manifest = _write_manifest(
            profile_tmp_path / "env.sut.yaml", "active_profile: full_specification_coverage\n"
        )
        explicit = _write_manifest(
            profile_tmp_path / "explicit.sut.yaml",
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              explicit_only_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(env_manifest))
        assert "explicit_only_cu" in load_supported_cus(manifest_path=explicit)


# ---------------------------------------------------------------------------
# _load_facets - missing facets.yaml warns and returns empty dict
# ---------------------------------------------------------------------------


class TestLoadFacetsMissingFile:
    def test_missing_facets_yaml_warns_and_returns_empty(self, manifest_path, monkeypatch, caplog):
        """When profiles/facets.yaml is absent, a WARNING is logged and the result
        is an empty frozenset (no facets to populate from)."""
        monkeypatch.setattr(_pl_module, "_PROFILES_DIR", manifest_path.parent)
        _write_manifest(manifest_path, "active_profile: full_specification_coverage\n")
        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            supported = load_supported_cus(manifest_path=manifest_path)
        assert isinstance(supported, frozenset)
        assert len(supported) == 0
        assert "facets.yaml not found" in caplog.text


class TestLoadSupportedCusUnknownFacetInProfile:
    def test_unknown_facet_in_active_profile_logs_warning(self, monkeypatch, caplog, manifest_path):
        _write_manifest(manifest_path, "active_profile: some_profile\n")

        # Force the profile to list a facet that does not exist in the facets dict
        monkeypatch.setattr(_pl_module, "_resolve_profile_facets", lambda profile: ["nonexistent_facet_xyz"])
        monkeypatch.setattr(_pl_module, "_load_facets", lambda: {})

        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            result = load_supported_cus(manifest_path=manifest_path)

        assert isinstance(result, frozenset)
        assert "nonexistent_facet_xyz" in caplog.text


# ---------------------------------------------------------------------------
# resolve_session_supported_cus - one explicit selection decides the run
# ---------------------------------------------------------------------------


class TestSelectedManifestPath:
    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
        assert selected_manifest_path() is None

    def test_blank_value_counts_as_unset(self):
        assert selected_manifest_path({"OPCUA_CAPABILITIES_FILE": "   "}) is None

    def test_returns_the_selected_path(self):
        assert selected_manifest_path({"OPCUA_CAPABILITIES_FILE": "a/b.sut.yaml"}) == Path("a/b.sut.yaml")


class TestResolveSessionSupportedCus:
    def test_no_selection_claims_every_cu(self, monkeypatch):
        monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
        supported = resolve_session_supported_cus()
        assert supported is not None and len(supported) == 123

    def test_selected_manifest_gates_the_run(self, manifest_path, monkeypatch):
        _write_manifest(
            manifest_path,
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              session_scope_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(manifest_path))
        supported = resolve_session_supported_cus()
        assert supported is not None and "session_scope_cu" in supported

    def test_explicit_argument_wins_over_the_environment(self, profile_tmp_path, monkeypatch):
        env_manifest = _write_manifest(
            profile_tmp_path / "env.sut.yaml", "active_profile: full_specification_coverage\n"
        )
        explicit = _write_manifest(
            profile_tmp_path / "explicit.sut.yaml",
            """\
            active_profile: full_specification_coverage
            cu_overrides:
              explicit_session_cu: supported
            """,
        )
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(env_manifest))
        supported = resolve_session_supported_cus(explicit)
        assert supported is not None and "explicit_session_cu" in supported

    def test_missing_selected_manifest_is_a_configuration_error(self, profile_tmp_path, monkeypatch):
        missing = profile_tmp_path / "absent.sut.yaml"
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(missing))
        with pytest.raises(ExplicitManifestError) as exc:
            resolve_session_supported_cus()
        assert "absent.sut.yaml" in str(exc.value)
        assert "OPCUA_CAPABILITIES_FILE" in str(exc.value)

    def test_unreadable_selected_manifest_is_a_configuration_error(self, manifest_path, monkeypatch):
        manifest_path.write_text("schema_version: 1\nname: broken\nlifecycle:\n  mode: nonsense\n", encoding="utf-8")
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(manifest_path))
        with pytest.raises(ExplicitManifestError, match="could not be used"):
            resolve_session_supported_cus()

    def test_legacy_paired_selection_is_a_configuration_error(self, profile_tmp_path, monkeypatch):
        legacy = profile_tmp_path / "old.capabilities.yaml"
        legacy.write_text("active_profile: full_specification_coverage\n", encoding="utf-8")
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(legacy))
        with pytest.raises(ExplicitManifestError, match="could not be used"):
            resolve_session_supported_cus()

    def test_selected_manifest_never_silently_disables_gating(self, profile_tmp_path, monkeypatch):
        """The old behaviour (warn, then run every CU-gated test) must not return."""
        monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(profile_tmp_path / "absent.sut.yaml"))
        with pytest.raises(ExplicitManifestError):
            resolve_session_supported_cus()

    def test_unusable_facet_catalogue_without_selection_disables_gating(self, monkeypatch, caplog):
        monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
        monkeypatch.setattr(
            _pl_module, "load_supported_cus", lambda *a, **k: (_ for _ in ()).throw(OSError("facets unreadable"))
        )
        with caplog.at_level(logging.WARNING, logger="helpers.profile_loader"):
            assert resolve_session_supported_cus() is None
        assert "facet catalogue could not be read" in caplog.text
