from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from helpers.namespaces import BN, JoiningProcessClassification
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
    call = AsyncMock(return_value=SimpleNamespace(success=True, output_list=[0, ""], error=None))
    monkeypatch.setattr(checks, "find_and_call_method", call)
    await checks._set_simulator_counter_baseline("jpm", 7, "tool", "batch", counter=3, size=10)
    assert [(args.args[1], args.args[5].Value) for args in call.call_args_list] == [
        (BN.SET_JOINING_PROCESS_COUNTER, 0),
        (BN.SET_JOINING_PROCESS_SIZE, 10),
        (BN.SET_JOINING_PROCESS_COUNTER, 3),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("success, outputs", [(False, []), (True, [5, "Rejected"])])
async def test_counter_baseline_does_not_hide_rejection(monkeypatch, success, outputs):
    call = AsyncMock(return_value=SimpleNamespace(success=success, output_list=outputs, error="Rejected"))
    monkeypatch.setattr(checks, "find_and_call_method", call)
    with pytest.raises(AssertionError, match="failed|rejected"):
        await checks._set_simulator_counter_baseline("jpm", 7, "tool", "batch", counter=3, size=10)
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
