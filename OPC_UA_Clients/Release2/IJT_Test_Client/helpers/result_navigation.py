"""
Reusable traversal helpers for decoded IJT result payloads.

The Test Client receives result structures through asyncua, which may wrap
nested ExtensionObjects in ua.Variant.  These helpers keep that unwrap and
result-content traversal logic in one place for result, trace, and engineering
unit checks.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from asyncua import ua


def unwrap_variant(item: Any) -> Any:
    """Unwrap one or two asyncua Variant containers, returning the inner value."""
    try:
        if isinstance(item, ua.Variant):
            inner = item.Value
            if inner is None:
                return None
            if isinstance(inner, ua.Variant):
                inner = inner.Value
            return inner
    except Exception:  # noqa: BLE001 - defensive against malformed asyncua payloads
        return item
    return item


def unwrap_sequence(items: Any) -> list[Any]:
    """Return a list with Variant wrappers removed from sequence entries."""
    if not isinstance(items, (list, tuple)):
        return []
    result = []
    for item in items:
        value = unwrap_variant(item)
        if value is not None:
            result.append(value)
    return result


def _looks_like_joining_result(item: Any) -> bool:
    return any(hasattr(item, attr) for attr in ("OverallResultValues", "StepResults", "Trace"))


def iter_joining_results(result_data: Any) -> Iterable[tuple[str, Any]]:
    """
    Yield ``(path, joining_result_like_object)`` from a result and nested
    ``ResultContent`` values.
    """
    root = unwrap_variant(result_data)
    pending: list[tuple[str, Any]] = [("$", root)]
    visited: set[int] = set()

    while pending:
        path, raw = pending.pop(0)
        item = unwrap_variant(raw)
        if item is None:
            continue
        marker = id(item)
        if marker in visited:
            continue
        visited.add(marker)

        if _looks_like_joining_result(item):
            yield path, item

        content = getattr(item, "ResultContent", None)
        if isinstance(content, (list, tuple)):
            pending.extend((f"{path}.ResultContent[{i}]", child) for i, child in enumerate(content))


def _extend_unwrapped(target: list[Any], values: Any) -> None:
    if isinstance(values, (list, tuple)):
        target.extend(value for value in (unwrap_variant(v) for v in values) if value is not None)


def collect_result_values(result_data: Any) -> list[Any]:
    """
    Return ResultValue-like entries from metadata, joining results, and nested
    step results.
    """
    values: list[Any] = []

    meta = getattr(unwrap_variant(result_data), "ResultMetaData", None)
    if meta is not None:
        _extend_unwrapped(values, getattr(unwrap_variant(meta), "OverallResultValues", None))

    for _, joining_result in iter_joining_results(result_data):
        _extend_unwrapped(values, getattr(joining_result, "OverallResultValues", None))
        _extend_unwrapped(values, getattr(joining_result, "ResultValues", None))

        for step in unwrap_sequence(getattr(joining_result, "StepResults", None)):
            _extend_unwrapped(values, getattr(step, "StepResultValues", None))

    return values


def collect_trace_entries(result_data: Any) -> list[tuple[str, Any]]:
    """Return ``(path, trace)`` entries for joining results with a non-null Trace."""
    traces: list[tuple[str, Any]] = []
    for path, joining_result in iter_joining_results(result_data):
        trace = unwrap_variant(getattr(joining_result, "Trace", None))
        if trace is not None:
            traces.append((path, trace))
    return traces


def collect_trace_entries_from_content(content: Any) -> list[tuple[int, Any]]:
    """
    Return ``(content_index, trace)`` entries for direct ResultContent children.

    Some trace tests need the original integer index to cross-reference the
    trace-bearing joining result with sibling StepResults.
    """
    if not isinstance(content, (list, tuple)):
        return []
    traces: list[tuple[int, Any]] = []
    for index, raw_joining_result in enumerate(content):
        joining_result = unwrap_variant(raw_joining_result)
        if joining_result is None:
            continue
        trace = unwrap_variant(getattr(joining_result, "Trace", None))
        if trace is not None:
            traces.append((index, trace))
    return traces
