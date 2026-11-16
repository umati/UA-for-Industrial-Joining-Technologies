"""Exact counter response and before/after evidence checks shared by execution routes."""

from __future__ import annotations

import uuid
from collections.abc import Set as AbstractSet
from typing import Any

from asyncua import ua

from helpers.method_caller import MethodCallResult
from helpers.result_collector import get_result_id, is_partial, unwrap_result


class CounterEvidenceUnavailable(ValueError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.reason_code = reason_code


# OPC 40450-1 Section 7.4 Table 55 defined negative business statuses (< 0 application-specific, 1..5 standard).
_IJT_INPUT_REJECTION_STATUSES = frozenset({1, 2, 3, 4, 5})
_UNKNOWN_PROCESS_STATUSES = frozenset({1, 4, 5})


def counter_negative_rejected(result: MethodCallResult) -> bool:
    """Return True when a negative counter probe returned a defined OPC 40450-1 rejection."""
    if not result.service_good_confirmed:
        return False
    if result.method_status_code is None or not ua.StatusCode(result.method_status_code).is_uncertain():
        return False
    outputs = result.output_list
    if len(outputs) != 2:
        return False
    status, message = outputs
    if isinstance(status, bool) or not isinstance(status, int):
        return False
    if status >= 0 and status not in _IJT_INPUT_REJECTION_STATUSES:
        return False
    return isinstance(message, ua.LocalizedText) and bool(message.Text)


def require_negative_counter_response(
    result: MethodCallResult,
    expected_status: int | AbstractSet[int],
) -> None:
    if not result.service_good_confirmed:
        raise CounterEvidenceUnavailable(
            "counter_response_unavailable", f"Call service was not confirmed Good: {result.error}"
        )
    assert result.method_status_code is not None and ua.StatusCode(result.method_status_code).is_uncertain(), (
        f"Expected Uncertain method status, got {result.method_status_code}"
    )
    outputs = result.output_list
    assert len(outputs) == 2, f"Expected Status and StatusMessage, got {outputs!r}"
    allowed = {expected_status} if isinstance(expected_status, int) else set(expected_status)
    assert isinstance(outputs[0], int) and not isinstance(outputs[0], bool) and outputs[0] in allowed, (
        f"Expected business Status in {sorted(allowed) if len(allowed) > 1 else next(iter(allowed))}, "
        f"got {outputs[0]!r}"
    )
    assert isinstance(outputs[1], ua.LocalizedText) and bool(outputs[1].Text), (
        f"Expected explanatory LocalizedText StatusMessage, got {outputs[1]!r}"
    )


def counter_negative_arguments(
    piu: str,
    identification: Any,
    known_process_ids: tuple[str, ...],
    exposed_pius: frozenset[str],
    kind: str,
) -> tuple[tuple[Any, ...], int | frozenset[int]]:
    """Prove an identifier is outside the current scope before a negative mutation probe."""
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable

    if kind not in {"invalid_piu", "unknown_process"}:
        raise ValueError(f"Unknown counter obligation: {kind}")
    if piu not in exposed_pius or str(identification.JoiningProcessId) not in known_process_ids:
        raise WorkflowEvidenceUnavailable(
            "A currently advertised valid counter-process identity is required.",
            "counter_negative_precondition_unproven",
            "blocked",
            "counter_negative",
        )
    identifier = f"ijt-test-absent-{uuid.uuid4().hex}"
    if kind == "invalid_piu":
        invalid_piu = f"urn:{identifier}"
        if invalid_piu in exposed_pius:
            raise WorkflowEvidenceUnavailable(
                "Generated PIU is exposed by the server.",
                "invalid_piu_not_proven",
                "blocked",
                "counter_negative",
            )
        return (
            ua.Variant(invalid_piu, ua.VariantType.String),
            ua.Variant(identification, ua.VariantType.ExtensionObject),
            ua.Variant(1, ua.VariantType.UInt32),
        ), 2
    if identifier in known_process_ids:
        raise WorkflowEvidenceUnavailable(
            "Generated process ID is advertised by the server.",
            "unknown_process_not_proven",
            "blocked",
            "counter_negative",
        )
    unknown = type(identification)()
    unknown.JoiningProcessId = identifier
    unknown.JoiningProcessOriginId = ""
    unknown.SelectionName = ""
    return (
        ua.Variant(piu, ua.VariantType.String),
        ua.Variant(unknown, ua.VariantType.ExtensionObject),
        ua.Variant(1, ua.VariantType.UInt32),
    ), _UNKNOWN_PROCESS_STATUSES


def counter_snapshot(result: Any, *, counter_name: str = "", counter_type: int = -1) -> dict[tuple[str, int], int]:
    counters = getattr(getattr(result, "ResultMetaData", None), "ResultCounters", None) or ()
    values: dict[tuple[str, int], int] = {}
    for raw in counters:
        counter = unwrap_result(raw)
        kind = unwrap_result(getattr(counter, "CounterType", None))
        value = unwrap_result(getattr(counter, "CounterValue", None))
        if isinstance(kind, bool) or not isinstance(kind, int) or isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("CounterType and CounterValue must be integers")
        key = (str(unwrap_result(getattr(counter, "Name", "")) or ""), kind)
        if (counter_name and key[0] != counter_name) or (counter_type != -1 and kind != counter_type):
            continue
        if key in values:
            raise CounterEvidenceUnavailable(
                "counter_identity_unproven", "Counter identities are ambiguous within the process result"
            )
        values[key] = value
    return values


def _child_result_ids(result: Any) -> tuple[str, ...]:
    ids: list[str] = []
    for field_name in ("ResultContent", "References"):
        values = getattr(result, field_name, None)
        if not isinstance(values, (list, tuple)):
            continue
        for raw in values:
            child_id = get_result_id(unwrap_result(raw))
            if child_id:
                ids.append(child_id)
    return tuple(ids)


def _has_partial_progression(before: Any, after: Any) -> bool:
    """Return True when after is a newer emission of an in-progress partial consolidated result."""
    if before is after or not is_partial(before):
        return False
    if not is_partial(after):
        return True
    if _child_result_ids(after) != _child_result_ids(before):
        return True
    before_meta = getattr(before, "ResultMetaData", None)
    after_meta = getattr(after, "ResultMetaData", None)
    before_seq = unwrap_result(getattr(before_meta, "SequenceNumber", None))
    after_seq = unwrap_result(getattr(after_meta, "SequenceNumber", None))
    if (
        isinstance(before_seq, int)
        and not isinstance(before_seq, bool)
        and isinstance(after_seq, int)
        and not isinstance(after_seq, bool)
        and after_seq > before_seq
    ):
        return True
    before_time = unwrap_result(getattr(before_meta, "CreationTime", None))
    after_time = unwrap_result(getattr(after_meta, "CreationTime", None))
    return bool(before_time is not None and after_time is not None and after_time > before_time)


def require_counter_delta(
    before: Any, after: Any, increment: int, *, counter_name: str = "", counter_type: int = -1
) -> None:
    """Do not infer counter semantics from a vendor-specific CounterType value."""
    before_values = counter_snapshot(before, counter_name=counter_name, counter_type=counter_type)
    after_values = counter_snapshot(after, counter_name=counter_name, counter_type=counter_type)
    if len(before_values) != 1 or before_values.keys() != after_values.keys():
        raise CounterEvidenceUnavailable(
            "counter_identity_unproven",
            "One unchanged joining-process counter identity is required for delta evidence.",
        )
    before_id = get_result_id(before)
    after_id = get_result_id(after)
    if not before_id or not after_id or (before_id == after_id and not _has_partial_progression(before, after)):
        raise CounterEvidenceUnavailable(
            "counter_freshness_unproven",
            "Distinct before/after ResultIds are required unless updating an in-progress partial result.",
        )
    key = next(iter(before_values))
    before_value = before_values[key]
    after_value = after_values[key]
    observed_delta = after_value - before_value
    assert observed_delta == increment, (
        f"Expected counter delta {increment} for {key!r}, observed {observed_delta} "
        f"(before={before_value}, after={after_value}, ResultId={before_id!r}->{after_id!r})"
    )
