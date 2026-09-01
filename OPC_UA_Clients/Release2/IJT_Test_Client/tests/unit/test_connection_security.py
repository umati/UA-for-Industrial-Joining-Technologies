"""
Unit tests for helpers/connection_security.py.

Covers the four declared credential sources (anonymous, prompt, local file,
environment/CI secret), the message security mode/policy application onto an
asyncua client, trust-store wiring, and the rule that a declared setting which
cannot be applied fails loudly instead of silently downgrading to an anonymous,
unsecured session.

No OPC UA server and no interactive input: clients are mocked and the prompt is
injected.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from helpers.connection_security import (
    SECURITY_MODE_ATTRIBUTES,
    SECURITY_POLICY_CLASS_NAMES,
    ConnectionSecurity,
    ConnectionSecurityError,
    Credentials,
    apply_connection_security,
    connection_security_from_manifest,
    connection_security_from_manifest_path,
    connection_security_from_mapping,
    describe_connection_security,
    require_appliable_connection_security,
    resolve_credentials,
    validate_connection_security,
)
from helpers.sut_manifest import build_preset, parse_sut_manifest

_PROJECT_ROOT = Path(__file__).parents[2]
_SIMULATOR_MANIFEST = _PROJECT_ROOT / "target_server_cu_profiles" / "simulator.sut.yaml"


def _write_cert_pair(tmp_path: Path) -> tuple[Path, Path]:
    cert = tmp_path / "client.der"
    key = tmp_path / "client-key.pem"
    cert.write_bytes(b"cert")
    key.write_bytes(b"key")
    return cert, key


def _secure_config(tmp_path: Path, **overrides) -> ConnectionSecurity:
    cert, key = _write_cert_pair(tmp_path)
    base = {
        "endpoint": "opc.tcp://controller:40451",
        "security_mode": "SignAndEncrypt",
        "security_policy": "Basic256Sha256",
        "client_certificate_path": str(cert),
        "client_private_key_path": str(key),
    }
    base.update(overrides)
    return ConnectionSecurity(**base)


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.set_security = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Building the declaration from a manifest
# ---------------------------------------------------------------------------


class TestBuildFromManifest:
    def test_simulator_manifest_is_anonymous_and_unsecured(self):
        security = connection_security_from_manifest(build_preset("simulator"))
        assert security.auth_source == "anonymous"
        assert security.is_default_anonymous is True
        assert security.uses_secure_channel is False

    def test_committed_simulator_manifest_file_stays_anonymous(self):
        security = connection_security_from_manifest_path(_SIMULATOR_MANIFEST)
        assert security.is_default_anonymous is True
        assert security.base_dir == str(_SIMULATOR_MANIFEST.parent)

    def test_manual_trigger_preset_declares_prompt_authentication(self):
        security = connection_security_from_manifest(build_preset("manual_trigger"))
        assert security.auth_source == "prompt"
        assert security.requires_user_identity is True

    def test_mapping_reads_connection_and_authentication(self):
        security = connection_security_from_mapping(
            {
                "connection": {
                    "endpoint": "opc.tcp://c:40451",
                    "security_mode": "Sign",
                    "security_policy": "Aes256_Sha256_RsaPss",
                    "client_certificate_path": "certs/client.der",
                },
                "authentication": {"source": "environment", "password_env_var": "IJT_PW"},
            },
            base_dir="/manifests",
        )
        assert security.security_policy == "Aes256_Sha256_RsaPss"
        assert security.password_env_var == "IJT_PW"
        assert security.resolve_path("certs/client.der") == Path("/manifests/certs/client.der")

    def test_missing_sections_fall_back_to_safe_defaults(self):
        security = connection_security_from_mapping({})
        assert security.is_default_anonymous is True

    def test_absolute_paths_are_not_rebased(self, tmp_path):
        security = ConnectionSecurity(base_dir="/manifests")
        assert security.resolve_path(str(tmp_path / "x.der")) == tmp_path / "x.der"

    def test_in_memory_manifest_has_no_base_dir(self):
        manifest = parse_sut_manifest(build_preset("manual_trigger").to_dict())
        assert connection_security_from_manifest(manifest).base_dir == ""

    def test_description_is_redacted_for_logs(self, tmp_path):
        config = _secure_config(tmp_path, auth_source="environment", password_env_var="IJT_PW", username="op")
        text = describe_connection_security(config)
        assert "IJT_PW" in text and "Basic256Sha256" in text

    def test_description_names_the_credentials_file_only(self):
        config = ConnectionSecurity(auth_source="file", credentials_file="local/creds.yaml")
        assert describe_connection_security(config) == "security=None/None identity=file:local/creds.yaml"

    def test_description_of_environment_without_username_var(self):
        config = ConnectionSecurity(auth_source="environment", password_env_var="PW")
        assert "env:(none)/PW" in describe_connection_security(config)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_anonymous_default_has_no_issues(self):
        assert validate_connection_security(ConnectionSecurity()) == []

    def test_complete_secure_config_has_no_issues(self, tmp_path):
        assert validate_connection_security(_secure_config(tmp_path)) == []

    def test_secure_mode_requires_certificate_and_key(self):
        issues = validate_connection_security(
            ConnectionSecurity(security_mode="Sign", security_policy="Basic256Sha256")
        )
        assert any("client_certificate_path" in issue for issue in issues)
        assert any("client_private_key_path" in issue for issue in issues)

    def test_missing_certificate_file_is_reported(self, tmp_path):
        config = _secure_config(tmp_path, client_certificate_path=str(tmp_path / "absent.der"))
        assert any("does not exist" in issue for issue in validate_connection_security(config))

    def test_directory_instead_of_certificate_is_reported(self, tmp_path):
        config = _secure_config(tmp_path, client_certificate_path=str(tmp_path))
        assert any("is not a file" in issue for issue in validate_connection_security(config))

    def test_mode_and_policy_must_agree(self, tmp_path):
        config = _secure_config(tmp_path, security_policy="None")
        assert any("must both be 'None' or both be secure" in issue for issue in validate_connection_security(config))

    def test_unsupported_policy_is_reported(self, tmp_path):
        config = _secure_config(tmp_path, security_policy="Basic128Rsa15")
        assert any("is not supported by this client" in issue for issue in validate_connection_security(config))

    def test_unknown_mode_is_reported(self, tmp_path):
        config = _secure_config(tmp_path, security_mode="Encrypt")
        assert any(
            "not a valid OPC UA message security mode" in issue for issue in validate_connection_security(config)
        )

    def test_server_certificate_must_exist_when_pinned(self, tmp_path):
        config = _secure_config(tmp_path, server_certificate_path=str(tmp_path / "server.der"))
        assert any("server_certificate_path" in issue for issue in validate_connection_security(config))

    def test_trust_store_must_be_a_directory(self, tmp_path):
        config = _secure_config(tmp_path, trust_store_path=str(tmp_path / "missing"))
        assert any("is not an existing directory" in issue for issue in validate_connection_security(config))

    def test_trust_store_directory_is_accepted(self, tmp_path):
        store = tmp_path / "trusted"
        store.mkdir()
        assert validate_connection_security(_secure_config(tmp_path, trust_store_path=str(store))) == []

    def test_file_source_requires_a_reference(self):
        issues = validate_connection_security(ConnectionSecurity(auth_source="file"))
        assert any("credentials_file: required" in issue for issue in issues)

    def test_file_source_reports_a_missing_file(self, tmp_path):
        config = ConnectionSecurity(auth_source="file", credentials_file=str(tmp_path / "creds.yaml"))
        assert any("does not exist" in issue for issue in validate_connection_security(config))

    def test_environment_source_requires_password_variable(self):
        issues = validate_connection_security(ConnectionSecurity(auth_source="environment"))
        assert any("password_env_var: required" in issue for issue in issues)

    def test_environment_source_reports_unset_secret(self):
        config = ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_ABSENT_PW")
        issues = validate_connection_security(config, env={})
        assert any("'IJT_ABSENT_PW' is referenced but not set" in issue for issue in issues)

    def test_environment_source_requires_a_user_name(self):
        config = ConnectionSecurity(auth_source="environment", password_env_var="PW")
        issues = validate_connection_security(config, env={"PW": "s3cret"})
        assert any("authentication.username" in issue for issue in issues)

    def test_environment_source_is_valid_with_both_variables(self):
        config = ConnectionSecurity(auth_source="environment", username_env_var="IJT_USER", password_env_var="IJT_PW")
        assert validate_connection_security(config, env={"IJT_USER": "op", "IJT_PW": "s3cret"}) == []

    def test_anonymous_source_rejects_a_user_name(self):
        issues = validate_connection_security(ConnectionSecurity(username="op"))
        assert any("must be empty when authentication.source is 'anonymous'" in issue for issue in issues)

    def test_unknown_source_is_reported(self):
        issues = validate_connection_security(ConnectionSecurity(auth_source="kerberos"))
        assert issues == ["authentication.source: 'kerberos' is not a supported credential source"]

    def test_prompt_source_is_valid_without_further_references(self):
        assert validate_connection_security(ConnectionSecurity(auth_source="prompt")) == []

    def test_require_appliable_raises_with_every_issue(self):
        with pytest.raises(ConnectionSecurityError) as exc:
            require_appliable_connection_security(
                ConnectionSecurity(security_mode="Sign", security_policy="Basic256Sha256")
            )
        assert "client_certificate_path" in str(exc.value)

    def test_require_appliable_accepts_a_valid_config(self, tmp_path):
        require_appliable_connection_security(_secure_config(tmp_path))


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------


class TestCredentialResolution:
    def test_anonymous_resolves_to_no_credentials(self):
        assert resolve_credentials(ConnectionSecurity()) is None

    def test_environment_source_reads_both_variables(self):
        config = ConnectionSecurity(auth_source="environment", username_env_var="IJT_USER", password_env_var="IJT_PW")
        creds = resolve_credentials(config, env={"IJT_USER": "operator", "IJT_PW": "s3cret"})
        assert creds == Credentials(username="operator", password="s3cret")

    def test_environment_source_uses_manifest_username(self):
        config = ConnectionSecurity(auth_source="environment", username="operator", password_env_var="IJT_PW")
        creds = resolve_credentials(config, env={"IJT_PW": "s3cret"})
        assert creds is not None and creds.username == "operator"

    def test_environment_source_without_password_variable_fails(self):
        with pytest.raises(ConnectionSecurityError, match="password_env_var is required"):
            resolve_credentials(ConnectionSecurity(auth_source="environment"), env={})

    def test_environment_source_with_unset_password_fails(self):
        config = ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_PW")
        with pytest.raises(ConnectionSecurityError, match="'IJT_PW' is not set"):
            resolve_credentials(config, env={})

    def test_environment_source_with_unset_username_variable_fails(self):
        config = ConnectionSecurity(auth_source="environment", username_env_var="IJT_USER", password_env_var="IJT_PW")
        with pytest.raises(ConnectionSecurityError, match="'IJT_USER' is not set"):
            resolve_credentials(config, env={"IJT_PW": "s3cret"})

    def test_environment_source_without_any_username_fails(self):
        config = ConnectionSecurity(auth_source="environment", password_env_var="IJT_PW")
        with pytest.raises(ConnectionSecurityError, match="no user name configured"):
            resolve_credentials(config, env={"IJT_PW": "s3cret"})

    def test_file_source_reads_a_local_yaml_file(self, tmp_path):
        creds_file = tmp_path / "creds.yaml"
        creds_file.write_text(yaml.safe_dump({"username": "operator", "password": "s3cret"}), encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        assert resolve_credentials(config) == Credentials(username="operator", password="s3cret")

    def test_file_source_reads_a_local_json_file(self, tmp_path):
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps({"user": "operator", "pass": "s3cret"}), encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        creds = resolve_credentials(config)
        assert creds is not None and creds.username == "operator"

    def test_file_source_resolves_relative_to_the_manifest(self, tmp_path):
        (tmp_path / "local").mkdir()
        (tmp_path / "local" / "creds.yaml").write_text("username: op\npassword: s3cret\n", encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file="local/creds.yaml", base_dir=str(tmp_path))
        creds = resolve_credentials(config)
        assert creds is not None and creds.password == "s3cret"

    def test_file_source_without_reference_fails(self):
        with pytest.raises(ConnectionSecurityError, match="credentials_file is required"):
            resolve_credentials(ConnectionSecurity(auth_source="file"))

    def test_file_source_with_unreadable_file_fails(self, tmp_path):
        config = ConnectionSecurity(auth_source="file", credentials_file=str(tmp_path / "absent.yaml"))
        with pytest.raises(ConnectionSecurityError, match="could not be read"):
            resolve_credentials(config)

    def test_file_source_rejects_a_non_mapping_file(self, tmp_path):
        creds_file = tmp_path / "creds.yaml"
        creds_file.write_text("- just\n- a list\n", encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        with pytest.raises(ConnectionSecurityError, match="must contain a mapping"):
            resolve_credentials(config)

    def test_file_source_rejects_unparsable_content(self, tmp_path):
        creds_file = tmp_path / "creds.yaml"
        creds_file.write_text("username: [unclosed\n", encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        with pytest.raises(ConnectionSecurityError, match="not valid YAML or JSON"):
            resolve_credentials(config)

    def test_file_source_requires_a_password_entry(self, tmp_path):
        creds_file = tmp_path / "creds.yaml"
        creds_file.write_text("username: operator\n", encoding="utf-8")
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        with pytest.raises(ConnectionSecurityError, match="no 'password' entry"):
            resolve_credentials(config)

    def test_prompt_source_uses_the_injected_provider(self):
        config = ConnectionSecurity(auth_source="prompt", endpoint="opc.tcp://c:40451")
        seen: list[ConnectionSecurity] = []

        def prompt(cfg: ConnectionSecurity) -> Credentials:
            seen.append(cfg)
            return Credentials(username="operator", password="typed")

        assert resolve_credentials(config, prompt=prompt) == Credentials("operator", "typed")
        assert seen == [config]

    def test_prompt_source_without_provider_fails_instead_of_blocking(self):
        with pytest.raises(ConnectionSecurityError, match="no credential prompt is available"):
            resolve_credentials(ConnectionSecurity(auth_source="prompt"))

    def test_prompt_source_rejects_an_empty_password(self):
        config = ConnectionSecurity(auth_source="prompt")
        with pytest.raises(ConnectionSecurityError, match="returned no password"):
            resolve_credentials(config, prompt=lambda cfg: Credentials(username="op"))

    def test_unknown_source_fails(self):
        with pytest.raises(ConnectionSecurityError, match="not a supported credential source"):
            resolve_credentials(ConnectionSecurity(auth_source="smartcard"))

    def test_password_is_never_rendered(self):
        creds = Credentials(username="operator", password="s3cret")
        assert "s3cret" not in repr(creds)
        assert "s3cret" not in str(creds)
        assert "***" in repr(creds)


# ---------------------------------------------------------------------------
# Application onto an asyncua client
# ---------------------------------------------------------------------------


class TestApplyConnectionSecurity:
    async def test_anonymous_default_touches_nothing(self):
        client = _mock_client()
        assert await apply_connection_security(client, ConnectionSecurity()) is None
        client.set_security.assert_not_awaited()
        client.set_user.assert_not_called()

    async def test_secure_channel_is_applied_with_policy_and_mode(self, tmp_path):
        from asyncua import ua
        from asyncua.crypto import security_policies

        client = _mock_client()
        config = _secure_config(tmp_path)
        await apply_connection_security(client, config)

        client.set_security.assert_awaited_once()
        args, kwargs = client.set_security.call_args
        assert args[0] is security_policies.SecurityPolicyBasic256Sha256
        assert args[1] == config.client_certificate_path
        assert args[2] == config.client_private_key_path
        assert kwargs["mode"] == ua.MessageSecurityMode.SignAndEncrypt
        assert kwargs["server_certificate"] is None

    async def test_pinned_server_certificate_is_forwarded(self, tmp_path):
        server_cert = tmp_path / "server.der"
        server_cert.write_bytes(b"server")
        client = _mock_client()
        await apply_connection_security(client, _secure_config(tmp_path, server_certificate_path=str(server_cert)))
        assert client.set_security.call_args.kwargs["server_certificate"] == str(server_cert)

    @pytest.mark.parametrize("policy", sorted(SECURITY_POLICY_CLASS_NAMES))
    async def test_every_supported_policy_maps_to_an_asyncua_class(self, tmp_path, policy):
        from asyncua.crypto import security_policies

        client = _mock_client()
        await apply_connection_security(client, _secure_config(tmp_path, security_policy=policy))
        expected = getattr(security_policies, SECURITY_POLICY_CLASS_NAMES[policy])
        assert client.set_security.call_args.args[0] is expected

    @pytest.mark.parametrize("mode", ["Sign", "SignAndEncrypt"])
    async def test_every_secure_mode_maps_to_an_asyncua_mode(self, tmp_path, mode):
        from asyncua import ua

        client = _mock_client()
        await apply_connection_security(client, _secure_config(tmp_path, security_mode=mode))
        assert client.set_security.call_args.kwargs["mode"] == getattr(
            ua.MessageSecurityMode, SECURITY_MODE_ATTRIBUTES[mode]
        )

    async def test_user_identity_is_applied_from_environment(self, tmp_path):
        client = _mock_client()
        config = _secure_config(
            tmp_path, auth_source="environment", username_env_var="IJT_USER", password_env_var="IJT_PW"
        )
        creds = await apply_connection_security(client, config, env={"IJT_USER": "operator", "IJT_PW": "s3cret"})
        assert creds == Credentials("operator", "s3cret")
        client.set_user.assert_called_once_with("operator")
        client.set_password.assert_called_once_with("s3cret")

    async def test_pre_resolved_credentials_are_reused(self):
        client = _mock_client()
        config = ConnectionSecurity(auth_source="prompt")
        creds = await apply_connection_security(client, config, credentials=Credentials("op", "typed"))
        assert creds == Credentials("op", "typed")
        client.set_user.assert_called_once_with("op")
        client.set_security.assert_not_awaited()

    async def test_user_identity_only_needs_no_secure_channel(self, tmp_path):
        creds_file = tmp_path / "creds.yaml"
        creds_file.write_text("username: op\npassword: s3cret\n", encoding="utf-8")
        client = _mock_client()
        config = ConnectionSecurity(auth_source="file", credentials_file=str(creds_file))
        await apply_connection_security(client, config)
        client.set_security.assert_not_awaited()
        client.set_password.assert_called_once_with("s3cret")

    async def test_unappliable_declaration_fails_before_connecting(self):
        client = _mock_client()
        config = ConnectionSecurity(security_mode="Sign", security_policy="Basic256Sha256")
        with pytest.raises(ConnectionSecurityError, match="cannot be applied"):
            await apply_connection_security(client, config)
        client.set_security.assert_not_awaited()

    async def test_asyncua_failure_is_reported_as_a_configuration_error(self, tmp_path):
        client = _mock_client()
        client.set_security = AsyncMock(side_effect=RuntimeError("bad key"))
        with pytest.raises(ConnectionSecurityError, match="Could not apply connection security"):
            await apply_connection_security(client, _secure_config(tmp_path))

    async def test_prompt_without_provider_fails_at_apply_time(self):
        client = _mock_client()
        with pytest.raises(ConnectionSecurityError, match="no credential prompt is available"):
            await apply_connection_security(client, ConnectionSecurity(auth_source="prompt"))

    async def test_trust_store_is_installed_as_certificate_validator(self, tmp_path, monkeypatch):
        import helpers.connection_security as cs

        store = tmp_path / "trusted"
        store.mkdir()
        installed: dict[str, object] = {}

        async def fake_trust_store(client, config):
            installed["path"] = config.resolve_path(config.trust_store_path)
            client.certificate_validator = object()

        monkeypatch.setattr(cs, "_apply_trust_store", fake_trust_store)
        client = _mock_client()
        await apply_connection_security(client, _secure_config(tmp_path, trust_store_path=str(store)))
        assert installed["path"] == store

    async def test_trust_store_failure_is_reported_clearly(self, tmp_path, monkeypatch):
        import helpers.connection_security as cs

        store = tmp_path / "trusted"
        store.mkdir()

        async def failing_trust_store(client, config):
            raise OSError("unreadable")

        monkeypatch.setattr(cs, "_apply_trust_store", failing_trust_store)
        with pytest.raises(ConnectionSecurityError, match="Could not load the trust store"):
            await apply_connection_security(_mock_client(), _secure_config(tmp_path, trust_store_path=str(store)))

    async def test_real_trust_store_helper_builds_a_validator(self, tmp_path):
        from helpers.connection_security import _apply_trust_store

        store = tmp_path / "trusted"
        store.mkdir()
        client = _mock_client()
        client.certificate_validator = None
        await _apply_trust_store(client, ConnectionSecurity(trust_store_path=str(store)))
        assert callable(client.certificate_validator)

    async def test_no_secret_reaches_the_log(self, tmp_path, caplog):
        client = _mock_client()
        config = _secure_config(tmp_path, auth_source="environment", username="op", password_env_var="IJT_PW")
        with caplog.at_level("DEBUG"):
            await apply_connection_security(client, config, env={"IJT_PW": "s3cret"})
        assert "s3cret" not in caplog.text
