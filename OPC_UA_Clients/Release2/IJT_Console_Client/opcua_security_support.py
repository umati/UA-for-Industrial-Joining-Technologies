from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


def preserve_test_artifacts() -> bool:
    return os.environ.get("IJT_PRESERVE_TEST_ARTIFACTS", "0").strip().lower() in {"1", "true", "yes", "on"}


def console_application_uri() -> str:
    return f"urn:{socket.getfqdn()}:IJT:ConsoleClient"


def console_opcua_security_common_name(target: str) -> str:
    """Return a stable X.509 common name for OPC UA security test certs.

    X.509 common names are limited to 64 characters by the cryptography
    library. CI target names are intentionally descriptive, but certificate
    subjects only need the SUT identity. Keep the full target in logs and
    artifact names; use this compact identity only for generated certificates.
    """

    lower_target = target.strip().lower()
    if "windows" in lower_target:
        label = "Windows"
    elif "linux" in lower_target:
        label = "Linux"
    elif lower_target == "local":
        label = "Local"
    elif lower_target:
        compact = "".join(ch for ch in target if ch.isalnum())
        if len(compact) > 24:
            compact = f"Target{hashlib.sha256(target.encode('utf-8')).hexdigest()[:8]}"
        label = compact or "Local"
    else:
        label = "Local"

    common_name = f"IJT Console OPC UA Security {label}"
    if len(common_name) > 64:
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()[:8]
        common_name = f"IJT Console OPC UA Security Target{digest}"
    return common_name


@dataclass(frozen=True)
class GeneratedCertificate:
    certificate_pem: Path
    certificate_der: Path
    private_key_pem: Path


@dataclass(frozen=True)
class OpcUaSecurityUser:
    username: str
    password: str


@dataclass(frozen=True)
class OpcUaSecurityUsers:
    positive: OpcUaSecurityUser
    wrong_password: OpcUaSecurityUser
    unknown_user: OpcUaSecurityUser


@dataclass(frozen=True)
class SimulatorUserIdentityConfig:
    path: Path
    x509_thumbprint_sha1_hex: str | None


def unique_temp_dir(root: Path, prefix: str) -> Path:
    path = root / f"{prefix}_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_self_signed_certificate(
    output_dir: Path,
    common_name: str,
    *,
    application_uri: str | None = None,
) -> GeneratedCertificate:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    output_dir.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OPC Foundation"),
        ]
    )
    now = datetime.now(timezone.utc)
    app_uri = application_uri or console_application_uri()
    hostnames = {socket.gethostname(), socket.getfqdn(), socket.gethostname().lower(), socket.getfqdn().lower()}
    san_entries: list[x509.GeneralName] = [x509.UniformResourceIdentifier(app_uri)]
    san_entries.extend(x509.DNSName(name) for name in sorted(hostnames) if name)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    cert_pem = output_dir / "cert.pem"
    cert_der = output_dir / "cert.der"
    key_pem = output_dir / "key.pem"
    cert_pem.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    cert_der.write_bytes(cert.public_bytes(serialization.Encoding.DER))
    key_pem.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return GeneratedCertificate(cert_pem, cert_der, key_pem)


def trust_application_certificate(server_pki_root: Path, certificate_der: Path) -> Path:
    """Place ``certificate_der`` in the server's DefaultApplicationGroup trust store.

    This is the secure-channel (client application) trust path. For X509
    user-token trust use :func:`trust_user_token_certificate` instead.
    """
    target_dir = server_pki_root / "pki" / "DefaultApplicationGroup" / "trusted" / "certs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / certificate_der.name
    shutil.copy2(certificate_der, target)
    return target


def trust_user_token_certificate(server_pki_root: Path, certificate_der: Path) -> Path:
    """Place ``certificate_der`` in the server's DefaultUserTokenGroup trust store.

    The OPC UA simulator validates X509 user-identity tokens against the
    ``DefaultUserTokenGroup`` PKI. This store is separate from
    ``DefaultApplicationGroup`` (which only trusts client application
    certificates for the secure channel); the X509 happy path requires the
    user-identity cert to be trusted in this group.
    """
    target_dir = server_pki_root / "pki" / "DefaultUserTokenGroup" / "trusted" / "certs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / certificate_der.name
    shutil.copy2(certificate_der, target)
    return target


def sha1_thumbprint_hex(certificate_der: Path) -> str:
    # OPC UA user-token thumbprints are protocol-defined SHA-1 identifiers,
    # not a cryptographic integrity check.
    return hashlib.sha1(certificate_der.read_bytes()).hexdigest()  # nosec B324


def write_simulator_user_identity_configuration(
    path: Path,
    users: OpcUaSecurityUsers,
    *,
    x509_user_certificate_der: Path | None = None,
    x509_user_name: str = "user1",
) -> SimulatorUserIdentityConfig:
    """Write the simulator user file expected by the current server package."""
    x509_thumbprint = sha1_thumbprint_hex(x509_user_certificate_der) if x509_user_certificate_der else None
    configured_users: dict[str, dict[str, object]] = {}

    configured_users[users.positive.username] = {
        "userName": users.positive.username,
        "password": users.positive.password,
        "roles": ["SecurityAdmin"] if users.positive.username == "SecurityAdmin" else [],
        "description": "OPC UA security positive user",
    }

    # Simulator default credential for OPC UA security test users. Server-side test fixture
    # only — never a real secret. Bandit B105 muted intentionally.
    _DEFAULT_SIMULATOR_PASSWORD = "password"  # nosec B105

    configured_users.setdefault(
        users.wrong_password.username,
        {
            "userName": users.wrong_password.username,
            "password": _DEFAULT_SIMULATOR_PASSWORD,
            "roles": [],
            "description": "OPC UA security wrong-password target",
        },
    )

    if x509_thumbprint:
        x509_user = configured_users.setdefault(
            x509_user_name,
            {
                "userName": x509_user_name,
                "password": _DEFAULT_SIMULATOR_PASSWORD,
                # SecurityAdmin so the activated session can read i=2255 NamespaceArray
                # (and otherwise complete the benign flow). The X509 thumbprint identity
                # path is still exercised end to end; only the post-authentication
                # permission set is widened.
                "roles": [],
                "description": "OPC UA security X509 user",
            },
        )
        roles = x509_user.get("roles")
        if not isinstance(roles, list):
            roles = []
            x509_user["roles"] = roles
        if "SecurityAdmin" not in roles:
            roles.append("SecurityAdmin")
        x509_user["x509ThumbprintSha1Hex"] = x509_thumbprint

    payload = {
        "userIdentityData": {
            "enabled": True,
            "users": list(configured_users.values()),
        },
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return SimulatorUserIdentityConfig(path=path, x509_thumbprint_sha1_hex=x509_thumbprint)


def load_opcua_security_users(path: Path) -> OpcUaSecurityUsers:
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        trimmed = raw_line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if not raw_line[0].isspace() and trimmed.endswith(":"):
            current = trimmed[:-1].strip()
            sections[current] = {}
            continue
        if current is None or ":" not in trimmed:
            continue
        key, value = trimmed.split(":", 1)
        sections[current][key.strip()] = value.strip().strip("\"'")

    def user(section: str) -> OpcUaSecurityUser:
        data = sections[section]
        return OpcUaSecurityUser(data["username"], data["password"])

    return OpcUaSecurityUsers(
        positive=user("positive"),
        wrong_password=user("wrong_password"),
        unknown_user=user("unknown_user"),
    )
