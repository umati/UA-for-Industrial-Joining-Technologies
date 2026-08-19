"""Unit test for Conformance Unit catalog exporter."""

import json
from pathlib import Path

from scripts.export_cu_catalog import build_cu_catalog, export_catalog


def test_build_cu_catalog_has_123_cus():
    catalog = build_cu_catalog()
    assert catalog["standard"] == "OPC 40450-1 IJT Base"
    assert catalog["version"] == "1.01.0"
    assert catalog["total_conformance_units"] == 123
    assert len(catalog["conformance_units"]) == 123


def test_export_catalog_roundtrip(tmp_path: Path):
    out = tmp_path / "test_catalog.json"
    export_catalog(out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_conformance_units"] == 123
