import pytest

from helpers.cu_registry import CU
from helpers.workbook_traceability import (
    EXPECTED_WORKBOOK_CASE_COUNT,
    load_workbook_cases,
    ordered_cu_keys,
    workbook_traceability_report,
)


def test_ordered_cu_keys_matches_official_workbook_count():
    keys = ordered_cu_keys()

    assert len(keys) == 123
    assert keys[0] == CU.JOINING_SYSTEM_BASE
    assert keys[-1] == CU.ENGINEERING_UNITS


def test_default_workbook_cases_load_all_tc_headers():
    cases = load_workbook_cases()
    total = sum(len(entries) for entries in cases.values())

    assert total == EXPECTED_WORKBOOK_CASE_COUNT
    first_case = cases[CU.JOINING_SYSTEM_BASE][0]
    assert first_case.sheet == "JS Base"
    assert first_case.row == 4
    assert first_case.tc_no == 1
    assert first_case.case_type == "positive"


def test_result_workbook_mapping_uses_cu_identity_not_sheet_order(monkeypatch):
    import helpers.workbook_traceability as module

    original = module.load_workbook

    def reordered(*args, **kwargs):
        workbook = original(*args, **kwargs)
        # Swapping these sheets already differs from registry declaration order.
        index = workbook._sheets.index(workbook["Intervention Result"])
        other = workbook._sheets.index(workbook["Batch Result Counters"])
        workbook._sheets[index], workbook._sheets[other] = workbook._sheets[other], workbook._sheets[index]
        return workbook

    monkeypatch.setattr(module, "load_workbook", reordered)
    cases = module.load_workbook_cases()
    assert cases[CU.INTERVENTION_RESULT][0].sheet == "Intervention Result"
    assert cases[CU.BATCH_RESULT_COUNTERS][0].sheet == "Batch Result Counters"


@pytest.mark.parametrize("identity", ["unknown", "duplicate"])
def test_workbook_refuses_unknown_or_duplicate_cu_identity_and_closes_file(monkeypatch, identity):
    from unittest.mock import Mock

    import helpers.workbook_traceability as module

    original = module.load_workbook
    opened = []

    def altered(*args, **kwargs):
        kwargs["read_only"] = False
        workbook = original(*args, **kwargs)
        opened.append(workbook)
        workbook.worksheets[module.INFRA_SHEET_COUNT + 1].cell(1, 1).value = (
            workbook.worksheets[module.INFRA_SHEET_COUNT].cell(1, 1).value
            if identity == "duplicate"
            else "CU-999: Unknown workbook identity"
        )
        workbook.close = Mock(wraps=workbook.close)
        return workbook

    monkeypatch.setattr(module, "load_workbook", altered)
    with pytest.raises(ValueError, match="Unknown or duplicate CU identity"):
        module.load_workbook_cases()
    assert len(opened) == 1
    opened[0].close.assert_called_once()


def test_exact_obligations_require_every_component_and_do_not_erase_a_failure():
    cases = load_workbook_cases()[CU.INTERVENTION_RESULT]
    tests = [
        {"nodeid": "pass", "outcome": "passed"},
        {"nodeid": "blocked", "outcome": "blocked"},
        {"nodeid": "fail", "outcome": "failed"},
    ]
    report = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row={cases[0].ref: ["pass", "blocked"]},
    )
    rows = report["by_cu"][CU.INTERVENTION_RESULT]["cases"]
    assert [row["outcome"] for row in rows] == ["incomplete", "incomplete"]
    failed = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row={cases[0].ref: ["pass", "fail"]},
    )
    assert failed["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "failed"


def test_equivalent_routes_require_all_components_of_at_least_one_complete_route():
    case = load_workbook_cases()[CU.INTERVENTION_RESULT][0]
    tests = [
        {"nodeid": "simulator", "outcome": "blocked", "evidence_route": "simulator_direct"},
        {"nodeid": "target-first", "outcome": "passed", "evidence_route": "target_workflow"},
        {"nodeid": "target-second", "outcome": "passed", "evidence_route": "target_workflow"},
    ]
    refs = {case.ref: [test["nodeid"] for test in tests]}
    routes = {case.ref: {test["nodeid"]: test["evidence_route"] for test in tests}}
    report = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row=refs,
        exact_routes_by_row=routes,
    )
    assert report["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "passed"
    tests[-1]["outcome"] = "blocked"
    incomplete = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row=refs,
        exact_routes_by_row=routes,
    )
    assert incomplete["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "incomplete"


def test_common_obligation_component_cannot_be_bypassed_by_a_passing_route():
    case = load_workbook_cases()[CU.INTERVENTION_RESULT][0]
    tests = [
        {"nodeid": "common", "outcome": "blocked"},
        {"nodeid": "effect", "outcome": "passed", "evidence_route": "target_workflow"},
    ]
    report = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row={case.ref: ["common", "effect"]},
    )
    assert report["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "incomplete"


def test_one_obligation_component_can_run_through_either_declared_route_without_overwrite():
    case = load_workbook_cases()[CU.INTERVENTION_RESULT][0]
    for route in ("simulator_direct", "target_workflow"):
        tests = [{"nodeid": "shared", "outcome": "passed", "evidence_route": route}]
        report = workbook_traceability_report(
            tests_by_cu={CU.INTERVENTION_RESULT: tests},
            exact_refs_by_row={case.ref: ["shared"]},
            exact_routes_by_row={case.ref: {"shared": {"simulator_direct", "target_workflow"}}},
        )
        assert report["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "passed"
    tests[0]["evidence_route"] = "unadvertised-route"
    report = workbook_traceability_report(
        tests_by_cu={CU.INTERVENTION_RESULT: tests},
        exact_refs_by_row={case.ref: ["shared"]},
        exact_routes_by_row={case.ref: {"shared": {"simulator_direct", "target_workflow"}}},
    )
    assert report["by_cu"][CU.INTERVENTION_RESULT]["cases"][0]["outcome"] == "incomplete"


def test_workbook_traceability_report_links_rows_to_cu_tests_and_exact_refs():
    first_case = load_workbook_cases()[CU.JOINING_SYSTEM_BASE][0]
    nodeid = "specification_tests/test_joining_system_base.py::test_joining_system_type_present"

    report = workbook_traceability_report(
        tests_by_cu={CU.JOINING_SYSTEM_BASE: [{"nodeid": nodeid}]},
        exact_refs_by_row={first_case.ref: [nodeid]},
    )

    assert report["case_count"] == EXPECTED_WORKBOOK_CASE_COUNT
    assert report["missing_case_cus"] == []
    by_cu = report["by_cu"][CU.JOINING_SYSTEM_BASE]
    assert by_cu["case_count"] == len(load_workbook_cases()[CU.JOINING_SYSTEM_BASE])
    row = by_cu["cases"][0]
    assert row["ref"] == first_case.ref
    assert row["linked_tests"] == [nodeid]
    assert row["exact_tests"] == [nodeid]
    assert row["mapping_precision"] == "exact"


def test_workbook_traceability_handles_missing_tests_by_cu():
    """Test that workbook_traceability_report handles missing tests_by_cu parameter."""
    report = workbook_traceability_report()

    assert report["schema"] == "ijt-workbook-traceability/v1"
    assert report["case_count"] == EXPECTED_WORKBOOK_CASE_COUNT
    # All CUs should have 0 linked tests
    for cu_data in report["by_cu"].values():
        assert cu_data["linked_test_count"] == 0


def test_workbook_case_to_json_with_no_tests():
    """Test WorkbookCase.to_json with no linked or exact tests."""
    cases = load_workbook_cases()
    first_case = cases[CU.JOINING_SYSTEM_BASE][0]

    json_data = first_case.to_json([], [])

    assert json_data["linked_test_count"] == 0
    assert json_data["exact_test_count"] == 0
    assert json_data["mapping_precision"] == "cu"


def test_is_step_zero_handles_invalid_types():
    """Test that _is_step_zero returns False for non-numeric types."""
    from helpers.workbook_traceability import _is_step_zero

    assert _is_step_zero("not a number") is False
    assert _is_step_zero(None) is False
    assert _is_step_zero([]) is False


def test_load_workbook_cases_sheet_count_mismatch(monkeypatch):
    from unittest.mock import MagicMock

    import pytest

    from helpers import workbook_traceability as wt

    mock_wb = MagicMock()
    mock_wb.worksheets = [MagicMock()] * (wt.INFRA_SHEET_COUNT + 5)
    mock_wb.close = MagicMock()
    monkeypatch.setattr(wt, "load_workbook", lambda *a, **k: mock_wb)

    with pytest.raises(ValueError, match="CU sheets but registry has"):
        wt.load_workbook_cases()
    mock_wb.close.assert_called_once()
