"""
Export OPC 40450-1 Conformance Units (CU) and Facets Catalog.

Generates a machine-readable JSON catalog of all 123 CUs, their display names,
associated OPC UA method BrowseNames, spec sections, and facet memberships.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TEST_CLIENT_ROOT = Path(__file__).resolve().parents[1]
if str(TEST_CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_CLIENT_ROOT))

from helpers.cu_registry import _CU_METHOD_NAMES, CU, cu_display_name

CATALOG_PATH = TEST_CLIENT_ROOT / "test-results" / "conformance_units_catalog.json"


def build_cu_catalog() -> dict[str, object]:
    cu_keys = [value for name, value in vars(CU).items() if not name.startswith("_") and isinstance(value, str)]
    cu_keys.sort()

    conformance_units: list[dict[str, object]] = []
    for key in cu_keys:
        methods = list(_CU_METHOD_NAMES.get(key, ()))
        conformance_units.append(
            {"key": key, "display_name": cu_display_name(key), "methods": methods, "has_methods": len(methods) > 0}
        )

    return {
        "standard": "OPC 40450-1 IJT Base",
        "version": "1.01.0",
        "total_conformance_units": len(cu_keys),
        "conformance_units": conformance_units,
    }


def export_catalog(target_path: Path | None = None) -> Path:
    target = target_path or CATALOG_PATH
    catalog = build_cu_catalog()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    out = export_catalog()
    catalog = build_cu_catalog()
    print(f"Exported CU catalog ({catalog['total_conformance_units']} CUs) to {out}")
