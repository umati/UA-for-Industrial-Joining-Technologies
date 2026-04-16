# ruff: noqa: E402
"""Extended tests for main.py — run_method_call, run_client, and main()."""

import asyncio
import contextlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from main import run_client, run_method_call

# ── run_method_call — select_joint ──


@pytest.mark.asyncio
async def test_run_method_call_select_joint_success():
    """run_method_call calls methods.select_joint and logs the result."""
    args = SimpleNamespace(call="select_joint", joint_id="j1", origin_id="orig1")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.select_joint = AsyncMock(return_value={"status": 0})

        await run_method_call("opc.tcp://localhost:4840", args)

        instance.methods.select_joint.assert_awaited_once()
        instance.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_method_call_select_joint_no_origin_id():
    """run_method_call passes empty string as joint_origin_id when origin_id is None."""
    args = SimpleNamespace(call="select_joint", joint_id="j2", origin_id=None)

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.select_joint = AsyncMock(return_value={"status": 0})

        await run_method_call("opc.tcp://localhost:4840", args)

        call_kwargs = instance.methods.select_joint.call_args
        assert call_kwargs.kwargs.get("joint_origin_id") == ""


@pytest.mark.asyncio
async def test_run_method_call_select_joint_missing_joint_id_returns_early():
    """run_method_call logs error and returns early when joint_id is missing."""
    args = SimpleNamespace(call="select_joint", joint_id=None, origin_id=None)

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.select_joint = AsyncMock()

        with patch("main.ijt_log") as mock_log:
            await run_method_call("opc.tcp://localhost:4840", args)
            mock_log.error.assert_called()

        instance.methods.select_joint.assert_not_awaited()
        instance.cleanup.assert_awaited()  # finally block still runs


# ── run_method_call — enable_asset ──


@pytest.mark.asyncio
async def test_run_method_call_enable_asset_true():
    """run_method_call calls enable_asset with enable=True when args.enable='true'."""
    args = SimpleNamespace(call="enable_asset", enable="true")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.enable_asset = AsyncMock(return_value={"status": 0})

        await run_method_call("opc.tcp://localhost:4840", args)

        call_kwargs = instance.methods.enable_asset.call_args
        assert call_kwargs.kwargs.get("enable") is True


@pytest.mark.asyncio
async def test_run_method_call_enable_asset_false():
    """run_method_call calls enable_asset with enable=False when args.enable='false'."""
    args = SimpleNamespace(call="enable_asset", enable="false")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.enable_asset = AsyncMock(return_value={"status": 0})

        await run_method_call("opc.tcp://localhost:4840", args)

        call_kwargs = instance.methods.enable_asset.call_args
        assert call_kwargs.kwargs.get("enable") is False


@pytest.mark.asyncio
async def test_run_method_call_enable_asset_invalid_enable_returns_early():
    """run_method_call logs error and returns early when enable value is invalid."""
    args = SimpleNamespace(call="enable_asset", enable="maybe")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.enable_asset = AsyncMock()

        with patch("main.ijt_log") as mock_log:
            await run_method_call("opc.tcp://localhost:4840", args)
            mock_log.error.assert_called()

        instance.methods.enable_asset.assert_not_awaited()


# ── run_method_call — start_selected_joining ──


@pytest.mark.asyncio
async def test_run_method_call_start_selected_joining_true():
    """run_method_call calls start_selected_joining with deselect=True."""
    args = SimpleNamespace(call="start_selected_joining", deselect="true")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.start_selected_joining = AsyncMock(return_value={"status": 0})

        await run_method_call("opc.tcp://localhost:4840", args)

        call_kwargs = instance.methods.start_selected_joining.call_args
        assert call_kwargs.kwargs.get("deselect_after_joining") is True


@pytest.mark.asyncio
async def test_run_method_call_start_selected_joining_invalid_deselect():
    """run_method_call logs error and returns early when deselect is invalid."""
    args = SimpleNamespace(call="start_selected_joining", deselect="maybe")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.start_selected_joining = AsyncMock()

        with patch("main.ijt_log") as mock_log:
            await run_method_call("opc.tcp://localhost:4840", args)
            mock_log.error.assert_called()

        instance.methods.start_selected_joining.assert_not_awaited()


# ── run_method_call — unknown call ──


@pytest.mark.asyncio
async def test_run_method_call_unknown_call_logs_error():
    """run_method_call logs an error and returns early for unknown method names."""
    args = SimpleNamespace(call="do_magic")

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()

        with patch("main.ijt_log") as mock_log:
            await run_method_call("opc.tcp://localhost:4840", args)
            mock_log.error.assert_called()

        instance.cleanup.assert_awaited()


# ── run_client ──


@pytest.mark.asyncio
async def test_run_client_connects_and_subscribes():
    """run_client calls connect() and subscribe_to_events() before looping."""
    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.subscribe_to_events = AsyncMock()
        instance.cleanup = AsyncMock()

        task = asyncio.create_task(run_client("opc.tcp://localhost:4840"))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        instance.connect.assert_awaited_once()
        instance.subscribe_to_events.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_client_calls_cleanup_on_cancellation():
    """run_client always calls cleanup() even when cancelled."""
    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.subscribe_to_events = AsyncMock()
        instance.cleanup = AsyncMock()

        task = asyncio.create_task(run_client("opc.tcp://localhost:4840"))
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        instance.cleanup.assert_awaited()


# ── main() ──


def test_main_runs_method_call_with_select_joint():
    """main() with --call=select_joint creates task and runs it to completion."""
    from main import main

    with patch("main.OPCUAClient") as MockClient:
        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.cleanup = AsyncMock()
        instance.methods.select_joint = AsyncMock(return_value={"status": 0})
        instance.clear_old_logs = AsyncMock()

        argv = ["prog", "--url", "opc.tcp://localhost:4840", "--call", "select_joint", "--joint-id", "jt1"]
        with patch("sys.argv", argv):
            main()  # must complete without error

        instance.connect.assert_awaited_once()


def test_main_runs_client_without_call():
    """main() without --call runs run_client until CancelledError."""
    from main import main

    argv = ["prog", "--url", "opc.tcp://localhost:4840"]
    with patch("sys.argv", argv):
        with patch("main.run_client", new_callable=AsyncMock):
            main()


def test_main_handles_keyboard_interrupt():
    """main() handles KeyboardInterrupt from the event loop gracefully."""
    from main import main

    call_count = [0]

    def _run_until_complete_raising(coro):
        call_count[0] += 1
        # Close any real coroutine to avoid ResourceWarning
        if hasattr(coro, "close"):
            coro.close()
        if call_count[0] == 1:
            raise KeyboardInterrupt()
        return None

    mock_loop = MagicMock()
    mock_task = MagicMock()
    mock_task.cancel = MagicMock()
    mock_loop.create_task.return_value = mock_task
    mock_loop.run_until_complete = _run_until_complete_raising
    mock_loop.is_closed.return_value = False

    # Patch asyncio.gather to return a simple non-coroutine value so the mock
    # loop.run_until_complete doesn't receive a dangling coroutine.
    with patch("asyncio.new_event_loop", return_value=mock_loop):
        with patch("asyncio.set_event_loop"):
            with patch("asyncio.all_tasks", return_value=[]):
                with patch("asyncio.gather", return_value=None):
                    argv = ["prog", "--url", "opc.tcp://localhost:4840"]
                    with patch("sys.argv", argv):
                        main()  # must not raise


def test_main_handles_unhandled_exception():
    """main() handles unhandled exceptions from the event loop and logs them."""
    from main import main

    call_count = [0]

    def _run_until_complete_raising(coro):
        call_count[0] += 1
        if call_count[0] == 1:
            if hasattr(coro, "close"):
                coro.close()
            raise ValueError("something went wrong")
        return None

    mock_loop = MagicMock()
    mock_task = MagicMock()
    mock_loop.create_task.return_value = mock_task
    mock_loop.run_until_complete = _run_until_complete_raising
    mock_loop.all_tasks.return_value = []
    mock_loop.is_closed.return_value = False

    with patch("asyncio.new_event_loop", return_value=mock_loop):
        with patch("asyncio.set_event_loop"):
            with patch("asyncio.all_tasks", return_value=[]):
                argv = ["prog", "--url", "opc.tcp://localhost:4840"]
                with patch("sys.argv", argv):
                    with patch("main.ijt_log") as mock_log:
                        main()  # must not raise
                        mock_log.error.assert_called()
