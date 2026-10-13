"""Resolve explicit joining-process selectors against a freshly discovered list."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_ID_FIELDS = ("id", "JoiningProcessId", "JoiningProcessIdentification", "Id")
_ORIGIN_FIELDS = ("origin_id", "JoiningProcessOriginId", "JoiningProcessIdentificationOrigin")


def _value(process: Any, *names: str) -> str:
    for name in names:
        value = process.get(name) if isinstance(process, Mapping) else getattr(process, name, None)
        is_mock = hasattr(value, "_mock_name") or type(value).__name__ == "MagicMock"
        if value is not None and not is_mock and str(value):
            return str(value)
    return ""


def selection_names(process: Any) -> set[str]:
    direct = _value(process, "selection_name", "SelectionName")
    names = {direct} if direct else set()
    associated = (
        process.get("AssociatedEntities", ())
        if isinstance(process, Mapping)
        else getattr(process, "AssociatedEntities", ())
    )
    for entity in associated or ():
        entity_name = _value(entity, "Name")
        entity_id = _value(entity, "EntityId")
        if entity_name == "SelectionName" and entity_id:
            names.add(entity_id)
    return names


def selector_value(selector: Any, match_by: str | None = None) -> str:
    key = match_by or getattr(selector, "match_by", "joining_process_id")
    value = selector.get(key, "") if isinstance(selector, Mapping) else getattr(selector, key, "")
    return str(value or "").strip()


def process_matches(process: Any, selector: Any, match_by: str | None = None) -> bool:
    key = match_by or getattr(selector, "match_by", "joining_process_id")
    expected = selector_value(selector, key).casefold()
    if not expected:
        return False
    if key == "joining_process_id":
        actual_values = {_value(process, *_ID_FIELDS).strip().casefold()}
    elif key == "joining_process_origin_id":
        actual_values = {_value(process, *_ORIGIN_FIELDS).strip().casefold()}
    elif key == "selection_name":
        actual_values = {name.strip().casefold() for name in selection_names(process)}
    else:
        return False
    return expected in actual_values


def matching_processes(processes: list[Any], selector: Any, match_by: str | None = None) -> list[Any]:
    """Return all exact matches; callers must reject zero or ambiguous results."""
    return [process for process in processes if process_matches(process, selector, match_by)]
