"""
conftest.py — Session and function-scoped pytest fixtures for the OPC UA IJT test suite.
Session fixtures are created once per test run and shared across all tests that
perform read-only address-space discovery.
Function fixtures (opcua_client, subscription_client) create fresh connections
per test to provide state isolation for method calls and event subscriptions.
All async fixtures require pytest-asyncio with asyncio_mode = "auto" (pytest.ini).
Design rules enforced here:
  - JoiningSystem is discovered by HasTypeDefinition, never by browse name.
  - Namespace indices are resolved once and cached in ns_indices dict.
  - Two separate client fixtures prevent asyncua concurrency issues with subscriptions.
"""
import asyncio
import logging
import os
import pytest
import pytest_asyncio
from asyncua import Client, ua
from helpers.namespaces import (
    NS_OPC_UA, NS_DI, NS_AMB, NS_IA, NS_MACHINERY, NS_MACH_RESULT,
    NS_IJT_BASE, NS_IJT_TIGHTENING, NS_APP,
    ALL_NAMESPACE_URIS, BN, RefTypes, IJTTypes, MachineryResultTypes,
)
from helpers.node_discovery import (
    find_joining_system,
    find_child_by_browse_name,
    browse_folder_instances,
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
    import socket
    host, port = "localhost", 40451
    url = os.environ.get("OPCUA_SERVER_URL", "")
    if url:
        try:
            parts = url.replace("opc.tcp://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 40451
        except Exception:
            pass
    try:
        with socket.create_connection((host, port), timeout=2.0):
            reachable = True
    except (socket.timeout, ConnectionRefusedError, OSError):
        reachable = False
    if not reachable:
        import sys
        border = "=" * 70
        exe = (
            "OPC_UA_Servers/Release2/OPC_UA_IJT_Server_Simulator/"
            "opcua_ijt_demo_application.exe"
        )
        msg = "\n".join([
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
            "  All tests require a live server and will be SKIPPED if unreachable.",
            border,
            "",
        ])
        print(msg, file=sys.stderr)
# ─── Server lifecycle ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def managed_server():
    """
    Ensure the OPC UA server is running before any test executes.
    Attempts to reuse an already-running server; falls back to launching the
    simulator executable. Skips the entire session if unavailable.
    """
    from helpers.server_manager import ServerManager
    manager = ServerManager()
    available = manager.ensure_running()
    if not available:
        pytest.skip(
            "OPC UA server not available. "
            "Start the server manually or set OPCUA_SIMULATOR_EXE env var."
        )
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
        pytest.skip(f"Could not connect to OPC UA server at {SERVER_URL}: {exc}")
    try:
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
    except Exception:
        pass
# ─── Namespace indices ────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def ns_indices(session_client) -> dict:
    """
    Dict mapping each namespace URI to its runtime namespace index.
    Resolved once per session.  Value is None for any namespace not registered
    on the server.  Tests should pytest.skip() when required namespaces are None.
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
    for discovery.  Skips if the node cannot be found.
    """
    js = await find_joining_system(session_client)
    if js is None:
        pytest.skip("JoiningSystem node not found in address space (by type definition)")
    return js
# ─── AddIn nodes on JoiningSystem ────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def asset_management(joining_system, ns_indices):
    """AssetManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(joining_system, BN.ASSET_MANAGEMENT, ns_ijt)
    if node is None:
        pytest.skip("AssetManagement node not found on JoiningSystem")
    return node
@pytest_asyncio.fixture(scope="session")
async def assets_folder(asset_management, ns_indices):
    """Assets folder node inside AssetManagement (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(asset_management, BN.ASSETS, ns_ijt)
    if node is None:
        pytest.skip("Assets folder not found inside AssetManagement")
    return node
@pytest_asyncio.fixture(scope="session")
async def result_management(joining_system, ns_indices):
    """ResultManagement AddIn node on the JoiningSystem (Machinery/Result ns)."""
    ns_mr = ns_indices.get(NS_MACH_RESULT)
    if ns_mr is None:
        pytest.skip("Machinery/Result namespace not registered")
    node = await find_child_by_browse_name(joining_system, BN.RESULT_MANAGEMENT, ns_mr)
    if node is None:
        pytest.skip("ResultManagement node not found on JoiningSystem")
    return node
@pytest_asyncio.fixture(scope="session")
async def joining_process_management(joining_system, ns_indices):
    """JoiningProcessManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(
        joining_system, BN.JOINING_PROCESS_MANAGEMENT, ns_ijt
    )
    if node is None:
        pytest.skip("JoiningProcessManagement node not found on JoiningSystem")
    return node
@pytest_asyncio.fixture(scope="session")
async def joint_management(joining_system, ns_indices):
    """JointManagement AddIn node on the JoiningSystem (IJT Base ns)."""
    ns_ijt = ns_indices.get(NS_IJT_BASE)
    if ns_ijt is None:
        pytest.skip("IJT Base namespace not registered")
    node = await find_child_by_browse_name(joining_system, BN.JOINT_MANAGEMENT, ns_ijt)
    if node is None:
        pytest.skip("JointManagement node not found on JoiningSystem")
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
    node = await find_child_by_browse_name(
        simulations_node, BN.SIMULATE_EVENTS_AND_CONDITIONS, ns_app
    )
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
# ─── Function-scoped clients for state-changing tests ────────────────────────
@pytest_asyncio.fixture(scope="function")
async def opcua_client(managed_server):
    """
    Function-scoped asyncua Client for method call and state-changing tests.
    A fresh connection is created and torn down for each test to ensure
    test isolation.  Use this client — not session_client — when calling
    OPC UA methods.
    """
    client = Client(SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    try:
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
    except Exception:
        pass
@pytest_asyncio.fixture(scope="function")
async def subscription_client(managed_server):
    """
    Function-scoped asyncua Client dedicated to event subscriptions.
    Kept separate from opcua_client because asyncua cannot safely handle
    concurrent OPC UA calls (method invocations + subscription callbacks)
    on a single client connection.
    """
    client = Client(SERVER_URL, timeout=_OPCUA_TIMEOUT_S)
    await client.connect()
    try:
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
    except Exception:
        pass