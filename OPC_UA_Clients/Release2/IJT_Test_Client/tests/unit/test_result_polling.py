"""
Unit tests for helpers/result_polling.py.

The polling helper must:

  - return immediately when the new ResultId is already published;
  - keep re-reading while the server is still working, and succeed as soon as
    the new ResultId appears (delayed change);
  - give up exactly at the caller's budget (timeout);
  - never mistake an empty/unreadable ResultId for a new result.

All timing is exercised on an injected virtual clock, so no test waits for real
wall-clock time.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from helpers.result_polling import (
    DEFAULT_POLL_INTERVAL_S,
    extract_result_id,
    poll_until_result_id_changes,
)


def _payload(result_id):
    """Result payload shaped like ResultDataType (ResultMetaData.ResultId)."""
    return SimpleNamespace(ResultMetaData=SimpleNamespace(ResultId=result_id))


class _VirtualClock:
    """Sleep hook that advances a fake monotonic clock instead of waiting."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    async def sleep(self, delay: float) -> None:
        self.slept.append(delay)
        self.now += delay

    def clock(self) -> float:
        return self.now


def _reader(payloads):
    """Async read callable yielding payloads in order, repeating the last one."""
    pending = list(payloads)

    async def read():
        return pending.pop(0) if len(pending) > 1 else pending[0]

    return read


class TestExtractResultId:
    def test_reads_nested_result_metadata(self):
        assert extract_result_id(_payload("RESULT-1")) == "RESULT-1"

    def test_reads_flat_result_metadata_object(self):
        assert extract_result_id(SimpleNamespace(ResultId="RESULT-2")) == "RESULT-2"

    def test_returns_empty_string_for_none(self):
        assert extract_result_id(None) == ""

    def test_returns_empty_string_when_metadata_is_none(self):
        assert extract_result_id(SimpleNamespace(ResultMetaData=None)) == ""

    def test_returns_empty_string_when_result_id_missing(self):
        assert extract_result_id(SimpleNamespace(ResultMetaData=SimpleNamespace())) == ""

    def test_stringifies_non_string_ids(self):
        assert extract_result_id(_payload(17)) == "17"


class TestPollUntilResultIdChanges:
    async def test_returns_immediately_when_already_changed(self):
        vc = _VirtualClock()
        outcome = await poll_until_result_id_changes(
            _reader([_payload("RESULT-2")]),
            "RESULT-1",
            timeout_s=60.0,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is True
        assert outcome.result_id == "RESULT-2"
        assert outcome.reads == 1
        assert outcome.elapsed_s == 0.0
        assert vc.slept == [], "no sleep may happen when the evidence is already there"

    async def test_delayed_change_succeeds_without_spending_the_whole_budget(self):
        vc = _VirtualClock()
        reader = _reader([_payload("RESULT-1"), _payload("RESULT-1"), _payload("RESULT-3")])
        outcome = await poll_until_result_id_changes(
            reader,
            "RESULT-1",
            timeout_s=60.0,
            poll_interval_s=0.5,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is True
        assert outcome.result_id == "RESULT-3"
        assert outcome.reads == 3
        assert vc.slept == [0.5, 0.5]
        assert outcome.elapsed_s == 1.0
        assert outcome.elapsed_s < outcome.timeout_s

    async def test_timeout_reports_no_change_after_the_full_budget(self):
        vc = _VirtualClock()
        outcome = await poll_until_result_id_changes(
            _reader([_payload("RESULT-1")]),
            "RESULT-1",
            timeout_s=2.0,
            poll_interval_s=0.5,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is False
        assert outcome.result_id == "RESULT-1"
        assert outcome.elapsed_s == pytest.approx(2.0)
        assert sum(vc.slept) == pytest.approx(2.0)
        assert outcome.reads == 5

    async def test_last_sleep_never_overshoots_the_deadline(self):
        vc = _VirtualClock()
        await poll_until_result_id_changes(
            _reader([_payload("RESULT-1")]),
            "RESULT-1",
            timeout_s=1.1,
            poll_interval_s=0.5,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert vc.slept == [0.5, 0.5, pytest.approx(0.1)]

    async def test_zero_budget_reads_once_and_never_sleeps(self):
        vc = _VirtualClock()
        outcome = await poll_until_result_id_changes(
            _reader([_payload("RESULT-1")]),
            "RESULT-1",
            timeout_s=0.0,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is False
        assert outcome.reads == 1
        assert vc.slept == []

    async def test_empty_result_id_is_never_treated_as_a_change(self):
        vc = _VirtualClock()
        outcome = await poll_until_result_id_changes(
            _reader([None]),
            "RESULT-1",
            timeout_s=1.0,
            poll_interval_s=0.5,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is False
        assert outcome.result_id == ""
        assert outcome.value is None

    async def test_empty_baseline_accepts_the_first_non_empty_id(self):
        vc = _VirtualClock()
        outcome = await poll_until_result_id_changes(
            _reader([None, _payload("RESULT-9")]),
            "",
            timeout_s=10.0,
            poll_interval_s=0.5,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert outcome.changed is True
        assert outcome.result_id == "RESULT-9"
        assert outcome.baseline_id == ""

    async def test_read_errors_propagate_to_the_caller(self):
        async def read():
            raise RuntimeError("connection lost")

        with pytest.raises(RuntimeError, match="connection lost"):
            await poll_until_result_id_changes(read, "RESULT-1", timeout_s=1.0)

    async def test_default_interval_is_used_when_not_overridden(self):
        vc = _VirtualClock()
        await poll_until_result_id_changes(
            _reader([_payload("RESULT-1")]),
            "RESULT-1",
            timeout_s=DEFAULT_POLL_INTERVAL_S,
            sleep=vc.sleep,
            clock=vc.clock,
        )
        assert vc.slept == [pytest.approx(DEFAULT_POLL_INTERVAL_S)]

    async def test_uses_real_asyncio_sleep_and_clock_by_default(self):
        """The production path needs no injection — a tiny budget proves it runs."""
        outcome = await poll_until_result_id_changes(
            _reader([_payload("RESULT-1")]),
            "RESULT-1",
            timeout_s=0.01,
            poll_interval_s=0.005,
        )
        assert outcome.changed is False
        assert outcome.reads >= 2
        assert outcome.elapsed_s > 0
