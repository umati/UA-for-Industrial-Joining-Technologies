"""
conftest.py — Session and module-scoped pytest fixtures for the OPC UA IJT test suite.
Session fixtures are created once per test run and shared across all tests that
perform read-only address-space discovery.
opcua_client is module-scoped — one OPC UA connection per test file.  This cuts
CI time from ~27 min to ~7 min by avoiding ~400 individual connection handshakes
(each takes ~3 s on GitHub Actions Windows runners).
subscription_client is module-scoped — one OPC UA connection per test file that
uses event subscriptions.  Event subscription isolation is maintained per-test by
EventCollector (which subscribes and unsubscribes on every call), so no cross-test
event noise occurs.  Promoting from function scope to module scope saves ~420 s
(~7 min) by eliminating 152 redundant TCP handshakes at ~3 s each.
All async fixtures require pytest-asyncio with asyncio_mode = "auto" (pyproject.toml).
Design rules enforced here:
  - JoiningSystem is discovered by HasTypeDefinition, never by browse name.
  - Namespace indices are resolved once and cached in ns_indices dict.
  - Two separate client fixtures prevent asyncua concurrency issues with subscriptions.
  - Module-scoped clients depend on session_client (not managed_server) so that
    load_type_definitions() and load_data_type_definitions() run exactly once
    per session — not once per module.
    This cuts per-test connection overhead from ~4 s to ~0.5 s.
"""
# pylint: disable=redefined-outer-name,unused-argument,broad-exception-caught

import contextlib
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from asyncua import Client

from helpers.cu_coverage_report import CuCoverageReportRecorder
from helpers.profile_loader import get_skip_reason, load_all_cus_from_facets, load_supported_cus

# Loaded once at collection time — all tests see the same supported-CU set.
# None means "no capabilities file / no gating" — all tests run.
# frozenset() means "file present but no CUs supported" — all CU-gated tests skip.
# Override the config file path via OPCUA_CAPABILITIES_FILE env var.
_SUPPORTED_CUS: frozenset[str] | None = None


def _deletes_disabled() -> bool:
    """Return True when the test session must preserve existing temp artifacts."""
    return os.environ.get("IJT_RUNNER_NO_DELETE", "").strip().lower() in {"1", "true", "yes", "on"}


def pytest_configure(config):
    """Register markers, load server capability profile, and set up fixture paths.

    Reads server_capabilities.yaml (or OPCUA_CAPABILITIES_FILE env var) once.
    Tests decorated with @pytest.mark.requires_cu(CU.SOME_KEY) are automatically
    skipped when that key is absent from the loaded supported-CU set — they are
    never failed just because a feature is not implemented on the server under test.
    """
    global _SUPPORTED_CUS  # noqa: PLW0603  # pylint: disable=global-statement

    config.addinivalue_line(
        "markers",
        "requires_cu(cu_key, ...): skip this test if the given conformance unit "
        "key(s) are not supported per server_capabilities.yaml",
    )
    config.addinivalue_line(
        "markers",
        "requires_dependency_cu(cu_key, ...): skip this test when a prerequisite "
        "conformance unit is outside the active server profile",
    )
    config.addinivalue_line(
        "markers",
        "workbook_ref(sheet, rows): optional exact Test Cases workbook sheet/row traceability for a test",
    )
    config.addinivalue_line("markers", "live: requires a live OPC UA server")
    config.addinivalue_line("markers", "conformance: IJT conformance unit test")
    config.addinivalue_line("markers", "negative: negative / error-path test")
    config.addinivalue_line("markers", "opcua_core: OPC UA core service probe, not official IJT CU evidence")
    config.addinivalue_line("markers", "simulation: requires the OPC UA IJT Server Simulator")
    config.addinivalue_line(
        "markers",
        "performance: end-to-end latency / throughput benchmark (requires a live OPC UA server)",
    )

    _project_root = Path(__file__).resolve().parent
    # Default to repo-local basetemp (stable in this environment). Set
    # IJT_USE_SYSTEM_BASETEMP=1 to opt out and let pytest use system temp.
    _use_system = os.environ.get("IJT_USE_SYSTEM_BASETEMP", "").lower() in {"1", "true", "yes"}
    if config.option.basetemp is None and not _use_system:
        _basetemp_chosen = None
        _pid = os.getpid()
        _tmp_root = _project_root / "tmp"
        for _candidate in ("pytest", "pytest_tmp", f"pytest_session_{_pid}"):
            _candidate_path = _tmp_root / _candidate
            try:
                if _candidate_path.exists():
                    if _deletes_disabled():
                        continue
                    shutil.rmtree(_candidate_path)
                _candidate_path.mkdir(parents=True)
                _probe = _candidate_path / ".acl_probe"
                _probe.write_text("ok")
                if not _deletes_disabled():
                    _probe.unlink()
                _ = list(_candidate_path.iterdir())
                _basetemp_chosen = _candidate_path
                break
            except OSError:
                continue
        if _basetemp_chosen is None:
            with contextlib.suppress(OSError):
                _tmp_root.mkdir(parents=True, exist_ok=True)
                _auto = Path(tempfile.mkdtemp(dir=_tmp_root, prefix="pytest_auto_"))
                _basetemp_chosen = _auto
        if _basetemp_chosen is None:
            sys.stderr.write(
                "\n[conftest] WARNING: all local tmp/ candidates are ACL-locked. "
                "Falling back to system temp. Set IJT_USE_SYSTEM_BASETEMP=1 to silence this.\n"
            )
        if _basetemp_chosen is not None:
            config.option.basetemp = str(_basetemp_chosen)
    _project_root.joinpath("tests", "fixtures").mkdir(parents=True, exist_ok=True)

    try:
        _SUPPORTED_CUS = load_supported_cus()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "Could not load server_capabilities.yaml (%s) — all conformance units treated as supported",
            exc,
        )
        _SUPPORTED_CUS = None  # None = no gating; run everything

    config.pluginmanager.register(
        CuCoverageReportRecorder(
            root=_project_root,
            all_cus=load_all_cus_from_facets(),
            supported_cus=_SUPPORTED_CUS,
        ),
        "ijt-cu-compliance-report",
    )


def pytest_runtest_setup(item):
    """Skip any test whose required conformance units are not in the supported set.

    Reads @pytest.mark.requires_cu(CU.KEY) markers.
    When _SUPPORTED_CUS is None (no capabilities file loaded) every test runs — safe default.
    When _SUPPORTED_CUS is an empty frozenset (file present but declares nothing) all
    CU-gated tests are skipped — this is the correct behaviour for an explicit empty profile.
    """
    if _SUPPORTED_CUS is None:
        return  # no profile loaded → run everything

    for marker in item.iter_markers("requires_cu"):
        for cu_key in marker.args:
            if cu_key not in _SUPPORTED_CUS:
                pytest.skip(get_skip_reason(cu_key))
    for marker in item.iter_markers("requires_dependency_cu"):
        for cu_key in marker.args:
            if cu_key not in _SUPPORTED_CUS:
                pytest.skip(get_skip_reason(cu_key))


# Inline helpers
def _parse_opcua_endpoint(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 40451


def _is_port_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


from helpers.namespaces import (
    ALL_NAMESPACE_URIS,
    BN,
    NS_APP,
    NS_IJT_BASE,
    NS_MACH_RESULT,
)
from helpers.node_discovery import (
    browse_folder_instances,
    find_child_by_browse_name,
    find_joining_system,
)

logger = logging.getLogger(__name__)
SERVER_URL = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
_OPCUA_TIMEOUT_S = 120  # SimulateJobResult fires many results; 4 s default is too short


# ─── Early connection check ───────────────────────────────────────────────────
def pytest_sessionstart(session) -> None:
    """
    Runs before test collection.  Does a fast TCP probe and prints a prominent
    warning if the OPC UA server is not reachable so the developer knows what to
    do before any fixture error is reported.
    """
    _server_url = os.environ.get("OPCUA_SERVER_URL", "opc.tcp://localhost:40451")
    host, port = _parse_opcua_endpoint(_server_url)
    reachable = _is_port_reachable(host, port, timeout=2.0)
    if not reachable:
        border = "=" * 70
        exe = "OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe"
        msg = "\n".join(
            [
                "",
                border,
                "  OPC UA SERVER NOT DETECTED",
                border,
                f"  Cannot reach: opc.tcp://{host}:{port}",
                "",
                "  Start the server (auto-launch attempted if OPCUA_SIMULATOR_EXE is set):",
                f"    {exe}",
                "",
                "  Or set env vars:",
                "    OPCUA_SIMULATOR_EXE=<path>   enable auto-launch on test start",
                "    OPCUA_SERVER_URL=opc.tcp://host:port   custom endpoint",
                "",
                "  All tests require a live server and will FAIL if unreachable.",
                border,
                "",
            ]
        )
        logger.warning(msg)


# ─── Server lifecycle ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def managed_server():
    """
    Ensure the OPC UA server is running before any test executes.
    Attempts to reuse an already-running server; falls back to launching the
    simulator executable. Skips the entire session if unavailable.
    """
    from helpers.server_manager import ServerManager

    host, port = _parse_opcua_endpoint(SERVER_URL)
    manager = ServerManager(host=host, port=port)
    available = manager.ensure_running()
    if not available:
        pytest.fail("OPC UA server did not start. Start the server manually or set OPCUA_SIMULATOR_EXE env var.")
    yield manager
    manager.teardown()


# ─── Session-scoped shared client ────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def session_client(managed_server):
    """
    Session-scoped asyncua Client for read-only structure and discovery tests.
    Connected once and reused for the entire test session.  Do NOT use this
    client for method calls or subscription tests (use opcua_client /
    subscription_client instead).
    """
    client = Client(SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    try:
        await client.connect()
    except Exception as exc:
        pytest.fail(f"Could not connect to OPC UA server at {SERVER_URL}: {exc}")
    try:
        # Compatibility bridge for the IJT simulator's custom Result/Event
        # payloads: asyncua's modern loader reads OPC UA 1.04
        # DataTypeDefinition attributes, while the simulator still exposes some
        # IJT structures only through the legacy OPC Binary dictionary path.
        await client.load_type_definitions()
    except Exception as exc:
        logger.warning("load_type_definitions() failed (non-fatal): %s", exc)
    try:
        await client.load_data_type_definitions()
    except Exception as exc:
        logger.warning("load_data_type_definitions() failed (non-fatal): %s", exc)
    yield client
    try:
        await client.disconnect()
    except Exception as exc:
        logger.debug("session_client disconnect failed (ignored): %s", exc)


# ─── Namespace indices ────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def ns_indices(session_client) -> dict:
    """
    Dict mapping each namespace URI to its runtime namespace index.
    Resolved once per session.  Value is None for any namespace not registered
    on the server.  Fixtures for required namespaces call pytest.fail() when None;
    fixtures for optional/vendor namespaces call pytest.skip() when None.
    """
    indices: dict = {}
    for uri in ALL_NAMESPACE_URIS:
        try:
            indices[uri] = await session_client.get_namespace_index(uri)
        except Exception:
            indices[uri] = None
    return indices


# ─── JoiningSystem discovery ─────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def joining_system(session_client, ns_indices):
    """
    JoiningSystem node discovered by HasTypeDefinition = JoiningSystemType.
    The system's browse name is implementation-defined and is never used
    for discovery.  Fails if the node cannot be found — required per IJT spec.
    """
    js = await find_joining_system(session_client)
    if js is None:
        pytest.fail("JoiningSystem node not found in address space (by type definition) — required per IJT spec")
    return js


# ─── AddIn nodes on JoiningSystem ────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def asset_management(joining_system, ns_indices):
    """AssetManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.fail("IJT Base namespace not registered — required for IJT conformance")
    node = await find_child_by_browse_name(joining_system, BN.ASSET_MANAGEMENT, ns_ijt)
    if node is None:
        pytest.fail("AssetManagement node not found on JoiningSystem — required per IJT spec")
    return node


@pytest_asyncio.fixture(scope="session")
async def assets_folder(asset_management, ns_indices):
    """Assets folder node inside AssetManagement (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.fail("IJT Base namespace not registered — required for IJT conformance")
    node = await find_child_by_browse_name(asset_management, BN.ASSETS, ns_ijt)
    if node is None:
        pytest.fail("Assets folder not found inside AssetManagement — required per IJT spec")
    return node


@pytest_asyncio.fixture(scope="session")
async def result_management(joining_system, ns_indices):
    """ResultManagement AddIn node on the JoiningSystem (Machinery/Result ns)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.fail("Machinery/Result namespace not registered — required for IJT conformance")
    node = await find_child_by_browse_name(joining_system, BN.RESULT_MANAGEMENT, ns_mr)
    if node is None:
        pytest.fail("ResultManagement node not found on JoiningSystem — required per IJT spec")
    return node


@pytest_asyncio.fixture(scope="session")
async def joining_process_management(joining_system, ns_indices):
    """JoiningProcessManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.fail("IJT Base namespace not registered — required for IJT conformance")
    node = await find_child_by_browse_name(joining_system, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt)
    if node is None:
        pytest.fail("JoiningProcessManagement node not found on JoiningSystem — required per IJT spec")
    return node


@pytest_asyncio.fixture(scope="session")
async def joint_management(joining_system, ns_indices):
    """JointManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.fail("IJT Base namespace not registered — required for IJT conformance")
    node = await find_child_by_browse_name(joining_system, BN.JOINT_MANAGEMENT, ns_ijt)
    if node is None:
        pytest.fail("JointManagement node not found on JoiningSystem — required per IJT spec")
    return node


@pytest_asyncio.fixture(scope="session")
async def simulations_node(joining_system, ns_indices):
    """Simulations folder node on the JoiningSystem (App ns)."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered — simulator not available")
    node = await find_child_by_browse_name(joining_system, BN.SIMULATIONS, ns_app)
    if node is None:
        pytest.skip("Simulations node not found on JoiningSystem")
    return node


@pytest_asyncio.fixture(scope="session")
async def simulate_results_folder(simulations_node, ns_indices):
    """SimulateResults folder under Simulations (App ns)."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered — simulator not available")
    node = await find_child_by_browse_name(simulations_node, BN.SIMULATE_RESULTS_FOLDER, ns_app)
    if node is None:
        pytest.skip("SimulateResults folder not found under Simulations")
    return node


@pytest_asyncio.fixture(scope="session")
async def simulate_events_folder(simulations_node, ns_indices):
    """SimulateEventsAndConditions folder under Simulations (App ns)."""
    ns_app = ns_indices.get(NS_APP)
    if ns_app is None:
        pytest.skip("App namespace not registered — simulator not available")
    node = await find_child_by_browse_name(simulations_node, BN.SIMULATE_EVENTS_AND_CONDITIONS, ns_app)
    if node is None:
        pytest.skip("SimulateEventsAndConditions folder not found under Simulations")
    return node


# ─── OPC UA Server node ───────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def server_node(session_client):
    """OPC UA OPC UA Server node — root for event subscriptions."""
    return session_client.nodes.server


# ─── Asset folder nodes ───────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def controllers_folder(assets_folder, ns_indices):
    """Controllers asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.CONTROLLERS, ns_ijt)
    if node is None:
        pytest.skip("Controllers folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def tools_folder(assets_folder, ns_indices):
    """Tools asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.TOOLS, ns_ijt)
    if node is None:
        pytest.skip("Tools folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def batteries_folder(assets_folder, ns_indices):
    """Batteries asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.BATTERIES, ns_ijt)
    if node is None:
        pytest.skip("Batteries folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def servos_folder(assets_folder, ns_indices):
    """Servos asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.SERVOS, ns_ijt)
    if node is None:
        pytest.skip("Servos folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def sensors_folder(assets_folder, ns_indices):
    """Sensors asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.SENSORS, ns_ijt)
    if node is None:
        pytest.skip("Sensors folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def power_supplies_folder(assets_folder, ns_indices):
    """PowerSupplies asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.POWER_SUPPLIES, ns_ijt)
    if node is None:
        pytest.skip("PowerSupplies folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def cables_folder(assets_folder, ns_indices):
    """Cables asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.CABLES, ns_ijt)
    if node is None:
        pytest.skip("Cables folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def feeders_folder(assets_folder, ns_indices):
    """Feeders asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.FEEDERS, ns_ijt)
    if node is None:
        pytest.skip("Feeders folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def memory_devices_folder(assets_folder, ns_indices):
    """MemoryDevices asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.MEMORY_DEVICES, ns_ijt)
    if node is None:
        pytest.skip("MemoryDevices folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def accessories_folder(assets_folder, ns_indices):
    """Accessories asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.ACCESSORIES, ns_ijt)
    if node is None:
        pytest.skip("Accessories folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def sub_components_folder(assets_folder, ns_indices):
    """SubComponents asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.SUB_COMPONENTS, ns_ijt)
    if node is None:
        pytest.skip("SubComponents folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def software_components_folder(assets_folder, ns_indices):
    """SoftwareComponents asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.SOFTWARE_COMPONENTS, ns_ijt)
    if node is None:
        pytest.skip("SoftwareComponents folder not found in Assets")
    return node


@pytest_asyncio.fixture(scope="session")
async def virtual_stations_folder(assets_folder, ns_indices):
    """VirtualStations asset folder node (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(assets_folder, BN.VIRTUAL_STATIONS, ns_ijt)
    if node is None:
        pytest.skip("VirtualStations folder not found in Assets")
    return node


# ─── Pre-browsed asset instance collections ──────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def controllers_instances(controllers_folder):
    """
    List of (browse_name_str, Node) for all controller instances.
    Skips if the Controllers folder has no children.
    """
    instances = await browse_folder_instances(controllers_folder)
    if not instances:
        pytest.skip("No controller instances found in Controllers folder")
    return instances


@pytest_asyncio.fixture(scope="session")
async def tools_instances(tools_folder):
    """
    List of (browse_name_str, Node) for all tool instances.
    Skips if the Tools folder has no children.
    """
    instances = await browse_folder_instances(tools_folder)
    if not instances:
        pytest.skip("No tool instances found in Tools folder")
    return instances


# ─── Per-module and per-test clients ─────────────────────────────────────────
@pytest_asyncio.fixture(scope="module")
async def opcua_client(session_client):
    """
    Module-scoped asyncua Client for method call and state-changing tests.
    One connection is shared across all tests in a module and torn down after
    the last test in that module.  Tests run sequentially so sharing is safe.

    Module scope instead of function scope cuts CI time dramatically: GitHub
    Actions Windows runners take ~3 s per OPC UA connection handshake, so
    ~400 per-test connections added ~20 minutes.  With ~30 modules the overhead
    drops to under a minute.

    Depends on session_client so that load_type_definitions() and
    load_data_type_definitions() have already run once before any per-module
    client connects.

    Use subscription_client (module-scoped) for event subscription tests —
    subscriptions must remain isolated per test to avoid cross-test event noise.
    """
    client = Client(SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    yield client
    try:
        await client.disconnect()
    except Exception as exc:
        logger.debug("opcua_client disconnect failed (ignored): %s", exc)


@pytest_asyncio.fixture(scope="module")
async def subscription_client(session_client):
    """
    Module-scoped asyncua Client dedicated to event subscriptions.
    Kept separate from opcua_client because asyncua cannot safely handle
    concurrent OPC UA calls (method invocations + subscription callbacks)
    on a single client connection.

    Module scope (not function scope) avoids one OPC UA TCP handshake (~3 s on
    GitHub Actions Windows runners) per test.  Subscription isolation is still
    maintained per-test by EventCollector, which subscribes and unsubscribes on
    every call regardless of the underlying connection scope.  Tests remain
    sequential so no cross-test event noise can occur.

    Depends on session_client so that load_type_definitions() and
    load_data_type_definitions() have already run before any per-module client
    connects — no redundant type loading.
    """
    client = Client(SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    yield client
    try:
        await client.disconnect()
    except Exception as exc:
        logger.debug("subscription_client disconnect failed (ignored): %s", exc)


# ─── Trigger fixtures (function-scoped, use module-scoped opcua_client) ──────
@pytest_asyncio.fixture(scope="function")
async def result_trigger(opcua_client, simulate_results_folder, ns_indices):
    """
    Function-scoped ResultTrigger.
    Returns SimulatorResultTrigger when the simulator's SimulateResults folder is available.
    Returns ExternalResultTrigger (no-op, causes test to skip) when running against a real
    controller that does not expose simulator methods.
    Controller teams can override this by setting OPCUA_TRIGGER_CLASS env var.
    """
    from helpers.trigger import make_result_trigger

    ns_app = ns_indices.get(NS_APP)
    trigger = make_result_trigger(opcua_client, simulate_results_folder, ns_app)
    # Allow controller teams to inject their own trigger implementation
    trigger_class_path = os.environ.get("OPCUA_TRIGGER_CLASS")
    if trigger_class_path:
        try:
            module_path, class_name = trigger_class_path.rsplit(".", 1)
            import importlib

            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            trigger = cls(opcua_client, simulate_results_folder, ns_app)
            logger.info("Using custom trigger class: %s", trigger_class_path)
        except Exception as exc:
            logger.warning(
                "Failed to load OPCUA_TRIGGER_CLASS='%s': %s — falling back to default", trigger_class_path, exc
            )
    return trigger


@pytest_asyncio.fixture(scope="function")
async def event_trigger(opcua_client, simulate_events_folder, ns_indices):
    """
    Function-scoped EventTrigger.
    Returns SimulatorEventTrigger when the simulator's SimulateEventsAndConditions folder is available.
    Returns ExternalEventTrigger (no-op, causes test to skip) otherwise.
    """
    from helpers.trigger import make_event_trigger

    ns_app = ns_indices.get(NS_APP)
    return make_event_trigger(opcua_client, simulate_events_folder, ns_app)


# ─── Virtual stations instances ───────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def virtual_stations_instances(virtual_stations_folder):
    """List of (browse_name_str, Node) for all virtual station instances. Skips if empty."""
    instances = await browse_folder_instances(virtual_stations_folder)
    if not instances:
        pytest.skip("No virtual station instances found in VirtualStations folder")
    return instances


def _sessionfinish_cleanup(session: object) -> None:
    """Best-effort cleanup — called by pytest_sessionfinish inside a try/except."""
    _project_root = Path(__file__).resolve().parent

    # Remove __pycache__ dirs.  os.walk is used instead of rglob so that
    # ACL-locked directories (e.g. tmp/pytest_session_* owned by another user)
    # are safely skipped via onerror rather than raising PermissionError.
    # "tmp" is pruned from the walk so we never attempt to traverse it at all.
    _skip_dirs = {".venv", "venv", "node_modules", "test-results", ".git", "tmp"}
    for _dirpath, _dirnames, _ in os.walk(_project_root, onerror=lambda _e: None):
        _dirnames[:] = [d for d in _dirnames if d not in _skip_dirs]
        if "__pycache__" in _dirnames:
            shutil.rmtree(Path(_dirpath) / "__pycache__", ignore_errors=True)
            _dirnames.remove("__pycache__")

    # Identify the active basetemp so we don't race with pytest's own cleanup.
    _active_basetemp: Path | None = None
    with contextlib.suppress(AttributeError, OSError):
        _bt = getattr(getattr(session, "config", None), "option", None)
        if _bt is not None:
            _bt = getattr(_bt, "basetemp", None)
        if _bt:
            _active_basetemp = Path(_bt).resolve()

    # Remove tool caches and stale pytest basetemp from tmp/
    _tmp_root = _project_root / "tmp"
    if _tmp_root.exists():
        _managed = {"pytest", "pytest_tmp", "ruff-cache", "mypy-cache", "pip-audit-cache"}
        for child in list(_tmp_root.iterdir()):
            try:
                if _active_basetemp is not None and child.resolve() == _active_basetemp:
                    continue  # pytest still owns this dir — leave it for next-run cleanup
            except (AttributeError, OSError):
                # Cannot resolve path — skip pytest-named children conservatively
                if child.name.startswith("pytest"):
                    continue
            if child.name in _managed or child.name.startswith("pytest"):
                shutil.rmtree(child, ignore_errors=True)
        # Remove tmp/ itself if now empty (gitignored — safe to delete)
        with contextlib.suppress(OSError):
            _tmp_root.rmdir()


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Remove __pycache__ dirs, tool caches, and stale pytest basetemp after every session.

    The currently active basetemp (session.config.option.basetemp) is intentionally
    skipped — pytest manages its own session dir and still holds Windows file handles
    at this point.  Only stale dirs from prior interrupted runs and tool caches are
    removed.  run_all_tests.py calls _cleanup_caches() independently (which covers the
    active basetemp at the start of the next run), so this hook is harmless when both
    run together.

    All cleanup is wrapped in a bare except so that filesystem errors (e.g. ACL-locked
    dirs left by a different OS user / sandbox) never cause pytest to exit non-zero.
    """
    try:
        _sessionfinish_cleanup(session)
    except Exception:  # noqa: BLE001
        return  # Best-effort cleanup — errors must never affect the test session exit code
