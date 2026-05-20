# ruff: noqa: E402,I001
from __future__ import annotations

import asyncio
import contextlib
import os
import re
import sys
from pathlib import Path

import pytest
from asyncua import Client, ua
from asyncua.crypto import security_policies

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from opcua_client import (  # noqa: E402
    OPCUAClient,
    OPCUASecurityConfig,
    UserIdentityKind,
    validate_username_user_token_policy,
    validate_x509_user_token_policy,
)
from opcua_security_support import (  # noqa: E402
    load_opcua_security_users,
    unique_temp_dir,
    write_self_signed_certificate,
)


pytestmark = [pytest.mark.live, pytest.mark.opcua_security]

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT = _CONSOLE_ROOT.parents[2]
_TMP_ROOT = _CONSOLE_ROOT / "tmp" / "opcua-security"

_USERNAME_POLICY = security_policies.SecurityPolicyBasic256Sha256.URI
_USERNAME_MODE = ua.MessageSecurityMode.SignAndEncrypt
_DEPRECATED_POLICY_URIS = {
    "http://opcfoundation.org/UA/SecurityPolicy#Basic128Rsa15",
    "http://opcfoundation.org/UA/SecurityPolicy#Basic256",
}
_ANONYMOUS_ENDPOINT_CASES = [
    (security_policies.SecurityPolicyNone.URI, ua.MessageSecurityMode.None_),
    (security_policies.SecurityPolicyBasic256Sha256.URI, ua.MessageSecurityMode.Sign),
    (security_policies.SecurityPolicyBasic256Sha256.URI, ua.MessageSecurityMode.SignAndEncrypt),
    (security_policies.SecurityPolicyAes128Sha256RsaOaep.URI, ua.MessageSecurityMode.Sign),
    (security_policies.SecurityPolicyAes128Sha256RsaOaep.URI, ua.MessageSecurityMode.SignAndEncrypt),
    (security_policies.SecurityPolicyAes256Sha256RsaPss.URI, ua.MessageSecurityMode.Sign),
    (security_policies.SecurityPolicyAes256Sha256RsaPss.URI, ua.MessageSecurityMode.SignAndEncrypt),
]
_SECURE_ENDPOINT_CASES = [
    (policy_uri, mode)
    for policy_uri, mode in _ANONYMOUS_ENDPOINT_CASES
    if policy_uri != security_policies.SecurityPolicyNone.URI
]


def _server_url() -> str:
    return os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40477")


def _client_app_certificate() -> tuple[Path, Path]:
    cert = os.environ.get("CONSOLE_SECURITY_CLIENT_CERT")
    key = os.environ.get("CONSOLE_SECURITY_CLIENT_KEY")
    if not cert or not key:
        # The opcua-security conftest provisions the client application
        # certificate only when the IJT_OPCUA_SECURITY_TARGET env var is set
        # (which is how CI runs each target). On a plain local run those env
        # vars are absent, so the opcua-security sub-suite is skipped rather
        # than failing loudly.
        pytest.skip(
            "Console OPC UA security client application certificate not provisioned "
            "(set IJT_OPCUA_SECURITY_TARGET to enable this sub-suite)."
        )
    return Path(cert), Path(key)


def _case_dir(case_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_name).strip("_") or "case"
    return unique_temp_dir(_TMP_ROOT, safe_name)


def _users_file() -> Path:
    configured = os.environ.get("OPCUA_SECURITY_USERS_FILE")
    if configured:
        return Path(configured)
    shared = _REPO_ROOT / "OPC_UA_Servers" / "Release2" / "opcua_security.users.yaml"
    if shared.exists():
        return shared
    return _CONSOLE_ROOT / "tests" / "opcua_security.users.yaml"


def _security_config(
    *,
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
    user_identity: UserIdentityKind = "anonymous",
    username: str | None = None,
    password: str | None = None,
    x509_certificate_path: Path | None = None,
    x509_private_key_path: Path | None = None,
) -> OPCUASecurityConfig:
    client_cert: Path | None = None
    client_key: Path | None = None
    if security_policy_uri != security_policies.SecurityPolicyNone.URI:
        client_cert, client_key = _client_app_certificate()

    return OPCUASecurityConfig(
        security_policy_uri=security_policy_uri,
        security_mode=security_mode,
        client_certificate_path=client_cert,
        client_private_key_path=client_key,
        user_identity=user_identity,
        username=username,
        password=password,
        x509_certificate_path=x509_certificate_path,
        x509_private_key_path=x509_private_key_path,
    )


async def _connect(config: OPCUASecurityConfig) -> OPCUAClient:
    client = OPCUAClient(_server_url(), security_config=config)
    await asyncio.wait_for(client.connect(), timeout=45)
    return client


async def _assert_benign_flow(client: OPCUAClient) -> None:
    root = client.client.get_root_node()
    children = await root.get_children()
    assert children, "Root node browse must return at least one child."


async def _assert_certificate_user_token_policy_uses_endpoint_policy(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    # Force the same skip semantics as the other OPC UA security targets on plain
    # local runs where the OPC UA security fixture has not provisioned cert material.
    _client_app_certificate()

    client = Client(_server_url(), timeout=45)
    endpoints = await client.connect_and_get_server_endpoints()
    endpoint = next(
        (
            candidate
            for candidate in endpoints
            if candidate.SecurityPolicyUri == security_policy_uri and candidate.SecurityMode == security_mode
        ),
        None,
    )
    assert endpoint is not None, f"Endpoint not found for policy={security_policy_uri}, mode={security_mode.name}."

    validate_x509_user_token_policy(endpoint, security_policy_uri)


async def _discover_endpoints() -> list[ua.EndpointDescription]:
    client = Client(_server_url(), timeout=45)
    return list(await client.connect_and_get_server_endpoints())


def _assert_endpoint(client: OPCUAClient, security_policy_uri: str, security_mode: ua.MessageSecurityMode) -> None:
    policy = client.client.security_policy
    assert policy.URI == security_policy_uri
    assert policy.Mode == security_mode


def _status_code_from_exception(exc: BaseException) -> int | None:
    if isinstance(exc, ua.UaStatusCodeError):
        return exc.code

    for child in getattr(exc, "exceptions", ()):
        found = _status_code_from_exception(child)
        if found is not None:
            return found

    for attr in ("__cause__", "__context__"):
        nested = getattr(exc, attr, None)
        if nested is not None:
            found = _status_code_from_exception(nested)
            if found is not None:
                return found
    return None


async def _assert_connect_fails(config: OPCUASecurityConfig, expected_status: int) -> None:
    await _assert_connect_fails_any(config, (expected_status,))


async def _assert_connect_fails_any(config: OPCUASecurityConfig, expected_statuses: tuple[int, ...]) -> None:
    client = OPCUAClient(_server_url(), security_config=config)
    try:
        with pytest.raises(Exception) as exc_info:
            await asyncio.wait_for(client.connect(), timeout=45)
        assert _status_code_from_exception(exc_info.value) in expected_statuses
    finally:
        with contextlib.suppress(Exception):
            await client.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("security_policy_uri", "security_mode"),
    _ANONYMOUS_ENDPOINT_CASES,
)
async def test_anonymous_modern_endpoint_connects_and_browses(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    client = await _connect(
        _security_config(
            security_policy_uri=security_policy_uri,
            security_mode=security_mode,
        )
    )
    try:
        _assert_endpoint(client, security_policy_uri, security_mode)
        await _assert_benign_flow(client)
    finally:
        await client.cleanup()


@pytest.mark.asyncio
async def test_endpoint_user_token_policies_are_hardened() -> None:
    _client_app_certificate()
    endpoints = await _discover_endpoints()

    advertised = {(endpoint.SecurityPolicyUri, endpoint.SecurityMode) for endpoint in endpoints}
    for policy_uri in _DEPRECATED_POLICY_URIS:
        assert all(endpoint.SecurityPolicyUri != policy_uri for endpoint in endpoints), (
            f"Deprecated endpoint policy is still advertised: {policy_uri}"
        )

    for policy_uri, mode in _ANONYMOUS_ENDPOINT_CASES:
        assert (policy_uri, mode) in advertised, f"Expected endpoint is missing: {policy_uri}/{mode.name}"
        endpoint = next(
            endpoint
            for endpoint in endpoints
            if endpoint.SecurityPolicyUri == policy_uri and endpoint.SecurityMode == mode
        )
        token_types = {policy.TokenType for policy in endpoint.UserIdentityTokens}
        assert ua.UserTokenType.Anonymous in token_types
        if policy_uri == security_policies.SecurityPolicyNone.URI:
            assert ua.UserTokenType.UserName not in token_types
            assert ua.UserTokenType.Certificate not in token_types
        else:
            validate_username_user_token_policy(endpoint, policy_uri)
            validate_x509_user_token_policy(endpoint, policy_uri)


@pytest.mark.asyncio
@pytest.mark.parametrize(("security_policy_uri", "security_mode"), _SECURE_ENDPOINT_CASES)
async def test_username_happy_path_connects_and_browses(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    users = load_opcua_security_users(_users_file())
    client = await _connect(
        _security_config(
            security_policy_uri=security_policy_uri,
            security_mode=security_mode,
            user_identity="username",
            username=users.positive.username,
            password=users.positive.password,
        )
    )
    try:
        _assert_endpoint(client, security_policy_uri, security_mode)
        await _assert_benign_flow(client)
    finally:
        await client.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize(("security_policy_uri", "security_mode"), _SECURE_ENDPOINT_CASES)
async def test_username_wrong_password_is_rejected(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    users = load_opcua_security_users(_users_file())
    await _assert_connect_fails_any(
        _security_config(
            security_policy_uri=security_policy_uri,
            security_mode=security_mode,
            user_identity="username",
            username=users.wrong_password.username,
            password=users.wrong_password.password,
        ),
        (ua.StatusCodes.BadUserAccessDenied, ua.StatusCodes.BadIdentityTokenRejected),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("security_policy_uri", "security_mode"), _SECURE_ENDPOINT_CASES)
async def test_username_unknown_user_is_rejected(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    users = load_opcua_security_users(_users_file())
    await _assert_connect_fails_any(
        _security_config(
            security_policy_uri=security_policy_uri,
            security_mode=security_mode,
            user_identity="username",
            username=users.unknown_user.username,
            password=users.unknown_user.password,
        ),
        (ua.StatusCodes.BadUserAccessDenied, ua.StatusCodes.BadIdentityTokenRejected),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("security_policy_uri", "security_mode"), _SECURE_ENDPOINT_CASES)
async def test_x509_certificate_user_token_policy_uses_endpoint_policy(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    await _assert_certificate_user_token_policy_uses_endpoint_policy(security_policy_uri, security_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize(("security_policy_uri", "security_mode"), _SECURE_ENDPOINT_CASES)
async def test_x509_identity_token_known_thumbprint_user1_opens_session(
    security_policy_uri: str,
    security_mode: ua.MessageSecurityMode,
) -> None:
    await _assert_certificate_user_token_policy_uses_endpoint_policy(security_policy_uri, security_mode)
    user_cert = os.environ.get("CONSOLE_X509_USER_CERT")
    user_key = os.environ.get("CONSOLE_X509_USER_KEY")
    if not user_cert or not user_key:
        pytest.skip("X509 user-identity cert not provisioned (set IJT_OPCUA_SECURITY_TARGET to enable this sub-suite).")
    client = await _connect(
        _security_config(
            security_policy_uri=security_policy_uri,
            security_mode=security_mode,
            user_identity="x509",
            x509_certificate_path=Path(user_cert),
            x509_private_key_path=Path(user_key),
        )
    )
    try:
        _assert_endpoint(client, security_policy_uri, security_mode)
        await _assert_benign_flow(client)
    finally:
        await client.cleanup()


@pytest.mark.asyncio
async def test_x509_identity_token_unknown_user_is_rejected() -> None:
    # This certificate is not configured in user_identity_configuration.json.
    # Depending on where the stack rejects it, either status is acceptable.
    user_cert = write_self_signed_certificate(_case_dir("x509-user"), "IJT Console X509 User")
    client = OPCUAClient(
        _server_url(),
        security_config=_security_config(
            security_policy_uri=_USERNAME_POLICY,
            security_mode=_USERNAME_MODE,
            user_identity="x509",
            x509_certificate_path=user_cert.certificate_pem,
            x509_private_key_path=user_cert.private_key_pem,
        ),
    )
    try:
        with pytest.raises(Exception) as exc_info:
            await asyncio.wait_for(client.connect(), timeout=45)
        code = _status_code_from_exception(exc_info.value)
        assert code in (
            ua.StatusCodes.BadIdentityTokenRejected,
            ua.StatusCodes.BadIdentityTokenInvalid,
        ), (
            f"Unexpected status code for unknown X509 user: 0x{code:08X}"
            if code is not None
            else "No status code captured"
        )
    finally:
        with contextlib.suppress(Exception):
            await client.cleanup()
