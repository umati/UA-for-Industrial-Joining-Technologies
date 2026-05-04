from types import SimpleNamespace

import pytest

from helpers import identifier_utils


def test_make_test_vin_has_expected_prefix_length_and_unique_suffix():
    first = identifier_utils.make_test_vin()
    second = identifier_utils.make_test_vin()

    assert first.startswith("TST")
    assert len(first) == 17
    assert first != second


def test_make_external_entity_populates_standard_identifier_fields(monkeypatch):
    class EntityDataType:
        pass

    monkeypatch.setattr(identifier_utils.ua, "EntityDataType", EntityDataType, raising=False)

    entity = identifier_utils.make_external_entity("VIN-123", entity_type_value=99)

    assert entity.Name == "VIN"
    assert entity.Description == "Vehicle Identification Number"
    assert entity.EntityId == "VIN-123"
    assert entity.EntityOriginId == ""
    assert entity.IsExternal is True
    assert entity.EntityType == 99


def test_make_external_entity_skips_when_entity_data_type_is_missing(monkeypatch):
    monkeypatch.setattr(identifier_utils.ua, "EntityDataType", None, raising=False)

    with pytest.raises(pytest.skip.Exception):
        identifier_utils.make_external_entity("VIN-123")


@pytest.mark.parametrize(
    ("value", "identifier", "expected"),
    [
        (None, "VIN-1", False),
        ("prefix-VIN-1-suffix", "VIN-1", True),
        (b"prefix-VIN-2-suffix", "VIN-2", True),
        ([SimpleNamespace(EntityId="VIN-3")], "VIN-3", True),
        ((SimpleNamespace(Name="VIN-4"),), "VIN-4", True),
        (SimpleNamespace(EntityOriginId="VIN-5"), "VIN-5", True),
        (SimpleNamespace(other="VIN-6"), "VIN-6", True),
        (SimpleNamespace(EntityId="OTHER"), "VIN-7", False),
    ],
)
def test_contains_identifier_handles_nested_values_and_common_entity_fields(value, identifier, expected):
    assert identifier_utils.contains_identifier(value, identifier) is expected


@pytest.mark.parametrize(
    "message",
    [
        "BadNotSupported",
        "BadMethodInvalid",
        "BadUserAccessDenied",
        "server returned BadNotSupported for optional identifier method",
    ],
)
def test_is_unsupported_identifier_error_matches_known_status_text(message):
    assert identifier_utils.is_unsupported_identifier_error(message) is True


def test_is_unsupported_identifier_error_rejects_unrelated_errors():
    assert identifier_utils.is_unsupported_identifier_error("BadInvalidArgument") is False


@pytest.mark.asyncio
async def test_read_required_product_instance_uri_returns_value(monkeypatch):
    async def fake_read(client, ns_ijt, ns_di, ns_app):
        assert ns_ijt == 7
        assert ns_di == 5
        assert ns_app == 2
        return "TOOL-PIU-1"

    monkeypatch.setattr(identifier_utils, "read_tool_product_instance_uri", fake_read)

    result = await identifier_utils.read_required_product_instance_uri(object(), 7, 5, 2)

    assert result == "TOOL-PIU-1"


@pytest.mark.asyncio
async def test_read_required_product_instance_uri_skips_when_missing(monkeypatch):
    async def fake_read(client, ns_ijt, ns_di, ns_app):
        return ""

    monkeypatch.setattr(identifier_utils, "read_tool_product_instance_uri", fake_read)

    with pytest.raises(pytest.skip.Exception):
        await identifier_utils.read_required_product_instance_uri(object(), 7, 5, None)
