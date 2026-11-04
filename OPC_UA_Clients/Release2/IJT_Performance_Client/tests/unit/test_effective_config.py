"""Unit tests for effective configuration tracking and env parsing."""

import pytest

from src.config import OpcUaPoolConfig
from src.effective_config import EffectiveConfigTracker, TrackedValue, parse_env_float, parse_env_int


def test_tracked_value_to_dict():
    tv = TrackedValue(value=100, source="cli")
    assert tv.to_dict() == {"value": 100, "source": "cli"}


def test_parse_env_int_success_and_error():
    assert parse_env_int("TEST_VAR", "42") == 42
    with pytest.raises(ValueError, match="Invalid integer for environment variable TEST_VAR"):
        parse_env_int("TEST_VAR", "not_a_number")


def test_parse_env_float_success_and_error():
    assert parse_env_float("TEST_VAR", "3.14") == 3.14
    with pytest.raises(ValueError, match="Invalid float for environment variable TEST_VAR"):
        parse_env_float("TEST_VAR", "not_a_float")


def test_effective_config_tracker_mark_and_snapshot():
    cfg = OpcUaPoolConfig(inventory_http_token="secret_token")
    tracker = EffectiveConfigTracker()
    tracker.mark("sub_period_ms", "cli")
    tracker.mark_many(["connect_concurrency", "duration_seconds"], "env")

    extra = {
        "custom_tracked": TrackedValue("custom_val", "profile"),
        "custom_dict": {"value": 99, "source": "inventory"},
        "custom_plain": "plain_val",
        "inventory_http_token": "ignore_me",
    }
    snap = tracker.snapshot(cfg, extra=extra)

    assert snap["sub_period_ms"]["source"] == "cli"
    assert snap["connect_concurrency"]["source"] == "env"
    assert snap["duration_seconds"]["source"] == "env"
    assert snap["inventory_http_token"]["value"] == "***"
    assert snap["custom_tracked"] == {"value": "custom_val", "source": "profile"}
    assert snap["custom_dict"] == {"value": 99, "source": "inventory"}
    assert snap["custom_plain"] == {"value": "plain_val", "source": "default"}
