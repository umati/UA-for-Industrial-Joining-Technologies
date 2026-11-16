from inspect import unwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from helpers.cu_coverage_report import WorkflowEvidenceUnavailable
from helpers.namespaces import BN, JoiningProcessClassification
from helpers.trigger import SimulatorResultTrigger
from specification_tests import test_joining_process as checks


def test_batch_selection_does_not_choose_first_program():
    program = SimpleNamespace(Classification=JoiningProcessClassification.PROGRAM.value)
    batch = SimpleNamespace(Classification=JoiningProcessClassification.BATCH.value)
    wrapped = SimpleNamespace(Value=SimpleNamespace(JoiningProcessMetaData=batch))
    assert checks._batch_process_entry([program, wrapped]) is wrapped.Value


def test_missing_batch_fails_instead_of_using_program():
    with pytest.raises(pytest.fail.Exception, match="did not expose a Batch"):
        checks._batch_process_entry([SimpleNamespace(Classification=JoiningProcessClassification.PROGRAM.value)])


@pytest.mark.asyncio
async def test_counter_baseline_orders_reset_before_size_and_seed(monkeypatch):
    monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    call = AsyncMock(return_value=SimpleNamespace(success=True, output_list=[0, ""], error=None))
    monkeypatch.setattr("helpers.method_caller.find_and_call_method", call)
    await checks._set_simulator_counter_baseline(
        "jpm", 7, "tool", "batch", counter=3, size=10, result_trigger=SimulatorResultTrigger(None, None, 7)
    )
    assert [(args.args[1], args.args[5].Value) for args in call.call_args_list] == [
        (BN.SET_JOINING_PROCESS_COUNTER, 0),
        (BN.SET_JOINING_PROCESS_SIZE, 10),
        (BN.SET_JOINING_PROCESS_COUNTER, 3),
    ]


@pytest.mark.asyncio
async def test_checked_in_simulator_manifest_authorizes_counter_setup_and_effect(monkeypatch):
    manifest = Path(__file__).resolve().parents[2] / "target_server_cu_profiles" / "simulator.sut.yaml"
    monkeypatch.setenv("OPCUA_CAPABILITIES_FILE", str(manifest))
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    monkeypatch.delenv("OPCUA_TARGET_MANIFEST_SHA256", raising=False)
    call = AsyncMock(return_value=SimpleNamespace(success=True, output_list=[0, ""], error=None))
    monkeypatch.setattr("helpers.method_caller.find_and_call_method", call)
    trigger = SimulatorResultTrigger(None, None, 7)

    await checks._set_simulator_counter_baseline("jpm", 7, "tool", "batch", counter=3, size=10, result_trigger=trigger)
    await trigger.call_counter_method("jpm", BN.INCREMENT_JOINING_PROCESS_COUNTER, 7, "tool", "batch", 1)

    assert [entry.args[1] for entry in call.await_args_list] == [
        BN.SET_JOINING_PROCESS_COUNTER,
        BN.SET_JOINING_PROCESS_SIZE,
        BN.SET_JOINING_PROCESS_COUNTER,
        BN.INCREMENT_JOINING_PROCESS_COUNTER,
    ]
    assert all(entry.kwargs["target_server_authorized"] for entry in call.await_args_list)


@pytest.mark.asyncio
@pytest.mark.parametrize("success, outputs", [(False, []), (True, [5, "Rejected"])])
async def test_counter_baseline_does_not_hide_rejection(monkeypatch, success, outputs):
    monkeypatch.delenv("OPCUA_CAPABILITIES_FILE", raising=False)
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    call = AsyncMock(return_value=SimpleNamespace(success=success, output_list=outputs, error="Rejected"))
    monkeypatch.setattr("helpers.method_caller.find_and_call_method", call)
    with pytest.raises(AssertionError, match="failed|rejected"):
        await checks._set_simulator_counter_baseline(
            "jpm", 7, "tool", "batch", counter=3, size=10, result_trigger=SimulatorResultTrigger(None, None, 7)
        )
    assert call.await_count == 1


@pytest.mark.asyncio
async def test_target_server_does_not_receive_simulator_setup(monkeypatch):
    call = AsyncMock()
    monkeypatch.setattr(checks, "find_and_call_method", call)
    fixture = unwrap(checks.simulator_counter_process)(None, {}, SimpleNamespace(is_simulator=False))
    assert await anext(fixture) is None
    with pytest.raises(StopAsyncIteration):
        await anext(fixture)
    call.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", [BN.SET_JOINING_PROCESS_COUNTER, BN.INCREMENT_JOINING_PROCESS_COUNTER])
@pytest.mark.parametrize("route", ["simulate_methods", "start_selected_joining"])
async def test_simulator_counter_cannot_bypass_manifest_method_permission(monkeypatch, method, route):
    profile = SimpleNamespace(
        triggers=SimpleNamespace(result=SimpleNamespace(mode=route)),
        cu_execution=SimpleNamespace(
            state_changing_methods=SimpleNamespace(allow_state_changing_method=lambda name: False)
        ),
    )
    monkeypatch.setattr("helpers.profile_loader.selected_manifest_path", lambda: Path("reviewed.sut.yaml"))
    monkeypatch.setattr("helpers.sut_manifest.manifest_change_reason", lambda *args: None)
    monkeypatch.setattr(
        "helpers.sut_manifest.load_sut_manifest",
        lambda path: SimpleNamespace(to_execution_profile=lambda: profile),
    )
    call = AsyncMock()
    monkeypatch.setattr("helpers.method_caller.find_and_call_method", call)
    trigger = SimulatorResultTrigger(None, None, 7)
    with pytest.raises(WorkflowEvidenceUnavailable) as error:
        await trigger.call_counter_method(None, method, 7)
    assert error.value.ijt_properties["ijt_reason_code"] == (
        "method_not_authorized" if route == "simulate_methods" else "simulator_counter_route_required"
    )
    call.assert_not_called()


@pytest.mark.asyncio
async def test_counter_setup_checks_all_permissions_before_first_mutation(monkeypatch):
    profile = SimpleNamespace(
        triggers=SimpleNamespace(result=SimpleNamespace(mode="simulate_methods")),
        cu_execution=SimpleNamespace(
            state_changing_methods=SimpleNamespace(
                allow_state_changing_method=lambda name: name == BN.SET_JOINING_PROCESS_COUNTER
            )
        ),
    )
    monkeypatch.setattr("helpers.profile_loader.selected_manifest_path", lambda: Path("reviewed.sut.yaml"))
    monkeypatch.setattr("helpers.sut_manifest.manifest_change_reason", lambda *args: None)
    monkeypatch.setattr(
        "helpers.sut_manifest.load_sut_manifest",
        lambda path: SimpleNamespace(to_execution_profile=lambda: profile),
    )
    call = AsyncMock()
    monkeypatch.setattr("helpers.method_caller.find_and_call_method", call)
    with pytest.raises(WorkflowEvidenceUnavailable, match=BN.SET_JOINING_PROCESS_SIZE):
        await checks._set_simulator_counter_baseline(
            None, 7, "tool", "batch", counter=3, size=10, result_trigger=SimulatorResultTrigger(None, None, 7)
        )
    call.assert_not_called()
