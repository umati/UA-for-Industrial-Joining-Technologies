from __future__ import annotations

from helpers.model_inventory import build_model_inventory, write_model_inventory


def test_model_inventory_public_api_exists() -> None:
    """build_model_inventory and write_model_inventory are importable."""
    assert callable(build_model_inventory)
    assert callable(write_model_inventory)
