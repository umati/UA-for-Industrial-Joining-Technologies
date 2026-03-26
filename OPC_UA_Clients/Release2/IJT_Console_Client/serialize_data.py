from datetime import datetime as std_datetime
from typing import Any

from ijt_logger import ijt_log

try:
    import orjson
except Exception:
    orjson = None


def _json_dumps(obj: Any) -> str:
    if orjson is not None:
        return orjson.dumps(obj).decode("utf-8")

    import json

    return json.dumps(obj, ensure_ascii=False)


def is_instance_of_user_class(obj: Any) -> bool:
    return str(type(obj)).startswith("<class") and (
        hasattr(obj, "__weakref__") or hasattr(obj, "__dict__")
    )


def serialize_value(value: Any) -> Any:
    if is_instance_of_user_class(value):
        return serialize_class_instance_as_dict(value)
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_value(item) for item in value]
    if isinstance(value, std_datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__slots__"):
        result = {"pythonclass": type(value).__name__}
        for slot in getattr(value, "__slots__", []):
            if slot == "_freeze":
                continue
            try:
                result[slot] = serialize_value(getattr(value, slot))
            except Exception as exc:  # nosec B112 — slot may be unreadable; skip it gracefully
                ijt_log.debug("Skipping unreadable slot '%s': %s", slot, exc)
                continue
        return result
    return str(value)


def serialize_class_instance_as_dict(obj: Any) -> dict:
    result = {"pythonclass": type(obj).__name__}
    if hasattr(obj, "__dict__"):
        for key, value in obj.__dict__.items():
            if key != "_freeze":
                result[key] = serialize_value(value)
    elif hasattr(obj, "__slots__"):
        for slot in getattr(obj, "__slots__", []):
            try:
                if slot != "_freeze":
                    result[slot] = serialize_value(getattr(obj, slot))
            except Exception as exc:  # nosec B112 — slot may be unreadable; skip it gracefully
                ijt_log.debug("Skipping unreadable slot '%s': %s", slot, exc)
                continue
    return result


def serialize_full_event(value: Any) -> Any:
    return serialize_value(value)


def serialize_tuple(list_of_tuples: list[tuple[str, Any]]) -> str:
    try:
        data = {key: serialize_value(val) for key, val in list_of_tuples}
        return _json_dumps(data)
    except Exception as exc:
        ijt_log.error(f"Failed to serialize tuple: {exc}")
        return "{}"

