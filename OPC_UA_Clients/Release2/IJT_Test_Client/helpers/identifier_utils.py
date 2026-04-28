"""Shared helpers for IJT identifier conformance tests."""

import uuid

import pytest
from asyncua import ua

from helpers.node_discovery import read_tool_product_instance_uri

ENTITY_TYPE_VEHICLE = 20
VIN_IDENTIFIER_NAME = "VIN"
VIN_IDENTIFIER_DESCRIPTION = "Vehicle Identification Number"
UNSUPPORTED_IDENTIFIER_ERROR_KEYWORDS = ("BadNotSupported", "BadMethodInvalid", "BadUserAccessDenied")


def make_test_vin() -> str:
    return f"TST{uuid.uuid4().hex[:14].upper()}"


def make_external_entity(identifier: str, entity_type_value: int = ENTITY_TYPE_VEHICLE):
    entity_type = getattr(ua, "EntityDataType", None)
    if entity_type is None:
        pytest.skip("EntityDataType not available - load_data_type_definitions() may have failed")

    entity = entity_type()
    entity.Name = VIN_IDENTIFIER_NAME
    entity.Description = VIN_IDENTIFIER_DESCRIPTION
    entity.EntityId = identifier
    entity.EntityOriginId = ""
    entity.IsExternal = True
    entity.EntityType = entity_type_value
    return entity


def contains_identifier(value, identifier: str) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return any(contains_identifier(item, identifier) for item in value)
    if isinstance(value, (str, bytes, bytearray)):
        return identifier in str(value)
    for attr in ("Name", "EntityId", "EntityOriginId"):
        if str(getattr(value, attr, "")) == identifier:
            return True
    return identifier in str(value)


def is_unsupported_identifier_error(err_str: str) -> bool:
    return any(keyword in err_str for keyword in UNSUPPORTED_IDENTIFIER_ERROR_KEYWORDS)


async def read_required_product_instance_uri(client, ns_ijt: int, ns_di: int, ns_app: int | None) -> str:
    product_instance_uri = await read_tool_product_instance_uri(client, ns_ijt, ns_di, ns_app)
    if not product_instance_uri:
        pytest.skip("No Tool ProductInstanceUri found - cannot exercise identifier persistence")
    return product_instance_uri
