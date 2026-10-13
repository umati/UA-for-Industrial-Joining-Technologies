"""Contract tests for shared simulator ZIP extraction."""

from __future__ import annotations

import logging
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import simulator_extract as extract


def _write_package_zip(path: Path, top: str, marker: str, *, unix_mode: int | None = None) -> None:
    binary = (
        "opcua_ijt_demo_application"
        if top == extract.LINUX_PACKAGE_NAME
        else "opcua_ijt_demo_application.exe"
    )
    with zipfile.ZipFile(path, "w") as zf:
        info = zipfile.ZipInfo(f"{top}/{binary}")
        if unix_mode is not None:
            info.create_system = 3  # Unix
            info.external_attr = (unix_mode & 0xFFFF) << 16
        zf.writestr(info, marker)


def test_ensure_simulator_package_extracts_newer_zip(tmp_path: Path) -> None:
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    target.mkdir()
    (target / "stale.txt").write_text("old", encoding="utf-8")
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package_zip(archive, target.name, "new")
    os.utime(target, (1, 1))

    assert extract.ensure_simulator_package(archive, target) is True
    assert (target / "opcua_ijt_demo_application.exe").read_text(encoding="utf-8") == "new"
    assert not (target / "stale.txt").exists()
    assert (target / extract._STAMP_NAME).is_file()
    assert [p.name for p in tmp_path.iterdir() if ".extract-" in p.name] == []
    assert [p.name for p in tmp_path.iterdir() if ".previous-" in p.name] == []


def test_ensure_simulator_package_keeps_stamp_current_folder(tmp_path: Path) -> None:
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package_zip(archive, "OPC_UA_IJT_Server_Simulator", "payload")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    assert extract.ensure_simulator_package(archive, target) is True
    (target / "keep.txt").write_text("extra", encoding="utf-8")

    assert extract.ensure_simulator_package(archive, target) is True
    assert (target / "keep.txt").read_text(encoding="utf-8") == "extra"
    assert (target / "opcua_ijt_demo_application.exe").read_text(encoding="utf-8") == "payload"


def test_ensure_simulator_package_repairs_incomplete_folder(tmp_path: Path) -> None:
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package_zip(archive, "OPC_UA_IJT_Server_Simulator", "fixed")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    target.mkdir()
    (target / "keep.txt").write_text("incomplete", encoding="utf-8")

    assert extract.ensure_simulator_package(archive, target) is True
    assert (target / "opcua_ijt_demo_application.exe").read_text(encoding="utf-8") == "fixed"
    assert not (target / "keep.txt").exists()


def test_ensure_simulator_package_adopts_legacy_folder_without_swap(tmp_path: Path) -> None:
    """Binary present but no stamp → write stamp in place; do not rename-aside."""
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package_zip(archive, "OPC_UA_IJT_Server_Simulator", "from-zip")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    target.mkdir()
    (target / "opcua_ijt_demo_application.exe").write_text("already-running", encoding="utf-8")
    (target / "keep.txt").write_text("stable", encoding="utf-8")

    assert extract.ensure_simulator_package(archive, target) is True
    assert (target / "opcua_ijt_demo_application.exe").read_text(
        encoding="utf-8"
    ) == "already-running"
    assert (target / "keep.txt").read_text(encoding="utf-8") == "stable"
    assert (target / extract._STAMP_NAME).is_file()
    assert [p.name for p in tmp_path.iterdir() if ".previous-" in p.name] == []


def test_ensure_simulator_package_missing_archive(tmp_path: Path) -> None:
    assert extract.ensure_simulator_package(tmp_path / "missing.zip", tmp_path / "Sim") is False


def test_ensure_simulator_package_bad_layout(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("wrong_top/file.txt", "x")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    with caplog.at_level(logging.WARNING):
        assert extract.ensure_simulator_package(archive, target) is False
    assert "outside top-level" in caplog.text or "no top-level" in caplog.text


def test_validate_simulator_zip_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("OPC_UA_IJT_Server_Simulator/../evil.exe", "x")
    with pytest.raises(RuntimeError, match="traversal|unsafe"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_validate_simulator_zip_rejects_oversized_member(tmp_path: Path, monkeypatch) -> None:
    archive = tmp_path / "big.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe", "x")
    monkeypatch.setattr(extract, "_MAX_UNCOMPRESSED_FILE", 0)
    with pytest.raises(RuntimeError, match="file size"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_validate_simulator_zip_rejects_absolute_member(tmp_path: Path) -> None:
    archive = tmp_path / "abs.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("/OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe", "x")
    with pytest.raises(RuntimeError, match="absolute/drive"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_validate_simulator_zip_rejects_drive_member(tmp_path: Path) -> None:
    archive = tmp_path / "drive.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("C:/OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe", "x")
    with pytest.raises(RuntimeError, match="absolute/drive"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_validate_simulator_zip_rejects_duplicate_member(tmp_path: Path) -> None:
    archive = tmp_path / "dup.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe", "a")
        zf.writestr("OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe", "b")
    with pytest.raises(RuntimeError, match="duplicate"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_validate_simulator_zip_rejects_symlink_member(tmp_path: Path) -> None:
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "target")
    with pytest.raises(RuntimeError, match="symlink"):
        extract.validate_simulator_zip(archive, "OPC_UA_IJT_Server_Simulator")


def test_ensure_simulator_package_sweeps_stale_staging(tmp_path: Path) -> None:
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    _write_package_zip(archive, "OPC_UA_IJT_Server_Simulator", "payload")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    stale = tmp_path / f"{target.name}.extract-leftover"
    stale.mkdir()
    (stale / "junk").write_text("x", encoding="utf-8")

    assert extract.ensure_simulator_package(archive, target) is True
    assert not stale.exists()
    assert (target / "opcua_ijt_demo_application.exe").read_text(encoding="utf-8") == "payload"


def test_ensure_simulator_package_rejects_traversal_zip(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    archive = tmp_path / "OPC_UA_IJT_Server_Simulator.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("OPC_UA_IJT_Server_Simulator/../evil.exe", "x")
    target = tmp_path / "OPC_UA_IJT_Server_Simulator"
    with caplog.at_level(logging.WARNING):
        assert extract.ensure_simulator_package(archive, target) is False
    assert "unsafe" in caplog.text or "traversal" in caplog.text


@pytest.mark.skipif(os.name == "nt", reason="Unix mode bits are a POSIX extract concern")
def test_ensure_simulator_package_restores_unix_exec_bits(tmp_path: Path) -> None:
    archive = tmp_path / extract.LINUX_ZIP_NAME
    _write_package_zip(
        archive,
        extract.LINUX_PACKAGE_NAME,
        "#!/bin/sh\n",
        unix_mode=0o100755,
    )
    target = tmp_path / extract.LINUX_PACKAGE_NAME
    assert extract.ensure_simulator_package(archive, target) is True
    mode = (target / "opcua_ijt_demo_application").stat().st_mode
    assert mode & stat.S_IXUSR


def test_ensure_present_packages_extracts_every_present_zip(tmp_path: Path) -> None:
    win_zip = tmp_path / extract.WINDOWS_ZIP_NAME
    linux_zip = tmp_path / extract.LINUX_ZIP_NAME
    _write_package_zip(win_zip, extract.WINDOWS_PACKAGE_NAME, "win")
    _write_package_zip(linux_zip, extract.LINUX_PACKAGE_NAME, "linux")

    ready = extract.ensure_present_simulator_packages(tmp_path)
    assert {p.name for p in ready} == {
        extract.WINDOWS_PACKAGE_NAME,
        extract.LINUX_PACKAGE_NAME,
    }
    assert (tmp_path / extract.WINDOWS_PACKAGE_NAME / "opcua_ijt_demo_application.exe").read_text(
        encoding="utf-8"
    ) == "win"
    assert (tmp_path / extract.LINUX_PACKAGE_NAME / "opcua_ijt_demo_application").read_text(
        encoding="utf-8"
    ) == "linux"


def test_ensure_present_packages_logs_when_no_zip(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        assert extract.ensure_present_simulator_packages(tmp_path) == []
    assert "No simulator ZIP found" in caplog.text
    assert "OPCUA_SIMULATOR_EXE" in caplog.text
