"""
Unit tests for scripts/generate_sut_manifest_docs.py

The committed template, example manifests, and Markdown field reference are
generated from the schema metadata. These tests guard freshness (``--check``
drift mode) so a schema change cannot land without regenerating the artifacts.
No OPC UA server required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import generate_sut_manifest_docs as generator  # noqa: E402

from helpers.sut_manifest import MANIFEST_SUFFIX, preset_names  # noqa: E402


class TestGeneratedArtifactSet:
    def test_every_preset_has_a_committed_manifest(self):
        assert set(generator.GENERATED_MANIFESTS) == set(preset_names())

    def test_artifacts_include_the_field_reference(self):
        artifacts = generator.build_artifacts()
        assert generator.FIELD_REFERENCE_PATH in artifacts
        assert len(artifacts) == len(preset_names()) + 1

    def test_committed_artifacts_exist(self):
        for path in generator.build_artifacts():
            assert path.exists(), f"{path.name} has not been generated"

    def test_manifest_paths_use_the_manifest_suffix(self):
        for path in generator.GENERATED_MANIFESTS.values():
            assert path.name.endswith(MANIFEST_SUFFIX)


class TestDriftDetection:
    def test_committed_artifacts_are_up_to_date(self):
        stale = generator.check_artifacts()
        assert not stale, (
            "Generated SUT manifest artifacts are stale: "
            f"{[path.name for path in stale]}. "
            "Run: python scripts/generate_sut_manifest_docs.py"
        )

    def test_check_mode_passes_for_fresh_artifacts(self, capsys):
        assert generator.main(["--check"]) == 0
        assert "up to date" in capsys.readouterr().out

    def test_check_mode_reports_a_stale_artifact(self, monkeypatch, tmp_path, capsys):
        missing = tmp_path / f"missing{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {missing: "content\n"})
        assert generator.main(["--check"]) == 1
        assert "out of date" in capsys.readouterr().out

    def test_check_mode_detects_modified_content(self, monkeypatch, tmp_path):
        drifted = tmp_path / f"drifted{MANIFEST_SUFFIX}"
        drifted.write_text("old\n", encoding="utf-8")
        monkeypatch.setattr(generator, "build_artifacts", lambda: {drifted: "new\n"})
        assert generator.check_artifacts() == [drifted]


class TestWriteMode:
    def test_write_creates_missing_artifacts(self, monkeypatch, tmp_path, capsys):
        target = tmp_path / "generated" / f"new{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "generated\n"})
        assert generator.main([]) == 0
        assert target.read_text(encoding="utf-8") == "generated\n"
        assert "Updated 1 generated artifact" in capsys.readouterr().out

    def test_write_is_idempotent(self, monkeypatch, tmp_path, capsys):
        target = tmp_path / f"stable{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "stable\n"})
        generator.main([])
        capsys.readouterr()
        assert generator.main([]) == 0
        assert "already up to date" in capsys.readouterr().out

    def test_write_artifacts_returns_changed_paths(self, monkeypatch, tmp_path):
        target = tmp_path / f"changed{MANIFEST_SUFFIX}"
        monkeypatch.setattr(generator, "build_artifacts", lambda: {target: "v1\n"})
        assert generator.write_artifacts() == [target]
        assert generator.write_artifacts() == []


class TestGeneratedContent:
    @pytest.mark.parametrize("preset", sorted(preset_names()))
    def test_generated_manifest_is_marked_generated(self, preset):
        text = generator.GENERATED_MANIFESTS[preset].read_text(encoding="utf-8")
        assert "GENERATED FILE" in text
        assert "generate_sut_manifest_docs.py" in text

    def test_field_reference_is_marked_generated(self):
        text = generator.FIELD_REFERENCE_PATH.read_text(encoding="utf-8")
        assert "GENERATED FILE" in text
        assert "| Field | Type | Required | Default | Allowed values | Description |" in text
