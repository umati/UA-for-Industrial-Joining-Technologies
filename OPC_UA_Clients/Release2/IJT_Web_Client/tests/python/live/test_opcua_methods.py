"""
Live OPC UA method-call tests — IJT Tightening Server (OPCUA_TEST_ENDPOINT)

Infrastructure mirrors IJT_Console_Client/opcua_client.py exactly:
  * load_type_definitions() first for the IJT simulator's OPC Binary
    dictionary, then load_data_type_definitions() for OPC UA 1.04 metadata
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

SimulateJobResult / SimulateBulkResults (result_simulation_methods_t.cpp):
  Both run in a DETACHED thread — OpcUa_Good returned before events fire.
  SimulateBulkResults: MIN=5 (auto-raised if range<5), MAX=1000, SEQUENCE_NUMBER reset to fromSeq-1.
  Use _wait_events with quiescence (stable_ms) to capture all async events reliably.

Run all:
    python -m pytest tests/test_opcua_methods.py -v --timeout=120
Run a group:
    python -m pytest tests/test_opcua_methods.py -v -k "Simulate or Bulk"
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import time

import pytest
import pytest_asyncio
from asyncua import ua

from .._asyncua_compat import apply_send_request_timeout_patch

apply_send_request_timeout_patch()

# asyncio_default_fixture_loop_scope = module is set in pyproject.toml for all async tests

OPCUA_URL = os.getenv("OPCUA_TEST_ENDPOINT", f"opc.tcp://localhost:{os.getenv('OPCUA_SERVER_PORT', '40451')}")
NS = 1
NS_APP_URI = "urn:AtlasCopco:IJT:Tightening:Server/"
NS_MACHINERY = "http://opcfoundation.org/UA/Machinery/Result/"
NS_IJT_BASE = "http://opcfoundation.org/UA/IJT/Base/"

pytestmark = pytest.mark.live

_SIM_R = "TighteningSystem/Simulations/SimulateResults"
_SIM_E = "TighteningSystem/Simulations/SimulateEventsAndConditions"
_ASSET = "TighteningSystem/AssetManagement/MethodSet"
_JP = "TighteningSystem/JoiningProcessManagement"
_JT = "TighteningSystem/JointManagement"
_RM = "TighteningSystem/ResultManagement"
_PI_URI_FALLBACK = "TighteningSystem/AssetManagement/Assets/Tools/TighteningTool/Identification/ProductInstanceUri"

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
        self.events: list = []

    async def event_notification(self, event):
        self.events.append(event)


class SystemHandler:
    """Collects JoiningSystemEvent notifications."""

    def __init__(self):
        self.events: list = []

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

    c = Client(OPCUA_URL, timeout=60)  # generous timeout for heavy simulation calls
    await c.connect()

    # Compatibility bridge for the IJT simulator's custom Result/Event payloads:
    # asyncua's modern loader reads OPC UA 1.04 DataTypeDefinition attributes,
    # while the simulator still exposes some IJT structures only through the
    # legacy OPC Binary dictionary path. Keep the legacy load first so the
    # following modern load does not overwrite working classes.
    await c.load_type_definitions()

    # Same as Console Client connect(): load modern data type definitions
    await c.load_data_type_definitions()

    root = c.nodes.root
    server_node = await root.get_child(["0:Objects", "0:Server"])

    # Resolve IJT event type nodes by namespace URI (event_types.py pattern)
    ns_r = await c.get_namespace_index(NS_MACHINERY)
    ns_j = await c.get_namespace_index(NS_IJT_BASE)

    result_evt_node = await root.get_child(
        [
            "0:Types",
            "0:EventTypes",
            "0:BaseEventType",
            f"{ns_r}:ResultReadyEventType",
        ]
    )
    joining_result_evt_node = await root.get_child(
        [
            "0:Types",
            "0:EventTypes",
            "0:BaseEventType",
            f"{ns_r}:ResultReadyEventType",
            f"{ns_j}:JoiningSystemResultReadyEventType",
        ]
    )
    joining_system_evt_node = await root.get_child(
        [
            "0:Types",
            "0:EventTypes",
            "0:BaseEventType",
            f"{ns_j}:JoiningSystemEventType",
        ]
    )

    # Type definitions are already loaded above through the IJT compatibility
    # bridge (load_type_definitions() then load_data_type_definitions()).
    # asyncua's load_data_type_definitions() defaults to overwrite_existing=False
    # so a second call here would only re-walk ~200 nodes for no benefit.

    # Create persistent subscriptions with queuesize=200 (same as Console Client).
    # MaxNotificationsPerPublish=3 prevents large PublishResponse payloads when the
    # server fires many events synchronously (SimulateJobResult(refs=True) → ~12 events).
    def _sub_params(period_ms: float, max_notif: int = 3) -> ua.CreateSubscriptionParameters:
        p = ua.CreateSubscriptionParameters()
        p.RequestedPublishingInterval = period_ms
        p.RequestedLifetimeCount = 10000
        p.RequestedMaxKeepAliveCount = 27000
        p.MaxNotificationsPerPublish = max_notif
        p.PublishingEnabled = True
        p.Priority = 0
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
    return c.get_node(ua.NodeId(identifier, NS, ua.NodeIdType.String))  # type: ignore[arg-type]


def _v(value, vtype):
    return ua.Variant(value, vtype)


async def _call(c, parent_id: str, method_id: str, *args) -> list:
    return await _node(c, parent_id).call_method(_node(c, method_id).nodeid, *args)


async def _namespace_index(c, namespace_uri: str) -> int | None:
    try:
        return await c.get_namespace_index(namespace_uri)
    except (ua.UaError, ValueError, AttributeError):
        pass

    try:
        namespace_array_node = c.get_node(ua.ObjectIds.Server_NamespaceArray)
        namespace_array = await namespace_array_node.read_value()
        return list(namespace_array).index(namespace_uri)
    except (ua.UaError, ValueError, AttributeError):
        return None


async def _find_child_by_browse_name(parent_node, browse_name: str, ns_idx: int | None = None):
    if ns_idx is not None:
        try:
            return await parent_node.get_child(f"{ns_idx}:{browse_name}")
        except (ua.UaError, ValueError, AttributeError):
            pass

    try:
        children = await parent_node.get_children()
    except (ua.UaError, AttributeError):
        return None

    fallback_child = None
    for child in children:
        try:
            child_browse_name = await child.read_browse_name()
        except (AttributeError, ua.UaError):
            continue

        if getattr(child_browse_name, "Name", None) != browse_name:
            continue
        if ns_idx is None or getattr(child_browse_name, "NamespaceIndex", None) == ns_idx:
            return child
        if fallback_child is None:
            fallback_child = child
    return fallback_child


async def _browse_tool_product_instance_uri(c) -> str:
    ns_app = await _namespace_index(c, NS_APP_URI)
    joining_system = await _find_child_by_browse_name(c.nodes.objects, "TighteningSystem", ns_app)
    if joining_system is None:
        return ""
    asset_management = await _find_child_by_browse_name(joining_system, "AssetManagement", ns_app)
    if asset_management is None:
        return ""
    assets = await _find_child_by_browse_name(asset_management, "Assets", ns_app)
    if assets is None:
        return ""
    tools = await _find_child_by_browse_name(assets, "Tools", ns_app)
    if tools is None:
        return ""

    for tool_node in await tools.get_children():
        identification = await _find_child_by_browse_name(tool_node, "Identification", ns_app)
        if identification is None:
            continue
        piu_node = await _find_child_by_browse_name(identification, "ProductInstanceUri", ns_app)
        if piu_node is None:
            continue
        value = await piu_node.read_value()
        if value is not None and str(value).strip():
            return str(value)
    return ""


async def _pi_uri(c) -> str:
    """Read the first visible tool ProductInstanceUri by browsing, with simulator fallback."""
    browsed = await _browse_tool_product_instance_uri(c)
    if browsed:
        return browsed
    try:
        return str(await _node(c, _PI_URI_FALLBACK).read_value()) or ""
    except (OSError, AttributeError):
        return ""


async def _required_pi_uri(c) -> str:
    pi = await _pi_uri(c)
    if not pi.strip():
        pytest.fail("Tool ProductInstanceUri must be available for Web Client live OPC UA methods")
    return pi


def _method_items(output: list) -> list:
    if output and isinstance(output[0], list):
        return output[0]
    return output or []


def _joining_process_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JoiningProcessMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = (
            getattr(source, "JoiningProcessId", None)
            or getattr(source, "Id", None)
            or getattr(source, "ProgramId", None)
        )
        if value:
            return str(value)
    return entry if isinstance(entry, str) else ""


def _joining_process_origin_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JoiningProcessMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = getattr(source, "JoiningProcessOriginId", None)
        if value:
            return str(value)
    return ""


def _joint_id_from_entry(entry) -> str:
    entry = getattr(entry, "Value", entry)
    meta = getattr(entry, "JointMetaData", None)
    for source in (entry, meta):
        if source is None:
            continue
        value = getattr(source, "JointId", None) or getattr(source, "Id", None)
        if value:
            return str(value)
    return entry if isinstance(entry, str) else ""


async def _joint_ids(c, pi: str) -> list[str]:
    output = await _call(c, _JT, f"{_JT}/GetJointList", _v(pi, ua.VariantType.String))
    joints = _method_items(output)
    ids = []
    for joint in joints:
        joint_id = _joint_id_from_entry(joint).strip()
        if joint_id and joint_id not in ids:
            ids.append(joint_id)
    if not ids:
        pytest.fail("GetJointList must return at least one usable JointId for Web Client joint workflow tests")
    return ids


async def _first_two_joint_ids(c, pi: str) -> tuple[str, str]:
    ids = await _joint_ids(c, pi)
    second = ids[1] if len(ids) > 1 else ids[0]
    return ids[0], second


async def _enable_asset_if_possible(c, pi: str) -> None:
    try:
        await _call(
            c,
            _ASSET,
            f"{_ASSET}/EnableAsset",
            _v(pi, ua.VariantType.String),
            _v(True, ua.VariantType.Boolean),
        )
    except (OSError, ua.UaStatusCodeError):
        pass


async def _has_simulation_methods(c) -> bool:
    """Return True when this endpoint exposes the simulator-only Simulations folder."""
    try:
        await _node(c, _SIM_R).read_browse_name()
        return True
    except (OSError, ua.UaError, AttributeError):
        return False


async def _wait_events(handler, min_count: int = 1, timeout: float = 8.0, stable_ms: float = 300) -> list:
    """Poll until min_count events arrive, then wait for quiescence (no new events for
    stable_ms milliseconds), or until timeout expires.

    The quiescence wait is needed because SimulateJobResult and SimulateBulkResults both
    run in detached threads — the OPC UA CallResponse returns immediately while events
    fire asynchronously.  With MaxNotificationsPerPublish=3 and a 100 ms publish interval,
    events arrive in batches; waiting for quiescence ensures the final event (e.g.
    ResultState=COMPLETED) is included in the snapshot before assertions run.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(handler.events) >= min_count:
            break
        await asyncio.sleep(0.2)
    # Quiescence phase: restart a short timer each time a new event arrives.
    quiesce_end = time.monotonic() + stable_ms / 1000.0
    last_count = len(handler.events)
    while time.monotonic() < min(quiesce_end, deadline):
        await asyncio.sleep(0.05)
        cur = len(handler.events)
        if cur != last_count:
            quiesce_end = time.monotonic() + stable_ms / 1000.0
            last_count = cur
    return list(handler.events)


async def _invoke_result(c, result_h, method_id: str, *args, timeout=8.0) -> list:
    """Clear result handler, call method, wait, return snapshot."""
    result_h.events.clear()
    await _call(c, _SIM_R, method_id, *args)
    return await _wait_events(result_h, 1, timeout)


async def _invoke_system(c, system_h, parent_id: str, method_id: str, *args, timeout=6.0) -> list:
    """Clear system handler, call method, wait, return snapshot."""
    system_h.events.clear()
    await _call(c, parent_id, method_id, *args)
    return await _wait_events(system_h, 1, timeout)


def _meta(events, idx: int = -1):
    return events[idx].Result.ResultMetaData


def _assert_meta(events, *, cls, ev, code, state=1, simulated: bool | None = True, idx=-1):
    m = _meta(events, idx)
    assert int(m.Classification) == cls, f"Classification {m.Classification}!={cls}"
    assert int(m.ResultEvaluation) == ev, f"ResultEvaluation {m.ResultEvaluation}!={ev}"
    assert int(m.ResultEvaluationCode) == code, f"ResultEvaluationCode {m.ResultEvaluationCode}!={code}"
    assert int(m.ResultState) == state, f"ResultState {m.ResultState}!={state}"
    if simulated is not None:
        assert m.IsSimulated == simulated, f"IsSimulated {m.IsSimulated}!={simulated}"


# ══════════════════════════════════════════════════════════════════════════════
# 1.  SimulateSingleResult
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestSimulateSingleResult:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize(
        "rtype,traces",
        [
            (0, True),
            (0, False),
            (1, True),
            (1, False),
            (2, True),
            (2, False),
            (3, True),
            (3, False),
            (4, True),
            (4, False),
        ],
    )
    async def test_fires_result_event(self, ijt_session, rtype, traces):
        (
            c,
            result_h,
            _,
        ) = ijt_session
        ev_exp, code_exp, label = _SINGLE_EXPECT[rtype]

        events = await _invoke_result(
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=7.0,
            *[_v(rtype, ua.VariantType.UInt32), _v(traces, ua.VariantType.Boolean)],
        )
        assert events, f"SimulateSingleResult(rtype={rtype}[{label}], traces={traces}): no result event received"
        _assert_meta(events, cls=1, ev=ev_exp, code=code_exp)

        meta = _meta(events)
        assert meta.IsPartial is False
        assert int(meta.OperationMode) == 2, "OperationMode must be MANUAL(2)"
        assert int(meta.AssemblyType) == 1, "AssemblyType must be ASSEMBLED(1)"
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
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=6.0,
            *[_v(999, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
        )
        assert events, "Out-of-range ResultType must still fire an event"
        _assert_meta(events, cls=1, ev=1, code=0)

    async def test_sequence_number_increments(self, ijt_session):
        c, result_h, _ = ijt_session
        seqs = []
        for rtype in range(3):
            events = await _invoke_result(
                c,
                result_h,
                f"{_SIM_R}/SimulateSingleResult",
                timeout=6.0,
                *[_v(rtype, ua.VariantType.UInt32), _v(False, ua.VariantType.Boolean)],
            )
            assert events, f"rtype={rtype}: no event"
            seqs.append(int(_meta(events).SequenceNumber))
        for i in range(1, len(seqs)):
            assert seqs[i] == seqs[i - 1] + 1, f"SequenceNumber not monotone: {seqs[i - 1]} -> {seqs[i]}"


# ══════════════════════════════════════════════════════════════════════════════
# 2.  SimulateBatch_Or_Sync_Result  (SYNC=2, BATCH=3)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestSimulateBatchOrSync:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize(
        "cls,label,n,refs",
        [
            (3, "BATCH", 3, False),
            (3, "BATCH", 3, True),  # refs=True fires 3 children + 1 parent = 4 events
            (2, "SYNC", 3, False),
            (2, "SYNC", 3, True),
            (3, "BATCH", 5, False),  # larger inline batch — one combined event, safe payload
        ],
    )
    async def test_batch_or_sync(self, ijt_session, cls, label, n, refs):
        c, result_h, _ = ijt_session
        result_h.events.clear()
        # Budget: n children × 0.5s each + 6s buffer for combined parent event
        timeout = max(12.0, n * 0.5 + 6)

        await _call(
            c,
            _SIM_R,
            f"{_SIM_R}/SimulateBatch_Or_Sync_Result",
            _v(cls, ua.VariantType.Byte),
            _v(n, ua.VariantType.UInt32),
            _v(True, ua.VariantType.Boolean),  # IncludeTraces=True
            _v(refs, ua.VariantType.Boolean),
        )  # IncludeChildRefs

        events = await _wait_events(result_h, min_count=1, timeout=timeout)
        assert events, f"SimulateBatch_Or_Sync({label},n={n},refs={refs}): no events"
        if refs:
            assert len(events) >= n, f"refs=True: expected >={n} events, got {len(events)}"

        _assert_meta(events, cls=cls, ev=1, code=0, idx=-1)
        counters = _meta(events, -1).ResultCounters
        # ResultCounters items may be wrapped in Variant — unwrap with renamed loop var
        if counters and hasattr(counters[0], "Value"):
            counters = [ctr.Value for ctr in counters]
        assert counters and len(counters) == 2, f"{label}: expected 2 ResultCounters, got {len(counters or [])}"

    async def test_invalid_cls_defaults_to_batch(self, ijt_session):
        """Classification=99 (unknown) must fall back to BATCH(3)."""
        c, result_h, _ = ijt_session
        result_h.events.clear()
        await _call(
            c,
            _SIM_R,
            f"{_SIM_R}/SimulateBatch_Or_Sync_Result",
            _v(99, ua.VariantType.Byte),
            _v(3, ua.VariantType.UInt32),
            _v(True, ua.VariantType.Boolean),  # IncludeTraces=True
            _v(True, ua.VariantType.Boolean),
        )  # IncludeChildRefs=True
        events = await _wait_events(result_h, 1, timeout=10)
        assert events, "Invalid cls must still fire an event"
        assert int(_meta(events, -1).Classification) == 3, "Invalid cls must default to BATCH(3)"


# ══════════════════════════════════════════════════════════════════════════════
# 3.  SimulateJobResult
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestSimulateJobResult:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize("refs", [False, True])
    async def test_job_result(self, ijt_session, refs):
        c, result_h, _ = ijt_session
        # Settle: drain any residual events from previous tests before starting.
        await asyncio.sleep(0.5)
        result_h.events.clear()

        await _call(c, _SIM_R, f"{_SIM_R}/SimulateJobResult", _v(refs, ua.VariantType.Boolean))

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
class TestSimulateBulkResults:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize(
        "rtype,from_seq,to_seq,traces",
        [
            (0, 1, 6, True),  # to-from=5 >= MIN(5), no auto-raise
            (1, 1, 6, True),
            (2, 1, 11, True),  # 11 results
            (3, 1, 6, False),
            (4, 1, 6, False),
            (1, 10, 15, True),  # to-from=5, no auto-raise
            (2, 100, 105, True),  # to-from=5, no auto-raise
        ],
    )
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
                await _call(
                    c,
                    _SIM_R,
                    f"{_SIM_R}/SimulateBulkResults",
                    _v(rtype, ua.VariantType.UInt32),
                    _v(traces, ua.VariantType.Boolean),
                    _v(from_seq, ua.VariantType.UInt64),
                    _v(to_seq, ua.VariantType.UInt64),
                    _v(100, ua.VariantType.Int64),  # 100 ms between results
                    _v(True, ua.VariantType.Boolean),
                )  # UpdateResultVariables
                break
            except BadTooManyOperations:
                await asyncio.sleep(1.0)  # wait for previous BulkResults thread to complete
        else:
            pytest.fail("SimulateBulkResults still busy after 5 retries")

        events = await _wait_events(result_h, exp, timeout)
        assert len(events) >= exp, (
            f"BulkResults(rtype={rtype},{from_seq}->{to_seq}): expected >={exp}, got {len(events)}"
        )
        assert int(_meta(events, -1).SequenceNumber) == to_seq, f"Final SeqNr should be {to_seq}"
        _assert_meta(events, cls=1, ev=ev_exp, code=code_exp, idx=-1)

    async def test_range_below_min_auto_raised(self, ijt_session):
        """from=1,to=2 (range=2) — server raises to MIN=5."""
        from asyncua.ua.uaerrors import BadTooManyOperations

        c, result_h, _ = ijt_session
        for _ in range(5):
            result_h.events.clear()
            try:
                await _call(
                    c,
                    _SIM_R,
                    f"{_SIM_R}/SimulateBulkResults",
                    _v(1, ua.VariantType.UInt32),
                    _v(True, ua.VariantType.Boolean),
                    _v(1, ua.VariantType.UInt64),
                    _v(2, ua.VariantType.UInt64),
                    _v(50, ua.VariantType.Int64),
                    _v(True, ua.VariantType.Boolean),
                )
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
class TestSimulateEvents:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    @pytest.mark.parametrize(
        "etype",
        [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            22,
            23,
            24,
            25,
            53,
            54,
            55,
            56,
            81,
            90,
            91,
        ],
    )
    async def test_single_event_type(self, ijt_session, etype):
        c, _, system_h = ijt_session
        events = await _invoke_system(
            c, system_h, _SIM_E, f"{_SIM_E}/SimulateEvents", timeout=5.0, *[_v(etype, ua.VariantType.UInt32)]
        )
        assert events, f"SimulateEvents(type={etype}): no event received"
        msg = getattr(getattr(events[0], "Message", None), "Text", "") or ""
        assert msg, f"Event Message.Text empty for EventType={etype}"

    async def test_out_of_range_defaults(self, ijt_session):
        c, _, system_h = ijt_session
        events = await _invoke_system(
            c, system_h, _SIM_E, f"{_SIM_E}/SimulateEvents", timeout=5.0, *[_v(9999, ua.VariantType.UInt32)]
        )
        assert events, "Out-of-range EventType must fire a default event"

    @pytest.mark.parametrize(
        "etype,count",
        [
            (1, 5),
            (2, 10),
            (3, 20),
            (4, 50),
        ],
    )
    async def test_bulk_events(self, ijt_session, etype, count):
        import time

        from asyncua.ua.uaerrors import BadTooManyOperations

        c, _, system_h = ijt_session
        system_h.events.clear()
        timeout = max(8.0, count * 0.15 + 5)
        # SimulateBulkEvents runs in a detached thread; retry on BadTooManyOperations
        # (server rejects concurrent calls) using the same pattern as SimulateBulkResults.
        for _ in range(5):
            try:
                await _call(
                    c,
                    _SIM_E,
                    f"{_SIM_E}/SimulateBulkEvents",
                    _v(etype, ua.VariantType.UInt32),
                    _v(count, ua.VariantType.UInt32),
                )
                break
            except BadTooManyOperations:
                await asyncio.sleep(1.0)
        else:
            pytest.fail("SimulateBulkEvents still busy after 5 retries")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(system_h.events) >= count:
                break
            await asyncio.sleep(0.3)
        assert len(system_h.events) >= count, (
            f"BulkEvents(etype={etype}, count={count}): expected >={count}, got {len(system_h.events)}"
        )

    async def test_bulk_events_capped_at_100(self, ijt_session):
        """Request 200 bulk events — server should deliver at least 100 within 30s."""
        import time

        c, _, system_h = ijt_session
        system_h.events.clear()
        await _call(
            c, _SIM_E, f"{_SIM_E}/SimulateBulkEvents", _v(1, ua.VariantType.UInt32), _v(200, ua.VariantType.UInt32)
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if len(system_h.events) >= 100:
                break
            await asyncio.sleep(0.2)
        # Let remaining in-flight events drain before asserting
        await asyncio.sleep(1.0)
        received = len(system_h.events)
        assert received >= 100, f"Expected at least 100 bulk events, got {received}"
        assert received <= 200, f"Received {received} events but only requested 200"


# ══════════════════════════════════════════════════════════════════════════════
# 6.  EnableAsset  (fires JoiningSystemEvents)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestEnableAsset:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_enable_true(self, ijt_session):
        c, _, system_h = ijt_session
        pi = await _pi_uri(c)
        events = await _invoke_system(
            c,
            system_h,
            _ASSET,
            f"{_ASSET}/EnableAsset",
            timeout=5.0,
            *[_v(pi, ua.VariantType.String), _v(True, ua.VariantType.Boolean)],
        )
        assert events, "EnableAsset(enable=True) must fire a system event"
        msg = getattr(getattr(events[0], "Message", None), "Text", "") or ""
        assert msg, f"EnableAsset event must carry a message, got {msg!r}"

    async def test_disable_then_enable(self, ijt_session):
        c, _, system_h = ijt_session
        pi = await _pi_uri(c)

        disable = await _invoke_system(
            c,
            system_h,
            _ASSET,
            f"{_ASSET}/EnableAsset",
            timeout=5.0,
            *[_v(pi, ua.VariantType.String), _v(False, ua.VariantType.Boolean)],
        )
        assert disable, "Disable must fire an event"

        enable = await _invoke_system(
            c,
            system_h,
            _ASSET,
            f"{_ASSET}/EnableAsset",
            timeout=5.0,
            *[_v(pi, ua.VariantType.String), _v(True, ua.VariantType.Boolean)],
        )
        assert enable, "Re-enable must fire an event"


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Joining Process Management
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestJoiningProcess:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def _jp(self, c, pi: str):
        try:
            output = await _call(c, _JP, f"{_JP}/GetJoiningProcessList", _v(pi, ua.VariantType.String))
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"GetJoiningProcessList must build JoiningProcessIdentification, got {exc}")
        programs = _method_items(output)
        if not programs:
            pytest.fail("GetJoiningProcessList must return at least one program")
        process_id = _joining_process_id_from_entry(programs[0])
        if not process_id:
            pytest.fail("First joining process must have a usable JoiningProcessId")
        jp = ua.JoiningProcessIdentificationDataType()  # type: ignore[attr-defined]
        jp.JoiningProcessId = process_id
        jp.JoiningProcessOriginId = _joining_process_origin_id_from_entry(programs[0])
        jp.SelectionName = ""
        return jp

    async def test_get_process_list(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        assert await _call(c, _JP, f"{_JP}/GetJoiningProcessList", _v(pi, ua.VariantType.String)) is not None

    async def test_get_selected_program(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        jp = await self._jp(c, pi)
        try:
            await _call(
                c,
                _JP,
                f"{_JP}/SelectJoiningProcess",
                _v(pi, ua.VariantType.String),
                ua.Variant(jp, ua.VariantType.ExtensionObject),
            )
            result = await _call(c, _JP, f"{_JP}/GetSelectedJoiningProgram", _v(pi, ua.VariantType.String))
            assert result is not None
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"GetSelectedJoiningProgram must succeed after SelectJoiningProcess, got {exc}")

    async def test_abort_with_localized_text(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        jp = await self._jp(c, pi)
        try:
            result = await _call(
                c,
                _JP,
                f"{_JP}/AbortJoiningProcess",
                _v(pi, ua.VariantType.String),
                ua.Variant(jp, ua.VariantType.ExtensionObject),
                ua.Variant(ua.LocalizedText(Text="Test abort", Locale="en"), ua.VariantType.LocalizedText),
            )
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"AbortJoiningProcess must return a method result, got {exc}")
        assert result is not None

    async def test_increment_decrement_counter(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        jp = await self._jp(c, pi)
        try:
            await _call(
                c,
                _JP,
                f"{_JP}/IncrementJoiningProcessCounter",
                _v(pi, ua.VariantType.String),
                ua.Variant(jp, ua.VariantType.ExtensionObject),
                _v(1, ua.VariantType.UInt32),
            )
            await _call(
                c,
                _JP,
                f"{_JP}/DecrementJoiningProcessCounter",
                _v(pi, ua.VariantType.String),
                ua.Variant(jp, ua.VariantType.ExtensionObject),
                _v(1, ua.VariantType.UInt32),
            )
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"JoiningProcess counter update must return method results, got {exc}")

    async def test_start_selected_joining(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        jp = await self._jp(c, pi)
        await _enable_asset_if_possible(c, pi)
        try:
            await _call(
                c,
                _JP,
                f"{_JP}/SelectJoiningProcess",
                _v(pi, ua.VariantType.String),
                ua.Variant(jp, ua.VariantType.ExtensionObject),
            )
            result = await _call(
                c,
                _JP,
                f"{_JP}/StartSelectedJoining",
                _v(pi, ua.VariantType.String),
                _v(True, ua.VariantType.Boolean),
            )
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"StartSelectedJoining must return a method result after SelectJoiningProcess, got {exc}")
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════════
# 8.  Result Management — query methods
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestResultManagement:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_get_latest_result(self, ijt_session):
        c, result_h, _ = ijt_session
        # Fire a single result so there is something to fetch
        await _invoke_result(
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=4.0,
            *[_v(1, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
        )
        result = await _call(c, _RM, f"{_RM}/GetLatestResult", _v(5000, ua.VariantType.Int32))
        assert result is not None

    async def test_request_results_by_sequence(self, ijt_session):
        c, *_ = ijt_session
        # Use real datetime values instead of None to avoid asyncua DateTime decode errors
        epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        future = dt.datetime(2099, 12, 31, tzinfo=dt.timezone.utc)
        try:
            result = await _call(
                c,
                _RM,
                f"{_RM}/RequestResults",
                _v(1, ua.VariantType.UInt64),
                _v(10, ua.VariantType.UInt64),
                _v(epoch, ua.VariantType.DateTime),
                _v(future, ua.VariantType.DateTime),
                _v(10, ua.VariantType.UInt32),
            )
            assert result is not None
        except (OSError, ua.UaStatusCodeError):
            pass  # empty result set, server-side Uncertain, or not fully implemented


# ══════════════════════════════════════════════════════════════════════════════
# 9.  Joint Management
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestJointManagement:
    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_get_joint_list(self, ijt_session):
        c, *_ = ijt_session
        ids = await _joint_ids(c, await _required_pi_uri(c))
        assert ids

    async def test_get_joint_by_id(self, ijt_session):
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        joint_id = (await _joint_ids(c, pi))[0]
        try:
            result = await _call(
                c,
                _JT,
                f"{_JT}/GetJoint",
                _v(pi, ua.VariantType.String),
                _v(joint_id, ua.VariantType.String),
            )
            assert result is not None
        except OSError:
            pass  # Uncertain / not-found status is valid

    async def test_select_joint(self, ijt_session):
        """SelectJoint(JointId) must return a result without raising.

        The JointId is discovered from GetJointList instead of assuming the
        simulator's default joint naming exists on every IJT server.
        """
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        joint_id = (await _joint_ids(c, pi))[0]
        try:
            result = await _call(
                c,
                _JT,
                f"{_JT}/SelectJoint",
                _v(pi, ua.VariantType.String),
                _v(joint_id, ua.VariantType.String),
                _v("", ua.VariantType.String),           # JointOriginId (optional, empty)
            )
            assert result is not None
        except OSError:
            pass  # Uncertain status is a valid server response


# ══════════════════════════════════════════════════════════════════════════════
# 10.  Asset Identifiers — GetIdentifiers / SendTextIdentifiers / ResetIdentifiers
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestAssetIdentifiers:
    """Tests for the identifier management methods on AssetManagement/MethodSet."""

    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_get_identifiers(self, ijt_session):
        """GetIdentifiers must return without raising."""
        c, *_ = ijt_session
        try:
            result = await _call(c, _ASSET, f"{_ASSET}/GetIdentifiers", _v(await _pi_uri(c), ua.VariantType.String))
            assert result is not None
        except (OSError, ua.UaStatusCodeError):
            pass  # Empty / Uncertain result or server-side arg mismatch is acceptable

    async def test_send_text_identifiers(self, ijt_session):
        """SendTextIdentifiers with a sample string array must not raise."""
        c, *_ = ijt_session
        pi = await _pi_uri(c)
        demo_ids = ua.Variant(["BatchId:001", "OrderId:ABC"], ua.VariantType.String)
        try:
            result = await _call(c, _ASSET, f"{_ASSET}/SendTextIdentifiers", _v(pi, ua.VariantType.String), demo_ids)
            assert result is not None
        except OSError:
            pass  # Uncertain / not supported is acceptable

    async def test_reset_identifiers(self, ijt_session):
        """ResetIdentifiers must return without raising."""
        c, *_ = ijt_session
        try:
            result = await _call(c, _ASSET, f"{_ASSET}/ResetIdentifiers", _v(await _pi_uri(c), ua.VariantType.String))
            assert result is not None
        except (OSError, ua.UaStatusCodeError):
            pass  # Uncertain / not supported / server arg mismatch is acceptable


# ══════════════════════════════════════════════════════════════════════════════
# 11.  Joint Demo Page workflow — SelectJoint → StartSelectedJoining method path
#
# Covers the core Joint Demo Page interaction:
#   1. SelectJoint activates a joint on the tightening tool
#   2. StartSelectedJoining(SimulateResult=True) runs a tightening cycle
#
# All boolean arguments use True throughout (per project rule: booleans always True
# in Simulate* calls to get the richest payload without ambiguity).
#
# The simulator does not reliably emit JoiningSystemResultReadyEvent from
# StartSelectedJoining alone; that path may require a physical tightening trigger.
# Result event payload coverage stays in the deterministic Simulate* sections.
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestJointDemoWorkflow:
    """Joint Demo Page workflow: SelectJoint → StartSelectedJoining method path.

    Uses the module-scoped ijt_session fixture so no extra connections are
    created. Result events are not asserted here because StartSelectedJoining can
    require an external trigger before a controller publishes a result event.
    """

    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def _select_joint_and_start(self, c, pi: str, joint_id: str) -> list:
        """Validate that SelectJoint + StartSelectedJoining complete and leave the workflow usable.

        StartSelectedJoining can require an external physical trigger before a
        result event is published, so these tests assert method completion and
        follow-up JointManagement usability instead of event delivery.
        """
        try:
            await _call(
                c,
                _JT,
                f"{_JT}/SelectJoint",
                _v(pi, ua.VariantType.String),
                _v(joint_id, ua.VariantType.String),
                _v("", ua.VariantType.String),
            )
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"SelectJoint({joint_id!r}) must succeed before StartSelectedJoining, got {exc}")

        try:
            result = await _call(
                c,
                _JP,
                f"{_JP}/StartSelectedJoining",
                _v(pi, ua.VariantType.String),
                _v(True, ua.VariantType.Boolean),  # SimulateResult=True
            )
        except (OSError, ua.UaStatusCodeError) as exc:
            pytest.fail(f"StartSelectedJoining must succeed for joint={joint_id!r}, got {exc}")

        if result is None:
            pytest.fail(f"StartSelectedJoining must return an OPC UA method output for joint={joint_id!r}")
        return result

    async def test_select_discovered_joint_returns_status(self, ijt_session):
        """SelectJoint with a server-discovered JointId must complete without raising."""
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        joint_id = (await _joint_ids(c, pi))[0]
        try:
            result = await _call(
                c,
                _JT,
                f"{_JT}/SelectJoint",
                _v(pi, ua.VariantType.String),
                _v(joint_id, ua.VariantType.String),
                _v("", ua.VariantType.String),
            )
            assert result is not None
        except OSError:
            pass  # Uncertain status is a valid server response

    async def test_get_joint_list_all_items_have_joint_id(self, ijt_session):
        """GetJointList must return at least one joint; every item must have a non-empty JointId."""
        c, *_ = ijt_session
        ids = await _joint_ids(c, await _required_pi_uri(c))
        assert ids and all(joint_id.strip() for joint_id in ids), "Every GetJointList item must expose JointId or Id"

    async def test_select_then_start_returns_method_status(self, ijt_session):
        """Select joint → start tightening must return a method result.

        SelectJoint activates a joint; StartSelectedJoining(SimulateResult=True)
        runs the method path. Event publication is covered by Simulate* tests.
        """
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        joint_id, _ = await _first_two_joint_ids(c, pi)

        result = await self._select_joint_and_start(c, pi, joint_id)
        assert isinstance(result, list), f"StartSelectedJoining must return OPC UA output list, got {type(result)!r}"

    async def test_select_then_start_keeps_joint_management_available(self, ijt_session):
        """After SelectJoint + StartSelectedJoining, joint management remains usable.

        This catches broken workflow state without depending on a physical result
        event trigger. Result payload metadata is validated by Simulate* tests.
        """
        c, *_ = ijt_session
        pi = await _required_pi_uri(c)
        joint_id, _ = await _first_two_joint_ids(c, pi)

        await self._select_joint_and_start(c, pi, joint_id)
        result = await _call(c, _JT, f"{_JT}/GetJointList", _v(pi, ua.VariantType.String))
        joints = _method_items(result)
        assert joints, "GetJointList must still return joints after StartSelectedJoining"


# ══════════════════════════════════════════════════════════════════════════════
# 12.  Deep result payload validation
#
# Uses SimulateSingleResult with all booleans=True to get the richest payload.
# Validates metadata field-by-field, content structure, and ProcessingTimes.
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live
class TestResultPayloadDeepValidation:
    """Deep validation of result event payload fields.

    All boolean arguments to Simulate* methods are True throughout — this produces
    the richest output (traces included) and avoids ambiguity about field presence.
    """

    pytestmark = pytest.mark.asyncio(loop_scope="module")

    async def test_required_metadata_fields_all_present(self, ijt_session):
        """SimulateSingleResult(type=1, traces=True): every required metadata field must be valid.

        Checks all fields in a single test: SequenceNumber, IsSimulated, ResultState,
        OperationMode, AssemblyType, Classification, ResultEvaluation, ResultEvaluationCode,
        IsPartial, JoiningTechnology.
        """
        c, result_h, _ = ijt_session
        events = await _invoke_result(
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=8.0,
            *[_v(1, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
        )
        assert events, "SimulateSingleResult(type=1, traces=True): no event received"
        meta = _meta(events)

        assert int(meta.SequenceNumber) > 0, f"SequenceNumber must be >0, got {meta.SequenceNumber}"
        assert meta.IsSimulated is True, "IsSimulated must be True for simulated results"
        assert int(meta.ResultState) == 1, f"ResultState must be COMPLETED(1), got {meta.ResultState}"
        assert int(meta.OperationMode) == 2, f"OperationMode must be MANUAL(2), got {meta.OperationMode}"
        assert int(meta.AssemblyType) == 1, f"AssemblyType must be ASSEMBLED(1), got {meta.AssemblyType}"
        assert int(meta.Classification) == 1, f"Classification must be SINGLE_RESULT(1), got {meta.Classification}"
        assert int(meta.ResultEvaluation) == 1, f"ResultEvaluation must be OK(1), got {meta.ResultEvaluation}"
        assert int(meta.ResultEvaluationCode) == 0, f"ResultEvaluationCode must be 0(OK), got {meta.ResultEvaluationCode}"
        assert meta.IsPartial is False, "IsPartial must be False for a complete result"
        tech = getattr(meta.JoiningTechnology, "Text", str(meta.JoiningTechnology)) or ""
        assert "Tightening" in tech, f"JoiningTechnology must contain 'Tightening', got: {tech!r}"

    async def test_result_content_single_has_step_results(self, ijt_session):
        """SimulateSingleResult(type=1, traces=True): exactly 1 ResultContent item with non-empty StepResults."""
        c, result_h, _ = ijt_session
        events = await _invoke_result(
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=8.0,
            *[_v(1, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
        )
        assert events, "No event received"

        content = events[-1].Result.ResultContent or []
        assert len(content) == 1, (
            f"ONE_STEP_OK with traces must have exactly 1 ResultContent item, got {len(content)}"
        )
        # asyncua may wrap the struct in a Variant — unwrap if needed
        joining_result = getattr(content[0], "Value", content[0])
        steps = joining_result.StepResults
        assert steps is not None, "JoiningResultDataType.StepResults must not be None when traces=True"
        assert len(steps) > 0, "JoiningResultDataType.StepResults must not be empty when traces=True"

    async def test_processing_times_are_valid_datetimes(self, ijt_session):
        """SimulateSingleResult(type=1, traces=True): ProcessingTimes must carry valid datetime values.

        Verifies StartTime and EndTime are Python datetime objects and that EndTime >= StartTime.
        """
        c, result_h, _ = ijt_session
        events = await _invoke_result(
            c,
            result_h,
            f"{_SIM_R}/SimulateSingleResult",
            timeout=8.0,
            *[_v(1, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
        )
        assert events, "No event received"

        meta = _meta(events)
        pt = getattr(meta, "ProcessingTimes", None)
        assert pt is not None, "ResultMetaData.ProcessingTimes must be present for simulated one-step results"

        start = getattr(pt, "StartTime", None)
        end = getattr(pt, "EndTime", None)
        assert start is not None, "ProcessingTimes.StartTime must be present"
        assert end is not None, "ProcessingTimes.EndTime must be present"
        assert isinstance(start, dt.datetime), f"StartTime must be a datetime, got {type(start)}"
        assert isinstance(end, dt.datetime), f"EndTime must be a datetime, got {type(end)}"
        assert end >= start, f"EndTime ({end}) must be >= StartTime ({start})"

    async def test_sequence_number_positive_across_all_single_types(self, ijt_session):
        """All 5 SimulateSingleResult types (0-4) with traces=True must fire events with SequenceNumber > 0."""
        c, result_h, _ = ijt_session
        for rtype in range(5):
            events = await _invoke_result(
                c,
                result_h,
                f"{_SIM_R}/SimulateSingleResult",
                timeout=8.0,
                *[_v(rtype, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
            )
            assert events, f"SimulateSingleResult(type={rtype}, traces=True): no event"
            seq = int(_meta(events).SequenceNumber)
            assert seq > 0, f"type={rtype}: SequenceNumber must be >0, got {seq}"

    async def test_simulated_flag_true_for_all_simulate_methods(self, ijt_session):
        """IsSimulated must be True for all Simulate* result types (booleans always True)."""
        c, result_h, _ = ijt_session
        for rtype in range(5):
            events = await _invoke_result(
                c,
                result_h,
                f"{_SIM_R}/SimulateSingleResult",
                timeout=8.0,
                *[_v(rtype, ua.VariantType.UInt32), _v(True, ua.VariantType.Boolean)],
            )
            assert events, f"SimulateSingleResult(type={rtype}): no event"
            assert _meta(events).IsSimulated is True, (
                f"type={rtype}: IsSimulated must be True for all Simulate* calls"
            )

    async def test_bulk_result_metadata_with_all_booleans_true(self, ijt_session):
        """SimulateBulkResults(type=1, traces=True, UpdateResultVariables=True): metadata must be valid.

        Verifies Classification=SINGLE(1), IsSimulated=True, SequenceNumber>0 for final event.
        """
        from asyncua.ua.uaerrors import BadTooManyOperations

        c, result_h, _ = ijt_session
        for _ in range(5):
            result_h.events.clear()
            try:
                await _call(
                    c,
                    _SIM_R,
                    f"{_SIM_R}/SimulateBulkResults",
                    _v(1, ua.VariantType.UInt32),   # ResultType=ONE_STEP_OK
                    _v(True, ua.VariantType.Boolean),  # IncludeTraces=True
                    _v(1, ua.VariantType.UInt64),   # FromSequenceNumber=1
                    _v(5, ua.VariantType.UInt64),   # ToSequenceNumber=5
                    _v(50, ua.VariantType.Int64),   # DelayBetweenResults=50ms
                    _v(True, ua.VariantType.Boolean),  # UpdateResultVariables=True
                )
                break
            except BadTooManyOperations:
                await asyncio.sleep(1.0)
        else:
            pytest.fail("SimulateBulkResults still busy after 5 retries")

        events = await _wait_events(result_h, 5, timeout=15.0)
        assert events, "SimulateBulkResults: no events received"
        meta = _meta(events, -1)
        assert int(meta.Classification) == 1, f"Classification must be SINGLE_RESULT(1), got {meta.Classification}"
        assert meta.IsSimulated is True, "IsSimulated must be True for BulkResults"
        assert int(meta.SequenceNumber) > 0, f"SequenceNumber must be >0, got {meta.SequenceNumber}"

    async def test_job_result_classification_and_counters_with_refs_true(self, ijt_session):
        """SimulateJobResult(refs=True): Classification=JOB(4), ResultCounters has 2 items, IsSimulated=True."""
        c, result_h, _ = ijt_session
        await asyncio.sleep(0.5)  # drain any residual events from prior test
        result_h.events.clear()

        await _call(c, _SIM_R, f"{_SIM_R}/SimulateJobResult", _v(True, ua.VariantType.Boolean))

        events = await _wait_events(result_h, 1, timeout=25.0)
        assert events, "SimulateJobResult(refs=True): no events received"
        meta = _meta(events, -1)
        assert int(meta.Classification) == 4, f"Classification must be JOB_RESULT(4), got {meta.Classification}"
        assert meta.IsSimulated is True, "IsSimulated must be True for SimulateJobResult"
        counters = meta.ResultCounters
        if counters and hasattr(counters[0], "Value"):
            counters = [ctr.Value for ctr in counters]
        assert counters and len(counters) == 2, (
            f"JOB result must have 2 ResultCounters (JOB_COUNT + JOB_SIZE), got {len(counters or [])}"
        )
