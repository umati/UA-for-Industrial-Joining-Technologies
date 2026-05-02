from types import SimpleNamespace

import pytest
from asyncua import ua

import helpers.method_signature as method_signature


class _FakeInputArgumentsNode:
    def __init__(self, value=None, *, error: Exception | None = None):
        self._value = value
        self._error = error

    async def read_value(self):
        if self._error is not None:
            raise self._error
        return self._value


@pytest.mark.asyncio
async def test_read_input_argument_names_returns_argument_names(monkeypatch):
    async def fake_find_child(method_node, browse_name, ns_opcua, *, timeout):
        assert method_node == "method"
        assert browse_name == "InputArguments"
        assert ns_opcua == 0
        assert timeout == 2.5
        return _FakeInputArgumentsNode(
            [
                SimpleNamespace(Name="ProductInstanceUri"),
                SimpleNamespace(Name="JoiningProcessIdentification"),
            ]
        )

    monkeypatch.setattr(method_signature, "find_child_by_browse_name", fake_find_child)

    assert await method_signature.read_input_argument_names("method", timeout=2.5) == [
        "ProductInstanceUri",
        "JoiningProcessIdentification",
    ]


@pytest.mark.asyncio
async def test_read_input_argument_names_returns_empty_when_input_arguments_absent(monkeypatch):
    async def fake_find_child(*_args, **_kwargs):
        return None

    monkeypatch.setattr(method_signature, "find_child_by_browse_name", fake_find_child)

    assert await method_signature.read_input_argument_names("method") == []


@pytest.mark.asyncio
async def test_read_input_argument_names_returns_empty_when_value_absent(monkeypatch):
    async def fake_find_child(*_args, **_kwargs):
        return _FakeInputArgumentsNode(None)

    monkeypatch.setattr(method_signature, "find_child_by_browse_name", fake_find_child)

    assert await method_signature.read_input_argument_names("method") == []


@pytest.mark.asyncio
async def test_read_input_argument_names_returns_empty_on_ua_error(monkeypatch):
    async def fake_find_child(*_args, **_kwargs):
        return _FakeInputArgumentsNode(error=ua.UaError("read failed"))

    monkeypatch.setattr(method_signature, "find_child_by_browse_name", fake_find_child)

    assert await method_signature.read_input_argument_names("method") == []


@pytest.mark.asyncio
async def test_assert_input_argument_names_passes_for_exact_match(monkeypatch):
    async def fake_read(_method_node, *, ns_opcua, timeout):
        assert ns_opcua == 0
        assert timeout == 1.0
        return ["ProductInstanceUri", "MaxCounterSize"]

    monkeypatch.setattr(method_signature, "read_input_argument_names", fake_read)

    await method_signature.assert_input_argument_names(
        "method",
        ("ProductInstanceUri", "MaxCounterSize"),
        method_name="SetJoiningProcessSize",
        timeout=1.0,
    )


@pytest.mark.asyncio
async def test_assert_input_argument_names_fails_with_method_context(monkeypatch):
    async def fake_read(_method_node, *, ns_opcua, timeout):
        return ["ProductInstanceUri", "CounterSize"]

    monkeypatch.setattr(method_signature, "read_input_argument_names", fake_read)

    with pytest.raises(AssertionError, match="SetJoiningProcessSize InputArguments mismatch"):
        await method_signature.assert_input_argument_names(
            "method",
            ("ProductInstanceUri", "MaxCounterSize"),
            method_name="SetJoiningProcessSize",
        )


def test_current_nodeset_signature_names_are_registered():
    assert method_signature.JOINING_PROCESS_METHOD_INPUTS["SetJoiningProcessSize"] == (
        "ProductInstanceUri",
        "JoiningProcessIdentification",
        "MaxCounterSize",
    )
    assert "SendIOSignals" not in method_signature.ASSET_MANAGEMENT_METHOD_INPUTS
    assert method_signature.ASSET_MANAGEMENT_METHOD_INPUTS["SetIOSignals"] == ("ProductInstanceUri", "SignalList")
