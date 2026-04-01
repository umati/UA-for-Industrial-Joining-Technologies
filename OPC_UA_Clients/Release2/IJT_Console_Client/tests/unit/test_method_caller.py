"""
Comprehensive tests for IJT_Console_Client/method_caller.py

Covers:
- _parse_outputs: tuple/list with int status + LocalizedText message,
  single element, empty, non-int status, non-LocalizedText message
- select_joint: no ProductInstanceUri returns None, happy path,
  missing joint_origin_id defaults to "", exception returns None
- enable_asset: no ProductInstanceUri returns None, happy path True/False,
  exception returns None
- start_selected_joining: no ProductInstanceUri returns None, happy path,
  exception returns None
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytest.importorskip("asyncua", reason="asyncua not installed")
from asyncua import ua  # noqa: E402

from method_caller import OPCUAMethodCaller  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_localized_text(text: str):
    # asyncua 1.2b2: LocalizedText(Text, Locale) — Text is first arg
    lt = ua.LocalizedText(text, "en")
    return lt


def _make_client(tool_id="urn:tool:001"):
    """Return a mock asyncua Client where get_node returns a callable mock node."""
    client = MagicMock()

    def _get_node(nodeid):
        node = AsyncMock()
        node.call_method = AsyncMock(return_value=(0, _make_localized_text("OK")))
        return node

    client.get_node = MagicMock(side_effect=_get_node)
    return client, tool_id


# ---------------------------------------------------------------------------
# _parse_outputs
# ---------------------------------------------------------------------------


def test_parse_outputs_tuple_int_and_localizedtext():
    lt = _make_localized_text("Method OK")
    caller = OPCUAMethodCaller(MagicMock())
    status, message = caller._parse_outputs((0, lt))
    assert status == 0
    assert message == "Method OK"


def test_parse_outputs_list_works_like_tuple():
    lt = _make_localized_text("Done")
    caller = OPCUAMethodCaller(MagicMock())
    status, message = caller._parse_outputs([1, lt])
    assert status == 1
    assert message == "Done"


def test_parse_outputs_single_element_no_message():
    caller = OPCUAMethodCaller(MagicMock())
    status, message = caller._parse_outputs((2,))
    assert status == 2
    assert message is None


def test_parse_outputs_empty_returns_none_none():
    caller = OPCUAMethodCaller(MagicMock())
    status, message = caller._parse_outputs(())
    assert status is None
    assert message is None


def test_parse_outputs_non_int_status():
    caller = OPCUAMethodCaller(MagicMock())
    status, _ = caller._parse_outputs(("not-an-int", "msg"))
    assert status is None


def test_parse_outputs_plain_string_message():
    caller = OPCUAMethodCaller(MagicMock())
    _, message = caller._parse_outputs((0, "plain string"))
    assert message == "plain string"


def test_parse_outputs_zero_is_valid_status():
    caller = OPCUAMethodCaller(MagicMock())
    status, _ = caller._parse_outputs((0,))
    assert status == 0


# ---------------------------------------------------------------------------
# select_joint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_joint_returns_none_when_no_tool_identifier():
    client, _ = _make_client()
    caller = OPCUAMethodCaller(client)

    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=None):
        result = await caller.select_joint("obj", "mth", "joint-1")

    assert result is None


@pytest.mark.asyncio
async def test_select_joint_happy_path():
    client, tool_id = _make_client("urn:tool:001")

    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("SelectJoint OK")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)

    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.select_joint("ns=1;s=Obj", "ns=1;s=Mth", "joint-7")

    assert result is not None
    assert result["status"] == 0
    assert result["status_message"] == "SelectJoint OK"
    assert result["raw"] == (0, node_mock.call_method.return_value[1])


@pytest.mark.asyncio
async def test_select_joint_default_origin_id_is_empty_string():
    """If joint_origin_id is not supplied, the method call must receive an empty string."""
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("OK")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        await caller.select_joint("obj", "mth", "joint-1")  # no origin_id

    # Third argument to call_method must be a Variant containing ""
    call_args = node_mock.call_method.call_args
    args_passed = call_args[0]  # positional args: (mth, *args)
    # args_passed[0] = mth node, args_passed[1..] = variants
    origin_variant = args_passed[3]  # 4th positional: product_uri, joint_id, origin_id
    assert origin_variant.Value == ""


@pytest.mark.asyncio
async def test_select_joint_explicit_origin_id():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("OK")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        await caller.select_joint("obj", "mth", "joint-1", joint_origin_id="origin-A")

    call_args = node_mock.call_method.call_args[0]
    origin_variant = call_args[3]
    assert origin_variant.Value == "origin-A"


@pytest.mark.asyncio
async def test_select_joint_exception_returns_none():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(side_effect=RuntimeError("server error"))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.select_joint("obj", "mth", "joint-1")

    assert result is None


# ---------------------------------------------------------------------------
# enable_asset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enable_asset_returns_none_when_no_tool_identifier():
    client, _ = _make_client()
    caller = OPCUAMethodCaller(client)

    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=None):
        result = await caller.enable_asset("obj", "mth", True)

    assert result is None


@pytest.mark.asyncio
async def test_enable_asset_true():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("Asset enabled")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.enable_asset("obj", "mth", True)

    assert result["status"] == 0
    assert result["status_message"] == "Asset enabled"
    # Boolean variant must be True
    call_args = node_mock.call_method.call_args[0]
    bool_variant = call_args[2]  # 3rd positional after mth: pi, enable
    assert bool_variant.Value is True


@pytest.mark.asyncio
async def test_enable_asset_false():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("Disabled")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        _ = await caller.enable_asset("obj", "mth", False)

    call_args = node_mock.call_method.call_args[0]
    bool_variant = call_args[2]
    assert bool_variant.Value is False


@pytest.mark.asyncio
async def test_enable_asset_exception_returns_none():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(side_effect=Exception("timeout"))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.enable_asset("obj", "mth", True)

    assert result is None


# ---------------------------------------------------------------------------
# start_selected_joining
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_selected_joining_returns_none_when_no_tool_id():
    client, _ = _make_client()
    caller = OPCUAMethodCaller(client)

    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=None):
        result = await caller.start_selected_joining("obj", "mth", True)

    assert result is None


@pytest.mark.asyncio
async def test_start_selected_joining_deselect_true():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("Started")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.start_selected_joining("obj", "mth", True)

    assert result["status"] == 0
    call_args = node_mock.call_method.call_args[0]
    deselect_variant = call_args[2]
    assert deselect_variant.Value is True


@pytest.mark.asyncio
async def test_start_selected_joining_deselect_false():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(return_value=(0, _make_localized_text("Started")))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        _ = await caller.start_selected_joining("obj", "mth", False)

    call_args = node_mock.call_method.call_args[0]
    deselect_variant = call_args[2]
    assert deselect_variant.Value is False


@pytest.mark.asyncio
async def test_start_selected_joining_exception_returns_none():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    node_mock.call_method = AsyncMock(side_effect=RuntimeError("bad"))
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.start_selected_joining("obj", "mth", True)

    assert result is None


# ---------------------------------------------------------------------------
# Result dict structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_dict_has_status_status_message_raw():
    client, tool_id = _make_client()
    node_mock = AsyncMock()
    raw = (0, _make_localized_text("All good"))
    node_mock.call_method = AsyncMock(return_value=raw)
    client.get_node = MagicMock(return_value=node_mock)

    caller = OPCUAMethodCaller(client)
    with patch("method_caller.read_tool_identifier", new_callable=AsyncMock, return_value=tool_id):
        result = await caller.enable_asset("obj", "mth", True)

    assert "status" in result
    assert "status_message" in result
    assert "raw" in result
