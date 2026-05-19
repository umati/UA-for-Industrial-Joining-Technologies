from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

_RUNNER_PATH = Path(__file__).resolve().parents[1] / "run_all_tests.py"
_SPEC = importlib.util.spec_from_file_location("server_run_all_tests", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def _user_identity_payload() -> dict[str, object]:
    return {
        "userIdentityData": {
            "enabled": True,
            "users": [
                {
                    "userName": "user1",
                    "password": "password",
                    "roles": [],
                    "description": "Generic operator-class user",
                },
                {
                    "userName": "x509-user",
                    "x509ThumbprintSha1Hex": "0123456789abcdef0123456789ABCDEF01234567",
                    "roles": ["AuthenticatedUser"],
                    "description": "Certificate-only user",
                },
            ],
        },
    }


def _write_package(
    path: Path,
    *,
    include_user_identity: bool = True,
    user_identity_payload: object | None = None,
) -> None:
    root = path.stem
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            f"{root}/server_configuration.json",
            json.dumps({"serverConfigurationData": {"serverEndpointTCPPort": 40451}}),
        )
        zf.writestr(f"{root}/simulated_asset_data.json", json.dumps({"simulatedAssetData": {}}))
        if include_user_identity:
            zf.writestr(
                f"{root}/user_identity_configuration.json",
                json.dumps(
                    user_identity_payload
                    if user_identity_payload is not None
                    else _user_identity_payload()
                ),
            )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"userIdentityData": {"enabled": "true", "users": []}}, "enabled must be a boolean"),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {"userName": "user1", "password": "password"},
                        {"userName": "user1", "password": "password"},
                    ],
                },
            },
            "duplicate userName",
        ),
        (
            {"userIdentityData": {"enabled": True, "users": [{"userName": "user1"}]}},
            "must define password or X509 identity material",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [{"userName": "user1", "password": ""}],
                },
            },
            "must define password or X509 identity material",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {
                            "userName": "user1",
                            "password": "password",
                            "roles": ["SecurityAdmin", 15656],
                        },
                    ],
                },
            },
            None,
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {
                            "userName": "user1",
                            "password": "password",
                            "x509ThumbprintSha1Hex": "bad",
                        },
                    ],
                },
            },
            "40-character SHA-1 hex string",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {
                            "userName": "user1",
                            "password": "password",
                            "x509ThumbprintSha1Hex": "0123456789abcdef0123456789abcdef01234567",
                            "x509CertificatePath": "user1.der",
                        }
                    ],
                },
            },
            "must not set both",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {
                            "userName": "user1",
                            "password": "password",
                            "roles": ["Anonymous"],
                        },
                    ],
                },
            },
            "must not grant Anonymous",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [{"userName": "user1", "password": "password", "roles": [True]}],
                },
            },
            "must be a string or integer",
        ),
        (
            {
                "userIdentityData": {
                    "enabled": True,
                    "users": [
                        {
                            "userName": "user1",
                            "x509ThumbprintSha1Hex": "0123456789abcdef0123456789abcdef01234567",
                        },
                        {
                            "userName": "user2",
                            "x509ThumbprintSha1Hex": "0123456789ABCDEF0123456789ABCDEF01234567",
                        },
                    ],
                },
            },
            "duplicate x509ThumbprintSha1Hex",
        ),
    ],
)
def test_validate_user_identity_config_payload(payload: object, expected: str | None) -> None:
    error = runner._validate_user_identity_config_payload(payload)

    if expected is None:
        assert error is None
    else:
        assert expected in error


def test_check_binaries_accepts_required_json_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linux_zip = tmp_path / "OPC_UA_IJT_Server_Simulator_Linux.zip"
    windows_zip = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package(linux_zip)
    _write_package(windows_zip)
    monkeypatch.setattr(runner, "_LINUX_ZIP", linux_zip)
    monkeypatch.setattr(runner, "_WINDOWS_ZIP", windows_zip)

    results: list[tuple] = []
    runner._check_binaries(results)

    assert results[-1][2] is True
    assert "required JSON files present" in results[-1][3]


def test_check_binaries_rejects_missing_user_identity_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linux_zip = tmp_path / "OPC_UA_IJT_Server_Simulator_Linux.zip"
    windows_zip = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package(linux_zip, include_user_identity=False)
    _write_package(windows_zip)
    monkeypatch.setattr(runner, "_LINUX_ZIP", linux_zip)
    monkeypatch.setattr(runner, "_WINDOWS_ZIP", windows_zip)

    results: list[tuple] = []
    runner._check_binaries(results)

    assert results[-1][2] is False
    assert "user_identity_configuration.json" in results[-1][3]


def test_check_binaries_rejects_bad_user_identity_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linux_zip = tmp_path / "OPC_UA_IJT_Server_Simulator_Linux.zip"
    windows_zip = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package(
        linux_zip,
        user_identity_payload={
            "userIdentityData": {
                "enabled": True,
                "users": [
                    {
                        "userName": "user1",
                        "password": "password",
                        "x509ThumbprintSha1Hex": "bad",
                    },
                ],
            },
        },
    )
    _write_package(windows_zip)
    monkeypatch.setattr(runner, "_LINUX_ZIP", linux_zip)
    monkeypatch.setattr(runner, "_WINDOWS_ZIP", windows_zip)

    results: list[tuple] = []
    runner._check_binaries(results)

    assert results[-1][2] is False
    assert "SHA-1 hex string" in results[-1][3]
