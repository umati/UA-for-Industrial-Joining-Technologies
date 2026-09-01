"""
Connection security and authentication for SUT manifest driven OPC UA sessions.

The SUT manifest declares how the client must reach the System Under Test::

    connection:
      security_mode: SignAndEncrypt
      security_policy: Basic256Sha256
      client_certificate_path: certs/client.der
      client_private_key_path: certs/client-key.pem
      server_certificate_path: certs/server.der      # optional pinning
      trust_store_path: certs/trusted                # optional trust list
    authentication:
      source: environment                            # anonymous | prompt | file | environment
      username_env_var: IJT_TARGET_USER
      password_env_var: IJT_TARGET_PASSWORD

This module turns those *declarations* into applied asyncua client settings.
Every asyncua session used against a manifest-configured target - preflight,
discovery, and the pytest fixtures - goes through :func:`apply_connection_security`,
so a declared mode can never be silently ignored.

Design rules
------------
* **Never log a secret.** Passwords are carried in :class:`Credentials`, whose
  repr is redacted, and are never written to a log, report, or exception text.
* **Fail before the tests.** :func:`validate_connection_security` reports every
  problem it can detect without I/O against the server (bad mode/policy pairing,
  missing certificate, key, credentials file, or environment variable) so a run
  stops as a configuration error instead of failing test by test.
* **Nothing interactive in automation.** ``source: prompt`` requires a prompt
  provider; tests and CI inject one (or a resolved :class:`Credentials`) instead
  of blocking on stdin.
* **Simulator stays anonymous.** An unset/anonymous manifest yields a no-op, so
  the default simulator run is unchanged.

Public API::

    from helpers.connection_security import (
        ConnectionSecurity, ConnectionSecurityError, Credentials,
        connection_security_from_manifest, connection_security_from_manifest_path,
        validate_connection_security, resolve_credentials,
        apply_connection_security, describe_connection_security,
    )
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

logger = logging.getLogger(__name__)

#: Manifest security policy name -> asyncua security policy class name.
SECURITY_POLICY_CLASS_NAMES: Mapping[str, str] = {
    "Basic256Sha256": "SecurityPolicyBasic256Sha256",
    "Aes128_Sha256_RsaOaep": "SecurityPolicyAes128Sha256RsaOaep",
    "Aes256_Sha256_RsaPss": "SecurityPolicyAes256Sha256RsaPss",
}

#: Manifest security mode name -> asyncua MessageSecurityMode attribute name.
SECURITY_MODE_ATTRIBUTES: Mapping[str, str] = {
    "None": "None_",
    "Sign": "Sign",
    "SignAndEncrypt": "SignAndEncrypt",
}

_ANONYMOUS = "anonymous"
_PROMPT = "prompt"
_FILE = "file"
_ENVIRONMENT = "environment"

_CREDENTIAL_USERNAME_KEYS = ("username", "user")
_CREDENTIAL_PASSWORD_KEYS = ("password", "pass")


class ConnectionSecurityError(RuntimeError):
    """Raised when a declared security or authentication setting cannot be applied.

    Messages never contain credential values - only the reference (file path or
    environment variable name) that could not be resolved.
    """


@dataclass(frozen=True, repr=False)
class Credentials:
    """A resolved user identity. The password is never rendered."""

    username: str = ""
    password: str = field(default="")

    def __repr__(self) -> str:  # pragma: no cover - trivial, but must stay redacted
        return f"Credentials(username={self.username!r}, password=***)"

    def __str__(self) -> str:
        return self.__repr__()


#: Callable used to obtain credentials interactively. Injected by callers so a
#: test or CI run never blocks on stdin.
CredentialPrompt = Callable[["ConnectionSecurity"], Credentials]


@dataclass(frozen=True)
class ConnectionSecurity:
    """The connection security + authentication *declaration* of one SUT."""

    endpoint: str = ""
    security_mode: str = "None"
    security_policy: str = "None"
    client_certificate_path: str = ""
    client_private_key_path: str = ""
    server_certificate_path: str = ""
    trust_store_path: str = ""
    auth_source: str = _ANONYMOUS
    username: str = ""
    credentials_file: str = ""
    username_env_var: str = ""
    password_env_var: str = ""
    base_dir: str = ""

    @property
    def uses_secure_channel(self) -> bool:
        """True when a signed and/or encrypted secure channel is declared."""
        return self.security_mode != "None" or self.security_policy != "None"

    @property
    def requires_user_identity(self) -> bool:
        """True when a user identity token (not anonymous) is declared."""
        return self.auth_source != _ANONYMOUS

    @property
    def is_default_anonymous(self) -> bool:
        """True when nothing has to be applied (the simulator default)."""
        return not self.uses_secure_channel and not self.requires_user_identity

    def resolve_path(self, value: str) -> Path:
        """Resolve a manifest-relative path against the manifest's directory."""
        path = Path(value).expanduser()
        if path.is_absolute() or not self.base_dir:
            return path
        return Path(self.base_dir) / path


def connection_security_from_mapping(data: Mapping[str, Any], *, base_dir: str = "") -> ConnectionSecurity:
    """Build a :class:`ConnectionSecurity` from a validated manifest mapping."""
    connection: Mapping[str, Any] = data.get("connection") or {}
    authentication: Mapping[str, Any] = data.get("authentication") or {}
    return ConnectionSecurity(
        endpoint=str(connection.get("endpoint", "")),
        security_mode=str(connection.get("security_mode", "None")),
        security_policy=str(connection.get("security_policy", "None")),
        client_certificate_path=str(connection.get("client_certificate_path", "")),
        client_private_key_path=str(connection.get("client_private_key_path", "")),
        server_certificate_path=str(connection.get("server_certificate_path", "")),
        trust_store_path=str(connection.get("trust_store_path", "")),
        auth_source=str(authentication.get("source", _ANONYMOUS)),
        username=str(authentication.get("username", "")),
        credentials_file=str(authentication.get("credentials_file", "")),
        username_env_var=str(authentication.get("username_env_var", "")),
        password_env_var=str(authentication.get("password_env_var", "")),
        base_dir=base_dir,
    )


def connection_security_from_manifest(manifest: Any) -> ConnectionSecurity:
    """Build a :class:`ConnectionSecurity` from a loaded :class:`SutManifest`."""
    source_path = str(getattr(manifest, "source_path", "") or "")
    base_dir = str(Path(source_path).parent) if source_path.endswith(".yaml") else ""
    return connection_security_from_mapping(manifest.to_dict(), base_dir=base_dir)


def connection_security_from_manifest_path(path: str | Path) -> ConnectionSecurity:
    """Load one ``*.sut.yaml`` manifest and return its security declaration."""
    from helpers.sut_manifest import load_sut_manifest

    return connection_security_from_manifest(load_sut_manifest(Path(path)))


def describe_connection_security(config: ConnectionSecurity) -> str:
    """Return a one-line, secret-free summary suitable for logs and reports."""
    identity = config.auth_source
    if config.auth_source == _FILE:
        identity = f"file:{config.credentials_file}"
    elif config.auth_source == _ENVIRONMENT:
        identity = f"env:{config.username_env_var or '(none)'}/{config.password_env_var}"
    return f"security={config.security_policy}/{config.security_mode} identity={identity}"


# ---------------------------------------------------------------------------
# Validation - everything detectable before a server is contacted
# ---------------------------------------------------------------------------


def _existing_file_issue(config: ConnectionSecurity, value: str, label: str) -> str | None:
    path = config.resolve_path(value)
    if not path.exists():
        return f"{label}: '{path}' does not exist"
    if not path.is_file():
        return f"{label}: '{path}' is not a file"
    return None


def validate_connection_security(
    config: ConnectionSecurity,
    *,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Return every reason *config* cannot be applied, or an empty list.

    Only references are reported; a credential value is never included.
    """
    environ = os.environ if env is None else env
    issues: list[str] = []

    if config.security_policy not in SECURITY_POLICY_CLASS_NAMES and config.security_policy != "None":
        issues.append(
            f"connection.security_policy: '{config.security_policy}' is not supported by this client. "
            f"Supported: {sorted(SECURITY_POLICY_CLASS_NAMES)}"
        )
    if config.security_mode not in SECURITY_MODE_ATTRIBUTES:
        issues.append(f"connection.security_mode: '{config.security_mode}' is not a valid OPC UA message security mode")

    secure_policy = config.security_policy != "None"
    secure_mode = config.security_mode != "None"
    if secure_policy != secure_mode:
        issues.append(
            "connection: security_mode and security_policy must both be 'None' or both be secure "
            f"(got security_mode='{config.security_mode}', security_policy='{config.security_policy}')"
        )

    if config.uses_secure_channel:
        if not config.client_certificate_path:
            issues.append("connection.client_certificate_path: required for a secure channel")
        if not config.client_private_key_path:
            issues.append("connection.client_private_key_path: required for a secure channel")

    for value, label in (
        (config.client_certificate_path, "connection.client_certificate_path"),
        (config.client_private_key_path, "connection.client_private_key_path"),
        (config.server_certificate_path, "connection.server_certificate_path"),
    ):
        if value:
            issue = _existing_file_issue(config, value, label)
            if issue:
                issues.append(issue)

    if config.trust_store_path:
        trust_path = config.resolve_path(config.trust_store_path)
        if not trust_path.is_dir():
            issues.append(f"connection.trust_store_path: '{trust_path}' is not an existing directory")

    issues.extend(_authentication_issues(config, environ))
    return issues


def _authentication_issues(config: ConnectionSecurity, environ: Mapping[str, str]) -> list[str]:
    issues: list[str] = []
    source = config.auth_source
    if source not in {_ANONYMOUS, _PROMPT, _FILE, _ENVIRONMENT}:
        return [f"authentication.source: '{source}' is not a supported credential source"]

    if source == _ANONYMOUS and config.username:
        issues.append("authentication.username: must be empty when authentication.source is 'anonymous'")

    if source == _FILE:
        if not config.credentials_file:
            issues.append("authentication.credentials_file: required when authentication.source is 'file'")
        else:
            issue = _existing_file_issue(config, config.credentials_file, "authentication.credentials_file")
            if issue:
                issues.append(issue)

    if source == _ENVIRONMENT:
        if not config.password_env_var:
            issues.append("authentication.password_env_var: required when authentication.source is 'environment'")
        for name in (config.username_env_var, config.password_env_var):
            if name and not (environ.get(name) or "").strip():
                issues.append(f"authentication: environment variable '{name}' is referenced but not set")
        if not config.username and not config.username_env_var:
            issues.append(
                "authentication: set authentication.username or authentication.username_env_var for the "
                "'environment' credential source"
            )
    return issues


def require_appliable_connection_security(
    config: ConnectionSecurity,
    *,
    env: Mapping[str, str] | None = None,
) -> None:
    """Raise :class:`ConnectionSecurityError` when *config* cannot be applied."""
    issues = validate_connection_security(config, env=env)
    if issues:
        raise ConnectionSecurityError(
            "The SUT manifest's connection security cannot be applied:\n  - " + "\n  - ".join(issues)
        )


# ---------------------------------------------------------------------------
# Credential resolution - references in, values out, nothing logged
# ---------------------------------------------------------------------------


def _read_credentials_file(path: Path) -> Credentials:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConnectionSecurityError(f"authentication.credentials_file '{path}' could not be read: {exc}") from exc

    data: Any
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ConnectionSecurityError(
                f"authentication.credentials_file '{path}' is not valid YAML or JSON"
            ) from exc
    if not isinstance(data, dict):
        raise ConnectionSecurityError(
            f"authentication.credentials_file '{path}' must contain a mapping with 'username' and 'password' keys"
        )

    username = next((str(data[key]) for key in _CREDENTIAL_USERNAME_KEYS if data.get(key)), "")
    password = next((str(data[key]) for key in _CREDENTIAL_PASSWORD_KEYS if data.get(key)), "")
    if not password:
        raise ConnectionSecurityError(
            f"authentication.credentials_file '{path}' has no 'password' entry (values are never read from the manifest)"
        )
    return Credentials(username=username, password=password)


def default_credential_prompt(config: ConnectionSecurity) -> Credentials:  # pragma: no cover - interactive
    """Ask the operator for credentials on the console (never echoed, never logged)."""
    import getpass

    target = config.endpoint or "the target server"
    username = config.username or input(f"OPC UA user name for {target}: ")
    password = getpass.getpass(f"OPC UA password for {username}@{target}: ")
    return Credentials(username=username, password=password)


def resolve_credentials(
    config: ConnectionSecurity,
    *,
    env: Mapping[str, str] | None = None,
    prompt: CredentialPrompt | None = None,
) -> Credentials | None:
    """Resolve the declared credential *reference* into usable credentials.

    Returns ``None`` for anonymous sessions. Raises
    :class:`ConnectionSecurityError` when a reference cannot be resolved - the
    error names the reference only, never the value.
    """
    environ = os.environ if env is None else env
    source = config.auth_source

    if source == _ANONYMOUS:
        return None

    if source == _FILE:
        if not config.credentials_file:
            raise ConnectionSecurityError(
                "authentication.credentials_file is required when authentication.source is 'file'"
            )
        return _read_credentials_file(config.resolve_path(config.credentials_file))

    if source == _ENVIRONMENT:
        if not config.password_env_var:
            raise ConnectionSecurityError(
                "authentication.password_env_var is required when authentication.source is 'environment'"
            )
        password = environ.get(config.password_env_var, "")
        if not password:
            raise ConnectionSecurityError(
                f"authentication: environment variable '{config.password_env_var}' is not set"
            )
        username = config.username
        if config.username_env_var:
            username = environ.get(config.username_env_var, "")
            if not username:
                raise ConnectionSecurityError(
                    f"authentication: environment variable '{config.username_env_var}' is not set"
                )
        if not username:
            raise ConnectionSecurityError(
                "authentication: no user name configured; set authentication.username or "
                "authentication.username_env_var"
            )
        return Credentials(username=username, password=password)

    if source == _PROMPT:
        provider = prompt
        if provider is None:
            raise ConnectionSecurityError(
                "authentication.source is 'prompt' but no credential prompt is available. "
                "Run interactively (--interactive-prompts) or use the 'file'/'environment' source in automation."
            )
        credentials = provider(config)
        if not credentials or not credentials.password:
            raise ConnectionSecurityError("authentication: the credential prompt returned no password")
        return credentials

    raise ConnectionSecurityError(f"authentication.source: '{source}' is not a supported credential source")


# ---------------------------------------------------------------------------
# Application onto an asyncua client
# ---------------------------------------------------------------------------


async def _apply_secure_channel(client: Any, config: ConnectionSecurity) -> None:
    from asyncua import ua
    from asyncua.crypto import security_policies

    policy_cls = getattr(security_policies, SECURITY_POLICY_CLASS_NAMES[config.security_policy])
    mode = getattr(ua.MessageSecurityMode, SECURITY_MODE_ATTRIBUTES[config.security_mode])
    server_certificate = (
        str(config.resolve_path(config.server_certificate_path)) if config.server_certificate_path else None
    )
    await client.set_security(
        policy_cls,
        str(config.resolve_path(config.client_certificate_path)),
        str(config.resolve_path(config.client_private_key_path)),
        server_certificate=server_certificate,
        mode=mode,
    )


async def _apply_trust_store(client: Any, config: ConnectionSecurity) -> None:
    from asyncua.crypto.truststore import TrustStore
    from asyncua.crypto.validator import CertificateValidator, CertificateValidatorOptions

    trust_store = TrustStore([config.resolve_path(config.trust_store_path)], [])
    await trust_store.load()
    client.certificate_validator = CertificateValidator(
        CertificateValidatorOptions.TRUSTED_VALIDATION | CertificateValidatorOptions.PEER_SERVER,
        trust_store,
    ).validate


async def apply_connection_security(
    client: Any,
    config: ConnectionSecurity,
    *,
    env: Mapping[str, str] | None = None,
    prompt: CredentialPrompt | None = None,
    credentials: Credentials | None = None,
) -> Credentials | None:
    """Apply *config* to an asyncua ``Client`` before it connects.

    Returns the credentials that were applied (``None`` for anonymous). Raises
    :class:`ConnectionSecurityError` when anything declared cannot be applied,
    so the caller can stop the run before any test executes.
    """
    if config.is_default_anonymous:
        return None

    require_appliable_connection_security(config, env=env)

    if config.uses_secure_channel:
        try:
            await _apply_secure_channel(client, config)
        except Exception as exc:
            raise ConnectionSecurityError(
                f"Could not apply connection security {config.security_policy}/{config.security_mode}: {exc}"
            ) from exc

    if config.trust_store_path:
        try:
            await _apply_trust_store(client, config)
        except Exception as exc:
            raise ConnectionSecurityError(
                f"Could not load the trust store '{config.resolve_path(config.trust_store_path)}': {exc}"
            ) from exc

    resolved = credentials if credentials is not None else resolve_credentials(config, env=env, prompt=prompt)
    # Log security config before applying credentials — never log credential values.
    logger.info("Applied SUT connection security (%s)", describe_connection_security(config))
    if resolved is not None:
        client.set_user(resolved.username)
        client.set_password(resolved.password)
    return resolved
