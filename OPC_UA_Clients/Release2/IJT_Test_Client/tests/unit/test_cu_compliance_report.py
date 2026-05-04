import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers.cu_compliance_report import (
    CuComplianceReportRecorder,
    _classify_report,
    _marker_cus,
    _rollup_compliance,
    _rollup_outcome,
    _skip_text,
)


class _Marker:
    def __init__(self, *args):
        self.args = args


class _Item:
    def __init__(self, *, nodeid: str, fspath: Path, name: str, markers: list[_Marker]):
        self.nodeid = nodeid
        self.fspath = fspath
        self.name = name
        self._markers = markers

    def iter_markers(self, name):
        return self._markers if name == "requires_cu" else []


class _Report:
    def __init__(
        self,
        *,
        nodeid: str = "conformance/test_file.py::test_case",
        when: str = "call",
        failed: bool = False,
        passed: bool = False,
        skipped: bool = False,
        duration: float = 0.0,
        longrepr="",
        longreprtext: str = "",
    ):
        self.nodeid = nodeid
        self.when = when
        self.failed = failed
        self.passed = passed
        self.skipped = skipped
        self.duration = duration
        self.longrepr = longrepr
        self.longreprtext = longreprtext


@pytest.fixture
def report_tmp_path():
    """Repo-local temp path for environments where pytest tmp_path ACLs are locked."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "cu_compliance_report" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield path


def test_marker_cus_returns_unique_sorted_strings():
    item = _Item(
        nodeid="n",
        fspath=Path("test_file.py"),
        name="test_case",
        markers=[_Marker("z_cu", "a_cu"), _Marker("a_cu")],
    )

    assert _marker_cus(item) == ["a_cu", "z_cu"]


def test_skip_text_prefers_longreprtext():
    report = _Report(longrepr="fallback", longreprtext="expanded reason")

    assert _skip_text(report) == "expanded reason"


def test_skip_text_extracts_pytest_tuple_reason():
    report = _Report(longrepr=("C:/repo/test_file.py", 42, "Skipped: optional method: Not Supported"))

    assert _skip_text(report) == "Skipped: optional method: Not Supported"


def test_classify_report_maps_pytest_outcomes():
    assert _classify_report(_Report(when="setup", failed=True)) == "error"
    assert _classify_report(_Report(when="call", failed=True)) == "failed"
    assert _classify_report(_Report(passed=True)) == "passed"
    assert (
        _classify_report(_Report(skipped=True, longrepr=("file.py", 1, "Skipped: method: Not Supported")))
        == "not_supported"
    )
    assert (
        _classify_report(_Report(skipped=True, longrepr=("file.py", 1, "Skipped: ACCEPTED POLICY - state")))
        == "accepted_policy"
    )
    assert (
        _classify_report(_Report(skipped=True, longrepr=("file.py", 1, "Skipped: ENVIRONMENT - asyncua limitation")))
        == "environment"
    )
    assert _classify_report(_Report(skipped=True, longrepr=("file.py", 1, "Skipped: precondition unavailable"))) == (
        "blocked"
    )


def test_rollup_outcome_uses_compliance_priority():
    assert _rollup_outcome([]) == "untested"
    assert _rollup_outcome(["passed", "failed", "not_supported"]) == "failed"
    assert _rollup_outcome(["passed", "blocked"]) == "passed"
    assert _rollup_outcome(["passed", "accepted_policy", "environment"]) == "passed"
    assert _rollup_outcome(["not_supported", "not_supported"]) == "not_supported"
    assert _rollup_outcome(["blocked", "not_supported"]) == "blocked"


def test_rollup_compliance_is_conservative_for_report_readers():
    assert _rollup_compliance([]) == "untested"
    assert _rollup_compliance(["passed", "failed", "not_supported"]) == "action_needed"
    assert _rollup_compliance(["passed", "blocked"]) == "partial"
    assert _rollup_compliance(["passed", "accepted_policy", "environment"]) == "supported"
    assert _rollup_compliance(["not_supported", "not_supported"]) == "not_supported"
    assert _rollup_compliance(["blocked", "not_supported"]) == "blocked"
    assert _rollup_compliance(["accepted_policy", "environment"]) == "blocked"


def test_recorder_writes_cu_compliance_json(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-compliance-report.json"
    monkeypatch.setenv("IJT_CU_COMPLIANCE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuComplianceReportRecorder(
        root=report_tmp_path,
        all_cus=["single_result", "acknowledge_results"],
        supported_cus=["single_result"],
    )
    items = [
        _Item(
            nodeid="conformance/test_file.py::test_passes",
            fspath=test_file,
            name="test_passes",
            markers=[_Marker("single_result")],
        ),
        _Item(
            nodeid="conformance/test_file.py::test_not_supported",
            fspath=test_file,
            name="test_not_supported",
            markers=[_Marker("acknowledge_results")],
        ),
        _Item(
            nodeid="conformance/test_file.py::test_extension",
            fspath=test_file,
            name="test_extension",
            markers=[_Marker("vendor_extension_cu")],
        ),
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(
        _Report(nodeid="conformance/test_file.py::test_passes", passed=True, duration=0.1234567)
    )
    recorder.pytest_runtest_logreport(
        _Report(
            nodeid="conformance/test_file.py::test_not_supported",
            skipped=True,
            longrepr=("file.py", 9, "Skipped: AcknowledgeResults method: Not Supported"),
        )
    )
    recorder.pytest_sessionfinish(None, 1)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "ijt-cu-compliance-report/v1"
    assert payload["exitstatus"] == 1
    assert payload["supported_cus"] == ["single_result"]
    assert payload["summary"]["official_cu_count"] == 2
    assert payload["summary"]["extension_cus"] == ["vendor_extension_cu"]
    assert payload["summary"]["missing_test_cus"] == []
    assert payload["by_cu"]["single_result"]["outcome"] == "passed"
    assert payload["by_cu"]["single_result"]["compliance"] == "supported"
    assert payload["by_cu"]["acknowledge_results"]["outcome"] == "not_supported"
    assert payload["by_cu"]["acknowledge_results"]["compliance"] == "not_supported"
    assert payload["by_cu"]["vendor_extension_cu"]["outcome"] == "untested"
    assert payload["by_cu"]["vendor_extension_cu"]["compliance"] == "untested"
    reasons = {entry["nodeid"]: entry["reason"] for entry in payload["tests"]}
    assert reasons["conformance/test_file.py::test_not_supported"] == (
        "Skipped: AcknowledgeResults method: Not Supported"
    )


def test_recorder_does_not_overwrite_main_report_during_collect_only(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-compliance-report.json"
    output.parent.mkdir(parents=True)
    original = {"schema": "existing-live-run-report", "summary": {"executed_cu_test_count": 831}}
    output.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setenv("IJT_CU_COMPLIANCE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuComplianceReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    recorder.pytest_collection_modifyitems(
        None,
        None,
        [
            _Item(
                nodeid="conformance/test_file.py::test_collected_only",
                fspath=test_file,
                name="test_collected_only",
                markers=[_Marker("single_result")],
            )
        ],
    )

    session = SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=True)))
    recorder.pytest_sessionfinish(session, 0)

    assert json.loads(output.read_text(encoding="utf-8")) == original


def test_recorder_does_not_overwrite_main_report_when_no_cu_tests(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-compliance-report.json"
    output.parent.mkdir(parents=True)
    original = {"schema": "existing-live-run-report", "summary": {"executed_cu_test_count": 831}}
    output.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setenv("IJT_CU_COMPLIANCE_REPORT_FILE", str(output))

    recorder = CuComplianceReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    session = SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=False)))
    recorder.pytest_sessionfinish(session, 0)

    assert json.loads(output.read_text(encoding="utf-8")) == original
