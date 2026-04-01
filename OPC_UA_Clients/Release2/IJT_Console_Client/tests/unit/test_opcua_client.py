"""
Unit tests for opcua_client.py (OPCUAClient class).
All OPC UA network calls are mocked — no real server required.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_CONSOLE_ROOT_PATH = __import__('pathlib').Path(__file__).resolve().parent.parent.parent
import sys; sys.path.insert(0, str(_CONSOLE_ROOT_PATH))

from opcua_client import OPCUAClient, _OPCUA_TIMEOUT_S, _SUBSCRIPTION_PERIOD_MS, _QUEUE_SIZE


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

def test_opcua_timeout_constant_exists():
    assert _OPCUA_TIMEOUT_S == 60

def test_subscription_period_constant_exists():
    assert _SUBSCRIPTION_PERIOD_MS == 100

def test_queue_size_constant_exists():
    assert _QUEUE_SIZE == 200

def test_queue_size_is_positive():
    assert _QUEUE_SIZE > 0

def test_opcua_timeout_is_positive():
    assert _OPCUA_TIMEOUT_S > 0

def test_subscription_period_is_positive():
    assert _SUBSCRIPTION_PERIOD_MS > 0


# ---------------------------------------------------------------------------
# OPCUAClient.__init__ — default state
# ---------------------------------------------------------------------------

def test_init_stores_server_url():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.server_url == "opc.tcp://localhost:40451"

def test_init_sub_result_event_is_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.sub_result_event is None

def test_init_sub_joining_event_is_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.sub_joining_event is None

def test_init_handler_result_event_is_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.handler_result_event is None

def test_init_handler_joining_event_is_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.handler_joining_event is None

def test_init_creates_asyncua_client_with_timeout():
    with patch("opcua_client.Client") as MockClient:
        OPCUAClient("opc.tcp://localhost:40451")
    MockClient.assert_called_once_with("opc.tcp://localhost:40451", timeout=_OPCUA_TIMEOUT_S)

def test_init_creates_method_caller():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")
    assert c.methods is not None


# ---------------------------------------------------------------------------
# connect() — failure path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_raises_on_server_unreachable():
    """When all retries fail, connect() must raise (not swallow) the last exception."""
    with patch("opcua_client.Client") as MockClient:
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
        MockClient.return_value = mock_client

        c = OPCUAClient("opc.tcp://localhost:40451")
        c.client = mock_client

        with patch.object(c, "clear_old_logs", new_callable=AsyncMock):
            with patch.dict("os.environ", {
                "OPCUA_CONNECT_RETRIES": "1",
                "OPCUA_CONNECT_DELAY_SEC": "0.01",
                "OPCUA_CONNECT_MAX_DELAY_SEC": "0.01",
            }):
                with pytest.raises(Exception):
                    await c.connect()

@pytest.mark.asyncio
async def test_connect_retries_configured_count():
    """connect() must attempt exactly OPCUA_CONNECT_RETRIES times."""
    attempt_count = 0
    with patch("opcua_client.Client") as MockClient:
        async def _fail(*_, **__):
            nonlocal attempt_count
            attempt_count += 1
            raise OSError("unreachable")

        mock_client = AsyncMock()
        mock_client.connect = _fail
        MockClient.return_value = mock_client

        c = OPCUAClient("opc.tcp://localhost:40451")
        c.client = mock_client

        with patch.object(c, "clear_old_logs", new_callable=AsyncMock):
            with patch.dict("os.environ", {
                "OPCUA_CONNECT_RETRIES": "3",
                "OPCUA_CONNECT_DELAY_SEC": "0.01",
                "OPCUA_CONNECT_MAX_DELAY_SEC": "0.01",
            }):
                with pytest.raises(Exception):
                    await c.connect()

    assert attempt_count == 3


# ---------------------------------------------------------------------------
# cleanup() — subscription deletion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_deletes_subscriptions():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")

    sub_mock = AsyncMock()
    c.sub_result_event = sub_mock
    c.sub_joining_event = None

    mock_inner_client = AsyncMock()
    c.client = mock_inner_client

    await c.cleanup()
    sub_mock.delete.assert_awaited_once()

@pytest.mark.asyncio
async def test_cleanup_sets_subs_to_none():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")

    c.sub_result_event = AsyncMock()
    c.sub_joining_event = AsyncMock()
    c.client = AsyncMock()

    await c.cleanup()

    assert c.sub_result_event is None
    assert c.sub_joining_event is None

@pytest.mark.asyncio
async def test_cleanup_disconnects_client():
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")

    mock_inner = AsyncMock()
    c.client = mock_inner

    await c.cleanup()
    mock_inner.disconnect.assert_awaited_once()

@pytest.mark.asyncio
async def test_cleanup_handles_sub_delete_exception():
    """cleanup() must not raise even if subscription.delete() fails."""
    with patch("opcua_client.Client"):
        c = OPCUAClient("opc.tcp://localhost:40451")

    bad_sub = AsyncMock()
    bad_sub.delete = AsyncMock(side_effect=Exception("network gone"))
    c.sub_result_event = bad_sub
    c.client = AsyncMock()

    await c.cleanup()  # must not raise


# ---------------------------------------------------------------------------
# setup_client_metadata — URI format
# ---------------------------------------------------------------------------

def test_setup_client_metadata_sets_uris():
    with patch("opcua_client.Client") as MockClient:
        mock_client_obj = MagicMock()
        MockClient.return_value = mock_client_obj
        c = OPCUAClient("opc.tcp://localhost:40451")
        c.setup_client_metadata()

    assert "IJT:ConsoleClient" in mock_client_obj.name
    assert "IJT:ConsoleClient" in mock_client_obj.description


# ---------------------------------------------------------------------------
# Named constants are importable at module level (regression guard)
# ---------------------------------------------------------------------------

def test_named_constants_importable():
    assert isinstance(_OPCUA_TIMEOUT_S, (int, float))
    assert isinstance(_SUBSCRIPTION_PERIOD_MS, (int, float))
    assert isinstance(_QUEUE_SIZE, int)
