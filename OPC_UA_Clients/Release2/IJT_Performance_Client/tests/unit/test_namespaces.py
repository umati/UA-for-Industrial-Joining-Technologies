"""
Unit tests for namespace resolution and type identifier helpers.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ijt_performance_client.namespaces import (
    JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID,
    NS_APP,
    NS_DI,
    NS_IJT_BASE,
    NS_IJT_TIGHTENING,
    NS_MACH_RESULT,
    NS_MACHINERY,
    NS_OPC_UA,
    resolve_namespace_index,
)


def test_namespace_constants():
    assert NS_OPC_UA == "http://opcfoundation.org/UA/"
    assert NS_DI == "http://opcfoundation.org/UA/DI/"
    assert NS_MACHINERY == "http://opcfoundation.org/UA/Machinery/"
    assert NS_MACH_RESULT == "http://opcfoundation.org/UA/Machinery/Result/"
    assert NS_IJT_BASE == "http://opcfoundation.org/UA/IJT/Base/"
    assert NS_IJT_TIGHTENING == "http://opcfoundation.org/UA/IJT/Tightening/"
    assert NS_APP == "urn:AtlasCopco:IJT:Tightening:Server/"
    assert JOINING_SYSTEM_RESULT_READY_EVENT_TYPE_ID == 1007


@pytest.mark.asyncio
async def test_resolve_namespace_index_found():
    mock_client = MagicMock()
    mock_client.server_url = "opc.tcp://localhost:40451"
    mock_client.get_namespace_index = AsyncMock(return_value=3)

    idx = await resolve_namespace_index(mock_client, NS_IJT_BASE)
    assert idx == 3
    mock_client.get_namespace_index.assert_awaited_once_with(NS_IJT_BASE)


@pytest.mark.asyncio
async def test_resolve_namespace_index_not_found():
    mock_client = MagicMock()
    mock_client.server_url = "opc.tcp://localhost:40451"
    err = RuntimeError("Namespace not registered")
    mock_client.get_namespace_index = AsyncMock(side_effect=err)

    idx = await resolve_namespace_index(mock_client, "http://unknown.com")
    assert idx is None
