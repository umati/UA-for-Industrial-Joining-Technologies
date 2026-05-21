from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID

from opcua_security_support import (
    console_opcua_security_common_name,
    load_opcua_security_users,
    preserve_test_artifacts,
    sha1_thumbprint_hex,
    trust_application_certificate,
    trust_user_token_certificate,
    unique_temp_dir,
    write_self_signed_certificate,
    write_simulator_user_identity_configuration,
)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("console-client-opcua-security-windows", "IJT Console OPC UA Security Windows"),
        ("console-client-opcua-security-linux", "IJT Console OPC UA Security Linux"),
        ("local", "IJT Console OPC UA Security Local"),
    ],
)
def test_console_opcua_security_common_name_uses_compact_sut_label(target: str, expected: str) -> None:
    assert console_opcua_security_common_name(target) == expected
    assert len(console_opcua_security_common_name(target)) <= 64


def test_console_opcua_security_common_name_hashes_unknown_long_targets() -> None:
    target = "console-client-opcua-security-future-platform-with-a-very-long-target-name"

    common_name = console_opcua_security_common_name(target)

    assert common_name.startswith("IJT Console OPC UA Security Target")
    assert len(common_name) <= 64


def test_write_self_signed_certificate_creates_cert_key_and_der(tmp_path: Path) -> None:
    generated = write_self_signed_certificate(
        tmp_path / "certs",
        "user1",
        application_uri="urn:test:opcua-security",
    )

    assert generated.certificate_pem.is_file()
    assert generated.certificate_der.is_file()
    assert generated.private_key_pem.is_file()

    cert = x509.load_pem_x509_certificate(generated.certificate_pem.read_bytes())
    common_names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    assert [attribute.value for attribute in common_names] == ["user1"]
    assert generated.certificate_der.read_bytes() == cert.public_bytes(serialization.Encoding.DER)
    subject_key_id = cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
    authority_key_id = cert.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value
    key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert authority_key_id.key_identifier == subject_key_id.digest
    assert key_usage.digital_signature
    assert key_usage.content_commitment
    assert key_usage.key_encipherment
    assert key_usage.data_encipherment


def test_trust_helpers_copy_to_distinct_server_pki_groups(tmp_path: Path) -> None:
    generated = write_self_signed_certificate(tmp_path / "client", "user1")
    server_pki = tmp_path / "server-pki"

    app_target = trust_application_certificate(server_pki, generated.certificate_der)
    user_target = trust_user_token_certificate(server_pki, generated.certificate_der)

    assert app_target == server_pki / "pki" / "DefaultApplicationGroup" / "trusted" / "certs" / "cert.der"
    assert user_target == server_pki / "pki" / "DefaultUserTokenGroup" / "trusted" / "certs" / "cert.der"
    assert app_target.read_bytes() == generated.certificate_der.read_bytes()
    assert user_target.read_bytes() == generated.certificate_der.read_bytes()


def test_load_opcua_security_users_reads_checked_in_yaml_shape(tmp_path: Path) -> None:
    users_file = tmp_path / "users.yaml"
    users_file.write_text(
        """
positive:
  username: user1
  password: password
wrong_password:
  username: user1
  password: wrong
unknown_user:
  username: no_such_user
  password: anything
""".strip(),
        encoding="utf-8",
    )

    users = load_opcua_security_users(users_file)

    assert users.positive.username == "user1"
    assert users.positive.password == "password"
    assert users.wrong_password.username == "user1"
    assert users.wrong_password.password == "wrong"
    assert users.unknown_user.username == "no_such_user"
    assert users.unknown_user.password == "anything"


def test_write_simulator_user_identity_configuration_adds_x509_thumbprint(tmp_path: Path) -> None:
    generated = write_self_signed_certificate(tmp_path / "certs", "user1")
    users_file = tmp_path / "users.yaml"
    users_file.write_text(
        """
positive:
  username: SecurityAdmin
  password: password
wrong_password:
  username: user1
  password: wrong
unknown_user:
  username: no_such_user
  password: anything
""".strip(),
        encoding="utf-8",
    )
    users = load_opcua_security_users(users_file)

    result = write_simulator_user_identity_configuration(
        tmp_path / "user_identity_configuration.json",
        users,
        x509_user_certificate_der=generated.certificate_der,
    )

    assert result.path.is_file()
    assert result.x509_thumbprint_sha1_hex == sha1_thumbprint_hex(generated.certificate_der)
    data = json.loads(result.path.read_text(encoding="utf-8"))
    configured_users = {entry["userName"]: entry for entry in data["userIdentityData"]["users"]}
    assert data["userIdentityData"]["enabled"] is True
    assert configured_users["user1"]["x509ThumbprintSha1Hex"] == result.x509_thumbprint_sha1_hex
    assert configured_users["user1"]["roles"] == ["SecurityAdmin"]
    assert configured_users["SecurityAdmin"]["roles"] == ["SecurityAdmin"]


def test_write_simulator_user_identity_configuration_keeps_one_entry_per_user(tmp_path: Path) -> None:
    generated = write_self_signed_certificate(tmp_path / "certs", "user1")
    users_file = tmp_path / "users.yaml"
    users_file.write_text(
        """
positive:
  username: user1
  password: matrix_password
wrong_password:
  username: user1
  password: wrong
unknown_user:
  username: no_such_user
  password: anything
""".strip(),
        encoding="utf-8",
    )
    users = load_opcua_security_users(users_file)

    result = write_simulator_user_identity_configuration(
        tmp_path / "user_identity_configuration.json",
        users,
        x509_user_certificate_der=generated.certificate_der,
    )

    data = json.loads(result.path.read_text(encoding="utf-8"))
    entries = data["userIdentityData"]["users"]
    user1_entries = [entry for entry in entries if entry["userName"] == "user1"]
    assert len(user1_entries) == 1
    assert user1_entries[0]["password"] == "matrix_password"
    assert user1_entries[0]["roles"] == ["SecurityAdmin"]
    assert user1_entries[0]["x509ThumbprintSha1Hex"] == result.x509_thumbprint_sha1_hex


def test_write_simulator_user_identity_configuration_without_x509_has_no_thumbprints(tmp_path: Path) -> None:
    users_file = tmp_path / "users.yaml"
    users_file.write_text(
        """
positive:
  username: SecurityAdmin
  password: password
wrong_password:
  username: user1
  password: wrong
unknown_user:
  username: no_such_user
  password: anything
""".strip(),
        encoding="utf-8",
    )
    users = load_opcua_security_users(users_file)

    result = write_simulator_user_identity_configuration(tmp_path / "user_identity_configuration.json", users)

    data = json.loads(result.path.read_text(encoding="utf-8"))
    assert result.x509_thumbprint_sha1_hex is None
    assert all("x509ThumbprintSha1Hex" not in entry for entry in data["userIdentityData"]["users"])


def test_unique_temp_dir_and_preserve_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = unique_temp_dir(tmp_path, "cell")
    second = unique_temp_dir(tmp_path, "cell")

    assert first.is_dir()
    assert second.is_dir()
    assert first != second

    monkeypatch.setenv("IJT_PRESERVE_TEST_ARTIFACTS", "yes")
    assert preserve_test_artifacts()

    monkeypatch.setenv("IJT_PRESERVE_TEST_ARTIFACTS", "0")
    assert not preserve_test_artifacts()
