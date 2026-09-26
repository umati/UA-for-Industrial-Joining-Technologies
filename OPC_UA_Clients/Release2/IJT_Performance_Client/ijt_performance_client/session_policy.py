"""
OPC UA Session Policy and Hygiene for High-Scale Operations.

Why does this module exist?
1. Session Timeouts:
   By default, many OPC UA clients disconnect if the server doesn't respond within 30 to 60 seconds.
   During high-stress testing of 500 controllers, temporary network hiccups or controller CPU spikes
   can cause sessions to drop. We configure a generous 10-minute (600,000 ms) timeout to keep connections stable.

2. Clean Disconnections:
   When disconnecting from 100+ servers quickly, closing sockets too fast without letting the server
   acknowledge the close can cause servers to run out of sessions ("BadTooManySessions"). We provide a
   safe disconnect helper with a brief settle delay.

3. Custom IJT Data Type Decoding (The asyncua 2.0.1 Fix):
   Industrial joining results contain custom structures (like torque and angle step traces).
   In the tested asyncua 2.0.1 baseline, abstract numeric fields (like SignalDataType.SignalValue) were decoded with the
   wrong binary format, causing subsequent bytes in the event payload to be misaligned (NotEnoughData error).
   The patch below ensures those numbers are safely decoded as standard Variants so complex traces unpack cleanly.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import fields
from enum import Enum
from typing import Annotated, get_args, get_origin, get_type_hints

from asyncua import Client
from asyncua.ua import ua_binary, uatypes

logger = logging.getLogger(__name__)

# Standard 10-minute session timeout (600,000 ms) for long test stability
DEFAULT_REQUESTED_SESSION_TIMEOUT_MS = 600_000
DISCONNECT_SETTLE_DELAY_S = 0.2
_TYPE_SERIALIZER_PATCHED_ATTR = "_ijt_number_serializer_patched"
ASYNCUA_VERIFIED_VERSION = "2.0.1"


def verify_asyncua_version_compatibility() -> str:
    """Require the asyncua version validated with the private serializer patch."""
    import asyncua

    current_ver = getattr(asyncua, "__version__", "unknown")
    if current_ver != ASYNCUA_VERIFIED_VERSION:
        raise RuntimeError(
            f"Unsupported asyncua version {current_ver}; this client and its serializer patch "
            f"are validated only with asyncua {ASYNCUA_VERIFIED_VERSION}."
        )
    return current_ver


def apply_session_policy(client: Client, session_timeout_ms: int = DEFAULT_REQUESTED_SESSION_TIMEOUT_MS) -> Client:
    """Configures safe session timeout parameters on a client before connecting."""
    verify_asyncua_version_compatibility()
    target = getattr(client, "aio_obj", client)
    target.session_timeout = session_timeout_ms
    client.session_timeout = session_timeout_ms
    apply_asyncua_generated_type_compatibility_patch()
    return client


def _is_subtyped_number(uatype: object) -> bool:
    """Checks if a data field represents an abstract numeric type."""
    resolved, _is_optional = ua_binary.resolve_uatype(uatype)
    if resolved is uatypes.Number:
        return True
    return get_origin(resolved) is Annotated and get_args(resolved)[:1] == (uatypes.Number,)


def _serialize_subtyped_number(value: object) -> bytes:
    """Encodes a numeric value into standard binary Variant format."""
    variant = value if isinstance(value, ua_binary.ua.Variant) else ua_binary.ua.Variant(value)
    return ua_binary.variant_to_binary(variant)


def apply_asyncua_generated_type_compatibility_patch() -> None:
    """Fix an asyncua 2.0.1 issue where abstract numeric fields in custom IJT types
    (like SignalDataType.SignalValue) were decoded with the wrong format,
    causing byte misalignment and NotEnoughData errors on complex trace arrays.
    """
    if getattr(ua_binary.create_type_serializer, _TYPE_SERIALIZER_PATCHED_ATTR, False):
        return

    original_create_type_serializer = ua_binary.create_type_serializer
    original_create_type_deserializer = ua_binary._create_type_deserializer
    original_create_dataclass_deserializer = ua_binary._create_dataclass_deserializer

    def _patched_get_safe_type_hints(cls: type, extra_ns: dict[str, object] | None = None):
        localns = {key: value for key, value in cls.__dict__.items() if not isinstance(value, property)}
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
            return ua_binary.create_enum_deserializer(objtype)
        if issubclass(objtype, ua_binary.ua.UaUnion):
            return original_create_dataclass_deserializer(objtype)

        enc_count = 0
        resolved_fieldtypes = ua_binary.get_safe_type_hints(objtype, {"ua": ua_binary.ua})
        has_number_field = any(_is_subtyped_number(resolved_fieldtypes[field.name]) for field in fields(objtype))
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

    setattr(_patched_create_type_serializer, "_ijt_number_serializer_patched", True)
    ua_binary.get_safe_type_hints = _patched_get_safe_type_hints  # type: ignore[assignment]
    ua_binary.create_type_serializer = _patched_create_type_serializer  # type: ignore[assignment]
    ua_binary._create_type_deserializer = _patched_create_type_deserializer  # type: ignore[assignment]
    ua_binary._create_dataclass_deserializer = _patched_create_dataclass_deserializer  # type: ignore[assignment]
    logger.debug("Applied asyncua subtype serializer patch for IJT structures")


patch_asyncua_subtype_serializer = apply_asyncua_generated_type_compatibility_patch


async def load_ijt_type_definitions(client: Client) -> None:
    """Tells the OPC UA client to read the server's data dictionary so custom structures unpack into Python objects."""
    res = client.load_data_type_definitions()
    if asyncio.iscoroutine(res):
        await res


async def is_client_connected(client: Client | None) -> bool:
    """Checks whether the client is actively connected and its session is open."""
    if client is None:
        return False
    try:
        target = getattr(client, "aio_obj", client)
        ua_client = getattr(target, "uaclient", None)
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
    except Exception:
        return False


async def disconnect_client(client: Client | None, settle_delay: float = DISCONNECT_SETTLE_DELAY_S) -> None:
    """Disconnects an OPC UA client and pauses briefly to let the server release the session,
    reducing the risk of 'BadTooManySessions' during rapid reconnect loops.
    """
    if client is None:
        return
    try:
        res = client.disconnect()
        if asyncio.iscoroutine(res):
            await res
    except Exception as exc:
        logger.debug(f"Client disconnect cleanup notice: {exc}")
    finally:
        if settle_delay > 0:
            await asyncio.sleep(settle_delay)
