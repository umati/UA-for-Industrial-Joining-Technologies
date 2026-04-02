"""
Wire-format contract tests.

Key names used in OPC UA calls and serialized events must NEVER change
silently. These tests parse the actual source code to verify exact strings.
"""

from pathlib import Path

_CONSOLE_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_source(filename: str) -> str:
    return (_CONSOLE_ROOT / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# method_caller.py — OPC UA method call argument names
# ---------------------------------------------------------------------------


def test_method_caller_uses_object_nodeid_param():
    """select_joint, enable_asset, start_selected_joining all use 'object_nodeid'."""
    src = _read_source("method_caller.py")
    assert "object_nodeid" in src, (
        "method_caller.py must use 'object_nodeid' parameter name — do NOT rename"
    )


def test_method_caller_uses_method_nodeid_param():
    src = _read_source("method_caller.py")
    assert "method_nodeid" in src, (
        "method_caller.py must use 'method_nodeid' parameter name"
    )


def test_no_object_node_key_in_method_caller():
    """Regression: must not use 'objectnode' or 'object_node' as a JSON key."""
    src = _read_source("method_caller.py")
    assert '"objectnode"' not in src
    assert '"object_node"' not in src


# ---------------------------------------------------------------------------
# opcua_client.py — subscription and browse constants
# ---------------------------------------------------------------------------


def test_opcua_client_uses_subscription_period_ms():
    src = _read_source("opcua_client.py")
    assert "_SUBSCRIPTION_PERIOD_MS" in src


def test_opcua_client_uses_queue_size():
    src = _read_source("opcua_client.py")
    assert "_QUEUE_SIZE" in src or "queuesize" in src.lower()


def test_opcua_client_subscribe_events_uses_queuesize_kwarg():
    """subscribe_events() must pass queuesize= to cap memory usage."""
    src = _read_source("opcua_client.py")
    assert "queuesize=" in src, (
        "subscribe_events() call must pass queuesize= to prevent unbounded memory growth"
    )


# ---------------------------------------------------------------------------
# ShortResultEvent wire shape — fields must not be renamed silently
# ---------------------------------------------------------------------------


def test_short_result_event_has_event_type_field():
    src = _read_source("result_event_handler.py")
    assert "EventType" in src


def test_short_result_event_has_event_id_field():
    src = _read_source("result_event_handler.py")
    assert "EventId" in src


def test_short_result_event_has_result_field():
    src = _read_source("result_event_handler.py")
    assert '"Result"' in src or "Result=" in src


def test_short_result_event_has_message_field():
    src = _read_source("result_event_handler.py")
    assert "Message" in src


# ---------------------------------------------------------------------------
# event_types.py — OPC UA namespace URIs must not change
# ---------------------------------------------------------------------------


def test_result_namespace_uri_unchanged():
    src = _read_source("event_types.py")
    assert "http://opcfoundation.org/UA/Machinery/Result/" in src, (
        "Result namespace URI changed — this is a breaking wire-format change"
    )


def test_joining_namespace_uri_unchanged():
    src = _read_source("event_types.py")
    assert "http://opcfoundation.org/UA/IJT/Base/" in src, (
        "IJT Base namespace URI changed — this is a breaking wire-format change"
    )


def test_joining_system_result_ready_event_type_name_unchanged():
    src = _read_source("event_types.py")
    assert "JoiningSystemResultReadyEventType" in src


def test_joining_system_event_type_name_unchanged():
    src = _read_source("event_types.py")
    assert "JoiningSystemEventType" in src
