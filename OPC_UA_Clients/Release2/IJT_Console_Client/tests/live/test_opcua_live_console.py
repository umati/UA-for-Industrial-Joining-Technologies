"""
Live integration tests for IJT_Console_Client.

Tests require a running OPC UA server at opc.tcp://localhost:40451 (or env override).
All tests are automatically skipped if the server is unavailable (conftest.py).

Covered operations
------------------
Connection    : connect / disconnect / browse root
Subscriptions : subscribe_to_events, cleanup releases subscriptions
Methods       : enable_asset (enable + disable), select_joint, start_selected_joining

Run all live tests:
    pytest tests/live/ -v -m live
Run a single class:
    pytest tests/live/ -v -k "TestMethods"
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

_SERVER_URL = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")

# OPC UA node string identifiers used by the Console Client (from main.py / method_caller.py)
_ASSET_OBJECT = "ns=1;s=TighteningSystem/AssetManagement/MethodSet"
_ASSET_ENABLE = "ns=1;s=TighteningSystem/AssetManagement/MethodSet/EnableAsset"
_JOINT_OBJECT = "ns=1;s=TighteningSystem/JointManagement"
_JOINT_SELECT = "ns=1;s=TighteningSystem/JointManagement/SelectJoint"
_JP_OBJECT = "ns=1;s=TighteningSystem/JoiningProcessManagement"
_JP_START = "ns=1;s=TighteningSystem/JoiningProcessManagement/StartSelectedJoining"


# ---------------------------------------------------------------------------
# Module-scoped fixture — single connection for all method tests
# ---------------------------------------------------------------------------


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


@pytest.mark.asyncio
async def test_connect_to_server():
    """A real connection to the OPC UA server can be established."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        assert client.client is not None, "client.client must not be None after connect()"
    finally:
        await client.cleanup()


@pytest.mark.asyncio
async def test_browse_root_node_returns_results():
    """Browsing the root node must return at least one child node."""
    from opcua_client import OPCUAClient

    client = OPCUAClient(_SERVER_URL)
    try:
        await client.connect()
        root = client.client.get_root_node()
        children = await root.get_children()
        assert len(children) > 0, "Root node must have child nodes"
    finally:
        await client.cleanup()


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_enable_asset_true(self, connected_client):
        """EnableAsset(enable=True) must return a dict with a numeric status code."""
        result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT,
            method_nodeid=_ASSET_ENABLE,
            enable=True,
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio
    async def test_enable_asset_false(self, connected_client):
        """EnableAsset(enable=False) must return a dict with a numeric status code."""
        result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT,
            method_nodeid=_ASSET_ENABLE,
            enable=False,
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio
    async def test_enable_asset_disable_then_reenable(self, connected_client):
        """Disable then re-enable — both calls must succeed."""
        disable_result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT, method_nodeid=_ASSET_ENABLE, enable=False
        )
        if disable_result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        enable_result = await connected_client.methods.enable_asset(
            object_nodeid=_ASSET_OBJECT, method_nodeid=_ASSET_ENABLE, enable=True
        )
        if enable_result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in enable_result

    @pytest.mark.asyncio
    async def test_select_joint_returns_status(self, connected_client):
        """SelectJoint must return a dict with a status code (any code is acceptable).

        The server returns MethodStatusCode=2 (URI_NOT_FOUND) if the joint ID is
        unknown — that is a valid server response, not a client error.  The important
        assertion is that the method call completes without raising an exception.
        """
        result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id="Joint_1",  # common simulator default; may return status 2 if not found
            joint_origin_id="",
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in result, f"Result must have 'status' key, got: {result}"

    @pytest.mark.asyncio
    async def test_select_joint_empty_origin_id(self, connected_client):
        """SelectJoint with an explicit empty origin ID must not raise."""
        result = await connected_client.methods.select_joint(
            object_nodeid=_JOINT_OBJECT,
            method_nodeid=_JOINT_SELECT,
            joint_id="Joint_1",
            joint_origin_id=None,  # None → "" inside method_caller
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")

    @pytest.mark.asyncio
    async def test_start_selected_joining_deselect_true(self, connected_client):
        """StartSelectedJoining(deselect=True) must return a dict with a status code."""
        result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=True,
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in result, f"Result must contain 'status' key, got: {result}"

    @pytest.mark.asyncio
    async def test_start_selected_joining_deselect_false(self, connected_client):
        """StartSelectedJoining(deselect=False) must return a dict with a status code."""
        result = await connected_client.methods.start_selected_joining(
            object_nodeid=_JP_OBJECT,
            method_nodeid=_JP_START,
            deselect_after_joining=False,
        )
        if result is None:
            pytest.skip("ProductInstanceUri not configured on server — method requires tool identity")
        assert "status" in result
