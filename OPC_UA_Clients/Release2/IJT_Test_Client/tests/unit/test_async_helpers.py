"""
Unit tests for helpers/address_space.py and helpers/method_caller.py async functions.

Tests the async exception-handling paths using AsyncMock.
No live OPC UA server is required.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncua import ua

from helpers.address_space import (
    read_node_class,
    read_property_value,
    read_variable_value_safe,
)
from helpers.method_caller import (
    MethodCallResult,
    call_method,
    call_method_and_assert_success,
    call_method_expect_bad_status,
    find_and_call_method,
)


class TestReadVariableValueSafe:
    @pytest.mark.asyncio
    async def test_returns_value_on_success(self):
        node = AsyncMock()
        node.read_value.return_value = 42
        result = await read_variable_value_safe(node)
        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        node = AsyncMock()
        node.read_value.side_effect = Exception("connection error")
        result = await read_variable_value_safe(node)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        node = AsyncMock()
        node.read_value.side_effect = asyncio.TimeoutError
        result = await read_variable_value_safe(node, timeout=0.01)
        assert result is None


class TestReadPropertyValue:
    @pytest.mark.asyncio
    async def test_returns_none_when_property_not_found(self):
        node = AsyncMock()
        with patch("helpers.address_space.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            result = await read_property_value(node, "SomeProperty", ns_index=2)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_value_when_property_found(self):
        node = AsyncMock()
        prop_node = AsyncMock()
        prop_node.read_value.return_value = "prop-value"
        with patch("helpers.address_space.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = prop_node
            result = await read_property_value(node, "SomeProperty", ns_index=2)
        assert result == "prop-value"

    @pytest.mark.asyncio
    async def test_returns_none_on_exception_in_find(self):
        node = AsyncMock()
        with patch("helpers.address_space.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.side_effect = Exception("browse error")
            result = await read_property_value(node, "SomeProp", ns_index=1)
        assert result is None


class TestReadNodeClass:
    @pytest.mark.asyncio
    async def test_returns_node_class_on_success(self):
        node = AsyncMock()
        node.read_node_class.return_value = 1
        result = await read_node_class(node)
        assert result == 1

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        node = AsyncMock()
        node.read_node_class.side_effect = Exception("error reading node class")
        result = await read_node_class(node)
        assert result is None


class TestCallMethod:
    @pytest.mark.asyncio
    async def test_returns_success_on_completion(self):
        node = AsyncMock()
        node.call_method.return_value = [42, "OK"]
        result = await call_method(node, "method-id", method_name="TestMethod")
        assert result.success is True
        assert result.output == [42, "OK"]

    @pytest.mark.asyncio
    async def test_returns_failure_on_ua_error(self):
        node = AsyncMock()
        node.call_method.side_effect = ua.UaError("bad status")
        result = await call_method(node, "method-id", method_name="TestMethod")
        assert result.success is False
        assert isinstance(result.error, ua.UaError)

    @pytest.mark.asyncio
    async def test_returns_failure_on_timeout(self):
        node = AsyncMock()
        node.call_method.side_effect = asyncio.TimeoutError()
        result = await call_method(node, "method-id", method_name="TestMethod")
        assert result.success is False
        assert isinstance(result.error, asyncio.TimeoutError)

    @pytest.mark.asyncio
    async def test_uses_method_node_str_as_label_when_no_name(self):
        node = AsyncMock()
        node.call_method.return_value = []
        result = await call_method(node, "fake-id")
        assert result.success is True


class TestCallMethodExpectBadStatus:
    @pytest.mark.asyncio
    async def test_returns_failure_when_call_unexpectedly_succeeds(self):
        node = AsyncMock()
        node.call_method.return_value = [99]
        result = await call_method_expect_bad_status(node, "method-id", method_name="NegTest")
        assert result.success is False
        assert isinstance(result.error, AssertionError)

    @pytest.mark.asyncio
    async def test_returns_success_on_any_ua_error(self):
        node = AsyncMock()
        node.call_method.side_effect = ua.UaStatusCodeError(0x80340000)
        result = await call_method_expect_bad_status(node, "method-id")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_returns_success_when_expected_status_matches(self):
        node = AsyncMock()
        node.call_method.side_effect = ua.UaStatusCodeError(0x80340000)
        result = await call_method_expect_bad_status(node, "method-id", expected_status_codes=[0x80340000])
        assert result.success is True

    @pytest.mark.asyncio
    async def test_returns_failure_when_status_not_in_expected(self):
        node = AsyncMock()
        node.call_method.side_effect = ua.UaStatusCodeError(0x803D0000)
        result = await call_method_expect_bad_status(node, "method-id", expected_status_codes=[0x80340000])
        assert result.success is False

    @pytest.mark.asyncio
    async def test_returns_failure_on_timeout(self):
        node = AsyncMock()
        node.call_method.side_effect = asyncio.TimeoutError()
        result = await call_method_expect_bad_status(node, "method-id")
        assert result.success is False
        assert isinstance(result.error, asyncio.TimeoutError)


class TestFindAndCallMethod:
    @pytest.mark.asyncio
    async def test_returns_failure_when_method_not_found(self):
        parent_node = AsyncMock()
        with patch("helpers.method_caller.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            result = await find_and_call_method(parent_node, "SomeMethod", method_ns_index=2)
        assert result.success is False
        assert isinstance(result.error, LookupError)
        assert "SomeMethod" in result.method_name

    @pytest.mark.asyncio
    async def test_returns_success_when_method_found_and_called(self):
        parent_node = AsyncMock()
        method_node = AsyncMock()
        parent_node.call_method.return_value = [1, 2]
        with patch("helpers.method_caller.find_child_by_browse_name", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = method_node
            result = await find_and_call_method(parent_node, "GoodMethod", method_ns_index=2)
        assert result.success is True


class TestCallMethodAndAssertSuccess:
    @pytest.mark.asyncio
    async def test_raises_assertion_on_failure(self):
        parent_node = AsyncMock()
        with patch("helpers.method_caller.call_method", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MethodCallResult(
                success=False,
                error=Exception("BadStatus"),
                method_name="TestMethod",
            )
            with pytest.raises(AssertionError, match="TestMethod"):
                await call_method_and_assert_success(parent_node, "fake-node-id", method_name="TestMethod")

    @pytest.mark.asyncio
    async def test_returns_output_on_success(self):
        parent_node = AsyncMock()
        with patch("helpers.method_caller.call_method", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MethodCallResult(
                success=True,
                output=[1, 2, 3],
                method_name="TestMethod",
            )
            result = await call_method_and_assert_success(parent_node, "fake-node-id", method_name="TestMethod")
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_raises_with_unknown_error_when_error_is_none(self):
        parent_node = AsyncMock()
        with patch("helpers.method_caller.call_method", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MethodCallResult(
                success=False,
                error=None,
                method_name="NoErrorMethod",
            )
            with pytest.raises(AssertionError, match="unknown error"):
                await call_method_and_assert_success(parent_node, "fake-node-id", method_name="NoErrorMethod")


# ---------------------------------------------------------------------------
# Additional address_space async functions
# ---------------------------------------------------------------------------

from helpers.address_space import (
    check_node_exists,
    get_component_nodes,
    get_property_nodes,
    read_browse_name,
    read_display_name,
    verify_mandatory_children,
)


class TestVerifyMandatoryChildren:
    @pytest.mark.asyncio
    async def test_returns_missing_names_when_browse_fails(self):
        node = AsyncMock()
        with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
            mock_browse.side_effect = Exception("browse error")
            result = await verify_mandatory_children(node, [("ChildA", 2), ("ChildB", 2)])
        assert "ChildA" in result
        assert "ChildB" in result

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_children_present(self):
        node = AsyncMock()
        ref_a = AsyncMock()
        ref_a.BrowseName.Name = "ChildA"
        ref_a.BrowseName.NamespaceIndex = 2
        ref_b = AsyncMock()
        ref_b.BrowseName.Name = "ChildB"
        ref_b.BrowseName.NamespaceIndex = 2
        with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
            mock_browse.return_value = [ref_a, ref_b]
            result = await verify_mandatory_children(node, [("ChildA", 2), ("ChildB", 2)])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_missing_when_some_children_absent(self):
        node = AsyncMock()
        ref_a = AsyncMock()
        ref_a.BrowseName.Name = "ChildA"
        ref_a.BrowseName.NamespaceIndex = 2
        with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
            mock_browse.return_value = [ref_a]
            result = await verify_mandatory_children(node, [("ChildA", 2), ("ChildB", 2)])
        assert "ChildB" in result
        assert "ChildA" not in result


class TestReadBrowseName:
    @pytest.mark.asyncio
    async def test_returns_name_on_success(self):
        node = AsyncMock()
        bn = AsyncMock()
        bn.Name = "TestNode"
        bn.NamespaceIndex = 3
        node.read_browse_name.return_value = bn
        result = await read_browse_name(node)
        assert result == ("TestNode", 3)

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        node = AsyncMock()
        node.read_browse_name.side_effect = Exception("read error")
        result = await read_browse_name(node)
        assert result is None


class TestReadDisplayName:
    @pytest.mark.asyncio
    async def test_returns_text_on_success(self):
        node = AsyncMock()
        dn = AsyncMock()
        dn.Text = "My Node"
        node.read_display_name.return_value = dn
        result = await read_display_name(node)
        assert result == "My Node"

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        node = AsyncMock()
        node.read_display_name.side_effect = Exception("read error")
        result = await read_display_name(node)
        assert result is None


class TestCheckNodeExists:
    @pytest.mark.asyncio
    async def test_returns_true_when_node_exists(self):
        node = AsyncMock()
        bn = AsyncMock()
        bn.Name = "Test"
        bn.NamespaceIndex = 0
        node.read_browse_name.return_value = bn
        result = await check_node_exists(node)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_node_not_found(self):
        node = AsyncMock()
        node.read_browse_name.side_effect = Exception("not found")
        result = await check_node_exists(node)
        assert result is False


class TestGetPropertyNodes:
    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        node = AsyncMock()
        with patch("helpers.address_space.get_children_by_reference", new_callable=AsyncMock) as mock_children:
            mock_children.side_effect = Exception("browse error")
            result = await get_property_nodes(node)
        assert result == []


class TestGetComponentNodes:
    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        node = AsyncMock()
        with patch("helpers.address_space.get_children_by_reference", new_callable=AsyncMock) as mock_children:
            mock_children.side_effect = Exception("browse error")
            result = await get_component_nodes(node)
        assert result == []


# ---------------------------------------------------------------------------
# find_all_instances_of_type
# ---------------------------------------------------------------------------

from helpers.address_space import find_all_instances_of_type


class TestFindAllInstancesOfType:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_match(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=85"

        type_node_id = MagicMock()
        type_node_id.Identifier = 9999
        type_node_id.NamespaceIndex = 2

        non_matching = MagicMock()
        non_matching.Identifier = 1234
        non_matching.NamespaceIndex = 0

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = non_matching
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = []
                result = await find_all_instances_of_type(client, root_node, type_node_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_matching_node_when_type_matches(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=1;i=100"

        type_node_id = MagicMock()
        type_node_id.Identifier = 1005
        type_node_id.NamespaceIndex = 2

        matching_type = MagicMock()
        matching_type.Identifier = 1005
        matching_type.NamespaceIndex = 2

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = matching_type
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = []
                result = await find_all_instances_of_type(client, root_node, type_node_id)

        assert root_node in result

    @pytest.mark.asyncio
    async def test_handles_browse_failure_gracefully(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=1"

        type_node_id = MagicMock()
        type_node_id.Identifier = 9999
        type_node_id.NamespaceIndex = 2

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = None
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.side_effect = Exception("browse error")
                result = await find_all_instances_of_type(client, root_node, type_node_id, max_depth=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_traverses_children_and_finds_match(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=1"

        child_node = MagicMock()
        child_node.nodeid = "ns=1;i=200"

        ref = MagicMock()
        ref.NodeId = "ns=1;i=200"

        type_node_id = MagicMock()
        type_node_id.Identifier = 1005
        type_node_id.NamespaceIndex = 2

        matching_type = MagicMock()
        matching_type.Identifier = 1005
        matching_type.NamespaceIndex = 2

        call_count = 0

        async def type_def_side_effect(node, _ns):
            nonlocal call_count
            call_count += 1
            if str(node.nodeid) == "ns=1;i=200":
                return matching_type
            return None

        with patch("helpers.address_space.get_type_definition") as mock_td:
            mock_td.side_effect = type_def_side_effect
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.side_effect = [
                    [ref],  # root has one child ref
                    [],  # child has no children
                ]
                with patch("helpers.address_space._node_from_ref") as mock_nfr:
                    mock_nfr.return_value = child_node
                    result = await find_all_instances_of_type(client, root_node, type_node_id, max_depth=1)

        assert child_node in result

    @pytest.mark.asyncio
    async def test_respects_max_depth_zero(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=1"

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = None
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = []
                result = await find_all_instances_of_type(client, root_node, MagicMock(), max_depth=0)

        # At depth=0 with max_depth=0: depth < max_depth is False, so no browse occurs
        mock_browse.assert_not_called()
        assert result == []

    @pytest.mark.asyncio
    async def test_avoids_revisiting_already_visited_nodes(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=1"

        # Ref points back to the root (circular)
        ref = MagicMock()
        ref.NodeId = "ns=0;i=1"

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = None
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = [ref]
                with patch("helpers.address_space._node_from_ref") as mock_nfr:
                    mock_nfr.return_value = root_node  # circular ref returns same node
                    result = await find_all_instances_of_type(client, root_node, MagicMock(), max_depth=3)

        assert result == []
        # Browse should be called only once (root node; after that the child is already visited)
        assert mock_browse.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_type_def_is_none(self):
        client = AsyncMock()
        client.get_namespace_index = AsyncMock(return_value=0)

        root_node = MagicMock()
        root_node.nodeid = "ns=0;i=1"

        with patch("helpers.address_space.get_type_definition", new_callable=AsyncMock) as mock_td:
            mock_td.return_value = None  # no type def → no match
            with patch("helpers.address_space._browse_refs", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = []
                result = await find_all_instances_of_type(client, root_node, MagicMock())

        assert result == []
