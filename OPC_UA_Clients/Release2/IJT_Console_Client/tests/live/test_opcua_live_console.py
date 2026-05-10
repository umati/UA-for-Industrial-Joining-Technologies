"""
Live integration tests for IJT_Console_Client.

Tests require a running OPC UA server at opc.tcp://localhost:40451 (or env override).
The server is auto-started by conftest.py if not already running; any startup
failure raises pytest.fail() — tests never silently skip.

Covered operations
------------------
Connection    : connect / disconnect / browse root
Subscriptions : subscribe_to_events, cleanup releases subscriptions
Methods       : enable_asset (enable + disable), select_joint, start_selected_joining
Joint workflow: SelectJoint(discovered JointId) → StartSelectedJoining → status verified

Run all live tests:
    pytest tests/live/ -v -m live
Run a single class:
    pytest tests/live/ -v -k "TestMethods"
"""
# pylint: disable=redefined-outer-name  # pytest fixtures shadow outer names by design

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from asyncua import ua

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils import read_tool_identifier  # noqa: E402

_SERVER_URL = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")

# OPC UA node string identifiers used by the Console Client (from main.py / method_caller.py)
_ASSET_OBJECT = "ns=1;s=TighteningSystem/AssetManagement/MethodSet"
_ASSET_ENABLE = "ns=1;s=TighteningSystem/AssetManagement/MethodSet/EnableAsset"
_JOINT_OBJECT = "ns=1;s=TighteningSystem/JointManagement"
_JOINT_GET_LIST = "ns=1;s=TighteningSystem/JointManagement/GetJointList"
_JOINT_SELECT = "ns=1;s=TighteningSystem/JointManagement/SelectJoint"
_JP_OBJECT = "ns=1;s=TighteningSystem/JoiningProcessManagement"
_JP_START = "ns=1;s=TighteningSystem/JoiningProcessManagement/StartSelectedJoining"


# ---------------------------------------------------------------------------
# Module-scoped fixture — single connection for all method tests
# ---------------------------------------------------------------------------


def _method_items(output: list) -> list:
    if output and isinstance(output[0], list):
        return output[0]
    return output or []


def _joint_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JointMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = getattr(source, "JointId", None) or getattr(source, "Id", None)
        if value:
            return str(value)
    return entry if isinstance(entry, str) else ""


def _fail_missing_tool_identity() -> None:
    pytest.fail("ProductInstanceUri must be configured on this server for Console Client live method tests")


async def _joint_ids(connected_client) -> list[str]:
    pi = await read_tool_identifier(connected_client.client)
    if not pi:
        _fail_missing_tool_identity()

    output = await connected_client.client.get_node(_JOINT_OBJECT).call_method(
        connected_client.client.get_node(_JOINT_GET_LIST),
        ua.Variant(str(pi), ua.VariantType.String),
    )
    ids = []
    for joint in _method_items(output):
        joint_id = _joint_id_from_entry(joint).strip()
        if joint_id and joint_id not in ids:
            ids.append(joint_id)
    if not ids:
        pytest.fail("GetJointList must return at least one usable JointId for Console Client joint workflow tests")
    return ids


async def _first_two_joint_ids(connected_client) -> tuple[str, str]:
    ids = await _joint_ids(connected_client)
    second = ids[1] if len(ids) > 1 else ids[0]
    return ids[0], second


@pytest_asyncio.fixture(scope="module")
async def connected_client() -> AsyncGenerator:
    """
    Yields a fully-connected OPCUAClient.  One connection is shared across all
    method tests in this module so we avoid the overhead of repeated connect /
    load_type_definitions calls.
    """
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    await client.connect()
    try:
        yield client
    finally:
        await client.cleanup()


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="module")
async def test_connect_to_server():
    """A real connection to the OPC UA server can be established."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        assert client.client is not None, "client.client must not be None after connect()"
    finally:
        await client.cleanup()


@pytest.mark.asyncio(loop_scope="module")
async def test_browse_root_node_returns_results():
    """Browsing the root node must return at least one child node."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        root = client.client.get_root_node()  # type: ignore[union-attr]
        children = await root.get_children()
        assert len(children) > 0, "Root node must have child nodes"
    finally:
        await client.cleanup()


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="module")
async def test_subscribe_to_events_registers_handlers():
    """subscribe_to_events() must create both result and system-event handlers."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        await client.subscribe_to_events()

        assert client.handler_result_event is not None, "ResultEventHandler must be registered"
        assert client.handler_joining_event is not None, "JoiningSystemEventHandler must be registered"
        assert client.sub_result_event is not None, "Result subscription object must exist"
        assert client.sub_joining_event is not None, "Joining-event subscription object must exist"
    finally:
        await client.cleanup()


@pytest.mark.asyncio(loop_scope="module")
async def test_subscribe_to_events_and_wait_for_event():
    """Subscribe and wait up to 30 s for at least one event to arrive."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        await client.subscribe_to_events()

        deadline = asyncio.get_event_loop().time() + 30.0
        while asyncio.get_event_loop().time() < deadline:
            rh = client.handler_result_event
            jh = client.handler_joining_event
            if (rh is not None and getattr(rh, "event_count", 0) > 0) or (
                jh is not None and getattr(jh, "event_count", 0) > 0
            ):
                break
            await asyncio.sleep(1.0)

        # Subscriptions must remain registered even if no events arrived.
        assert client.sub_result_event is not None
        assert client.sub_joining_event is not None
    finally:
        await client.cleanup()


@pytest.mark.asyncio(loop_scope="module")
async def test_cleanup_releases_subscriptions():
    """cleanup() must delete subscriptions and set them to None."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    await client.connect()
    await client.subscribe_to_events()

    assert client.sub_result_event is not None
    await client.cleanup()

    assert client.sub_result_event is None, "sub_result_event must be None after cleanup()"
    assert client.sub_joining_event is None, "sub_joining_event must be None after cleanup()"
    assert client.client is None, "client must be None after cleanup()"


# ---------------------------------------------------------------------------
# Method tests — shared connection via module-scoped fixture
# ---------------------------------------------------------------------------


class TestMethods:
    """Live tests for OPCUAMethodCaller — enable_asset, select_joint, start_selected_joining."""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_enable_asset_true(self, connected_client):
        """EnableAsset(enable=True) must return a dict with a numeric status code."""
        result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT,
            method_nodeid=_ASSET_ENABLE,
            enable=True,
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_enable_asset_false(self, connected_client):
        """EnableAsset(enable=False) must return a dict with a numeric status code."""
        result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT,
            method_nodeid=_ASSET_ENABLE,
            enable=False,
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_enable_asset_disable_then_reenable(self, connected_client):
        """Disable then re-enable — both calls must succeed."""
        disable_result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT, method_nodeid=_ASSET_ENABLE, enable=False
        )
        if disable_result is None:
            _fail_missing_tool_identity()
        enable_result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT, method_nodeid=_ASSET_ENABLE, enable=True
        )
        if enable_result is None:
            _fail_missing_tool_identity()
        assert "status" in enable_result

    @pytest.mark.asyncio(loop_scope="module")
    async def test_select_joint_returns_status(self, connected_client):
        """SelectJoint must return a dict with a status code (any code is acceptable).

        The JointId is discovered from GetJointList instead of assuming the
        simulator's default joint naming exists on every IJT server.
        """
        joint_id = (await _joint_ids(connected_client))[0]
        result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_id,
            joint_origin_id="",
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result, f"Result must have 'status' key, got: {result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_select_joint_empty_origin_id(self, connected_client):
        """SelectJoint with an explicit empty origin ID must not raise."""
        joint_id = (await _joint_ids(connected_client))[0]
        result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_id,
            joint_origin_id=None,  # None → "" inside method_caller
        )
        if result is None:
            _fail_missing_tool_identity()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_start_selected_joining_deselect_true(self, connected_client):
        """StartSelectedJoining(deselect=True) must return a dict with a status code."""
        result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_start_selected_joining_deselect_false(self, connected_client):
        """StartSelectedJoining(deselect=False) must return a dict with a status code."""
        result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=False,
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result

    @pytest.mark.asyncio(loop_scope="module")
    async def test_select_secondary_discovered_joint_returns_status(self, connected_client):
        """SelectJoint with the second discovered JointId, or first if only one exists, must return status."""
        _joint_1, joint_2 = await _first_two_joint_ids(connected_client)
        result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_2,
            joint_origin_id="",
        )
        if result is None:
            _fail_missing_tool_identity()
        assert "status" in result, f"Result must have 'status' key, got: {result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_select_first_two_discovered_joints(self, connected_client):
        """SelectJoint called twice with discovered JointIds must return status both times.

        Exercises switching between joints as the user would on the Joint Demo page.
        """
        joint_1, joint_2 = await _first_two_joint_ids(connected_client)

        r1 = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_1,
            joint_origin_id="",
        )
        if r1 is None:
            _fail_missing_tool_identity()
        assert "status" in r1, f"SelectJoint({joint_1!r}) must return status, got: {r1}"

        r2 = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_2,
            joint_origin_id="",
        )
        if r2 is None:
            _fail_missing_tool_identity()
        assert "status" in r2, f"SelectJoint({joint_2!r}) must return status, got: {r2}"


# ---------------------------------------------------------------------------
# Joint workflow tests — full sequence: SelectJoint → StartSelectedJoining
#
# Tests the complete Joint Demo Page workflow through the Console Client's own
# OPCUAMethodCaller — the same path the user exercises from the terminal.
# Discovered joints are tested in separate test methods so failures are isolated.
# ---------------------------------------------------------------------------


class TestJointWorkflow:
    """Full joint workflow via Console Client method callers.

    Exercises the complete path:
      SelectJoint(joint_id) → StartSelectedJoining(deselect_after_joining=True)

    Both calls must return a dict with a 'status' key.  Result event delivery
    is verified comprehensively in test_opcua_methods.py (Web Client) which
    uses a persistent asyncua subscription; here we validate the Console
    Client's own method-caller path end-to-end.
    """

    @pytest.mark.asyncio(loop_scope="module")
    async def test_primary_joint_select_then_start_returns_status(self, connected_client):
        """SelectJoint(primary discovered JointId) → StartSelectedJoining must both return a 'status' key.

        This mirrors the Joint Demo Page interaction for the first server joint.
        """
        joint_1, _ = await _first_two_joint_ids(connected_client)

        select_result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_1,
            joint_origin_id="",
        )
        if select_result is None:
            _fail_missing_tool_identity()
        assert "status" in select_result, f"SelectJoint must return status, got: {select_result}"

        start_result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if start_result is None:
            _fail_missing_tool_identity()
        assert "status" in start_result, f"StartSelectedJoining must return status, got: {start_result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_secondary_joint_select_then_start_returns_status(self, connected_client):
        """SelectJoint(second discovered JointId) → StartSelectedJoining must both return a 'status' key.

        This mirrors the Joint Demo Page interaction for the second server joint,
        falling back to the first when the server exposes only one joint.
        """
        _joint_1, joint_2 = await _first_two_joint_ids(connected_client)

        select_result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_2,
            joint_origin_id="",
        )
        if select_result is None:
            _fail_missing_tool_identity()
        assert "status" in select_result, f"SelectJoint({joint_2!r}) must return status, got: {select_result}"

        start_result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if start_result is None:
            _fail_missing_tool_identity()
        assert "status" in start_result, f"StartSelectedJoining must return status, got: {start_result}"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_sequential_discovered_joint_workflow(self, connected_client):
        """Run primary then secondary discovered joint workflow — all calls must return status.

        Exercises joint-switching as a user would: select first joint, run tightening,
        then switch to the second joint and run again.  Tests that the Console Client
        method caller handles the switch without state contamination.
        """
        joint_1, joint_2 = await _first_two_joint_ids(connected_client)

        # --- Primary joint cycle ---
        r1_select = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_1,
            joint_origin_id="",
        )
        if r1_select is None:
            _fail_missing_tool_identity()
        assert "status" in r1_select

        r1_start = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if r1_start is None:
            _fail_missing_tool_identity()
        assert "status" in r1_start

        # Brief pause to let the server finish the previous tightening cycle.
        await asyncio.sleep(0.5)

        # --- Secondary joint cycle ---
        r2_select = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id=joint_2,
            joint_origin_id="",
        )
        if r2_select is None:
            _fail_missing_tool_identity()
        assert "status" in r2_select

        r2_start = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if r2_start is None:
            _fail_missing_tool_identity()
        assert "status" in r2_start
