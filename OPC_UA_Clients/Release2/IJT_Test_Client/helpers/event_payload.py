"""
Helpers for reading IJT event payload fields across asyncua decode variants.
"""

from __future__ import annotations


def unwrap_variant(value):
    """Unwrap asyncua Variant containers used for nested ExtensionObjects."""
    return getattr(value, "Value", value)


def event_payload_field(event, field_name: str):
    """
    Read JoiningSystemEventContent fields across asyncua decoding variants.

    Supported representations:
      - event.<Field>
      - event.EventContent.<Field>
      - event.JoiningSystemEventContent.<Field>
      - event.__dict__['JoiningSystemEventContent/<Field>']
    """
    value = unwrap_variant(getattr(event, field_name, None))
    if value is not None:
        return value

    for content_name in ("EventContent", "JoiningSystemEventContent"):
        content = unwrap_variant(getattr(event, content_name, None))
        if content is not None:
            content_value = unwrap_variant(getattr(content, field_name, None))
            if content_value is not None:
                return content_value

    event_dict = getattr(event, "__dict__", {})
    slash_key = f"JoiningSystemEventContent/{field_name}"
    if slash_key in event_dict:
        return unwrap_variant(event_dict.get(slash_key))

    for nested_key in ("EventContent", "JoiningSystemEventContent"):
        nested = unwrap_variant(event_dict.get(nested_key))
        if nested is not None:
            nested_value = unwrap_variant(getattr(nested, field_name, None))
            if nested_value is not None:
                return nested_value

    return None
