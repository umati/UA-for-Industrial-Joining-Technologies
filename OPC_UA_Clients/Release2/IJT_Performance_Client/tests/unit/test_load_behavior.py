"""Behavior added for production load tests. These tests check control flow, not latency."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.config import OpcUaPoolConfig, load_config
from src.connection_security import ConnectionSecurity, validate_connection_security
from src.engine.session_policy import DEFAULT_CLIENT_TIMEOUT_S, DEFAULT_WATCHDOG_INTERVAL_S, apply_session_policy
from src.results.latency import INTEGRITY_INCOMPLETE, INTEGRITY_VALID, extract_sample_from_event


def _fleet():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "run_fleet.py"
    spec = importlib.util.spec_from_file_location("fleet_load_behavior", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_measurement_window_grows_only_when_the_cap_splits_a_round():
    fleet = _fleet()
    uncapped = fleet.measurement_window_seconds(
        servers=300, samples_per_server=10, burst_delay=1.5, workers=20, max_inflight=0
    )
    capped = fleet.measurement_window_seconds(
        servers=300, samples_per_server=10, burst_delay=1.5, workers=20, max_inflight=4
    )
    one_wave = fleet.measurement_window_seconds(
        servers=300, samples_per_server=10, burst_delay=1.5, workers=20, max_inflight=15
    )
    assert uncapped == 60.0
    assert one_wave == uncapped
    assert capped > uncapped


def test_measurement_window_uses_the_worker_count_the_pool_will_start(monkeypatch):
    fleet = _fleet()
    args = argparse.Namespace(workers=None, max_inflight=None, mode=None)
    pinned = OpcUaPoolConfig(endpoints=["opc.tcp://127.0.0.1:1"], max_worker_processes=4)
    assert fleet._worker_count(args, pinned) == 4
    many_workers = fleet.measurement_window_seconds(
        servers=500, samples_per_server=10, burst_delay=1.0, workers=25, max_inflight=4
    )
    few_workers = fleet.measurement_window_seconds(
        servers=500, samples_per_server=10, burst_delay=1.0, workers=4, max_inflight=4
    )
    assert few_workers > many_workers
    monkeypatch.setenv("OPCUA_WORKERS", "8")
    assert fleet._worker_count(args, pinned) == 8
    assert fleet._worker_count(argparse.Namespace(workers=2, max_inflight=None, mode=None), pinned) == 2
    monkeypatch.delenv("OPCUA_WORKERS", raising=False)
    free = OpcUaPoolConfig(endpoints=["opc.tcp://127.0.0.1:1"])
    assert fleet._worker_count(args, free) is None


def test_default_fleet_mode_stays_both_and_a_passive_profile_is_honored():
    fleet = _fleet()
    args = argparse.Namespace(mode=None, max_inflight=None)
    simulator = OpcUaPoolConfig(endpoints=["opc.tcp://127.0.0.1:1"])
    assert fleet._execution_mode(args, simulator) == "both"
    assert fleet._inflight_cap(args, simulator) == 4

    passive = OpcUaPoolConfig(endpoints=["opc.tcp://127.0.0.1:1"], mode="passive")
    passive.explicit_profile_fields = frozenset({"mode"})
    assert fleet._execution_mode(args, passive) == "passive"
    assert fleet._execution_mode(argparse.Namespace(mode="active_burst", max_inflight=None), passive) == "active_burst"


def test_controller_profile_is_listen_only_and_anonymous():
    cfg = load_config("controller_observe.yaml")
    assert cfg.mode == "passive"
    assert cfg.role == "client-only"
    assert cfg.burst_trigger_count == 0
    assert cfg.connection_security.is_default_anonymous
    assert "mode" in cfg.explicit_profile_fields


def test_secure_profile_without_a_certificate_fails_before_connect(tmp_path):
    profile = tmp_path / "secure.yaml"
    profile.write_text(
        "schema_version: 2\n"
        "name: Secure\n"
        "role: client-only\n"
        "inventory:\n"
        "  source: inv.json\n"
        "connection:\n"
        "  security_mode: SignAndEncrypt\n"
        "  security_policy: Basic256Sha256\n",
        encoding="utf-8",
    )
    try:
        load_config(profile)
    except ValueError as exc:
        text = str(exc)
    else:
        raise AssertionError("secure profile without certificates must not load")
    assert "client_certificate_path" in text
    assert validate_connection_security(load_config("controller_observe.yaml").connection_security) == []


def test_failed_clock_probe_excludes_an_otherwise_valid_sample_from_statistics():
    now = datetime.now(UTC)
    event = SimpleNamespace(
        Time=now,
        Result=SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="R1", ProcessingTimes=SimpleNamespace(StartTime=now, EndTime=now))
        ),
    )
    failed = extract_sample_from_event(event, now, 1, "opc.tcp://controller:4840", clock_probe_failed=True)
    ok = extract_sample_from_event(event, now, 1, "opc.tcp://127.0.0.1:4840", clock_probe_failed=False)
    assert failed.integrity_status == INTEGRITY_INCOMPLETE
    assert "not calibrated" in failed.integrity_reason
    assert ok.integrity_status == INTEGRITY_VALID


def test_mistyped_security_key_does_not_load_as_anonymous(tmp_path):
    profile = tmp_path / "typo.yaml"
    profile.write_text(
        "schema_version: 2\n"
        "name: Typo\n"
        "role: client-only\n"
        "inventory:\n"
        "  source: inv.json\n"
        "connection:\n"
        "  security_modee: SignAndEncrypt\n"
        "  security_policy: Basic256Sha256\n",
        encoding="utf-8",
    )
    try:
        load_config(profile)
    except ValueError as exc:
        text = str(exc)
    else:
        raise AssertionError("unknown connection key must not load")
    assert "security_modee" in text


def test_inline_password_is_rejected(tmp_path):
    profile = tmp_path / "secret.yaml"
    profile.write_text(
        "schema_version: 2\n"
        "name: Secret\n"
        "role: client-only\n"
        "inventory:\n"
        "  source: inv.json\n"
        "authentication:\n"
        "  source: anonymous\n"
        "  password: hunter2\n",
        encoding="utf-8",
    )
    try:
        load_config(profile)
    except ValueError as exc:
        text = str(exc)
    else:
        raise AssertionError("inline password must not load")
    assert "password" in text
    assert "hunter2" not in text


def test_certificates_or_user_identity_without_a_secure_channel_fail():
    material = ConnectionSecurity(client_certificate_path="client.der", trust_store_path="trusted")
    identity = ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_PW")
    assert material.is_default_anonymous is False
    assert identity.is_default_anonymous is False
    assert any("other than 'None'" in issue for issue in validate_connection_security(material))
    assert any("user identity" in issue for issue in validate_connection_security(identity))
    assert ConnectionSecurity().is_default_anonymous is True
    assert validate_connection_security(ConnectionSecurity()) == []


def test_relative_certificate_path_without_a_profile_directory_is_refused(tmp_path):
    cert = tmp_path / "client.der"
    key = tmp_path / "client.pem"
    trust = tmp_path / "trusted"
    cert.write_bytes(b"cert")
    key.write_bytes(b"key")
    trust.mkdir()
    anchored = ConnectionSecurity(
        security_mode="SignAndEncrypt",
        security_policy="Basic256Sha256",
        client_certificate_path=cert.name,
        client_private_key_path=key.name,
        trust_store_path=trust.name,
        base_dir="",
    )
    issues = validate_connection_security(anchored)
    assert any("relative path" in issue for issue in issues)
    absolute = ConnectionSecurity(
        security_mode="SignAndEncrypt",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        trust_store_path=str(trust),
        base_dir="",
    )
    assert validate_connection_security(absolute) == []


def test_session_policy_sets_the_request_timeout_and_watchdog():
    from unittest.mock import MagicMock

    from asyncua import Client

    client = MagicMock()
    client.aio_obj = MagicMock()
    apply_session_policy(client)
    assert client.timeout == DEFAULT_CLIENT_TIMEOUT_S
    assert client.watchdog_intervall == DEFAULT_WATCHDOG_INTERVAL_S
    assert client.session_timeout == 600_000

    real = Client("opc.tcp://127.0.0.1:1", timeout=4, watchdog_intervall=1)
    apply_session_policy(real)
    assert real.uaclient._timeout == DEFAULT_CLIENT_TIMEOUT_S
    assert real._watchdog_intervall == DEFAULT_WATCHDOG_INTERVAL_S


@pytest.mark.asyncio
async def test_apply_connection_security_is_a_noop_for_anonymous():
    from unittest.mock import MagicMock

    from src.connection_security import apply_connection_security

    client = MagicMock()
    assert await apply_connection_security(client, ConnectionSecurity()) is None
    client.set_security.assert_not_called()
    client.set_user.assert_not_called()
    client.set_password.assert_not_called()


def test_connection_security_rejects_unsupported_policy_and_auth(tmp_path):
    from src.connection_security import (
        ConnectionSecurityError,
        Credentials,
        connection_security_from_mapping,
        describe_connection_security,
        require_appliable_connection_security,
        resolve_credentials,
    )

    bad_policy = ConnectionSecurity(security_mode="Sign", security_policy="Basic128Rsa15")
    assert any("not supported" in issue for issue in validate_connection_security(bad_policy))

    bad_auth = ConnectionSecurity(auth_source="ldap")
    assert any("not a supported credential source" in issue for issue in validate_connection_security(bad_auth))

    try:
        require_appliable_connection_security(bad_policy)
    except ConnectionSecurityError as exc:
        assert "cannot be applied" in str(exc)
    else:
        raise AssertionError("require_appliable must raise")

    creds = tmp_path / "creds.yaml"
    creds.write_text("username: op\npassword: s3cret\n", encoding="utf-8")
    file_cfg = ConnectionSecurity(
        security_mode="SignAndEncrypt",
        security_policy="Basic256Sha256",
        client_certificate_path=str(tmp_path / "c.der"),
        client_private_key_path=str(tmp_path / "c.pem"),
        auth_source="file",
        credentials_file=str(creds),
    )
    (tmp_path / "c.der").write_bytes(b"c")
    (tmp_path / "c.pem").write_bytes(b"k")
    resolved = resolve_credentials(file_cfg)
    assert resolved == Credentials(username="op", password="s3cret")
    assert "s3cret" not in repr(resolved)
    assert "s3cret" not in describe_connection_security(file_cfg)

    mapped = connection_security_from_mapping(
        {
            "connection": {
                "security_mode": "None",
                "security_policy": "None",
            },
            "authentication": {"source": "anonymous"},
        },
        base_dir=str(tmp_path),
    )
    assert mapped.is_default_anonymous is True
    assert resolve_credentials(mapped) is None


def test_environment_credentials_resolve_without_leaking_the_password(monkeypatch):
    from src.connection_security import resolve_credentials

    monkeypatch.setenv("IJT_PERF_USER", "operator")
    monkeypatch.setenv("IJT_PERF_PW", "top-secret")
    cfg = ConnectionSecurity(
        security_mode="Sign",
        security_policy="Basic256Sha256",
        client_certificate_path="C:/abs/client.der",
        client_private_key_path="C:/abs/client.pem",
        auth_source="environment",
        username_env_var="IJT_PERF_USER",
        password_env_var="IJT_PERF_PW",
        base_dir="",
    )
    # Absolute paths still need to exist for validate; resolve_credentials does not re-check files.
    creds = resolve_credentials(cfg, env={"IJT_PERF_USER": "operator", "IJT_PERF_PW": "top-secret"})
    assert creds is not None
    assert creds.username == "operator"
    assert creds.password == "top-secret"
    assert "top-secret" not in repr(creds)


@pytest.mark.asyncio
async def test_apply_connection_security_sets_channel_and_user(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    from src.connection_security import (
        ConnectionSecurityError,
        Credentials,
        apply_connection_security,
        resolve_credentials,
    )

    cert = tmp_path / "client.der"
    key = tmp_path / "client.pem"
    trust = tmp_path / "trusted"
    cert.write_bytes(b"cert")
    key.write_bytes(b"key")
    trust.mkdir()
    cfg = ConnectionSecurity(
        security_mode="SignAndEncrypt",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        trust_store_path=str(trust),
        auth_source="environment",
        username="op",
        password_env_var="IJT_APPLY_PW",
    )
    client = MagicMock()
    client.set_security = AsyncMock()
    monkeypatch.setattr(
        "src.connection_security._apply_trust_store",
        AsyncMock(),
    )
    resolved = await apply_connection_security(
        client,
        cfg,
        env={"IJT_APPLY_PW": "pw"},
        credentials=Credentials(username="op", password="pw"),
    )
    assert resolved == Credentials(username="op", password="pw")
    client.set_security.assert_awaited_once()
    client.set_user.assert_called_once_with("op")
    client.set_password.assert_called_once_with("pw")

    with pytest.raises(ConnectionSecurityError, match="credentials_file is required"):
        resolve_credentials(ConnectionSecurity(auth_source="file"))
    with pytest.raises(ConnectionSecurityError, match="password_env_var is required"):
        resolve_credentials(ConnectionSecurity(auth_source="environment"))
    with pytest.raises(ConnectionSecurityError, match="no credential prompt"):
        resolve_credentials(ConnectionSecurity(auth_source="prompt"))
    with pytest.raises(ConnectionSecurityError, match="returned no password"):
        resolve_credentials(
            ConnectionSecurity(auth_source="prompt"),
            prompt=lambda _cfg: Credentials(username="op", password=""),
        )
    prompted = resolve_credentials(
        ConnectionSecurity(auth_source="prompt", username="op"),
        prompt=lambda _cfg: Credentials(username="op", password="typed"),
    )
    assert prompted == Credentials(username="op", password="typed")

    bad = tmp_path / "bad.json"
    bad.write_text('{"username": "op"}', encoding="utf-8")
    with pytest.raises(ConnectionSecurityError, match="no 'password' entry"):
        resolve_credentials(ConnectionSecurity(auth_source="file", credentials_file=str(bad)))

    anon_with_user = ConnectionSecurity(username="op")
    assert any("must be empty" in issue for issue in validate_connection_security(anon_with_user))

    with pytest.raises(ConnectionSecurityError, match="is not set"):
        resolve_credentials(
            ConnectionSecurity(auth_source="environment", username="op", password_env_var="IJT_MISSING_PW"),
            env={},
        )
    with pytest.raises(ConnectionSecurityError, match="is not set"):
        resolve_credentials(
            ConnectionSecurity(
                auth_source="environment",
                username_env_var="IJT_MISSING_USER",
                password_env_var="IJT_APPLY_PW",
            ),
            env={"IJT_APPLY_PW": "pw"},
        )
    with pytest.raises(ConnectionSecurityError, match="no user name"):
        resolve_credentials(
            ConnectionSecurity(auth_source="environment", password_env_var="IJT_APPLY_PW"),
            env={"IJT_APPLY_PW": "pw"},
        )
    with pytest.raises(ConnectionSecurityError, match="not a supported credential source"):
        resolve_credentials(ConnectionSecurity(auth_source="ldap"))

    missing_file = ConnectionSecurity(auth_source="file", credentials_file=str(tmp_path / "nope.yaml"))
    with pytest.raises(ConnectionSecurityError, match="could not be read|does not exist|no 'password'|not valid"):
        resolve_credentials(missing_file)

    broken = tmp_path / "broken.txt"
    broken.write_text("{]", encoding="utf-8")
    with pytest.raises(ConnectionSecurityError, match="not valid YAML or JSON"):
        resolve_credentials(ConnectionSecurity(auth_source="file", credentials_file=str(broken)))

    not_mapping = tmp_path / "list.yaml"
    not_mapping.write_text("- only\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConnectionSecurityError, match="must contain a mapping"):
        resolve_credentials(ConnectionSecurity(auth_source="file", credentials_file=str(not_mapping)))

    client.set_security = AsyncMock(side_effect=RuntimeError("set_security boom"))
    with pytest.raises(ConnectionSecurityError, match="Could not apply connection security"):
        await apply_connection_security(client, cfg, env={"IJT_APPLY_PW": "pw"})

    trust_cfg = ConnectionSecurity(
        security_mode="Sign",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        trust_store_path=str(trust),
        auth_source="anonymous",
    )
    client.set_security = AsyncMock()
    monkeypatch.setattr(
        "src.connection_security._apply_trust_store",
        AsyncMock(side_effect=RuntimeError("trust boom")),
    )
    with pytest.raises(ConnectionSecurityError, match="Could not load the trust store"):
        await apply_connection_security(client, trust_cfg)

    file_missing = ConnectionSecurity(
        security_mode="Sign",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        auth_source="file",
    )
    assert any("credentials_file: required" in issue for issue in validate_connection_security(file_missing))
    env_missing_pw = ConnectionSecurity(
        security_mode="Sign",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        auth_source="environment",
        username="op",
    )
    assert any("password_env_var: required" in issue for issue in validate_connection_security(env_missing_pw))
    env_missing_user = ConnectionSecurity(
        security_mode="Sign",
        security_policy="Basic256Sha256",
        client_certificate_path=str(cert),
        client_private_key_path=str(key),
        auth_source="environment",
        password_env_var="IJT_APPLY_PW",
    )
    assert any(
        "username" in issue for issue in validate_connection_security(env_missing_user, env={"IJT_APPLY_PW": "pw"})
    )


@pytest.mark.asyncio
async def test_apply_trust_store_installs_a_certificate_validator(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    from src.connection_security import ConnectionSecurity, _apply_trust_store

    trust = tmp_path / "trusted"
    trust.mkdir()
    cfg = ConnectionSecurity(trust_store_path=str(trust))
    client = MagicMock()
    fake_store = MagicMock()
    fake_store.load = AsyncMock()
    monkeypatch.setattr("asyncua.crypto.truststore.TrustStore", MagicMock(return_value=fake_store))
    monkeypatch.setattr(
        "asyncua.crypto.validator.CertificateValidator",
        MagicMock(return_value=MagicMock(validate="validator")),
    )
    await _apply_trust_store(client, cfg)
    assert client.certificate_validator == "validator"
    fake_store.load.assert_awaited_once()


def test_effective_config_redacts_connection_security_and_tokens():
    from src.effective_config import EffectiveConfigTracker

    cfg = OpcUaPoolConfig(
        endpoints=["opc.tcp://127.0.0.1:1"],
        inventory_http_token="super-secret-token",
        connection_security=ConnectionSecurity(auth_source="environment", password_env_var="IJT_PW"),
    )
    snap = EffectiveConfigTracker().snapshot(cfg)
    assert snap["inventory_http_token"]["value"] == "***"
    assert "super-secret-token" not in str(snap)
    assert "password=" not in str(snap["connection_security"]["value"])
    assert "IJT_PW" in str(snap["connection_security"]["value"])
