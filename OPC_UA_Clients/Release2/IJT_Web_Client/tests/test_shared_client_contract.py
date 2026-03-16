import os
from pathlib import Path

import pytest

from tests.shared_opcua.adapters import adapters_from_env, discover_simulation_methods, make_adapter


pytestmark = pytest.mark.integration


@pytest.fixture
def opcua_endpoint() -> str:
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("Set OPCUA_TEST_ENDPOINT to run shared cross-client contract tests.")
    return endpoint


@pytest.fixture
def ws_url() -> str:
    return os.getenv("OPCUA_WS_URL", "ws://localhost:8001")


@pytest.fixture
def console_client_dir() -> str:
    default = Path(__file__).resolve().parents[2] / "IJT_Console_Client"
    return os.getenv("OPCUA_CONSOLE_CLIENT_DIR", str(default.resolve()))


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_name", adapters_from_env())
async def test_shared_client_contract(adapter_name: str, opcua_endpoint: str, ws_url: str, console_client_dir: str):
    adapter = make_adapter(
        adapter_name=adapter_name,
        endpoint=opcua_endpoint,
        ws_url=ws_url,
        console_dir=console_client_dir,
    )

    methods = await discover_simulation_methods(opcua_endpoint)
    wanted = ["SimulateSingleResult", "SimulateJobResult", "SimulateEvents"]

    try:
        await adapter.start()

        connected = await adapter.connect()
        assert "exception" not in str(connected).lower(), f"{adapter_name} connect failed: {connected}"

        namespaces = await adapter.namespaces()
        assert namespaces.get("namespaces"), f"{adapter_name} namespaces empty: {namespaces}"

        read_result = await adapter.read_objects()
        assert "exception" not in str(read_result).lower(), f"{adapter_name} read failed: {read_result}"

        await adapter.subscribe()

        call_results = []
        for name in wanted:
            spec = next((m for m in methods if m.name == name), None)
            if not spec:
                call_results.append({"name": name, "status": "not_found"})
                continue

            result = await adapter.call_method(spec)
            ok = "exception" not in str(result).lower()
            call_results.append({"name": name, "status": "ok" if ok else "failed", "result": result})

        failures = [x for x in call_results if x["status"] == "failed"]
        assert not failures, f"{adapter_name} method failures: {failures}"

        events = await adapter.collect_events(seconds=6.0)
        assert events.get("total", 0) >= 0

    finally:
        try:
            await adapter.terminate()
        finally:
            await adapter.stop()
