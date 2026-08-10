from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, get_args, get_origin
from unittest.mock import AsyncMock

import pytest
from asyncua import ua
from asyncua.client.ua_client import UaClientState, UASocketState
from asyncua.ua import ua_binary

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from opcua_session_policy import (  # noqa: E402
    apply_asyncua_generated_type_compatibility_patch,
    connect_client,
    disconnect_client,
    is_client_connected,
)


@dataclass
class _NumericSubtypeEnvelope:
    Value: Annotated[ua.Number, "AllowSubtypes"] = field(
        default_factory=lambda: ua.Variant(42, ua.VariantType.Int32)
    )


@dataclass
class _StructuredSubtypeEnvelope:
    Value: Annotated[ua.ExtensionObject, "AllowSubtypes"] = field(default_factory=ua.EUInformation)


def test_asyncua_2_connected_session_is_detected() -> None:
    client = SimpleNamespace(
        uaclient=SimpleNamespace(
            has_session=True,
            state=UaClientState.CONNECTED,
        )
    )

    assert is_client_connected(client)


def test_open_socket_without_session_is_not_connected() -> None:
    client = SimpleNamespace(
        uaclient=SimpleNamespace(
            has_session=False,
            state=UaClientState.SOCKET_OPEN,
            protocol=SimpleNamespace(state=UASocketState.OPEN),
        )
    )

    assert not is_client_connected(client)


def test_legacy_enum_socket_state_is_detected_by_value() -> None:
    client = SimpleNamespace(
        uaclient=SimpleNamespace(
            protocol=SimpleNamespace(state=UASocketState.OPEN),
        )
    )

    assert is_client_connected(client)


@pytest.mark.asyncio
async def test_connect_client_is_idempotent_for_active_session() -> None:
    client = SimpleNamespace(
        uaclient=SimpleNamespace(
            has_session=True,
            state=UaClientState.CONNECTED,
        ),
        connect=AsyncMock(),
        session_timeout=None,
    )

    await connect_client(client)

    client.connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_disconnect_client_propagates_cleanup_failure() -> None:
    client = SimpleNamespace(disconnect=AsyncMock(side_effect=OSError("socket cleanup failed")))

    with pytest.raises(OSError, match="socket cleanup failed"):
        await disconnect_client(client, settle_delay=0)


def test_generated_type_hints_preserve_allow_subtypes_metadata() -> None:
    apply_asyncua_generated_type_compatibility_patch()

    hints = ua_binary.get_safe_type_hints(_StructuredSubtypeEnvelope, {"ua": ua})
    field_type = hints["Value"]

    assert get_origin(field_type) is Annotated
    assert get_args(field_type) == (ua.ExtensionObject, "AllowSubtypes")


def test_numeric_subtype_round_trips_as_variant() -> None:
    apply_asyncua_generated_type_compatibility_patch()

    encoded = ua_binary.to_binary(_NumericSubtypeEnvelope, _NumericSubtypeEnvelope())
    decoded = ua_binary.from_binary(_NumericSubtypeEnvelope, ua_binary.Buffer(encoded))

    assert isinstance(decoded.Value, ua.Variant)
    assert decoded.Value.VariantType == ua.VariantType.Int32
    assert decoded.Value.Value == 42


def test_structured_subtype_round_trips_as_extension_object() -> None:
    apply_asyncua_generated_type_compatibility_patch()

    encoded = ua_binary.to_binary(_StructuredSubtypeEnvelope, _StructuredSubtypeEnvelope())
    decoded = ua_binary.from_binary(_StructuredSubtypeEnvelope, ua_binary.Buffer(encoded))

    assert isinstance(decoded.Value, ua.EUInformation)
