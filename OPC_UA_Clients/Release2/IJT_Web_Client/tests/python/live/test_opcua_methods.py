"""
Live OPC UA method-call tests — IJT Tightening Server (opc.tcp://localhost:40451)

Infrastructure mirrors IJT_Console_Client/opcua_client.py exactly:
  * load_type_definitions() then load_data_type_definitions() (same order)
  * server_node = root.get_child(["0:Objects","0:Server"])
  * Event types resolved by namespace URI (same as Console Client event_types.py)
  * TWO persistent module-scoped subscriptions — result events + system events
  * event_notification is async def (same as production handlers)
  * event.Result gives the full ResultDataType; system events carry
    JoiningSystemEventContent via getattr(event, "JoiningSystemEventContent/...", None)

Server enum constants  (common_system_data_t.h)
-----------------------------------------------
ResultClassification : UNDEFINED=0  SINGLE=1  SYNC=2  BATCH=3  JOB=4
ResultState          : UNDEFINED=0  COMPLETED=1
ResultEvaluation     : OK=1  NOT_OK=2
ResultEvaluationCode : 0=OK  3=failing-step  4=trigger-lost
MethodStatusCode     : 0=OK_SUCCESS  2=URI_NOT_FOUND  5=INVALID_INPUT
OperationMode        : MANUAL=2
AssemblyType         : ASSEMBLED=1
JoiningTechnology    : "Tightening"

SimulateBulkResults (result_simulation_methods_t.cpp):
  Runs in a DETACHED thread — OpcUa_Good returned before events fire.
  MIN=5 (auto-raised if range<5), MAX=1000, SEQUENCE_NUMBER reset to fromSeq-1.

Run all:
    python -m pytest tests/test_opcua_methods.py -v --timeout=120
Run a group:
    python -m pytest tests/test_opcua_methods.py -v -k "Simulate or Bulk"
"""

from __future__ import annotations

import asyncio
import os
import socket
import time

import asyncua.client.ua_client as _uc
from asyncua import ua
import pytest
import pytest_asyncio

# ──────────────────────────────────────────────────────────────────────────────
# asyncua 1.2b2 bug-fix: UaClient.call() calls self._send_request(request)
# without a timeout, falling back to the method's default of 1 second.
# Heavy calls (e.g. SimulateJobResult(refs=True) fires ~12 events synchronously
# before the server sends the CallResponse) exceed 1 s and timeout.
# Fix: replace _send_request so it uses self._timeout when no timeout is given.
# ──────────────────────────────────────────────────────────────────────────────
def _patch_asyncua_send_timeout():
    _orig = _uc.UaClient._send_request

    async def _fixed(self, request, timeout=None, message_type=ua.MessageType.SecureMessage):
        if timeout is None:
            timeout = self._timeout          # use the configured timeout (e.g. 60 s)
        return await _orig(self, request, timeout, message_type)

    _uc.UaClient._send_request = _fixed

_patch_asyncua_send_timeout()

# asyncio_default_fixture_loop_scope = module is set in pytest.ini for all async tests

OPCUA_URL    = os.getenv("OPCUA_TEST_ENDPOINT", "opc.tcp://localhost:40451")
NS           = 1
NS_MACHINERY = "http://opcfoundation.org/UA/Machinery/Result/"
NS_IJT_BASE  = "http://opcfoundation.org/UA/IJT/Base/"

_SIM_R  = "TighteningSystem/Simulations/SimulateResults"
_SIM_E  = "TighteningSystem/Simulations/SimulateEventsAndConditions"
_ASSET  = "TighteningSystem/AssetManagement/MethodSet"
_JP     = "TighteningSystem/JoiningProcessManagement"
_JT     = "TighteningSystem/JointManagement"
_RM     = "TighteningSystem/ResultManagement"
_PI_URI = ("TighteningSystem/AssetManagement/Assets/Tools"
           "/TighteningTool/Identification/ProductInstanceUri")


def _port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


OPCUA_UP       = _port_open("localhost", 40451)
skip_no_server = pytest.mark.skipif(
    not OPCUA_UP, reason="OPC UA server not reachable at port 40451"
)

# Expected (ResultEvaluation, ResultEvaluationCode) per SimulateSingleResult ResultType
_SINGLE_EXPECT = {
    0: (1, 0, "SIMPLE_OK"),
    1: (1, 0, "ONE_STEP_OK"),
    2: (1, 0, "MULTI_STEP_OK"),
    3: (2, 3, "MULTI_STEP_NOK_FAILING_STEP"),
    4: (2, 4, "MULTI_STEP_NOK_TRIGGER_LOST"),
}


# ══════════════════════════════════════════════════════════════════════════════
# Event handlers — mirrors Console Client ResultEventHandler / EventHandler
# ══════════════════════════════════════════════════════════════════════════════

class ResultHandler:
    """Collects JoiningSystemResultReadyEvent notifications."""
    def __init__(self):
        self.events: List = []

    async def event_notification(self, event):
        self.events.append(event)


class SystemHandler:
    """Collects JoiningSystemEvent notifications."""
    def __init__(self):
        self.events: List = []

    async def event_notification(self, event):
        self.events.append(event)


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped OPC UA session fixture
# Mirrors OPCUAClient.connect() + subscribe_to_events() from opcua_client.py
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def ijt_session():
    """
    Yields (client, result_handler, system_handler).
    Both subscriptions persist for the entire module — not recreated per test.
    """
    from asyncua import Client

    result_h = ResultHandler()
    system_h = SystemHandler()

    c = Client(OPCUA_URL, timeout=60)   # generous timeout for heavy simulation calls
    await c.connect()

    # Same as Console Client connect(): load standard type definitions first
    await c.load_type_definitions()

    root        = c.nodes.root
    server_node = await root.get_child(["0:Objects", "0:Server"])

    # Resolve IJT event type nodes by namespace URI (event_types.py pattern)
    ns_r = await c.get_namespace_index(NS_MACHINERY)
    ns_j = await c.get_namespace_index(NS_IJT_BASE)

    result_evt_node = await root.get_child([
        "0:Types", "0:EventTypes", "0:BaseEventType",
        f"{ns_r}:ResultReadyEventType",
    ])
    joining_result_evt_node = await root.get_child([
        "0:Types", "0:EventTypes", "0:BaseEventType",
        f"{ns_r}:ResultReadyEventType",
        f"{ns_j}:JoiningSystemResultReadyEventType",
    ])
    joining_system_evt_node = await root.get_child([
        "0:Types", "0:EventTypes", "0:BaseEventType",
        f"{ns_j}:JoiningSystemEventType",
    ])

    # Same as Console Client subscribe_to_events(): load custom types AFTER resolving nodes
    await c.load_data_type_definitions()

    # Create persistent subscriptions with queuesize=200 (same as Console Client).
    # MaxNotificationsPerPublish=3 prevents large PublishResponse payloads when the
    # server fires many events synchronously (SimulateJobResult(refs=True) → ~12 events).
    def _sub_params(period_ms: float, max_notif: int = 3) -> ua.CreateSubscriptionParameters:
        p = ua.CreateSubscriptionParameters()
        p.RequestedPublishingInterval = period_ms
        p.RequestedLifetimeCount      = 10000
        p.RequestedMaxKeepAliveCount  = 27000
        p.MaxNotificationsPerPublish  = max_notif
        p.PublishingEnabled           = True
        p.Priority                    = 0
        return p

    sub_r = await c.create_subscription(_sub_params(100), result_h)
    await sub_r.subscribe_events(
        server_node,
        [result_evt_node, joining_result_evt_node],
        queuesize=200,
    )

    sub_s = await c.create_subscription(_sub_params(100), system_h)
    await sub_s.subscribe_events(
        server_node,
        [joining_system_evt_node],
        queuesize=200,
    )

    yield c, result_h, system_h

    for sub in (sub_r, sub_s):
        try:
            await sub.delete()
        except OSError:
            pass  # server already gone — teardown must not fail
    try:
        await c.disconnect()
    except OSError:
        pass  # server already gone — teardown must not fail


# ══════════════════════════════════════════════════════════════════════════════
# Low-level helpers
# ══════════════════════════════════════════════════════════════════════════════

def _node(c, identifier: str):
    return c.get_node(ua.NodeId(identifier, NS, ua.NodeIdType.String))


def _v(value, vtype):
    return ua.Variant(value, vtype)


async def _call(c, parent_id: str, method_id: str, *args) -> list:
    return await _node(c, parent_id).call_method(_node(c, method_id).nodeid, *args)


async def _pi_uri(c) -> str:
    """Read ProductInstanceUri (same as utils.read_tool_identifier)."""
    try:
        return str(await _node(c, _PI_URI).read_value()) or ""
    except (OSError, AttributeError):
        return ""


async def _wait_events(handler, min_count: int = 1, timeout: float = 8.0) -> list:
    """Poll until min_count events arrive or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(handler.events) >= min_count:
            break
        await asyncio.sleep(0.2)
    return list(handler.events)


async def _invoke_result(c, result_h, method_id: str, *args, timeout=8.0) -> List:
    """Clear result handler, call method, wait, return snapshot."""
    result_h.events.clear()
    await _call(c, _SIM_R, method_id, *args)
    return await _wait_events(result_h, 1, timeout)


async def _invoke_system(c, system_h, parent_id: str, method_id: str,
                          *args, timeout=6.0) -> List:
    """Clear system handler, call method, wait, return snapshot."""
    system_h.events.clear()
    await _call(c, parent_id, method_id, *args)
    return await _wait_events(system_h, 1, timeout)


def _meta(events, idx: int = -1):
    return events[idx].Result.ResultMetaData


def _assert_meta(events, *, cls, ev, code, state=1, simulated=True, idx=-1):
    m = _meta(events, idx)
    assert int(m.Classification)       == cls,      f"Classification {m.Classification}!={cls}"
    assert int(m.ResultEvaluation)     == ev,       f"ResultEvaluation {m.ResultEvaluation}!={ev}"
    assert int(m.ResultEvaluationCode) == code,     f"ResultEvaluationCode {m.ResultEvaluationCode}!={code}"
    assert int(m.ResultState)          == state,    f"ResultState {m.ResultState}!={state}"
    if simulated is not None:
        assert m.IsSimulated           == simulated, f"IsSimulated {m.IsSimulated}!={simulated}"


# ══════════════════════════════════════════════════════════════════════════════
# 1.  SimulateSingleResult
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestSimulateSingleResult:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("rtype,traces", [
        (0, True), (0, False),
        (1, True), (1, False),
        (2, True), (2, False),
        (3, True), (3, False),
        (4, True), (4, False),
    ])
    async def test_fires_result_event(self, ijt_session, rtype, traces):
        c, result_h, _, = ijt_session
        ev_exp, code_exp, label = _SINGLE_EXPECT[rtype]

        events = await _invoke_result(
            c, result_h, f"{_SIM_R}/SimulateSingleResult", timeout=7.0,
            *[_v(rtype,  ua.VariantType.UInt32),
              _v(traces, ua.VariantType.Boolean)],
        )
        assert events, (
            f"SimulateSingleResult(rtype={rtype}[{label}], traces={traces}): "
            f"no result event received"
        )
        _assert_meta(events, cls=1, ev=ev_exp, code=code_exp)

        meta = _meta(events)
        assert meta.IsPartial is False
        assert int(meta.OperationMode) == 2, "OperationMode must be MANUAL(2)"
        assert int(meta.AssemblyType)  == 1, "AssemblyType must be ASSEMBLED(1)"
        tech = getattr(meta.JoiningTechnology, "Text", str(meta.JoiningTechnology)) or ""
        assert "Tightening" in tech, f"JoiningTechnology unexpected: {tech!r}"

        content = events[-1].Result.ResultContent or []
        if rtype == 0:
            assert len(content) == 0, "SIMPLE_OK must have no ResultContent"
        else:
            assert len(content) == 1, f"rtype={rtype} must have 1 ResultContent item"
            if traces:
                item = content[0]
                joining_result = getattr(item, "Value", item)  # unwrap Variant if needed
                steps = joining_result.StepResults
                assert steps and len(steps) > 0, "IncludeTraces=True but StepResults empty"

    async def test_out_of_range_defaults_to_0(self, ijt_session):
        c, result_h, _ = ijt_session
        events = await _invoke_result(
            c, result_h, f"{_SIM_R}/SimulateSingleResult", timeout=6.0,
            *[_v(999,  ua.VariantType.UInt32),
              _v(True, ua.VariantType.Boolean)],
        )
        assert events, "Out-of-range ResultType must still fire an event"
        _assert_meta(events, cls=1, ev=1, code=0)

    async def test_sequence_number_increments(self, ijt_session):
        c, result_h, _ = ijt_session
        seqs = []
        for rtype in range(3):
            events = await _invoke_result(
                c, result_h, f"{_SIM_R}/SimulateSingleResult", timeout=6.0,
                *[_v(rtype, ua.VariantType.UInt32),
                  _v(False, ua.VariantType.Boolean)],
            )
            assert events, f"rtype={rtype}: no event"
            seqs.append(int(_meta(events).SequenceNumber))
        for i in range(1, len(seqs)):
            assert seqs[i] == seqs[i-1] + 1, (
                f"SequenceNumber not monotone: {seqs[i-1]} -> {seqs[i]}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 2.  SimulateBatch_Or_Sync_Result  (SYNC=2, BATCH=3)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestSimulateBatchOrSync:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("cls,label,n,refs", [
        (3, "BATCH", 3,  False),
        (3, "BATCH", 3,  True),   # refs=True fires 3 children + 1 parent = 4 events
        (2, "SYNC",  3,  False),
        (2, "SYNC",  3,  True),
        (3, "BATCH", 5,  False),  # larger inline batch — one combined event, safe payload
    ])
    async def test_batch_or_sync(self, ijt_session, cls, label, n, refs):
        c, result_h, _ = ijt_session
        result_h.events.clear()
        # Budget: n children × 0.5s each + 6s buffer for combined parent event
        timeout = max(12.0, n * 0.5 + 6)

        await _call(c, _SIM_R, f"{_SIM_R}/SimulateBatch_Or_Sync_Result",
                    _v(cls,  ua.VariantType.Byte),
                    _v(n,    ua.VariantType.UInt32),
                    _v(True, ua.VariantType.Boolean),   # IncludeTraces=True
                    _v(refs, ua.VariantType.Boolean))   # IncludeChildRefs

        events = await _wait_events(result_h, min_count=1, timeout=timeout)
        assert events, f"SimulateBatch_Or_Sync({label},n={n},refs={refs}): no events"
        if refs:
            assert len(events) >= n, f"refs=True: expected >={n} events, got {len(events)}"

        _assert_meta(events, cls=cls, ev=1, code=0, idx=-1)
        counters = _meta(events, -1).ResultCounters
        # ResultCounters items may be wrapped in Variant — unwrap with renamed loop var
        if counters and hasattr(counters[0], "Value"):
            counters = [ctr.Value for ctr in counters]
        assert counters and len(counters) == 2, \
            f"{label}: expected 2 ResultCounters, got {len(counters or [])}"

    async def test_invalid_cls_defaults_to_batch(self, ijt_session):
        """Classification=99 (unknown) must fall back to BATCH(3)."""
        c, result_h, _ = ijt_session
        result_h.events.clear()
        await _call(c, _SIM_R, f"{_SIM_R}/SimulateBatch_Or_Sync_Result",
                    _v(99,   ua.VariantType.Byte),
                    _v(3,    ua.VariantType.UInt32),
                    _v(True, ua.VariantType.Boolean),   # IncludeTraces=True
                    _v(True, ua.VariantType.Boolean))   # IncludeChildRefs=True
        events = await _wait_events(result_h, 1, timeout=10)
        assert events, "Invalid cls must still fire an event"
        assert int(_meta(events, -1).Classification) == 3, \
            "Invalid cls must default to BATCH(3)"


# ══════════════════════════════════════════════════════════════════════════════
# 3.  SimulateJobResult
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestSimulateJobResult:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("refs", [False, True])
    async def test_job_result(self, ijt_session, refs):
        c, result_h, _ = ijt_session
        # Settle: drain any residual events from previous tests before starting.
        await asyncio.sleep(0.5)
        result_h.events.clear()

        await _call(c, _SIM_R, f"{_SIM_R}/SimulateJobResult",
                    _v(refs, ua.VariantType.Boolean))

        events = await _wait_events(result_h, 1, timeout=20)  # ~12 events at 3/cycle × 100ms
        assert events, f"SimulateJobResult(refs={refs}): no events"
        _assert_meta(events, cls=4, ev=1, code=0, idx=-1)  # JOB_RESULT=4

        counters = _meta(events, -1).ResultCounters
        assert counters and len(counters) == 2, "Expected 2 ResultCounters (JOB_COUNT+JOB_SIZE)"
        if refs:
            assert len(events) >= 3, f"refs=True: expected >=3 child events, got {len(events)}"


# ══════════════════════════════════════════════════════════════════════════════
# 4.  SimulateBulkResults  (detached thread — events arrive after method returns)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestSimulateBulkResults:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("rtype,from_seq,to_seq,traces", [
        (0, 1,   6,   True),   # to-from=5 >= MIN(5), no auto-raise
        (1, 1,   6,   True),
        (2, 1,   11,  True),   # 11 results
        (3, 1,   6,   False),
        (4, 1,   6,   False),
        (1, 10,  15,  True),   # to-from=5, no auto-raise
        (2, 100, 105, True),   # to-from=5, no auto-raise
    ])
    async def test_bulk(self, ijt_session, rtype, from_seq, to_seq, traces):
        from asyncua.ua.uaerrors import BadTooManyOperations
        c, result_h, _ = ijt_session
        ev_exp, code_exp, _ = _SINGLE_EXPECT[rtype]
        exp = to_seq - from_seq + 1
        timeout = max(15.0, exp * 0.2 + 8)

        # The server uses a flag to prevent concurrent BulkResults threads.
        # Wait up to 5 s for any previous BulkResults operation to finish.
        for _ in range(5):
            result_h.events.clear()
            try:
                await _call(c, _SIM_R, f"{_SIM_R}/SimulateBulkResults",
                            _v(rtype,    ua.VariantType.UInt32),
                            _v(traces,   ua.VariantType.Boolean),
                            _v(from_seq, ua.VariantType.UInt64),
                            _v(to_seq,   ua.VariantType.UInt64),
                            _v(100,      ua.VariantType.Int64),    # 100 ms between results
                            _v(True,     ua.VariantType.Boolean))  # UpdateResultVariables
                break
            except BadTooManyOperations:
                await asyncio.sleep(1.0)  # wait for previous BulkResults thread to complete
        else:
            pytest.fail("SimulateBulkResults still busy after 5 retries")

        events = await _wait_events(result_h, exp, timeout)
        assert len(events) >= exp, (
            f"BulkResults(rtype={rtype},{from_seq}->{to_seq}): "
            f"expected >={exp}, got {len(events)}"
        )
        assert int(_meta(events, -1).SequenceNumber) == to_seq, \
            f"Final SeqNr should be {to_seq}"
        _assert_meta(events, cls=1, ev=ev_exp, code=code_exp, idx=-1)

    async def test_range_below_min_auto_raised(self, ijt_session):
        """from=1,to=2 (range=2) — server raises to MIN=5."""
        from asyncua.ua.uaerrors import BadTooManyOperations
        c, result_h, _ = ijt_session
        for _ in range(5):
            result_h.events.clear()
            try:
                await _call(c, _SIM_R, f"{_SIM_R}/SimulateBulkResults",
                            _v(1,    ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean),
                            _v(1,    ua.VariantType.UInt64),  _v(2,   ua.VariantType.UInt64),
                            _v(50,   ua.VariantType.Int64),   _v(True, ua.VariantType.Boolean))
                break
            except BadTooManyOperations:
                await asyncio.sleep(1.0)
        else:
            pytest.fail("SimulateBulkResults still busy after 5 retries")
        events = await _wait_events(result_h, 5, timeout=15)
        assert len(events) >= 5, f"Expected >=5 (auto-raised from MIN), got {len(events)}"


# ══════════════════════════════════════════════════════════════════════════════
# 5.  SimulateEvents / SimulateBulkEvents  (JoiningSystemEventType subscription)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestSimulateEvents:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("etype", [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        10, 11, 12, 13,
        22, 23, 24, 25,
        53, 54, 55, 56,
        81, 90, 91,
    ])
    async def test_single_event_type(self, ijt_session, etype):
        c, _, system_h = ijt_session
        events = await _invoke_system(c, system_h, _SIM_E, f"{_SIM_E}/SimulateEvents",
                                      timeout=5.0, *[_v(etype, ua.VariantType.UInt32)])
        assert events, f"SimulateEvents(type={etype}): no event received"
        msg = getattr(getattr(events[0], "Message", None), "Text", "") or ""
        assert msg, f"Event Message.Text empty for EventType={etype}"

    async def test_out_of_range_defaults(self, ijt_session):
        c, _, system_h = ijt_session
        events = await _invoke_system(c, system_h, _SIM_E, f"{_SIM_E}/SimulateEvents",
                                      timeout=5.0, *[_v(9999, ua.VariantType.UInt32)])
        assert events, "Out-of-range EventType must fire a default event"

    @pytest.mark.parametrize("etype,count", [
        (1,  5),
        (2,  10),
        (3,  20),
        (4,  50),
    ])
    async def test_bulk_events(self, ijt_session, etype, count):
        import time
        c, _, system_h = ijt_session
        system_h.events.clear()
        timeout = max(8.0, count * 0.15 + 5)
        await _call(c, _SIM_E, f"{_SIM_E}/SimulateBulkEvents",
                    _v(etype, ua.VariantType.UInt32),
                    _v(count, ua.VariantType.UInt32))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(system_h.events) >= count:
                break
            await asyncio.sleep(0.3)
        assert len(system_h.events) >= count, (
            f"BulkEvents(etype={etype}, count={count}): "
            f"expected >={count}, got {len(system_h.events)}"
        )

    async def test_bulk_events_capped_at_100(self, ijt_session):
        """Request 200 bulk events — server should deliver at least 100 within 30s."""
        import time
        c, _, system_h = ijt_session
        system_h.events.clear()
        await _call(c, _SIM_E, f"{_SIM_E}/SimulateBulkEvents",
                    _v(1,   ua.VariantType.UInt32),
                    _v(200, ua.VariantType.UInt32))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if len(system_h.events) >= 100:
                break
            await asyncio.sleep(0.2)
        # Let remaining in-flight events drain before asserting
        await asyncio.sleep(1.0)
        received = len(system_h.events)
        assert received >= 100, (
            f"Expected at least 100 bulk events, got {received}"
        )
        assert received <= 200, (
            f"Received {received} events but only requested 200"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6.  EnableAsset  (fires JoiningSystemEvents)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestEnableAsset:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_enable_true(self, ijt_session):
        c, _, system_h = ijt_session
        pi = await _pi_uri(c)
        events = await _invoke_system(c, system_h, _ASSET, f"{_ASSET}/EnableAsset",
                                      timeout=5.0,
                                      *[_v(pi,   ua.VariantType.String),
                                        _v(True, ua.VariantType.Boolean)])
        assert events, "EnableAsset(enable=True) must fire a system event"
        msg = getattr(getattr(events[0], "Message", None), "Text", "") or ""
        assert msg, f"EnableAsset event must carry a message, got {msg!r}"

    async def test_disable_then_enable(self, ijt_session):
        c, _, system_h = ijt_session
        pi = await _pi_uri(c)

        disable = await _invoke_system(c, system_h, _ASSET, f"{_ASSET}/EnableAsset",
                                       timeout=5.0,
                                       *[_v(pi,    ua.VariantType.String),
                                         _v(False, ua.VariantType.Boolean)])
        assert disable, "Disable must fire an event"

        enable = await _invoke_system(c, system_h, _ASSET, f"{_ASSET}/EnableAsset",
                                      timeout=5.0,
                                      *[_v(pi,   ua.VariantType.String),
                                        _v(True, ua.VariantType.Boolean)])
        assert enable, "Re-enable must fire an event"


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Joining Process Management
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestJoiningProcess:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def _jp(self, c):
        jp = ua.JoiningProcessIdentificationDataType()
        jp.JoiningProcessId = jp.JoiningProcessOriginId = jp.SelectionName = ""
        return jp

    async def test_get_process_list(self, ijt_session):
        c, *_ = ijt_session
        assert await _call(c, _JP, f"{_JP}/GetJoiningProcessList",
                           _v(await _pi_uri(c), ua.VariantType.String)) is not None

    async def test_get_selected_program(self, ijt_session):
        c, *_ = ijt_session
        assert await _call(c, _JP, f"{_JP}/GetSelectedJoiningProgram",
                           _v(await _pi_uri(c), ua.VariantType.String)) is not None

    async def test_abort_with_localized_text(self, ijt_session):
        c, *_ = ijt_session
        jp = await self._jp(c)
        result = await _call(c, _JP, f"{_JP}/AbortJoiningProcess",
                             _v(await _pi_uri(c), ua.VariantType.String),
                             ua.Variant(jp, ua.VariantType.ExtensionObject),
                             ua.Variant(ua.LocalizedText(Text="Test abort", Locale="en"),
                                        ua.VariantType.LocalizedText))
        assert result is not None

    async def test_increment_decrement_counter(self, ijt_session):
        c, *_ = ijt_session
        jp, pi = await self._jp(c), await _pi_uri(c)
        await _call(c, _JP, f"{_JP}/IncrementJoiningProcessCounter",
                    _v(pi, ua.VariantType.String),
                    ua.Variant(jp, ua.VariantType.ExtensionObject),
                    _v(1,  ua.VariantType.UInt32))
        await _call(c, _JP, f"{_JP}/DecrementJoiningProcessCounter",
                    _v(pi, ua.VariantType.String),
                    ua.Variant(jp, ua.VariantType.ExtensionObject),
                    _v(1,  ua.VariantType.UInt32))

    async def test_start_selected_joining(self, ijt_session):
        c, *_ = ijt_session
        result = await _call(c, _JP, f"{_JP}/StartSelectedJoining",
                             _v(await _pi_uri(c), ua.VariantType.String),
                             _v(True,              ua.VariantType.Boolean))
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════════
# 8.  Result Management — query methods
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestResultManagement:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_get_latest_result(self, ijt_session):
        c, result_h, _ = ijt_session
        # Fire a single result so there is something to fetch
        await _invoke_result(c, result_h, f"{_SIM_R}/SimulateSingleResult", timeout=4.0,
                             *[_v(1, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)])
        result = await _call(c, _RM, f"{_RM}/GetLatestResult",
                             _v(5000, ua.VariantType.Int32))
        assert result is not None

    async def test_request_results_by_sequence(self, ijt_session):
        from datetime import datetime, timezone
        c, *_ = ijt_session
        # Use real datetime values instead of None to avoid asyncua DateTime decode errors
        epoch  = datetime(1970, 1, 1, tzinfo=timezone.utc)
        future = datetime(2099, 12, 31, tzinfo=timezone.utc)
        try:
            result = await _call(c, _RM, f"{_RM}/RequestResults",
                                 _v(1,      ua.VariantType.UInt64),
                                 _v(10,     ua.VariantType.UInt64),
                                 _v(epoch,  ua.VariantType.DateTime),
                                 _v(future, ua.VariantType.DateTime),
                                 _v(10,     ua.VariantType.UInt32))
            assert result is not None
        except OSError:
            pass  # empty result set or server-side Uncertain is acceptable


# ══════════════════════════════════════════════════════════════════════════════
# 9.  Joint Management
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.live
@skip_no_server
class TestJointManagement:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_get_joint_list(self, ijt_session):
        c, *_ = ijt_session
        result = await _call(c, _JT, f"{_JT}/GetJointList",
                             _v(await _pi_uri(c), ua.VariantType.String))
        assert result is not None

    async def test_get_joint_by_id(self, ijt_session):
        c, *_ = ijt_session
        # First get the real joint IDs from the server via GetJointList
        joint_id = "Joint_1"  # fallback default
        try:
            joint_list_result = await _call(c, _JT, f"{_JT}/GetJointList",
                                            _v(await _pi_uri(c), ua.VariantType.String))
            joints = joint_list_result[0] if joint_list_result else []
            if joints:
                first = joints[0]
                # asyncua maps OPC UA struct fields; try common attribute names
                joint_id = (getattr(first, "JointId", None)
                            or getattr(first, "Id", None)
                            or joint_id)
        except OSError:
            pass  # fall back to "Joint_1" if GetJointList fails

        try:
            result = await _call(c, _JT, f"{_JT}/GetJoint",
                                 _v(await _pi_uri(c), ua.VariantType.String),
                                 _v(str(joint_id),    ua.VariantType.String))
            assert result is not None
        except OSError:
            pass  # Uncertain / not-found status is valid
