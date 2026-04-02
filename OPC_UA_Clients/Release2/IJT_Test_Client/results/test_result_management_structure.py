"""
Structural tests for ResultManagement — verifies that the expected folder,
methods and child nodes are present and browsable.
"""
import pytest
from helpers.namespaces import (
    NS_MACH_RESULT,
    NS_IJT_BASE,
    NS_APP,
    BN,
)
from helpers.node_discovery import find_child_by_browse_name
pytestmark = [pytest.mark.live, pytest.mark.structure]
# ---------------------------------------------------------------------------
# Existence of ResultManagement itself
# ---------------------------------------------------------------------------
async def test_result_management_exists(result_management):
    assert result_management is not None, (
        "ResultManagement node must not be None"
    )
# ---------------------------------------------------------------------------
# Child folder
# ---------------------------------------------------------------------------
async def test_results_folder_exists(result_management, ns_indices):
    ns_mr = ns_indices[NS_MACH_RESULT]
    node = await find_child_by_browse_name(result_management, BN.RESULTS, ns_mr)
    assert node is not None, (
        f"Expected child '{BN.RESULTS}' (ns={ns_mr}) under ResultManagement"
    )
# ---------------------------------------------------------------------------
# Methods in NS_MACH_RESULT
# ---------------------------------------------------------------------------
async def test_get_latest_result_method_exists(result_management, ns_indices):
    ns_mr = ns_indices[NS_MACH_RESULT]
    node = await find_child_by_browse_name(result_management, BN.GET_LATEST_RESULT, ns_mr)
    assert node is not None, (
        f"Method '{BN.GET_LATEST_RESULT}' must exist in ResultManagement (ns_mr={ns_mr})"
    )
async def test_get_result_by_id_method_exists(result_management, ns_indices):
    ns_mr = ns_indices[NS_MACH_RESULT]
    node = await find_child_by_browse_name(result_management, BN.GET_RESULT_BY_ID, ns_mr)
    assert node is not None, (
        f"Method '{BN.GET_RESULT_BY_ID}' must exist in ResultManagement (ns_mr={ns_mr})"
    )
async def test_get_result_id_list_filtered_method_exists(result_management, ns_indices):
    ns_mr = ns_indices[NS_MACH_RESULT]
    node = await find_child_by_browse_name(result_management, BN.GET_RESULT_ID_LIST_FILTERED, ns_mr)
    assert node is not None, (
        f"Method '{BN.GET_RESULT_ID_LIST_FILTERED}' must exist in ResultManagement (ns_mr={ns_mr})"
    )
async def test_release_result_handle_method_exists(result_management, ns_indices):
    ns_mr = ns_indices[NS_MACH_RESULT]
    node = await find_child_by_browse_name(result_management, BN.RELEASE_RESULT_HANDLE, ns_mr)
    assert node is not None, (
        f"Method '{BN.RELEASE_RESULT_HANDLE}' must exist in ResultManagement (ns_mr={ns_mr})"
    )
# ---------------------------------------------------------------------------
# Method in NS_IJT_BASE
# ---------------------------------------------------------------------------
async def test_request_results_method_exists(result_management, ns_indices):
    ns_ijt_base = ns_indices[NS_IJT_BASE]
    node = await find_child_by_browse_name(result_management, BN.REQUEST_RESULTS, ns_ijt_base)
    assert node is not None, (
        f"Method '{BN.REQUEST_RESULTS}' must exist in ResultManagement (ns_ijt_base={ns_ijt_base})"
    )
# ---------------------------------------------------------------------------
# Simulation methods in NS_APP
# ---------------------------------------------------------------------------
async def test_simulate_single_result_method_exists(simulate_results_folder, ns_indices):
    ns_app = ns_indices[NS_APP]
    node = await find_child_by_browse_name(simulate_results_folder, BN.SIMULATE_SINGLE_RESULT, ns_app)
    assert node is not None, (
        f"Method '{BN.SIMULATE_SINGLE_RESULT}' must exist in SimulateResults folder (ns_app={ns_app})"
    )
async def test_simulate_batch_or_sync_method_exists(simulate_results_folder, ns_indices):
    ns_app = ns_indices[NS_APP]
    node = await find_child_by_browse_name(simulate_results_folder, BN.SIMULATE_BATCH_OR_SYNC_RESULT, ns_app)
    assert node is not None, (
        f"Method '{BN.SIMULATE_BATCH_OR_SYNC_RESULT}' must exist in SimulateResults folder (ns_app={ns_app})"
    )
async def test_simulate_job_result_method_exists(simulate_results_folder, ns_indices):
    ns_app = ns_indices[NS_APP]
    node = await find_child_by_browse_name(simulate_results_folder, BN.SIMULATE_JOB_RESULT, ns_app)
    assert node is not None, (
        f"Method '{BN.SIMULATE_JOB_RESULT}' must exist in SimulateResults folder (ns_app={ns_app})"
    )