from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import docker_freshness


def test_parse_docker_created_timestamp_handles_nanosecond_utc_value() -> None:
    parsed = docker_freshness.parse_docker_created_timestamp("2026-05-21T13:41:19.204798168Z")

    assert parsed == pytest.approx(1779370879.204798)


def test_parse_docker_created_timestamp_handles_offset_and_naive_values() -> None:
    with_offset = docker_freshness.parse_docker_created_timestamp("2026-05-21T15:41:19.2+02:00")
    naive = docker_freshness.parse_docker_created_timestamp("2026-05-21T13:41:19")

    assert with_offset == pytest.approx(1779370879.2)
    assert naive == pytest.approx(1779370879.0)


@pytest.mark.parametrize("value", ["", "not-a-timestamp"])
def test_parse_docker_created_timestamp_rejects_unparseable_values(value: str) -> None:
    assert docker_freshness.parse_docker_created_timestamp(value) is None


def test_docker_image_created_timestamp_returns_inspect_created_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        cwd = kwargs.get("cwd")
        assert cwd is None or isinstance(cwd, str)
        calls.append((cmd, cwd))
        return SimpleNamespace(returncode=0, stdout="2026-05-21T13:41:19Z\n")

    monkeypatch.setattr(docker_freshness.subprocess, "run", fake_run)

    created = docker_freshness.docker_image_created_timestamp(
        "docker",
        "opcua-ijt-server:latest",
        cwd="compose-dir",
    )

    assert created == pytest.approx(1779370879.0)
    assert calls == [
        (
            [
                "docker",
                "image",
                "inspect",
                "opcua-ijt-server:latest",
                "--format",
                "{{.Created}}",
            ],
            "compose-dir",
        )
    ]


def test_docker_image_created_timestamp_returns_none_when_inspect_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        docker_freshness.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
    )

    assert docker_freshness.docker_image_created_timestamp("docker", "missing") is None


def test_docker_image_created_timestamp_returns_none_on_process_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=10)

    monkeypatch.setattr(docker_freshness.subprocess, "run", raise_timeout)

    assert docker_freshness.docker_image_created_timestamp("docker", "hung") is None


def test_is_image_stale_false_when_reference_is_missing(tmp_path: Path) -> None:
    missing_zip = tmp_path / "missing.zip"

    assert not docker_freshness.is_image_stale("docker", "image", missing_zip)


def test_is_image_stale_true_when_image_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = tmp_path / "OPC_UA_IJT_Server_Simulator_Linux.zip"
    reference.write_bytes(b"zip")
    monkeypatch.setattr(docker_freshness, "docker_image_created_timestamp", lambda *a, **k: None)

    assert docker_freshness.is_image_stale("docker", "image", reference)


def test_is_image_stale_compares_reference_mtime_to_image_created_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = tmp_path / "OPC_UA_IJT_Server_Simulator_Linux.zip"
    reference.write_bytes(b"zip")
    reference_mtime = reference.stat().st_mtime
    monkeypatch.setattr(
        docker_freshness,
        "docker_image_created_timestamp",
        lambda *a, **k: reference_mtime + 1,
    )

    assert not docker_freshness.is_image_stale("docker", "image", reference)

    monkeypatch.setattr(
        docker_freshness,
        "docker_image_created_timestamp",
        lambda *a, **k: reference_mtime - 1,
    )

    assert docker_freshness.is_image_stale("docker", "image", reference)
