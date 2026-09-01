"""
Mock-driven checks of the result-evidence semantics in specification_tests/.

These execute the real specification test coroutines against mocked OPC UA
objects (no server) to prove the Aug-31 regression is fixed:

  an ACCEPTED remote start (``TriggerOutcome.triggered=True``) followed by no new
  result must FAIL, not silently skip.

Manual/observe-only triggers still return ``triggered=False`` with a reason and
therefore still produce an explicit skip — that path is asserted too.
"""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helpers import result_polling as _polling
from helpers.namespaces import NS_IJT_BASE, NS_MACH_RESULT
from helpers.trigger import TriggerOutcome

_PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
_access: Any = importlib.import_module("specification_tests.test_result_access")

# pytest.skip() raises a BaseException subclass, so it must be named explicitly.
_SKIPPED = pytest.skip.Exception

_NS = {NS_MACH_RESULT: 4, NS_IJT_BASE: 3}


@contextmanager
def _virtual_clock():
    """Run bounded polling on a virtual clock — no real waiting in unit tests.

    Sleeps advance the fake clock instead of the wall clock, so a 60-second
    poll budget is exercised in full without the test taking 60 seconds.
    """
    state = {"now": 0.0, "slept": 0.0}

    async def fake_sleep(delay: float) -> None:
        state["now"] += delay
        state["slept"] += delay

    def fake_clock() -> float:
        return state["now"]

    with (
        patch.object(_polling, "_default_sleep", fake_sleep),
        patch.object(_polling, "_default_clock", fake_clock),
    ):
        yield state


def _meta_node(result_ids: list[str]) -> MagicMock:
    """Node whose ResultMetaData reads return the given ResultIds in order.

    The final value repeats for every further read, so a bounded poll can
    re-read the node as often as its budget allows.
    """
    values = [MagicMock(ResultMetaData=MagicMock(ResultId=rid)) for rid in result_ids]
    pending = list(values)

    async def read_value():
        return pending.pop(0) if len(pending) > 1 else pending[0]

    node = MagicMock()
    node.read_value = AsyncMock(side_effect=read_value)
    return node


def _accepted_trigger() -> MagicMock:
    trigger = MagicMock()
    trigger.is_simulator = False
    trigger.active_result_timeout_s = 60.0
    trigger.passive_observation_timeout_s = 5.0
    trigger.trigger_single = AsyncMock(return_value=TriggerOutcome(triggered=True, method="StartSelectedJoining"))
    return trigger


def _manual_trigger() -> MagicMock:
    trigger = MagicMock()
    trigger.is_simulator = False
    trigger.active_result_timeout_s = 5.0
    trigger.passive_observation_timeout_s = 5.0
    trigger.trigger_single = AsyncMock(
        return_value=TriggerOutcome(
            triggered=False,
            skip_reason="Manual trigger required for single result.",
            method="ManualTrigger",
        )
    )
    return trigger


class TestLastResultMetadataAfterTrigger:
    def _patches(self, meta_node):
        return (
            patch.object(_access, "_get_result_management", new=AsyncMock(return_value=MagicMock())),
            patch.object(_access, "_find_result_var", new=AsyncMock(return_value=MagicMock())),
            patch.object(
                _access,
                "find_child_by_browse_name",
                new=AsyncMock(side_effect=[MagicMock(), meta_node]),
            ),
        )

    async def test_accepted_start_without_new_result_fails(self):
        """Regression guard: this must NOT be downgraded to a skip."""
        meta_node = _meta_node(["RESULT-1", "RESULT-1"])
        p1, p2, p3 = self._patches(meta_node)
        with (
            _virtual_clock() as clock,
            p1,
            p2,
            p3,
            pytest.raises(AssertionError, match="did not change after an accepted trigger"),
        ):
            await _access.test_last_result_metadata_updated_after_trigger(MagicMock(), _accepted_trigger(), _NS)
        # The whole 60 s budget was exercised on the virtual clock only.
        assert clock["slept"] >= 60.0

    async def test_accepted_start_with_new_result_passes(self):
        meta_node = _meta_node(["RESULT-1", "RESULT-2"])
        p1, p2, p3 = self._patches(meta_node)
        with _virtual_clock(), p1, p2, p3:
            await _access.test_last_result_metadata_updated_after_trigger(MagicMock(), _accepted_trigger(), _NS)

    async def test_result_published_late_still_passes_without_waiting_the_full_budget(self):
        """A ResultId that only appears after a few polls must pass, not time out."""
        meta_node = _meta_node(["RESULT-1", "RESULT-1", "RESULT-1", "RESULT-2"])
        p1, p2, p3 = self._patches(meta_node)
        with _virtual_clock() as clock, p1, p2, p3:
            await _access.test_last_result_metadata_updated_after_trigger(MagicMock(), _accepted_trigger(), _NS)
        assert 0 < clock["slept"] < 60.0, "poll must return as soon as the new ResultId appears"
        assert meta_node.read_value.await_count == 4

    async def test_manual_trigger_still_skips_with_its_reason(self):
        meta_node = _meta_node(["RESULT-1", "RESULT-1"])
        p1, p2, p3 = self._patches(meta_node)
        with _virtual_clock() as clock, p1, p2, p3, pytest.raises(_SKIPPED) as exc_info:
            await _access.test_last_result_metadata_updated_after_trigger(MagicMock(), _manual_trigger(), _NS)
        assert "Manual trigger required" in str(exc_info.value)
        # Manual/observe triggers skip before any polling starts.
        assert clock["slept"] == 0.0
        assert meta_node.read_value.await_count == 1


class TestGetLatestResultAfterSecondTrigger:
    def _result(self, result_id: str) -> MagicMock:
        return MagicMock(ResultMetaData=MagicMock(ResultId=result_id))

    def _latest_reader(self, result_ids: list[str]) -> AsyncMock:
        """GetLatestResult stub returning the given ResultIds, last one repeating."""
        pending = [("h", self._result(rid)) for rid in result_ids]

        async def call(*_args, **_kwargs):
            return pending.pop(0) if len(pending) > 1 else pending[0]

        return AsyncMock(side_effect=call)

    async def test_accepted_second_start_returning_same_id_fails(self):
        rm = MagicMock()
        with (
            _virtual_clock() as clock,
            patch.object(
                _access,
                "_trigger_single_and_get_latest",
                new=AsyncMock(return_value=(rm, "h1", self._result("RESULT-1"))),
            ),
            patch.object(_access, "_call_get_latest_result", new=self._latest_reader(["RESULT-1"])),
            pytest.raises(AssertionError, match="same ResultId after an accepted new trigger"),
        ):
            await _access.test_get_latest_result_returns_new_result_after_second_trigger(
                MagicMock(), _accepted_trigger(), _NS
            )
        assert clock["slept"] >= 60.0

    async def test_accepted_second_start_returning_new_id_passes(self):
        rm = MagicMock()
        with (
            _virtual_clock() as clock,
            patch.object(
                _access,
                "_trigger_single_and_get_latest",
                new=AsyncMock(return_value=(rm, "h1", self._result("RESULT-1"))),
            ),
            patch.object(_access, "_call_get_latest_result", new=self._latest_reader(["RESULT-2"])),
        ):
            await _access.test_get_latest_result_returns_new_result_after_second_trigger(
                MagicMock(), _accepted_trigger(), _NS
            )
        assert clock["slept"] == 0.0, "an immediately available new result must not sleep at all"

    async def test_late_second_result_passes_without_waiting_the_full_budget(self):
        rm = MagicMock()
        reader = self._latest_reader(["RESULT-1", "RESULT-1", "RESULT-2"])
        with (
            _virtual_clock() as clock,
            patch.object(
                _access,
                "_trigger_single_and_get_latest",
                new=AsyncMock(return_value=(rm, "h1", self._result("RESULT-1"))),
            ),
            patch.object(_access, "_call_get_latest_result", new=reader),
        ):
            await _access.test_get_latest_result_returns_new_result_after_second_trigger(
                MagicMock(), _accepted_trigger(), _NS
            )
        assert 0 < clock["slept"] < 60.0
        assert reader.await_count == 3

    async def test_manual_trigger_still_skips(self):
        rm = MagicMock()
        reader = self._latest_reader(["RESULT-1"])
        with (
            _virtual_clock() as clock,
            patch.object(
                _access,
                "_trigger_single_and_get_latest",
                new=AsyncMock(return_value=(rm, "h1", self._result("RESULT-1"))),
            ),
            patch.object(_access, "_call_get_latest_result", new=reader),
            pytest.raises(_SKIPPED) as exc_info,
        ):
            await _access.test_get_latest_result_returns_new_result_after_second_trigger(
                MagicMock(), _manual_trigger(), _NS
            )
        assert "Manual trigger required" in str(exc_info.value)
        # Manual/observe triggers skip before any polling starts.
        assert clock["slept"] == 0.0
        assert reader.await_count == 0


# ---------------------------------------------------------------------------
# Result-ready event evidence (specification_tests/test_single_result_data.py)
# ---------------------------------------------------------------------------

_single: Any = importlib.import_module("specification_tests.test_single_result_data")


def _event_collector(events: list) -> MagicMock:
    collector = MagicMock()
    collector.__aenter__ = AsyncMock(return_value=collector)
    collector.__aexit__ = AsyncMock(return_value=None)
    collector.subscribe = AsyncMock(return_value=None)
    collector.collect = AsyncMock(return_value=events)
    return collector


class TestResultReadyEventEvidence:
    async def test_accepted_start_without_event_fails(self):
        """Regression guard: an accepted remote start with no result-ready event
        must FAIL rather than skip."""
        collector = _event_collector([])
        with (
            patch.object(_single, "EventCollector", return_value=collector),
            pytest.raises(AssertionError, match="after an accepted result trigger"),
        ):
            await _single.test_result_ready_event_received_after_result_trigger(MagicMock(), _accepted_trigger(), _NS)

    async def test_accepted_start_with_event_passes(self):
        collector = _event_collector([MagicMock()])
        with patch.object(_single, "EventCollector", return_value=collector):
            await _single.test_result_ready_event_received_after_result_trigger(MagicMock(), _accepted_trigger(), _NS)

    async def test_manual_trigger_still_skips(self):
        collector = _event_collector([])
        with (
            patch.object(_single, "EventCollector", return_value=collector),
            pytest.raises(_SKIPPED) as exc_info,
        ):
            await _single.test_result_ready_event_received_after_result_trigger(MagicMock(), _manual_trigger(), _NS)
        assert "Manual trigger required" in str(exc_info.value)

    async def test_wait_uses_the_active_result_budget_not_a_hardcoded_fallback(self):
        """The removed `getattr(trigger, "wait_timeout", 10.0)` always yielded 10s.
        The configured active budget must be used instead."""
        collector = _event_collector([MagicMock()])
        trigger = _accepted_trigger()
        trigger.active_result_timeout_s = 75.0
        trigger.passive_observation_timeout_s = 5.0
        with patch.object(_single, "EventCollector", return_value=collector):
            await _single.test_result_ready_event_received_after_result_trigger(MagicMock(), trigger, _NS)
        assert collector.collect.await_args.kwargs["timeout_s"] == 75.0
