"""
Unit tests for session policy, timeout configuration,
connection guards, and type serializer patches.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua
from asyncua.ua import uatypes

from ijt_performance_client.session_policy import (
    _is_subtyped_number,
    _serialize_subtyped_number,
    apply_asyncua_generated_type_compatibility_patch,
    apply_session_policy,
    disconnect_client,
    is_client_connected,
    load_ijt_type_definitions,
    patch_asyncua_subtype_serializer,
)


def test_apply_session_policy():
    mock_client = MagicMock()
    mock_client.aio_obj = MagicMock()

    result = apply_session_policy(mock_client, 120_000)
    assert result is mock_client
    assert mock_client.session_timeout == 120_000
    assert mock_client.aio_obj.session_timeout == 120_000


def test_is_subtyped_number():
    assert _is_subtyped_number(uatypes.Number) is True
    assert _is_subtyped_number(uatypes.Double) is False
    assert _is_subtyped_number(str) is False


def test_serialize_subtyped_number():
    raw_val = 42.5
    b = _serialize_subtyped_number(raw_val)
    assert isinstance(b, bytes)
    assert len(b) > 0

    var_val = ua.Variant(99.9, ua.VariantType.Double)
    b_var = _serialize_subtyped_number(var_val)
    assert isinstance(b_var, bytes)
    assert len(b_var) > 0


def test_patch_asyncua_subtype_serializer_idempotent():
    # Calling it multiple times should safely return without re-patching
    patch_asyncua_subtype_serializer()
    patch_asyncua_subtype_serializer()


@pytest.mark.asyncio
async def test_load_ijt_type_definitions_coroutine():
    mock_client = MagicMock()
    mock_client.load_data_type_definitions = AsyncMock()
    await load_ijt_type_definitions(mock_client)
    mock_client.load_data_type_definitions.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_ijt_type_definitions_sync():
    mock_client = MagicMock()
    mock_client.load_data_type_definitions = MagicMock(return_value=None)
    await load_ijt_type_definitions(mock_client)
    mock_client.load_data_type_definitions.assert_called_once()


@pytest.mark.asyncio
async def test_is_client_connected_states():
    # None client
    assert await is_client_connected(None) is False

    # Client with no uaclient
    mock_client = MagicMock()
    mock_client.aio_obj = mock_client
    mock_client.uaclient = None
    assert await is_client_connected(mock_client) is False

    # Client with state = connected and has_session = True
    mock_ua = MagicMock()
    mock_ua.has_session = True
    mock_ua.state = "connected"
    mock_client.uaclient = mock_ua
    assert await is_client_connected(mock_client) is True

    # Client with state = disconnected
    mock_ua.state = "disconnected"
    assert await is_client_connected(mock_client) is False

    # Client socket protocol fallback
    del mock_ua.has_session
    del mock_ua.state
    mock_protocol = MagicMock()
    mock_protocol.state = "open"
    mock_ua.protocol = mock_protocol
    assert await is_client_connected(mock_client) is True

    mock_protocol.state = "closed"
    assert await is_client_connected(mock_client) is False


@pytest.mark.asyncio
async def test_disconnect_client_clean():
    # None client
    await disconnect_client(None, settle_delay=0)

    # Normal async disconnect
    mock_client = MagicMock()
    mock_client.disconnect = AsyncMock()
    await disconnect_client(mock_client, settle_delay=0.01)
    mock_client.disconnect.assert_awaited_once()

    # Exception during disconnect is safely caught
    mock_client_err = MagicMock()
    mock_client_err.disconnect = AsyncMock(side_effect=RuntimeError("Socket already closed"))
    await disconnect_client(mock_client_err, settle_delay=0)


def test_patched_dataclass_deserializer():
    import io
    from dataclasses import dataclass

    from asyncua.ua import ua_binary

    apply_asyncua_generated_type_compatibility_patch()

    @dataclass
    class DummyTrace:
        Value: uatypes.Number

    decoder = ua_binary._create_dataclass_deserializer(DummyTrace)
    assert callable(decoder)

    var = ua.Variant(12.34, ua.VariantType.Double)
    raw_bytes = ua_binary.variant_to_binary(var)
    stream = io.BytesIO(raw_bytes)
    decoded = decoder(stream)
    assert isinstance(decoded, DummyTrace)
    assert decoded.Value.Value == 12.34


@pytest.mark.asyncio
async def test_is_client_connected_exception():
    mock_bad_client = MagicMock()
    # Accessing aio_obj raises an unexpected exception
    type(mock_bad_client).aio_obj = property(fget=MagicMock(side_effect=RuntimeError("Corrupt state")))
    assert await is_client_connected(mock_bad_client) is False


def test_patched_type_serializers_and_branches():
    import io
    import typing
    from dataclasses import dataclass
    from enum import Enum

    from asyncua.ua import ua_binary

    apply_asyncua_generated_type_compatibility_patch()

    # 1. _patched_create_type_serializer for Number vs standard type
    ser_num = ua_binary.create_type_serializer(uatypes.Number)
    assert ser_num is not None
    ser_std = ua_binary.create_type_serializer(uatypes.Int32)
    assert ser_std is not None

    # 2. _patched_create_type_deserializer for Number vs standard type
    deser_num = ua_binary._create_type_deserializer(uatypes.Number, None)
    assert deser_num is not None
    deser_std = ua_binary._create_type_deserializer(uatypes.Int32, None)
    assert deser_std is not None

    # 3. _create_dataclass_deserializer with string name (e.g., "NodeId")
    deser_str = ua_binary._create_dataclass_deserializer("NodeId")
    assert callable(deser_str)

    # 4. _create_dataclass_deserializer with Enum
    class ColorEnum(Enum):
        RED = 1
        BLUE = 2

    deser_enum = ua_binary._create_dataclass_deserializer(ColorEnum)
    assert callable(deser_enum)

    # 5. _create_dataclass_deserializer with UaUnion subclass
    @dataclass
    class DummyUnion(ua.UaUnion):
        Encoding: uatypes.Byte
        _union_types = (uatypes.Int32,)

    deser_union = ua_binary._create_dataclass_deserializer(DummyUnion)
    assert callable(deser_union)

    # 6. _create_dataclass_deserializer with class having no Number field
    @dataclass
    class PureStringClass:
        name: uatypes.String

    deser_pure = ua_binary._create_dataclass_deserializer(PureStringClass)
    assert callable(deser_pure)

    # 7. _create_dataclass_deserializer with mixed fields (Encoding, Number, Optional ExtensionObject, standard type)
    @dataclass
    class DummyMixedClass:
        ValNum: uatypes.Number
        Encoding: uatypes.Byte = 0
        OptExt: typing.Optional[typing.Annotated[uatypes.Int32, "subclass"]] = None
        StdVal: uatypes.Int32 = 0

    deser_mixed = ua_binary._create_dataclass_deserializer(DummyMixedClass)
    assert callable(deser_mixed)

    # Stream bytes: ValNum (Variant Double 10.0), Encoding=0 (Byte), StdVal (Int32 42)
    var = ua.Variant(10.0, ua.VariantType.Double)
    var_bytes = ua_binary.variant_to_binary(var)
    int_bytes = b"\x2a\x00\x00\x00"  # 42 in 32-bit LE
    stream_bytes = var_bytes + b"\x00" + int_bytes
    decoded = deser_mixed(io.BytesIO(stream_bytes))
    assert isinstance(decoded, DummyMixedClass)
    assert decoded.ValNum.Value == 10.0
    assert decoded.StdVal == 42


def test_verify_asyncua_version_compatibility_rejects_unknown_version(monkeypatch):
    import asyncua

    from ijt_performance_client.session_policy import verify_asyncua_version_compatibility

    monkeypatch.setattr(asyncua, "__version__", "3.0.0")
    with pytest.raises(RuntimeError, match="validated only with asyncua 2.0.1"):
        verify_asyncua_version_compatibility()
