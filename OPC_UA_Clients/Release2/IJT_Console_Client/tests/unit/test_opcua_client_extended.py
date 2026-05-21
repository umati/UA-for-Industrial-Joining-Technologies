# ruff: noqa: E402
"""Extended tests for opcua_client.py — covers remaining coverage gaps."""

import asyncio
import contextlib
import os
import shutil
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_ = pytest.importorskip("asyncua", reason="asyncua not installed")

from asyncua import ua
from asyncua.crypto import security_policies
from asyncua.ua.uaerrors import UaError

from opcua_client import (
    OPCUAClient,
    OPCUASecurityConfig,
    _load_ijt_type_definitions,
    validate_username_user_token_policy,
    validate_x509_user_token_policy,
)


def _preserve_test_artifacts() -> bool:
    return os.environ.get("IJT_PRESERVE_TEST_ARTIFACTS", "").lower() in {"1", "true", "yes", "on"}


def _endpoint_with_certificate_token(token_security_policy_uri: str) -> ua.EndpointDescription:
    token = ua.UserTokenPolicy()
    token.PolicyId = "certificate"
    token.TokenType = ua.UserTokenType.Certificate
    token.SecurityPolicyUri = token_security_policy_uri

    endpoint = ua.EndpointDescription()
    endpoint.SecurityPolicyUri = security_policies.SecurityPolicyBasic256Sha256.URI
    endpoint.SecurityMode = ua.MessageSecurityMode.SignAndEncrypt
    endpoint.UserIdentityTokens = [token]
    return endpoint


def _endpoint_with_username_token(token_security_policy_uri: str) -> ua.EndpointDescription:
    token = ua.UserTokenPolicy()
    token.PolicyId = "username"
    token.TokenType = ua.UserTokenType.UserName
    token.SecurityPolicyUri = token_security_policy_uri

    endpoint = ua.EndpointDescription()
    endpoint.SecurityPolicyUri = security_policies.SecurityPolicyBasic256Sha256.URI
    endpoint.SecurityMode = ua.MessageSecurityMode.SignAndEncrypt
    endpoint.UserIdentityTokens = [token]
    return endpoint


@pytest.mark.asyncio
async def test_load_ijt_type_definitions_continues_after_legacy_loader_failure():
    client = AsyncMock()
    client.load_type_definitions = AsyncMock(side_effect=RuntimeError("legacy unavailable"))
    client.load_data_type_definitions = AsyncMock()

    with patch("opcua_client.ijt_log") as mock_log:
        await _load_ijt_type_definitions(client, "unit")

    client.load_data_type_definitions.assert_awaited_once()
    assert "legacy unavailable" in str(mock_log.warning.call_args)


@pytest.mark.asyncio
async def test_configure_security_is_idempotent_when_already_configured():
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840")
    client._security_configured = True
    client.client = AsyncMock()

    await client.configure_security()

    client.client.set_security.assert_not_called()


@pytest.mark.asyncio
async def test_configure_security_rejects_unknown_secure_policy():
    config = OPCUASecurityConfig(security_policy_uri="urn:unsupported-policy")
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)

    with pytest.raises(ValueError, match="Unsupported OPC UA security policy"):
        await client.configure_security()


@pytest.mark.asyncio
async def test_configure_security_requires_client_certificate_for_secure_endpoint():
    config = OPCUASecurityConfig(security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI)
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)

    with pytest.raises(ValueError, match="client certificate and private key"):
        await client.configure_security()


@pytest.mark.asyncio
async def test_configure_security_sets_transport_security_for_secure_anonymous_client(tmp_path: Path):
    cert = tmp_path / "client.der"
    key = tmp_path / "client.pem"
    cert.write_text("cert")
    key.write_text("key")
    config = OPCUASecurityConfig(
        security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI,
        client_certificate_path=cert,
        client_private_key_path=key,
    )
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)
    client.client = AsyncMock()

    await client.configure_security()

    client.client.set_security.assert_awaited_once()
    args, kwargs = client.client.set_security.call_args
    assert args[1:] == (str(cert), str(key))
    assert kwargs["mode"] == ua.MessageSecurityMode.SignAndEncrypt
    assert client._security_configured is True


@pytest.mark.asyncio
async def test_configure_security_requires_username_credentials():
    config = OPCUASecurityConfig(user_identity="username", username="user1")
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)

    with pytest.raises(ValueError, match="UserName identity requires"):
        await client.configure_security()


@pytest.mark.asyncio
async def test_configure_security_sets_username_identity(tmp_path: Path):
    client_cert = tmp_path / "client.der"
    client_key = tmp_path / "client.pem"
    client_cert.write_text("cert")
    client_key.write_text("key")
    config = OPCUASecurityConfig(
        security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI,
        client_certificate_path=client_cert,
        client_private_key_path=client_key,
        user_identity="username",
        username="user1",
        password="pw",
    )
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)
    client.client = MagicMock()
    client.client.set_security = AsyncMock()

    with patch.object(client, "validate_configured_user_token_policy", new_callable=AsyncMock) as validate_policy:
        await client.configure_security()

    validate_policy.assert_awaited_once_with(
        config,
        ua.UserTokenType.UserName,
        "UserName",
    )
    client.client.set_user.assert_called_once_with("user1")
    client.client.set_password.assert_called_once_with("pw")


@pytest.mark.asyncio
async def test_configure_security_requires_x509_identity_material():
    config = OPCUASecurityConfig(user_identity="x509")
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)

    with pytest.raises(ValueError, match="X509 identity requires"):
        await client.configure_security()


@pytest.mark.asyncio
async def test_configure_security_loads_x509_identity_material(tmp_path: Path):
    client_cert = tmp_path / "client.der"
    client_key = tmp_path / "client.pem"
    cert = tmp_path / "user.der"
    key = tmp_path / "user.pem"
    client_cert.write_text("cert")
    client_key.write_text("key")
    cert.write_text("cert")
    key.write_text("key")
    config = OPCUASecurityConfig(
        security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI,
        client_certificate_path=client_cert,
        client_private_key_path=client_key,
        user_identity="x509",
        x509_certificate_path=cert,
        x509_private_key_path=key,
    )
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)
    client.client = AsyncMock()

    with patch.object(client, "validate_configured_user_token_policy", new_callable=AsyncMock) as validate_policy:
        await client.configure_security()

    client.client.load_client_certificate.assert_awaited_once_with(str(cert))
    client.client.load_private_key.assert_awaited_once_with(key)
    validate_policy.assert_awaited_once_with(
        config,
        ua.UserTokenType.Certificate,
        "X509 Certificate",
    )


@pytest.mark.asyncio
async def test_configure_security_rejects_unknown_identity_kind():
    config = OPCUASecurityConfig(user_identity="issued-token")  # type: ignore[arg-type]
    with patch("opcua_client.Client"):
        client = OPCUAClient("opc.tcp://localhost:4840", config)

    with pytest.raises(ValueError, match="Unsupported user identity kind"):
        await client.configure_security()


@pytest.mark.asyncio
async def test_validate_configured_user_token_policy_accepts_matching_endpoint():
    config = OPCUASecurityConfig(security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI)
    endpoint = _endpoint_with_username_token(security_policies.SecurityPolicyBasic256Sha256.URI)
    probe = AsyncMock()
    probe.connect_and_get_server_endpoints = AsyncMock(return_value=[endpoint])

    with patch("opcua_client.Client", return_value=probe):
        client = OPCUAClient("opc.tcp://localhost:4840")
        await client.validate_configured_user_token_policy(config, ua.UserTokenType.UserName, "UserName")


@pytest.mark.asyncio
async def test_validate_configured_user_token_policy_rejects_missing_endpoint():
    config = OPCUASecurityConfig(security_policy_uri=security_policies.SecurityPolicyBasic256Sha256.URI)
    wrong_endpoint = _endpoint_with_username_token(security_policies.SecurityPolicyBasic256Sha256.URI)
    wrong_endpoint.SecurityMode = ua.MessageSecurityMode.Sign
    probe = AsyncMock()
    probe.connect_and_get_server_endpoints = AsyncMock(return_value=[wrong_endpoint])

    with patch("opcua_client.Client", return_value=probe):
        client = OPCUAClient("opc.tcp://localhost:4840")
        with pytest.raises(ValueError, match="Endpoint not found"):
            await client.validate_configured_user_token_policy(config, ua.UserTokenType.UserName, "UserName")


# ── connect() — retry then success ──


@pytest.mark.asyncio
async def test_connect_retries_then_succeeds():
    """connect() logs retry info and succeeds on second attempt."""
    attempt = [0]

    async def _connect_mock():
        attempt[0] += 1
        if attempt[0] < 2:
            raise OSError("transient failure")

    with patch("opcua_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = _connect_mock
        mock_client.load_type_definitions = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        MockClient.return_value = mock_client

        c = OPCUAClient("opc.tcp://localhost:4840")
        c.client = mock_client

        with patch.object(c, "clear_old_logs", new_callable=AsyncMock):
            with patch.dict(
                "os.environ",
                {
                    "OPCUA_CONNECT_RETRIES": "3",
                    "OPCUA_CONNECT_DELAY_SEC": "0.01",
                    "OPCUA_CONNECT_MAX_DELAY_SEC": "0.01",
                },
            ):
                await c.connect()  # must succeed

    assert attempt[0] == 2


@pytest.mark.asyncio
async def test_connect_logs_retry_message():
    """connect() logs a retry message between attempts."""
    attempt = [0]

    async def _connect_mock():
        attempt[0] += 1
        if attempt[0] < 2:
            raise OSError("fail once")

    with patch("opcua_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = _connect_mock
        mock_client.load_type_definitions = AsyncMock()
        mock_client.load_data_type_definitions = AsyncMock()
        MockClient.return_value = mock_client

        c = OPCUAClient("opc.tcp://localhost:4840")
        c.client = mock_client

        with patch.object(c, "clear_old_logs", new_callable=AsyncMock):
            with patch("opcua_client.ijt_log") as mock_log:
                with patch.dict(
                    "os.environ",
                    {
                        "OPCUA_CONNECT_RETRIES": "2",
                        "OPCUA_CONNECT_DELAY_SEC": "0.01",
                        "OPCUA_CONNECT_MAX_DELAY_SEC": "0.01",
                    },
                ):
                    await c.connect()

        # "Retrying in" should appear in one of the info calls
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        assert any("Retrying" in s for s in info_calls)


def test_validate_x509_user_token_policy_accepts_endpoint_default_uri():
    endpoint = _endpoint_with_certificate_token("")

    validate_x509_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_x509_user_token_policy_rejects_security_policy_none_endpoint_default():
    endpoint = _endpoint_with_certificate_token("")

    with pytest.raises(ValueError, match="requires a secure endpoint"):
        validate_x509_user_token_policy(endpoint, security_policies.SecurityPolicyNone.URI)


def test_validate_x509_user_token_policy_rejects_security_policy_none():
    endpoint = _endpoint_with_certificate_token(security_policies.SecurityPolicyNone.URI)

    with pytest.raises(ValueError, match="SecurityPolicy#None"):
        validate_x509_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_x509_user_token_policy_rejects_policy_mismatch():
    endpoint = _endpoint_with_certificate_token(security_policies.SecurityPolicyAes256Sha256RsaPss.URI)

    with pytest.raises(ValueError, match="does not match"):
        validate_x509_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_x509_user_token_policy_requires_certificate_token():
    endpoint = ua.EndpointDescription()
    endpoint.SecurityPolicyUri = security_policies.SecurityPolicyBasic256Sha256.URI
    endpoint.SecurityMode = ua.MessageSecurityMode.SignAndEncrypt
    endpoint.UserIdentityTokens = []

    with pytest.raises(ValueError, match="Certificate user-token policy"):
        validate_x509_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_username_user_token_policy_accepts_endpoint_default_uri():
    endpoint = _endpoint_with_username_token("")

    validate_username_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_username_user_token_policy_rejects_security_policy_none_endpoint_default():
    endpoint = _endpoint_with_username_token("")

    with pytest.raises(ValueError, match="requires a secure endpoint"):
        validate_username_user_token_policy(endpoint, security_policies.SecurityPolicyNone.URI)


def test_validate_username_user_token_policy_rejects_security_policy_none():
    endpoint = _endpoint_with_username_token(security_policies.SecurityPolicyNone.URI)

    with pytest.raises(ValueError, match="SecurityPolicy#None"):
        validate_username_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_username_user_token_policy_rejects_policy_mismatch():
    endpoint = _endpoint_with_username_token(security_policies.SecurityPolicyAes256Sha256RsaPss.URI)

    with pytest.raises(ValueError, match="does not match"):
        validate_username_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


def test_validate_username_user_token_policy_requires_username_token():
    endpoint = ua.EndpointDescription()
    endpoint.SecurityPolicyUri = security_policies.SecurityPolicyBasic256Sha256.URI
    endpoint.SecurityMode = ua.MessageSecurityMode.SignAndEncrypt
    endpoint.UserIdentityTokens = []

    with pytest.raises(ValueError, match="UserName user-token policy"):
        validate_username_user_token_policy(endpoint, security_policies.SecurityPolicyBasic256Sha256.URI)


# ── subscribe_to_events() — happy path ──


@pytest.mark.asyncio
async def test_subscribe_to_events_sets_handlers():
    """subscribe_to_events creates and stores handler_result_event and handler_joining_event."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    mock_root = AsyncMock()
    server_node = AsyncMock()
    mock_root.get_child = AsyncMock(return_value=server_node)

    node1, node2, node3 = AsyncMock(), AsyncMock(), AsyncMock()

    mock_sub = AsyncMock()
    mock_sub.subscribe_events = AsyncMock()

    c.client = MagicMock()
    c.client.get_root_node = MagicMock(return_value=mock_root)
    c.client.load_data_type_definitions = AsyncMock()
    c.client.create_subscription = AsyncMock(return_value=mock_sub)

    with patch("opcua_client.get_event_types", return_value=(node1, node2, node3)):
        with patch("opcua_client.ResultEventHandler"):
            with patch("opcua_client.EventHandler"):
                await c.subscribe_to_events()

    assert c.handler_result_event is not None
    assert c.handler_joining_event is not None


@pytest.mark.asyncio
async def test_subscribe_to_events_creates_two_subscriptions():
    """subscribe_to_events creates one subscription for results and one for joining events."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    mock_root = AsyncMock()
    server_node = AsyncMock()
    mock_root.get_child = AsyncMock(return_value=server_node)

    mock_sub = AsyncMock()
    mock_sub.subscribe_events = AsyncMock()

    c.client = MagicMock()
    c.client.get_root_node = MagicMock(return_value=mock_root)
    c.client.load_data_type_definitions = AsyncMock()
    c.client.create_subscription = AsyncMock(return_value=mock_sub)

    with patch("opcua_client.get_event_types", return_value=(AsyncMock(), AsyncMock(), AsyncMock())):
        with patch("opcua_client.ResultEventHandler"):
            with patch("opcua_client.EventHandler"):
                await c.subscribe_to_events()

    assert c.client.create_subscription.await_count == 2


# ── subscribe_to_events() — exception path ──


@pytest.mark.asyncio
async def test_subscribe_to_events_exception_calls_cleanup_and_reraises():
    """subscribe_to_events calls cleanup() and re-raises on failure."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    c.client = MagicMock()
    c.client.get_root_node = MagicMock(side_effect=RuntimeError("root node failed"))

    with patch.object(c, "cleanup", new_callable=AsyncMock) as mock_cleanup:
        with patch("opcua_client.ResultEventHandler"):
            with patch("opcua_client.EventHandler"):
                with pytest.raises(RuntimeError, match="root node failed"):
                    await c.subscribe_to_events()

        mock_cleanup.assert_awaited_once()


# ── run_forever() ──


@pytest.mark.asyncio
async def test_run_forever_calls_cleanup_on_cancellation():
    """run_forever calls cleanup() when cancelled."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    with patch.object(c, "cleanup", new_callable=AsyncMock) as mock_cleanup:
        task = asyncio.create_task(c.run_forever())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        mock_cleanup.assert_awaited()


@pytest.mark.asyncio
async def test_run_forever_handles_unexpected_exception():
    """run_forever logs unexpected exceptions and calls cleanup."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    with patch.object(c, "cleanup", new_callable=AsyncMock) as mock_cleanup:
        with patch("asyncio.sleep", side_effect=RuntimeError("unexpected")):
            with patch("opcua_client.ijt_log") as mock_log:
                await c.run_forever()

            mock_log.warning.assert_called()
            mock_cleanup.assert_awaited()


# ── cleanup() — UaError variants ──


@pytest.mark.asyncio
async def test_cleanup_ua_error_no_request_found_is_warning():
    """cleanup() logs 'No request found' UaError as a warning (not an error)."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    mock_inner = AsyncMock()
    mock_inner.disconnect = AsyncMock(side_effect=UaError("No request found for request handle"))
    c.client = mock_inner

    with patch("opcua_client.ijt_log") as mock_log:
        await c.cleanup()

    warning_calls = [str(call) for call in mock_log.warning.call_args_list]
    assert any("No request found" in s or "Late server response" in s for s in warning_calls)


@pytest.mark.asyncio
async def test_cleanup_ua_error_other_is_warning():
    """cleanup() logs other UaError as a warning."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    mock_inner = AsyncMock()
    mock_inner.disconnect = AsyncMock(side_effect=UaError("Connection reset"))
    c.client = mock_inner

    with patch("opcua_client.ijt_log") as mock_log:
        await c.cleanup()

    mock_log.warning.assert_called()


@pytest.mark.asyncio
async def test_cleanup_generic_disconnect_exception_is_warning():
    """cleanup() logs generic disconnect exceptions as warnings."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    mock_inner = AsyncMock()
    mock_inner.disconnect = AsyncMock(side_effect=OSError("connection dropped"))
    c.client = mock_inner

    with patch("opcua_client.ijt_log") as mock_log:
        await c.cleanup()

    mock_log.warning.assert_called()


@pytest.mark.asyncio
async def test_cleanup_client_already_none_logs_info():
    """cleanup() logs 'already cleaned up' message when client is None."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    c.client = None

    with patch("opcua_client.ijt_log") as mock_log:
        await c.cleanup()

    info_calls = [str(call) for call in mock_log.info.call_args_list]
    assert any("already" in s.lower() or "cleaned" in s.lower() for s in info_calls)


# ── clear_old_logs() ──


@pytest.mark.asyncio
async def test_clear_old_logs_deletes_json_files(monkeypatch):
    """clear_old_logs deletes .json files from the logs/results directory."""
    orig_cwd = Path.cwd()
    work_dir = orig_cwd / "tmp" / f"pytest-local-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    try:
        monkeypatch.chdir(work_dir)

        log_dir = work_dir / "logs" / "results"
        log_dir.mkdir(parents=True)
        (log_dir / "result1.json").write_text("{}")
        (log_dir / "result2.json").write_text("{}")
        (log_dir / "keep.txt").write_text("keep")

        with patch("opcua_client.Client"):
            c = OPCUAClient("opc.tcp://localhost:4840")

        await c.clear_old_logs()

        remaining = list(log_dir.glob("*.json"))
        if _preserve_test_artifacts():
            assert len(remaining) == 2
        else:
            assert len(remaining) == 0
        assert (log_dir / "keep.txt").exists()
    finally:
        monkeypatch.chdir(orig_cwd)
        if not _preserve_test_artifacts():
            shutil.rmtree(work_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_clear_old_logs_creates_directory_if_missing(monkeypatch):
    """clear_old_logs creates logs/results directory when it does not exist."""
    orig_cwd = Path.cwd()
    work_dir = orig_cwd / "tmp" / f"pytest-local-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    try:
        monkeypatch.chdir(work_dir)
        # mkdir() without parents=True requires the parent to exist
        (work_dir / "logs").mkdir()

        log_dir = work_dir / "logs" / "results"
        assert not log_dir.exists()

        with patch("opcua_client.Client"):
            c = OPCUAClient("opc.tcp://localhost:4840")

        await c.clear_old_logs()

        if _preserve_test_artifacts():
            assert not log_dir.exists()
        else:
            assert log_dir.exists()
    finally:
        monkeypatch.chdir(orig_cwd)
        if not _preserve_test_artifacts():
            shutil.rmtree(work_dir, ignore_errors=True)


# ── cleanup() — outer except catches unexpected error (L175-177) ──


@pytest.mark.asyncio
async def test_cleanup_outer_except_catches_unexpected_error():
    """cleanup() outer except block catches and logs unexpected errors (L175-177)."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:4840")

    c.client = None  # skip inner disconnect branch

    with patch("opcua_client.asyncio.sleep", side_effect=RuntimeError("sleep boom")):
        with patch("opcua_client.ijt_log") as mock_log:
            await c.cleanup()  # must NOT raise

    error_calls = [str(call) for call in mock_log.error.call_args_list]
    assert any("sleep boom" in s or "Cleanup error" in s for s in error_calls)
