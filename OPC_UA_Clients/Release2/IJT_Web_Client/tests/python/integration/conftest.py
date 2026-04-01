"""Automatically apply pytest.mark.integration to all tests in this directory."""
import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if item.fspath and "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
