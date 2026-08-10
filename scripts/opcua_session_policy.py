"""Shared OPC UA client session policy for IJT Python clients.

This module centralizes the runtime rules we rely on across Test, Web, and
Console clients when using asyncua:

* use one explicit session timeout everywhere
* connect/disconnect through one policy instead of ad hoc per-client code
* interpret asyncua enum-backed client/session state consistently
* give the server a short settle window after disconnect so released sessions do
  not immediately trip BadTooManySessions on the next client
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import fields
from enum import Enum
from typing import Annotated, get_args, get_origin, get_type_hints

from asyncua import Client
from asyncua.ua import ua_binary, uatypes

OPCUA_SESSION_TIMEOUT_MS = 600_000
OPCUA_SESSION_RELEASE_SETTLE_SECS = 0.2
_TYPE_SERIALIZER_PATCHED_ATTR = "_ijt_number_serializer_patched"


def apply_session_policy(client: Client) -> Client:
    """Apply the shared IJT OPC UA session policy to *client*."""
    client.session_timeout = OPCUA_SESSION_TIMEOUT_MS
    apply_asyncua_generated_type_compatibility_patch()
    return client


def is_client_connected(client: Client | None) -> bool:
    """Return whether asyncua has an active session on an open connection.

    asyncua 2.x exposes enum-backed ``UaClient.state`` and ``has_session`` values.
    Comparing ``str(protocol.state)`` with ``"open"`` is incorrect because an open
    socket renders as ``"UASocketState.OPEN"``. Prefer the session-aware 2.x state
    and retain a value-based socket fallback for older supported client shapes.
    """
    if client is None:
        return False

    ua_client = getattr(client, "uaclient", None)
    if ua_client is None:
        return False

    has_session = getattr(ua_client, "has_session", None)
    client_state = getattr(ua_client, "state", None)
    if has_session is not None or client_state is not None:
        state_value = getattr(client_state, "value", client_state)
        return bool(has_session) and str(state_value).strip().lower() == "connected"

    protocol = getattr(ua_client, "protocol", None)
    socket_state = getattr(protocol, "state", None)
    state_value = getattr(socket_state, "value", socket_state)
    return str(state_value).strip().lower() == "open"


def apply_asyncua_generated_type_compatibility_patch() -> None:
    """Preserve subtype metadata and encode abstract numeric fields as Variants.

    asyncua 2.0.1 (and current upstream master) resolves generated annotations
    without ``include_extras=True``, which removes ``AllowSubtypes`` metadata.
    Once preserved, asyncua's generic subtype path uses ExtensionObject encoding;
    that is correct for structured fields but abstract ``ua.Number`` fields such
    as ``SignalDataType.SignalValue`` require Variant encoding. Reading either
    category with the wrong codec shifts the remaining binary payload.
    """

    if getattr(ua_binary.create_type_serializer, _TYPE_SERIALIZER_PATCHED_ATTR, False):
        return

    original_create_type_serializer = ua_binary.create_type_serializer
    original_create_type_deserializer = ua_binary._create_type_deserializer
    original_create_dataclass_deserializer = ua_binary._create_dataclass_deserializer

    def _patched_get_safe_type_hints(cls: type, extra_ns: dict[str, object] | None = None):
        localns = {
            key: value for key, value in cls.__dict__.items() if not isinstance(value, property)
        }
        if extra_ns:
            localns.update(extra_ns)
        return get_type_hints(cls, globalns=None, localns=localns, include_extras=True)

    def _patched_create_type_serializer(uatype: type):
        if _is_subtyped_number(uatype):
            return _serialize_subtyped_number
        return original_create_type_serializer(uatype)

    def _patched_create_type_deserializer(uatype, dataclazz):
        resolved_uatype, _is_optional = ua_binary.resolve_uatype(uatype)
        if _is_subtyped_number(resolved_uatype):
            return ua_binary.variant_from_binary
        return original_create_type_deserializer(uatype, dataclazz)

    def _patched_create_dataclass_deserializer(objtype):
        if isinstance(objtype, str):
            objtype = getattr(ua_binary.ua, objtype)
        assert isinstance(objtype, type)
        if issubclass(objtype, Enum):
            return ua_binary.create_enum_deserializer(objtype)  # type: ignore[arg-type]
        if issubclass(objtype, ua_binary.ua.UaUnion):
            return original_create_dataclass_deserializer(objtype)

        enc_count = 0
        resolved_fieldtypes = ua_binary.get_safe_type_hints(objtype, {"ua": ua_binary.ua})
        has_number_field = any(
            _is_subtyped_number(resolved_fieldtypes[field.name]) for field in fields(objtype)
        )
        if not has_number_field:
            return original_create_dataclass_deserializer(objtype)

        field_deserializers = []
        for field in fields(objtype):
            optional_enc_bit = 0
            field_type = resolved_fieldtypes[field.name]
            if ua_binary.type_is_optional(field_type):
                optional_enc_bit = 1 << enc_count
                enc_count += 1
                field_type = ua_binary.type_from_optional(field_type)
            if _is_subtyped_number(field_type):
                deserialize_field = ua_binary.variant_from_binary
            elif ua_binary.type_allow_subclass(field_type):
                deserialize_field = ua_binary.extensionobject_from_binary
            else:
                deserialize_field = _patched_create_type_deserializer(field_type, objtype)
            field_deserializers.append((field, optional_enc_bit, deserialize_field))

        def decode(data):
            kwargs: dict[str, object] = {}
            enc = 0
            for field, optional_enc_bit, deserialize_field in field_deserializers:
                if field.name == "Encoding":
                    enc = deserialize_field(data)
                elif optional_enc_bit == 0 or enc & optional_enc_bit:
                    kwargs[field.name] = deserialize_field(data)
            return objtype(**kwargs)

        return decode

    _patched_create_type_serializer._ijt_number_serializer_patched = True  # type: ignore[attr-defined]
    ua_binary.get_safe_type_hints = _patched_get_safe_type_hints  # type: ignore[assignment]
    ua_binary.create_type_serializer = _patched_create_type_serializer  # type: ignore[assignment]
    ua_binary._create_type_deserializer = _patched_create_type_deserializer  # type: ignore[assignment]
    ua_binary._create_dataclass_deserializer = _patched_create_dataclass_deserializer  # type: ignore[assignment]


def _is_subtyped_number(uatype: object) -> bool:
    resolved, _is_optional = ua_binary.resolve_uatype(uatype)
    if resolved is uatypes.Number:
        return True
    return get_origin(resolved) is Annotated and get_args(resolved)[:1] == (uatypes.Number,)


def _serialize_subtyped_number(value: object) -> bytes:
    variant = value if isinstance(value, ua_binary.ua.Variant) else ua_binary.ua.Variant(value)
    return ua_binary.variant_to_binary(variant)


async def load_ijt_type_definitions(client: Client) -> None:
    """Load IJT custom structures using asyncua's modern DataTypeDefinition path."""
    await client.load_data_type_definitions()


async def connect_client(client: Client) -> None:
    """Connect a client after applying the shared session policy."""
    apply_session_policy(client)
    if is_client_connected(client):
        return
    await client.connect()


async def disconnect_client(
    client: Client | None,
    *,
    settle_delay: float = OPCUA_SESSION_RELEASE_SETTLE_SECS,
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """Disconnect a client and wait briefly for server-side session release."""
    if client is None:
        return
    try:
        await client.disconnect()
    except Exception as exc:
        if on_error is not None:
            on_error(exc)
        else:
            raise
    finally:
        await asyncio.sleep(settle_delay)
