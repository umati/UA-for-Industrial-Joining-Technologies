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
from types import SimpleNamespace
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


class TestConfiguredAssociatedEntities:
    @staticmethod
    def _result(classification, entities=(), content=()):
        return SimpleNamespace(
            ResultMetaData=SimpleNamespace(Classification=classification, AssociatedEntities=list(entities)),
            ResultContent=list(content),
        )

    async def test_cached_single_content_enforces_required_sut_entities(self):
        from helpers.result_collector import collect_single_evidence
        from helpers.target_server_cu_config import AssociatedEntityExpectation
        from helpers.trigger import ExternalResultTrigger

        trigger = ExternalResultTrigger()
        trigger.associated_entity_expectations = (AssociatedEntityExpectation("single", required=("TOOL",)),)
        single = self._result(1)
        single.ResultMetaData.ResultId = "single"
        single.ResultMetaData.IsPartial = False
        single.ResultMetaData.ResultState = 1
        progression = SimpleNamespace(classification=1, final_result=single, all_results=(single,), is_complete=True)
        with (
            patch.object(trigger, "get_reusable_progression", new=AsyncMock(return_value=progression), create=True),
            pytest.raises(AssertionError, match="Missing configured required entity types"),
        ):
            await collect_single_evidence(None, trigger, {}, 0)

    def test_optional_counter_tool_is_not_an_ownership_waiver(self):
        from helpers.result_validator import assert_associated_entity_expectations
        from helpers.target_server_cu_config import AssociatedEntityExpectation
        from helpers.target_server_triggers import StartSelectedJoiningResultTrigger

        result = self._result(
            6,
            [
                SimpleNamespace(EntityType=41, EntityId="station"),
                SimpleNamespace(EntityType=28, EntityId="job"),
            ],
        )
        rules = (AssociatedEntityExpectation("intervention", context="counter_intervention", optional=("TOOL",)),)
        assert_associated_entity_expectations(result, rules, context="counter_intervention")
        assert not StartSelectedJoiningResultTrigger._result_matches_context(result, "tool", "job")

    @pytest.mark.parametrize("entity_id", ["tool", ""])
    def test_present_optional_entity_still_requires_valid_identity(self, entity_id):
        from helpers.result_validator import assert_associated_entity_expectations
        from helpers.target_server_cu_config import AssociatedEntityExpectation

        result = self._result(6, [SimpleNamespace(EntityType=4, EntityId=entity_id)])
        rules = (AssociatedEntityExpectation("intervention", optional=("TOOL",)),)
        if entity_id:
            assert_associated_entity_expectations(result, rules)
        else:
            with pytest.raises(AssertionError, match="non-empty EntityId"):
                assert_associated_entity_expectations(result, rules)

    @pytest.mark.parametrize("present_type", [27, 26, 6], ids=["program", "joining_process", "memory_only"])
    def test_one_of_requirements_allow_extra_entities(self, present_type):
        from helpers.result_validator import assert_associated_entity_expectations
        from helpers.target_server_cu_config import AssociatedEntityExpectation

        result = self._result(
            1,
            [SimpleNamespace(EntityType=present_type, EntityId="id"), SimpleNamespace(EntityType=41, EntityId="vs")],
        )
        rules = (AssociatedEntityExpectation("single", at_least_one_of=("PROGRAM", "JOINING_PROCESS")),)
        if present_type == 6:
            with pytest.raises(AssertionError, match="at least one entity type"):
                assert_associated_entity_expectations(result, rules)
        else:
            assert_associated_entity_expectations(result, rules)

    def test_rules_distinguish_context_and_do_not_require_identities_in_child_stubs(self):
        from helpers.result_validator import assert_associated_entity_expectations
        from helpers.target_server_cu_config import AssociatedEntityExpectation

        rules = (AssociatedEntityExpectation("single", context="joining", required=("TOOL",)),)
        child = self._result(1)
        batch = self._result(3, content=[child])
        assert_associated_entity_expectations(batch, rules)
        assert_associated_entity_expectations(child, rules, context="counter_intervention")
        child.ResultContent = [SimpleNamespace(OverallResultValues=[])]
        with pytest.raises(AssertionError, match="Missing configured required"):
            assert_associated_entity_expectations(batch, rules)


class TestConsolidatedMeasurementEvidence:
    @staticmethod
    def _single(result_id, *, quantity=3, final=True):
        value = SimpleNamespace(ValueTag=1 if final else 8, PhysicalQuantity=quantity)
        payload = SimpleNamespace(
            OverallResultValues=[value],
            StepResults=[SimpleNamespace(StepResultValues=[value])],
        )
        return SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId=result_id, Classification=1),
            ResultContent=[payload],
        )

    @staticmethod
    def _stub(result_id, classification=1):
        return SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId=result_id, Classification=classification),
            ResultContent=[],
        )

    @pytest.mark.parametrize("references", [False, True], ids=["inline", "referenced"])
    @pytest.mark.parametrize(
        "consumer",
        [
            "test_batch_result_sub_results_contain_final_tagged_values",
            "test_single_result_has_final_tagged_torque_or_angle_value",
            "test_each_step_has_at_most_one_final_per_physical_quantity",
            "test_final_tag_present_in_consecutive_results",
        ],
    )
    async def test_measurement_checks_accept_exact_referenced_or_inline_content(self, references, consumer):
        from helpers.method_caller import MethodCallResult
        from specification_tests import test_consolidated_results as spec

        singles = {name: self._single(name) for name in ("one", "two", "three")}
        children = [self._stub(name) if references else single for name, single in singles.items()]
        batch = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="batch", Classification=3),
            ResultContent=children,
        )

        async def read(_management, method, namespace, result_id, timeout_ms, **kwargs):
            assert method == "GetResultById" and namespace == _NS[NS_MACH_RESULT]
            assert timeout_ms.Value == 5000
            return MethodCallResult(success=True, output=[0, singles[result_id.Value], 0])

        with (
            patch.object(spec, "_get_combined", new=AsyncMock(return_value=batch)),
            patch.object(spec, "find_joining_system", new=AsyncMock(return_value=object())),
            patch.object(spec, "find_child_by_browse_name", new=AsyncMock(return_value=object())),
            patch("helpers.method_caller.find_and_call_method", new=AsyncMock(side_effect=read)) as reader,
        ):
            await getattr(spec, consumer)(object(), object(), object(), _NS)
        assert reader.await_count == (3 if references else 0)
        assert batch.ResultContent is children
        if references:
            assert all(child.ResultContent == [] for child in batch.ResultContent)

    @pytest.mark.parametrize("quantity", [1, 2, 3], ids=["time", "torque", "angle"])
    async def test_final_quantity_check_uses_specification_quantity_values(self, quantity):
        from specification_tests import test_consolidated_results as spec

        batch = SimpleNamespace(ResultContent=[self._single("one", quantity=quantity)])
        with patch.object(spec, "_get_combined", new=AsyncMock(return_value=batch)):
            if quantity == 1:
                with pytest.raises(AssertionError, match="No FINAL-tagged Torque or Angle"):
                    await spec.test_single_result_has_final_tagged_torque_or_angle_value(None, None, None, _NS)
            else:
                await spec.test_single_result_has_final_tagged_torque_or_angle_value(None, None, None, _NS)

    async def test_available_content_without_final_values_still_fails(self):
        from specification_tests import test_consolidated_results as spec

        batch = SimpleNamespace(ResultContent=[self._single("one", final=False)])
        with patch.object(spec, "_get_combined", new=AsyncMock(return_value=batch)):
            with pytest.raises(AssertionError, match="No sub-result contains a FINAL-tagged"):
                await spec.test_batch_result_sub_results_contain_final_tagged_values(None, None, None, _NS)
            with pytest.raises(AssertionError, match="No FINAL-tagged values"):
                await spec.test_final_tag_present_in_consecutive_results(None, None, None, _NS)

    async def test_duplicate_final_quantity_still_fails(self):
        from specification_tests import test_consolidated_results as spec

        single = self._single("one")
        values = single.ResultContent[0].StepResults[0].StepResultValues
        values.append(values[0])
        with patch.object(spec, "_get_combined", new=AsyncMock(return_value=SimpleNamespace(ResultContent=[single]))):
            with pytest.raises(AssertionError, match="appears more than once"):
                await spec.test_each_step_has_at_most_one_final_per_physical_quantity(None, None, None, _NS)

    @pytest.mark.parametrize("response", ["missing", "wrong_id", "wrong_classification", "malformed", "cycle"])
    async def test_invalid_or_unavailable_references_cannot_become_measurement_passes(self, response):
        from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
        from helpers.method_caller import MethodCallResult
        from specification_tests import test_consolidated_results as spec

        single = self._single("wrong" if response == "wrong_id" else "one")
        if response == "wrong_classification":
            single.ResultMetaData.Classification = 3
        if response == "cycle":
            single.ResultContent = [self._stub("batch", classification=3)]
        outputs = [0, single, 1 if response == "missing" else 0]
        if response == "malformed":
            outputs = [single]
        batch = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="batch", Classification=3),
            ResultContent=[self._stub("one")],
        )
        expected = (
            WorkflowEvidenceUnavailable
            if response == "missing"
            else (pytest.fail.Exception if response == "cycle" else AssertionError)
        )
        with (
            patch.object(spec, "find_joining_system", new=AsyncMock(return_value=object())),
            patch.object(spec, "find_child_by_browse_name", new=AsyncMock(return_value=object())),
            patch(
                "helpers.method_caller.find_and_call_method",
                new=AsyncMock(return_value=MethodCallResult(success=True, output=outputs)),
            ),
            pytest.raises(expected),
        ):
            await spec._measurement_sub_results(object(), _NS, batch)

    async def test_nested_references_are_resolved_once_without_modifying_packaging(self):
        from helpers.method_caller import MethodCallResult
        from specification_tests import test_consolidated_results as spec

        nested = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="nested", Classification=3),
            ResultContent=[self._stub("single"), self._stub("single")],
        )
        root = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="root", Classification=4),
            ResultContent=[self._stub("nested", classification=3)],
        )
        returned = {"nested": nested, "single": self._single("single")}

        async def read(_management, _method, _namespace, result_id, *_args, **_kwargs):
            return MethodCallResult(success=True, output=[0, returned[result_id.Value], 0])

        with (
            patch.object(spec, "find_joining_system", new=AsyncMock(return_value=object())),
            patch.object(spec, "find_child_by_browse_name", new=AsyncMock(return_value=object())),
            patch("helpers.method_caller.find_and_call_method", new=AsyncMock(side_effect=read)) as reader,
        ):
            resolved = await spec._measurement_sub_results(object(), _NS, root)
        assert spec._has_final_tag_in_result(resolved[0])
        assert reader.await_count == 2
        assert root.ResultContent[0].ResultContent == []
        assert all(child.ResultContent == [] for child in nested.ResultContent)


@pytest.mark.parametrize("consumer", ["identifier_reset", "result_identifiers"])
async def test_identifier_consumers_preserve_typed_unavailable_evidence(consumer):
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
    from helpers.target_server_triggers import TargetServerTriggerOutcome
    from specification_tests import test_identifiers, test_result_identifiers

    trigger = SimpleNamespace(
        owns_result_subscription=True,
        trigger_single=AsyncMock(
            return_value=TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="inconclusive",
                reason_code="operation_evidence_timeout",
                skip_reason="Original interrupted joining action",
                mutation_attempted=True,
            )
        ),
    )
    with pytest.raises(WorkflowEvidenceUnavailable) as error:
        if consumer == "identifier_reset":
            await test_identifiers._assert_identifier_absent_after_reset(object(), trigger, _NS, "owned-id")
        else:
            await test_result_identifiers._get_result_and_associated_entities(object(), trigger, _NS)
    assert error.value.ijt_properties["ijt_reason_code"] == "operation_evidence_timeout"
    assert error.value.ijt_properties["ijt_canonical_outcome"] == "inconclusive"


async def test_identifier_reset_does_not_promote_cleanup_uncertainty_to_specification_failure():
    from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
    from helpers.target_server_triggers import TargetServerTriggerOutcome
    from specification_tests import test_identifiers

    trigger = SimpleNamespace(
        reset_all_identifiers=AsyncMock(
            return_value=TargetServerTriggerOutcome(
                triggered=False,
                execution_outcome="inconclusive",
                reason_code="identifier_reset_unconfirmed",
                skip_reason="Reset service response was lost",
                mutation_attempted=True,
                claim_mismatch=True,
            )
        )
    )
    with pytest.raises(WorkflowEvidenceUnavailable) as error:
        await test_identifiers._run_approved_reset_all(trigger)
    assert error.value.ijt_properties["ijt_reason_code"] == "identifier_reset_unconfirmed"


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


def _accepted_trigger(*, is_simulator: bool = True) -> MagicMock:
    trigger = MagicMock()
    trigger.is_simulator = is_simulator
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

    async def test_accepted_start_on_controller_without_variable_update_skips_as_accepted_policy(self):
        """Accepted trigger on physical controller where variable is not updated skips as accepted policy."""
        meta_node = _meta_node(["RESULT-1", "RESULT-1"])
        p1, p2, p3 = self._patches(meta_node)
        with (
            _virtual_clock() as clock,
            p1,
            p2,
            p3,
            pytest.raises(_SKIPPED) as exc_info,
        ):
            await _access.test_last_result_metadata_updated_after_trigger(
                MagicMock(), _accepted_trigger(is_simulator=False), _NS
            )
        assert "ACCEPTED POLICY" in str(exc_info.value)
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

    async def test_consecutive_single_result_id_uniqueness_requests_fresh_second_operation(self):
        from helpers.trigger import ExternalResultTrigger

        cached = SimpleNamespace(
            ResultMetaData=SimpleNamespace(
                ResultId="cached-single-1", Classification=1, IsPartial=False, ResultState=1
            ),
            ResultContent=[],
        )
        fresh = SimpleNamespace(
            ResultMetaData=SimpleNamespace(ResultId="fresh-single-2", Classification=1, IsPartial=False, ResultState=1),
            ResultContent=[],
        )
        progression_a = SimpleNamespace(classification=1, final_result=cached, all_results=(cached,), is_complete=True)
        progression_b = SimpleNamespace(classification=1, final_result=fresh, all_results=(fresh,), is_complete=True)

        trigger: Any = ExternalResultTrigger()
        trigger.owns_result_subscription = True
        trigger.get_reusable_progression = AsyncMock(return_value=progression_a)
        trigger.trigger_single = AsyncMock(
            return_value=SimpleNamespace(triggered=True, result_progression=progression_b)
        )

        await _single.test_single_result_ids_are_unique_between_consecutive_operations(MagicMock(), trigger, _NS)
        trigger.get_reusable_progression.assert_awaited_once()
        trigger.trigger_single.assert_awaited_once()
