import importlib
import json
from typing import Any

import pytest


class FakeWebSocket:
    def __init__(self, messages):
        self.remote_address = ("127.0.0.1", 5000)
        self._messages = list(messages)
        self.sent = []

    def __aiter__(self):
        self._iter = iter(self._messages)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, value):
        self.sent.append(value)


class FakeIJTInterface:
    created: list[Any] = []

    def __init__(self):
        self.handled = []
        self.disconnect_calls = 0
        FakeIJTInterface.created.append(self)

    async def handle(self, websocket, message):
        self.handled.append((websocket, message))

    async def disconnect(self):
        self.disconnect_calls += 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handler_routes_message_and_disconnects(monkeypatch):
    idx = importlib.import_module("index")
    idx.opcuaHandler = None
    monkeypatch.setattr(idx, "IJTInterface", FakeIJTInterface)

    ws = FakeWebSocket([json.dumps({"command": "ping", "value": 1})])
    await idx.handler(ws)

    assert len(FakeIJTInterface.created) >= 1
    created = FakeIJTInterface.created[-1]
    assert len(created.handled) == 1
    assert created.handled[0][1]["command"] == "ping"
    assert created.disconnect_calls == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handler_disconnects_on_invalid_json(monkeypatch):
    idx = importlib.import_module("index")
    idx.opcuaHandler = None
    monkeypatch.setattr(idx, "IJTInterface", FakeIJTInterface)

    ws = FakeWebSocket(["not-json"])
    await idx.handler(ws)

    created = FakeIJTInterface.created[-1]
    assert created.disconnect_calls == 1
