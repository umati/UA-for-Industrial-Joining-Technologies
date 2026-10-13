from unittest.mock import AsyncMock, MagicMock

import pytest

import conftest


@pytest.mark.parametrize(
    "fixture_name,target",
    [
        ("session_client", False),
        ("opcua_client", False),
        ("_module_subscription_client", False),
        ("subscription_client", True),
    ],
)
async def test_fixture_clients_use_bounded_health_probe(monkeypatch, fixture_name, target):
    client = object()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(conftest, "Client", factory)
    monkeypatch.setattr(conftest, "_connect_test_client", AsyncMock())
    monkeypatch.setattr(conftest, "_disconnect_test_client", AsyncMock())
    monkeypatch.setattr(conftest, "_target_server_profile_path", lambda: "target.yaml" if target else "")
    fixture = getattr(conftest, fixture_name).__wrapped__
    args = (object(), None) if fixture_name == "subscription_client" else (object(),)
    generator = fixture(*args)
    assert await anext(generator) is client
    factory.assert_called_once_with(conftest.SERVER_URL, timeout=120, watchdog_intervall=30)
    await generator.aclose()
