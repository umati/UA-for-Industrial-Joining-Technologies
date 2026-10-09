"""
Unit tests for namespace resolution and type identifier helpers.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.namespaces import (
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


def _ns_child(uri, version=None, date=None, version_error=False):
    props = {"0:NamespaceUri": uri}
    if version is not None:
        props["0:NamespaceVersion"] = version
    if date is not None:
        props["0:NamespacePublicationDate"] = date

    async def get_child(name):
        if name == "0:NamespaceVersion" and version_error:
            raise RuntimeError("BadNodeIdUnknown")
        if name not in props:
            raise RuntimeError("BadNoMatch")
        return MagicMock(read_value=AsyncMock(return_value=props[name]))

    return MagicMock(get_child=AsyncMock(side_effect=get_child))


@pytest.mark.asyncio
async def test_read_namespace_metadata_finds_matching_namespace():
    from datetime import datetime

    from src.namespaces import NS_IJT_BASE, read_namespace_metadata

    client = MagicMock()
    client.get_node.return_value = MagicMock(
        get_children=AsyncMock(
            return_value=[
                _ns_child("http://opcfoundation.org/UA/DI/", version="1.04"),
                _ns_child(NS_IJT_BASE, version="1.01.0", date=datetime(2024, 6, 1)),
            ]
        )
    )
    assert await read_namespace_metadata(client, NS_IJT_BASE) == {
        "version": "1.01.0",
        "publication_date": "2024-06-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_read_namespace_metadata_missing_values_are_none():
    from src.namespaces import NS_IJT_BASE, read_namespace_metadata

    client = MagicMock()
    client.get_node.return_value = MagicMock(
        get_children=AsyncMock(return_value=[_ns_child(NS_IJT_BASE, version_error=True)])
    )
    assert await read_namespace_metadata(client, NS_IJT_BASE) == {"version": None, "publication_date": None}

    client.get_node.return_value = MagicMock(get_children=AsyncMock(side_effect=RuntimeError("BadNodeIdUnknown")))
    assert await read_namespace_metadata(client, NS_IJT_BASE) == {"version": None, "publication_date": None}


@pytest.mark.asyncio
async def test_read_namespace_metadata_child_uri_error():
    from src.namespaces import NS_IJT_BASE, read_namespace_metadata

    broken_child = MagicMock()
    broken_child.get_child = AsyncMock(side_effect=RuntimeError("uri inaccessible"))
    valid_child = _ns_child(NS_IJT_BASE, version="1.0.0")

    client = MagicMock()
    client.get_node.return_value = MagicMock(get_children=AsyncMock(return_value=[broken_child, valid_child]))
    result = await read_namespace_metadata(client, NS_IJT_BASE)
    assert result["version"] == "1.0.0"
