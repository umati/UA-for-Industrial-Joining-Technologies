import contextlib
import os

import pytest

from python.network_utils import endpoint_reachable
from tests.shared_opcua.adapters import adapters_from_env, discover_simulation_methods, make_adapter


pytestmark = pytest.mark.integration


def _assert_adapter_response_ok(adapter_name: str, action: str, response) -> None:
    assert isinstance(response, dict), (
        f"{adapter_name} {action} should return a structured dict, got: {type(response).__name__}"
    )
    if "status" in response:
        assert response["status"] == "ok", f"{adapter_name} {action} failed: {response}"
    assert "exception" not in response, f"{adapter_name} {action} failed: {response}"
    assert "error" not in response, f"{adapter_name} {action} failed: {response}"


def _assert_events_payload(adapter_name: str, events: dict) -> None:
    assert isinstance(events, dict), f"{adapter_name} events response should be dict: {events}"
    assert "total" in events, f"{adapter_name} events missing 'total': {events}"
    assert isinstance(events["total"], int), f"{adapter_name} events total must be int: {events}"
    assert events["total"] >= 0, f"{adapter_name} events total must be non-negative: {events}"
    if "result_events" in events:
        assert isinstance(events["result_events"], int), (
            f"{adapter_name} result_events must be int: {events}"
        )
        assert 0 <= events["result_events"] <= events["total"], (
            f"{adapter_name} invalid result_events count: {events}"
        )


def _is_websocket_startup_error(exc: Exception) -> bool:
    if isinstance(exc, (ConnectionRefusedError, TimeoutError, OSError)):
        return True

    try:
        from websockets import exceptions as ws_exceptions

        ws_related = []
        for name in (
            "WebSocketException",
            "InvalidURI",
            "InvalidStatus",
            "InvalidStatusCode",
            "InvalidHandshake",
            "NegotiationError",
        ):
            typ = getattr(ws_exceptions, name, None)
            if typ is not None:
                ws_related.append(typ)
        if ws_related and isinstance(exc, tuple(ws_related)):
            return True
    except (ImportError, AttributeError):
        # If the optional 'websockets' dependency is missing or does not expose
        # the expected exception types, fall back to the heuristic checks below.
        pass

    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "websocket",
            "handshake",
            "connection refused",
            "failed to establish a new connection",
            "invalid uri",
            "ws://",
            "wss://",
        )
    )


@pytest.fixture
def opcua_endpoint() -> str:
    endpoint = os.getenv("OPCUA_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("Set OPCUA_TEST_ENDPOINT to run shared cross-client contract tests.")

    if not endpoint_reachable(endpoint):
        pytest.skip(
            f"OPC UA endpoint {endpoint} is not reachable. Start the simulator/server and rerun."
        )

    return endpoint


@pytest.fixture
def ws_url() -> str:
    return os.getenv("OPCUA_WS_URL", "ws://localhost:8001")


@pytest.fixture
def console_client_dir() -> str:
    return os.getenv("OPCUA_CONSOLE_CLIENT_DIR", "")


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
        try:
            await adapter.start()
        except Exception as exc:
            msg = str(exc).lower()
            if adapter_name == "web" and _is_websocket_startup_error(exc):
                pytest.skip(
                    f"Web adapter websocket is unavailable/misconfigured at {ws_url}: {exc}"
                )
            if adapter_name == "console" and "console adapter dependency missing" in msg:
                pytest.skip(
                    "Console adapter dependency missing in active venv "
                    f"({exc}). Install console deps or use console venv."
                )
            raise

        connected = await adapter.connect()
        _assert_adapter_response_ok(adapter_name, "connect", connected)

        namespaces = await adapter.namespaces()
        assert namespaces.get("namespaces"), f"{adapter_name} namespaces empty: {namespaces}"

        read_result = await adapter.read_objects()
        _assert_adapter_response_ok(adapter_name, "read", read_result)

        await adapter.subscribe()

        call_results = []
        for name in wanted:
            spec = next((m for m in methods if m.name == name), None)
            if not spec:
                call_results.append({"name": name, "status": "not_found"})
                continue

            try:
                result = await adapter.call_method(spec)
                ok = True
            except Exception as exc:
                result = exc
                ok = False
            call_results.append({"name": name, "status": "ok" if ok else "failed", "result": result})

        missing = [x for x in call_results if x["status"] == "not_found"]
        failures = [x for x in call_results if x["status"] == "failed"]
        assert not missing, f"{adapter_name} missing expected methods: {missing}"
        assert not failures, f"{adapter_name} method failures: {failures}"

        events = await adapter.collect_events(seconds=6.0)
        _assert_events_payload(adapter_name, events)
        if adapter_name == "web":
            assert events.get("total", 0) > 0, f"{adapter_name} expected events, got: {events}"

    finally:
        with contextlib.suppress(Exception):
            await adapter.terminate()
        with contextlib.suppress(Exception):
            await adapter.stop()
