"""Serialization helpers for converting asyncua objects to JSON-safe structures.

The functions in this module walk arbitrary Python objects (asyncua
extension-object instances, tuples, plain values, …) and produce nested
``dict``/``list`` structures that are safe to pass to :func:`json.dumps`.
"""

import json
from datetime import datetime as std_datetime
from typing import Any

from python.ijt_logger import ijt_log


def is_instance_of_class(cls: Any) -> bool:
    """Best-effort check for user-defined class instances."""
    # Keep backward-compatible behavior with previous serializer logic:
    # many asyncua objects were detected via __weakref__.
    return str(type(cls)).startswith("<class") and (
        hasattr(cls, "__weakref__") or hasattr(cls, "__dict__")
    )


def _to_jsonable(value: Any) -> Any:
    if is_instance_of_class(value):
        return serialize_class_instance_as_dict(value)
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, std_datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__slots__"):
        result = {"pythonclass": type(value).__name__}
        for slot in getattr(value, "__slots__", []):
            try:
                result[slot] = _to_jsonable(getattr(value, slot))
            except Exception as exc:
                ijt_log.debug("serialize: skipped slot '%s' on %s: %s", slot, type(value).__name__, exc)
                continue
        if len(result) > 1:
            return result
    return str(value)


def serialize_tuple(list_of_tuples: list[tuple[str, Any]]) -> str:
    """Serialize a zipped list of key/value tuples as JSON string."""
    return json.dumps({k: _to_jsonable(v) for k, v in list_of_tuples}, ensure_ascii=False)


def serialize_value(value: Any) -> str:
    """Serialize a value as JSON string."""
    return json.dumps(_to_jsonable(value), ensure_ascii=False)


def serialize_full_event(value: Any) -> Any:
    """Serialize recursively into JSON-compatible python types."""
    return _to_jsonable(value)


def serialize_class_instance_as_dict(obj: Any) -> dict:
    """Recursively convert a class instance to a JSON-serializable dict.

    Walks ``__dict__`` (for regular objects) or ``__slots__`` (for slotted
    objects) and converts each attribute value through :func:`_to_jsonable`.
    Attributes named ``"_freeze"`` are skipped.  Slot attributes that cannot
    be read are silently skipped with a ``DEBUG``-level log entry.

    Args:
        obj: Any Python object to serialize.

    Returns:
        A dict with a ``"pythonclass"`` key (the type name) plus one entry per
        serializable attribute.
    """
    result = {"pythonclass": type(obj).__name__}
    if hasattr(obj, "__dict__"):
        for key, value in obj.__dict__.items():
            if key != "_freeze":
                result[key] = _to_jsonable(value)
    elif hasattr(obj, "__slots__"):
        for slot in getattr(obj, "__slots__", []):
            try:
                if slot != "_freeze":
                    result[slot] = _to_jsonable(getattr(obj, slot))
            except Exception as exc:
                ijt_log.debug("serialize: skipped slot '%s' on %s: %s", slot, type(obj).__name__, exc)
                continue
    return result
