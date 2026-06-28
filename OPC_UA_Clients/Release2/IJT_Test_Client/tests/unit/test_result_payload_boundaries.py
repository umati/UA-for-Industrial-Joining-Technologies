from __future__ import annotations

from types import SimpleNamespace

from specification_tests.test_single_result_data import _reported_value_field_failures


def test_result_payload_boundary_allows_absent_or_empty_reported_values():
    payload = SimpleNamespace(ReportedValues=[], OverallReportedValues=())

    assert _reported_value_field_failures("Result", payload) == []


def test_result_payload_boundary_reports_non_empty_reported_values():
    payload = SimpleNamespace(ReportedValues=[SimpleNamespace(CurrentValue=1.0)])

    assert _reported_value_field_failures("Result", payload) == ["Result.ReportedValues is present and non-empty"]
