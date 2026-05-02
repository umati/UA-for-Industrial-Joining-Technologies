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
    assert first_case.sheet == "Joining System Base"
    assert first_case.row == 4
    assert first_case.tc_no == 1
    assert first_case.case_type == "positive"


def test_workbook_traceability_report_links_rows_to_cu_tests_and_exact_refs():
    first_case = load_workbook_cases()[CU.JOINING_SYSTEM_BASE][0]
    nodeid = "conformance/test_joining_system_base.py::test_joining_system_type_present"

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
