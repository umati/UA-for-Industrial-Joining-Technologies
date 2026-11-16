import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers.cu_coverage_report import (
    CuCoverageReportRecorder,
    WorkflowEvidenceUnavailable,
    _classify_report,
    _dependency_cus_for_not_supported_reason,
    _marker_cus,
    _marker_dependency_cus,
    _rollup_compliance,
    _rollup_outcome,
    _skip_text,
    qualification_disposition,
    run_assessment,
)


def test_pilot_cannot_qualify_from_presence_while_exact_obligations_are_missing():
    coverage: dict = {
        "by_cu": {
            "increment_joining_process_counter": {
                "claimed": True,
                "compliance": "supported",
                "passed": 5,
                "test_count": 5,
                "requirement_outcome": "incomplete",
            }
        }
    }
    assert qualification_disposition(coverage)["outcome"] == "incomplete"
    assert run_assessment(coverage, 0) == {
        "execution_health": "passed",
        "requirement_qualification": "incomplete",
        "scope_completeness": "complete",
    }
    coverage["deselected_cus"] = ["increment_joining_process_counter"]
    assert run_assessment(coverage, 6)["scope_completeness"] == "incomplete"
    assert run_assessment(coverage, 1)["execution_health"] == "failed"


@pytest.mark.parametrize("route", ["simulator_direct", "target_workflow"])
def test_exact_counter_effect_mapping_is_bound_to_the_executed_route(report_tmp_path, monkeypatch, route):
    output = report_tmp_path / "coverage.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["increment_joining_process_counter"],
        supported_cus=["increment_joining_process_counter"],
    )
    recorder.items_by_nodeid["effect"] = {
        "nodeid": "effect",
        "path": "test_counter.py",
        "name": "effect",
        "cus": ["increment_joining_process_counter"],
        "workbook_refs": [
            {"sheet": "Increment JP Counter", "row": 6, "ref": "Increment JP Counter!R6", "route": "simulator_direct"}
        ],
    }
    report = _Report(nodeid="effect", passed=True)
    report.user_properties = [("ijt_evidence_route", route)]
    recorder.pytest_runtest_logreport(report)
    recorder.pytest_sessionfinish(None, 0)
    payload = json.loads(output.read_text())
    functional = payload["workbook"]["by_cu"]["increment_joining_process_counter"]["cases"][1]
    assert functional["outcome"] == ("passed" if route == "simulator_direct" else "incomplete")
    assert payload["summary"]["workbook_exact_case_count"] == 1
    assert payload["qualification"]["outcome"] == "incomplete"
    assert payload["by_cu"]["increment_joining_process_counter"]["compliance"] == "partial"


@pytest.mark.parametrize(("phase", "route"), [("setup", ""), ("call", "target_workflow")])
def test_route_binding_never_hides_a_failed_counter_execution(report_tmp_path, monkeypatch, phase, route):
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "coverage.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["increment_joining_process_counter"],
        supported_cus=["increment_joining_process_counter"],
    )
    recorder.items_by_nodeid["effect"] = {
        "nodeid": "effect",
        "path": "test_counter.py",
        "name": "effect",
        "cus": ["increment_joining_process_counter"],
        "workbook_refs": [{"ref": "Increment JP Counter!R6", "route": "simulator_direct"}],
    }
    report = _Report(nodeid="effect", when=phase, failed=True)
    report.user_properties = [("ijt_evidence_route", route)] if route else []
    recorder.pytest_runtest_logreport(report)
    recorder.pytest_sessionfinish(None, 1)
    payload = json.loads(recorder.output_path.read_text())
    assert payload["workbook"]["by_cu"]["increment_joining_process_counter"]["cases"][1]["outcome"] == "failed"
    assert payload["by_cu"]["increment_joining_process_counter"]["requirement_outcome"] == "failed"
    assert payload["summary"]["workbook_exact_case_count"] == 1
    assert payload["qualification"]["outcome"] == "failed"


@pytest.mark.parametrize("final_exitstatus", [1, 6])
def test_assessment_preserves_raw_execution_status_after_qualification_override(final_exitstatus):
    coverage = {
        "raw_pytest_exitstatus": 0,
        "by_cu": {
            "intervention_result": {
                "claimed": True,
                "passed": 1,
                "test_count": 1,
                "compliance": "partial",
                "requirement_outcome": "failed" if final_exitstatus == 1 else "incomplete",
            }
        },
    }
    assessment = run_assessment(coverage, final_exitstatus)
    assert assessment["execution_health"] == "passed"
    assert assessment["requirement_qualification"] == ("failed" if final_exitstatus == 1 else "incomplete")
    assert run_assessment(coverage, -1)["execution_health"] == "failed"


@pytest.mark.parametrize("route", ["", "simulate_methods", "start_selected_joining"])
def test_scope_deselection_uses_applicability_from_resolved_trigger_mode(report_tmp_path, monkeypatch, route):
    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "coverage.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["single_result"],
        supported_cus=["single_result"],
        result_trigger_mode=route,
    )
    selected = _Item(
        nodeid="applicable",
        fspath=report_tmp_path / "test_scope.py",
        name="applicable",
        markers=[_Marker("single_result")],
    )
    excluded = _Item(
        nodeid="simulated",
        fspath=report_tmp_path / "test_scope.py",
        name="simulated",
        markers=[_Marker("single_result"), _Marker(name="simulation")],
    )
    recorder.pytest_collection_modifyitems(None, None, [selected, excluded])
    recorder.pytest_deselected([excluded])
    recorder.pytest_runtest_logreport(_Report(nodeid="applicable", passed=True))
    recorder.pytest_sessionfinish(None, 0)
    payload = json.loads(recorder.output_path.read_text())
    assert payload["deselected_cus"] == ([] if route == "start_selected_joining" else ["single_result"])
    assert payload["by_cu"]["single_result"]["test_count"] == (1 if route == "start_selected_joining" else 2)
    assert payload["assessment"]["scope_completeness"] == (
        "complete" if route == "start_selected_joining" else "incomplete"
    )


@pytest.mark.parametrize("compliance", ["blocked", "partial", "untested", "not_supported"])
def test_required_unresolved_coverage_is_never_pass(compliance):
    result = qualification_disposition(
        {
            "by_cu": {
                "single_result": {"claimed": True, "compliance": "supported", "passed": 1},
                "job_result": {"claimed": True, "compliance": compliance},
            },
        }
    )
    assert result["outcome"] == "incomplete"
    assert result["incomplete_cus"] == ["job_result"]


def test_claimed_scope_exclusion_is_visible_and_never_passes():
    result = qualification_disposition(
        {
            "by_cu": {
                "single_result": {"claimed": True, "compliance": "supported", "passed": 1},
                "job_result": {"claimed": True, "compliance": "untested", "scope_excluded": True},
            },
        }
    )
    assert result["outcome"] == "incomplete"
    assert result["scope_excluded_claimed_cus"] == ["job_result"]


@pytest.mark.parametrize(
    "coverage",
    [
        [],
        {},
        {"by_cu": {"job": None}},
        {"by_cu": {"job": {"claimed": False}}},
        {"by_cu": {"job": {"claimed": True, "compliance": "supported", "passed": 0}}},
        {"by_cu": {"job": {"claimed": True, "compliance": "supported", "passed": True}}},
        {"by_cu": {"job": {"claimed": True, "compliance": "supported", "passed": 1}}, "supported_cus": ["missing"]},
    ],
)
def test_missing_or_unproven_claims_never_qualify(coverage):
    assert qualification_disposition(coverage)["outcome"] == "incomplete"


def test_structured_block_is_not_reclassified_by_reason_keywords():
    report = _Report(skipped=True, longrepr=("file.py", 1, "Environment unavailable, not supported"))
    report.user_properties = [("ijt_outcome", "blocked"), ("ijt_reason_code", "target_changed")]
    assert _classify_report(report) == "blocked"


@pytest.mark.parametrize("outcome", ["blocked", "environment"])
def test_workflow_skip_preserves_structured_reason_through_pytest_report(outcome, report_tmp_path):
    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=[], supported_cus=[])
    error = WorkflowEvidenceUnavailable(
        "not supported is not the real reason", "mutation_retry_prohibited", outcome, "counter"
    )
    report = _Report(skipped=True, longrepr=("file.py", 1, str(error)))
    report.user_properties = []
    hook = recorder.pytest_runtest_makereport(None, SimpleNamespace(excinfo=SimpleNamespace(value=error)))
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(SimpleNamespace(get_result=lambda: report))
    assert _classify_report(report) == outcome
    assert dict(report.user_properties)["ijt_reason_code"] == "mutation_retry_prohibited"


def test_definite_failure_cannot_be_hidden_by_scope_exclusion():
    result = qualification_disposition({"by_cu": {"counter": {"claimed": True, "failed": 1, "scope_excluded": True}}})
    assert result["outcome"] == "failed"
    assert result["scope_excluded_claimed_cus"] == ["counter"]


@pytest.mark.parametrize("pending", [None, "future_cu", [123]])
@pytest.mark.parametrize("failed", [0, 1])
def test_malformed_catalogue_review_metadata_never_passes(pending, failed):
    coverage = {
        "by_cu": {"known": {"claimed": True, "passed": 1, "failed": failed, "compliance": "supported"}},
        "unreviewed_cus": pending,
    }
    assert qualification_disposition(coverage)["outcome"] == ("failed" if failed else "incomplete")


def test_unreviewed_row_cannot_be_hidden_by_missing_top_level_metadata():
    coverage = {
        "by_cu": {
            "known": {"claimed": True, "passed": 1, "compliance": "supported"},
            "future_cu": {"claimed": False, "declaration_state": "unreviewed"},
        },
    }
    result = qualification_disposition(coverage)
    assert result["outcome"] == "incomplete"
    assert result["unreviewed_cus"] == ["future_cu"]


@pytest.mark.parametrize("rows", [[], {"known": "invalid row"}])
def test_malformed_report_rows_cannot_become_complete_scope(rows):
    assessment = run_assessment({"by_cu": rows, "supported_cus": ["known"]}, 0)
    assert assessment["scope_completeness"] == "incomplete"
    assert assessment["requirement_qualification"] == "incomplete"


def test_later_skipped_phase_cannot_erase_failed_test(report_tmp_path, monkeypatch):
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "preserved-failure.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path, all_cus=["single_result"], supported_cus=["single_result"]
    )
    recorder.items_by_nodeid["test"] = {"nodeid": "test", "cus": ["single_result"], "name": "test", "path": "test.py"}
    recorder.pytest_runtest_logreport(_Report(nodeid="test", when="call", failed=True))
    recorder.pytest_runtest_logreport(
        _Report(nodeid="test", when="teardown", skipped=True, longrepr="cleanup unavailable")
    )
    assert recorder.results_by_nodeid["test"]["outcome"] == "failed"
    assert recorder.results_by_nodeid["test"]["phase"] == "call"


def test_partial_cu_retains_canonical_inconclusive_action_evidence(report_tmp_path, monkeypatch):
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "inconclusive-cause.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path, all_cus=["single_result"], supported_cus=["single_result"]
    )
    for nodeid in ("content", "action"):
        recorder.items_by_nodeid[nodeid] = {
            "nodeid": nodeid,
            "cus": ["single_result"],
            "name": nodeid,
            "path": "test.py",
        }
    recorder.pytest_runtest_logreport(_Report(nodeid="content", passed=True))
    report = _Report(nodeid="action", skipped=True, longrepr="Accepted action was not observed")
    report.user_properties = [
        ("ijt_outcome", "environment"),
        ("ijt_canonical_outcome", "inconclusive"),
        ("ijt_reason_code", "operation_evidence_timeout"),
    ]
    recorder.pytest_runtest_logreport(report)
    recorder.pytest_sessionfinish(None, 0)
    payload = json.loads(recorder.output_path.read_text())
    assert payload["by_cu"]["single_result"]["canonical_outcome"] == "inconclusive"
    assert payload["by_cu"]["single_result"]["compliance"] == "partial"
    assert payload["qualification"]["outcome"] == "incomplete"


def test_unreviewed_additions_preserve_approved_results_but_do_not_qualify_newer_catalogue(
    report_tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", "reviewed.sut.yaml")
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "coverage.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["single_result", "future_cu"],
        supported_cus=["single_result"],
        unreviewed_cus=["future_cu"],
    )
    item = _Item(
        nodeid="approved-test",
        fspath=report_tmp_path / "test_approved.py",
        name="approved",
        markers=[_Marker("single_result")],
    )
    recorder.pytest_collection_modifyitems(None, None, [item])
    recorder.pytest_runtest_logreport(_Report(nodeid="approved-test", passed=True))
    session = SimpleNamespace(exitstatus=0)
    recorder.pytest_sessionfinish(session, 0)
    payload = json.loads(recorder.output_path.read_text(encoding="utf-8"))
    assert payload["by_cu"]["single_result"]["passed"] == 1
    assert payload["by_cu"]["single_result"]["declaration_state"] == "declared"
    assert payload["by_cu"]["future_cu"]["compliance"] == "untested"
    assert payload["by_cu"]["future_cu"]["declaration_state"] == "unreviewed"
    assert payload["qualification"]["unreviewed_cus"] == ["future_cu"]
    assert session.exitstatus == 6


def test_external_session_with_blocked_claim_returns_incomplete(report_tmp_path, monkeypatch):
    monkeypatch.setenv("OPCUA_TARGET_SERVER_PROFILE", "reviewed.sut.yaml")
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "coverage.json"))
    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["job_result"], supported_cus=["job_result"])
    item = _Item(nodeid="job-test", fspath=report_tmp_path / "test_job.py", name="job", markers=[_Marker("job_result")])
    recorder.pytest_collection_modifyitems(None, None, [item])
    recorder.pytest_runtest_logreport(_Report(nodeid="job-test", skipped=True, longrepr="BLOCKED: stale target"))
    session = SimpleNamespace(exitstatus=0)
    recorder.pytest_sessionfinish(session, 0)
    assert session.exitstatus == 6
    coverage = json.loads(recorder.output_path.read_text())
    assert coverage["qualification"]["outcome"] == "incomplete"
    assert coverage["exitstatus"] == 6
    assert coverage["raw_pytest_exitstatus"] == 0
    assert coverage["assessment"] == run_assessment(coverage, session.exitstatus)


class _Marker:
    def __init__(self, *args, name: str = "requires_cu"):
        self.args = args
        self.name = name


class _Item:
    def __init__(self, *, nodeid: str, fspath: Path, name: str, markers: list[_Marker]):
        self.nodeid = nodeid
        self.fspath = fspath
        self.name = name
        self._markers = markers

    def iter_markers(self, name):
        return [marker for marker in self._markers if marker.name == name]


class _Report:
    def __init__(
        self,
        *,
        nodeid: str = "specification_tests/test_file.py::test_case",
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
        self.user_properties: list[tuple[str, object]] = []


@pytest.mark.parametrize("route", ["simulator_direct", "target_workflow"])
def test_recorder_preserves_both_exact_route_markers_on_one_test(report_tmp_path, monkeypatch, route):
    class WorkbookMarker(_Marker):
        def __init__(self, evidence_route):
            super().__init__("Increment JP Counter", 6, name="workbook_ref")
            self.kwargs = {"route": evidence_route}

    monkeypatch.delenv("OPCUA_TARGET_SERVER_PROFILE", raising=False)
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(report_tmp_path / "dual-route.json"))
    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["increment_joining_process_counter"],
        supported_cus=["increment_joining_process_counter"],
    )
    item = _Item(
        nodeid="effect",
        fspath=report_tmp_path / "test_counter.py",
        name="effect",
        markers=[
            _Marker("increment_joining_process_counter"),
            WorkbookMarker("simulator_direct"),
            WorkbookMarker("target_workflow"),
        ],
    )
    recorder.pytest_collection_modifyitems(None, None, [item])
    report = _Report(nodeid="effect", passed=True)
    report.user_properties = [("ijt_evidence_route", route)]
    recorder.pytest_runtest_logreport(report)
    recorder.pytest_sessionfinish(None, 0)
    payload = json.loads(recorder.output_path.read_text())
    functional = payload["workbook"]["by_cu"]["increment_joining_process_counter"]["cases"][1]
    assert functional["outcome"] == "passed"
    assert payload["summary"]["workbook_exact_case_count"] == 1


@pytest.fixture
def report_tmp_path():
    """Repo-local temp path for environments where pytest tmp_path ACLs are locked."""
    path = Path(__file__).resolve().parents[2] / "tmp" / "cu_coverage_report" / uuid.uuid4().hex
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


def test_marker_dependency_cus_returns_unique_sorted_strings():
    item = _Item(
        nodeid="n",
        fspath=Path("test_file.py"),
        name="test_case",
        markers=[
            _Marker("engineering_units"),
            _Marker("joint_design_data", "engineering_units", name="requires_dependency_cu"),
        ],
    )

    assert _marker_cus(item) == ["engineering_units"]
    assert _marker_dependency_cus(item) == ["engineering_units", "joint_design_data"]


def test_dependency_cus_for_not_supported_reason_matches_public_cu_label():
    reason = "Skipped: Conformance unit 'IJT Joint Design Data' is not supported NOT SUPPORTED"

    assert _dependency_cus_for_not_supported_reason(reason, ["joint_design_data", "engineering_units"]) == [
        "joint_design_data"
    ]


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
    assert (
        _classify_report(
            _Report(skipped=True, longrepr=("file.py", 1, "Skipped: TOOLING LIMITATION - asyncua AddNodes"))
        )
        == "environment"
    )
    assert (
        _classify_report(
            _Report(
                skipped=True,
                longrepr=("file.py", 1, "Skipped: SIMULATOR REGRESSION LIMIT - SimulateBulkResults"),
            )
        )
        == "accepted_policy"
    )
    assert (
        _classify_report(
            _Report(
                skipped=True,
                longrepr=("file.py", 1, "Skipped: COMPANION SPEC PROFILE NOTE - Monitoring.Notifications"),
            )
        )
        == "accepted_policy"
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
    assert _rollup_compliance(["passed", "accepted_policy", "environment"]) == "partial"
    assert _rollup_compliance(["not_supported", "not_supported"]) == "not_supported"
    assert _rollup_compliance(["blocked", "not_supported"]) == "blocked"
    assert _rollup_compliance(["accepted_policy", "environment"]) == "blocked"


def test_recorder_writes_cu_compliance_json(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["single_result", "acknowledge_results"],
        supported_cus=["single_result"],
    )
    items = [
        _Item(
            nodeid="specification_tests/test_file.py::test_passes",
            fspath=test_file,
            name="test_passes",
            markers=[_Marker("single_result")],
        ),
        _Item(
            nodeid="specification_tests/test_file.py::test_not_supported",
            fspath=test_file,
            name="test_not_supported",
            markers=[_Marker("acknowledge_results")],
        ),
        _Item(
            nodeid="specification_tests/test_file.py::test_extension",
            fspath=test_file,
            name="test_extension",
            markers=[_Marker("vendor_extension_cu")],
        ),
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(
        _Report(nodeid="specification_tests/test_file.py::test_passes", passed=True, duration=0.1234567)
    )
    recorder.pytest_runtest_logreport(
        _Report(
            nodeid="specification_tests/test_file.py::test_not_supported",
            skipped=True,
            longrepr=("file.py", 9, "Skipped: AcknowledgeResults method: Not Supported"),
        )
    )
    recorder.pytest_sessionfinish(None, 1)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "ijt-cu-coverage-report/v1"
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
    # Final reports read the canonical outcome; the detailed values above stay intact.
    assert payload["by_cu"]["single_result"]["canonical_outcome"] == "passed"
    assert payload["by_cu"]["single_result"]["claimed"] is True
    # acknowledge_results is not claimed by the manifest, so its absence is informational.
    assert payload["by_cu"]["acknowledge_results"]["claimed"] is False
    assert payload["by_cu"]["acknowledge_results"]["canonical_outcome"] == "not_supported"
    assert payload["by_cu"]["vendor_extension_cu"]["canonical_outcome"] == "not_tested"
    canonical_by_test = {entry["nodeid"]: entry["canonical_outcome"] for entry in payload["tests"]}
    assert canonical_by_test["specification_tests/test_file.py::test_passes"] == "passed"
    assert canonical_by_test["specification_tests/test_file.py::test_not_supported"] == "not_supported"
    assert canonical_by_test["specification_tests/test_file.py::test_extension"] == "not_tested"
    reasons = {entry["nodeid"]: entry["reason"] for entry in payload["tests"]}
    assert reasons["specification_tests/test_file.py::test_not_supported"] == (
        "Skipped: AcknowledgeResults method: Not Supported"
    )


def test_recorder_attributes_not_supported_dependency_to_dependency_cu(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["engineering_units", "joint_design_data"],
        supported_cus=["engineering_units"],
    )
    items = [
        _Item(
            nodeid="specification_tests/test_file.py::test_engineering_units_pass",
            fspath=test_file,
            name="test_engineering_units_pass",
            markers=[_Marker("engineering_units")],
        ),
        _Item(
            nodeid="specification_tests/test_file.py::test_design_value_engineering_units",
            fspath=test_file,
            name="test_design_value_engineering_units",
            markers=[
                _Marker("engineering_units"),
                _Marker("joint_design_data", name="requires_dependency_cu"),
            ],
        ),
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(
        _Report(
            nodeid="specification_tests/test_file.py::test_engineering_units_pass",
            passed=True,
            duration=0.1,
        )
    )
    recorder.pytest_runtest_logreport(
        _Report(
            nodeid="specification_tests/test_file.py::test_design_value_engineering_units",
            when="setup",
            skipped=True,
            longrepr=("file.py", 9, "Skipped: Conformance unit 'IJT Joint Design Data' is not supported NOT SUPPORTED"),
        )
    )
    recorder.pytest_sessionfinish(None, 0)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["by_cu"]["engineering_units"]["outcome"] == "passed"
    assert payload["by_cu"]["engineering_units"]["compliance"] == "supported"
    assert payload["by_cu"]["engineering_units"]["not_supported"] == 0
    assert payload["by_cu"]["joint_design_data"]["outcome"] == "not_supported"
    assert payload["by_cu"]["joint_design_data"]["compliance"] == "not_supported"
    dependency_entry = next(
        entry
        for entry in payload["tests"]
        if entry["nodeid"] == "specification_tests/test_file.py::test_design_value_engineering_units"
    )
    assert dependency_entry["cus"] == ["joint_design_data"]
    assert "dependency_cus" not in dependency_entry


def test_recorder_does_not_overwrite_main_report_during_collect_only(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    output.parent.mkdir(parents=True)
    original = {"schema": "existing-live-run-report", "summary": {"executed_cu_test_count": 831}}
    output.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    recorder.pytest_collection_modifyitems(
        None,
        None,
        [
            _Item(
                nodeid="specification_tests/test_file.py::test_collected_only",
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
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    output.parent.mkdir(parents=True)
    original = {"schema": "existing-live-run-report", "summary": {"executed_cu_test_count": 831}}
    output.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))

    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    session = SimpleNamespace(config=SimpleNamespace(option=SimpleNamespace(collectonly=False)))
    recorder.pytest_sessionfinish(session, 0)

    assert json.loads(output.read_text(encoding="utf-8")) == original


def test_normalize_rows_handles_various_input_types():
    from helpers.cu_coverage_report import _normalize_rows

    assert _normalize_rows(None) == []
    assert _normalize_rows(5) == [5]
    assert _normalize_rows("10") == [10]
    assert _normalize_rows("10, 12, 14") == [10, 12, 14]
    assert _normalize_rows("10-12") == [10, 11, 12]
    assert _normalize_rows("5, 8-10, 15") == [5, 8, 9, 10, 15]
    assert _normalize_rows([3, 5, 7]) == [3, 5, 7]
    assert _normalize_rows("  ") == []
    assert _normalize_rows(",,,") == []


def test_marker_workbook_refs_extracts_sheet_and_rows():
    from helpers.cu_coverage_report import _marker_workbook_refs

    class _WorkbookMarker:
        def __init__(self, args=(), kwargs=None):
            self.args = args
            self.kwargs = kwargs or {}

    class _ItemWithRefs:
        def __init__(self, markers):
            self._markers = markers

        def iter_markers(self, name):
            return self._markers if name == "workbook_ref" else []

    # Test with kwargs
    item = _ItemWithRefs([_WorkbookMarker(kwargs={"sheet": "CU_001", "rows": "10-12"})])
    refs = _marker_workbook_refs(item)
    assert len(refs) == 3
    assert refs[0]["sheet"] == "CU_001"
    assert refs[0]["row"] == 10
    assert refs[0]["ref"] == "CU_001!R10"

    # Test with args
    item = _ItemWithRefs([_WorkbookMarker(args=("CU_002", 5), kwargs={})])
    refs = _marker_workbook_refs(item)
    assert len(refs) == 1
    assert refs[0]["sheet"] == "CU_002"
    assert refs[0]["row"] == 5

    # Test with missing sheet
    item = _ItemWithRefs([_WorkbookMarker(kwargs={"rows": 10})])
    refs = _marker_workbook_refs(item)
    assert refs == []


def test_skip_text_handles_longrepr_string():
    report = _Report(longrepr="Direct string reason", longreprtext="")
    assert _skip_text(report) == "Direct string reason"


def test_classify_report_handles_teardown_failure():
    assert _classify_report(_Report(when="teardown", failed=True)) == "error"


def test_rollup_compliance_handles_edge_cases():
    assert _rollup_compliance(["passed"]) == "supported"
    assert _rollup_compliance(["error"]) == "action_needed"
    assert _rollup_compliance(["skipped"]) == "unknown"
    assert _rollup_compliance(["untested"]) == "untested"


def test_recorder_ignores_passed_setup_and_teardown():
    from pathlib import Path

    recorder = CuCoverageReportRecorder(root=Path("."), all_cus=["test_cu"], supported_cus=None)
    test_file = Path("specification_tests/test_file.py")
    item = _Item(
        nodeid="specification_tests/test_file.py::test_case",
        fspath=test_file,
        name="test_case",
        markers=[_Marker("test_cu")],
    )

    recorder.items_by_nodeid[item.nodeid] = {
        "nodeid": item.nodeid,
        "path": str(test_file),
        "name": item.name,
        "cus": ["test_cu"],
        "workbook_refs": [],
    }

    # Passed setup should be ignored
    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="setup", passed=True))
    assert item.nodeid not in recorder.results_by_nodeid

    # Passed teardown should be ignored
    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="call", passed=True))
    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="teardown", passed=True))
    assert recorder.results_by_nodeid[item.nodeid]["outcome"] == "passed"


def test_recorder_handles_teardown_after_result():
    from pathlib import Path

    recorder = CuCoverageReportRecorder(root=Path("."), all_cus=["test_cu"], supported_cus=None)
    test_file = Path("specification_tests/test_file.py")
    item = _Item(
        nodeid="specification_tests/test_file.py::test_case",
        fspath=test_file,
        name="test_case",
        markers=[_Marker("test_cu")],
    )

    recorder.items_by_nodeid[item.nodeid] = {
        "nodeid": item.nodeid,
        "path": str(test_file),
        "name": item.name,
        "cus": ["test_cu"],
        "workbook_refs": [],
    }

    # Log call phase first
    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="call", passed=True))
    # Cleanup errors invalidate otherwise passing execution evidence.
    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="teardown", failed=True))
    assert recorder.results_by_nodeid[item.nodeid]["outcome"] == "error"


def test_recorder_ignores_non_cu_tests():
    from pathlib import Path

    recorder = CuCoverageReportRecorder(root=Path("."), all_cus=["test_cu"], supported_cus=None)
    report = _Report(nodeid="unit/test_helper.py::test_function", passed=True)
    recorder.pytest_runtest_logreport(report)
    assert "unit/test_helper.py::test_function" not in recorder.results_by_nodeid


def test_recorder_ignores_invalid_report_phases():
    from pathlib import Path

    recorder = CuCoverageReportRecorder(root=Path("."), all_cus=["test_cu"], supported_cus=None)
    test_file = Path("specification_tests/test_file.py")
    item = _Item(
        nodeid="specification_tests/test_file.py::test_case",
        fspath=test_file,
        name="test_case",
        markers=[_Marker("test_cu")],
    )

    recorder.items_by_nodeid[item.nodeid] = {
        "nodeid": item.nodeid,
        "path": str(test_file),
        "name": item.name,
        "cus": ["test_cu"],
        "workbook_refs": [],
    }

    recorder.pytest_runtest_logreport(_Report(nodeid=item.nodeid, when="collect", passed=True))
    assert item.nodeid not in recorder.results_by_nodeid


def test_classify_report_handles_service_unavailable():
    report = _Report(skipped=True, longrepr=("file.py", 1, "SERVICE UNAVAILABLE via this asyncua version"))
    assert _classify_report(report) == "environment"

    report = _Report(skipped=True, longrepr=("file.py", 1, "Client-library limitation prevents this test"))
    assert _classify_report(report) == "environment"


def test_recorder_handles_workbook_error(report_tmp_path, monkeypatch):
    """Test that recorder gracefully handles workbook traceability errors."""
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    # Force workbook error by using non-existent path
    monkeypatch.setattr("helpers.cu_coverage_report.workbook_traceability_report", lambda **kw: {"error": "test_error"})

    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    items = [
        _Item(
            nodeid="specification_tests/test_file.py::test_case",
            fspath=test_file,
            name="test_case",
            markers=[_Marker("single_result")],
        )
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(_Report(nodeid="specification_tests/test_file.py::test_case", passed=True))
    recorder.pytest_sessionfinish(None, 0)

    payload = json.loads(output.read_text(encoding="utf-8"))
    # Should gracefully handle error
    assert "workbook" in payload


def test_rollup_compliance_handles_passed_with_environment():
    """Unavailable evidence cannot be hidden behind another passing test."""
    assert _rollup_compliance(["passed", "environment"]) == "partial"


def test_rollup_compliance_handles_all_not_supported():
    """Test that all not_supported outcomes return not_supported."""
    assert _rollup_compliance(["not_supported"]) == "not_supported"


def test_classify_report_returns_skipped_for_generic_skip():
    """Test that generic skip reasons return 'blocked'."""
    report = _Report(skipped=True, longrepr=("file.py", 1, "Skipped: generic reason"))
    assert _classify_report(report) == "blocked"


def test_normalize_rows_handles_int_value():
    """Test that _normalize_rows handles integer values."""
    from helpers.cu_coverage_report import _normalize_rows

    assert _normalize_rows(5) == [5]


def test_marker_workbook_refs_handles_kwargs_row():
    """Test that _marker_workbook_refs extracts row from kwargs."""
    from helpers.cu_coverage_report import _marker_workbook_refs

    class _WorkbookMarker:
        def __init__(self, args=(), kwargs=None):
            self.args = args
            self.kwargs = kwargs or {}

    class _ItemWithRefs:
        def __init__(self, markers):
            self._markers = markers

        def iter_markers(self, name):
            return self._markers if name == "workbook_ref" else []

    # Test with row in kwargs
    item = _ItemWithRefs([_WorkbookMarker(kwargs={"sheet": "CU_001", "row": 5})])
    refs = _marker_workbook_refs(item)
    assert len(refs) == 1
    assert refs[0]["row"] == 5


def test_recorder_handles_workbook_exception(report_tmp_path, monkeypatch):
    """Test that recorder handles exception in workbook_traceability_report."""
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    # Force workbook exception
    def raise_exception(**kwargs):
        raise RuntimeError("Workbook error")

    monkeypatch.setattr("helpers.cu_coverage_report.workbook_traceability_report", raise_exception)

    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    items = [
        _Item(
            nodeid="specification_tests/test_file.py::test_case",
            fspath=test_file,
            name="test_case",
            markers=[_Marker("single_result")],
        )
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(_Report(nodeid="specification_tests/test_file.py::test_case", passed=True))
    recorder.pytest_sessionfinish(None, 0)

    payload = json.loads(output.read_text(encoding="utf-8"))
    # Should gracefully handle exception with error field
    assert payload["workbook"]["schema"] == "ijt-workbook-traceability/v1"
    assert "error" in payload["workbook"]


def test_classify_report_returns_skipped_for_empty_reason():
    rep = _Report(skipped=False, passed=False, failed=False)
    assert _classify_report(rep) == "skipped"


def test_rollup_outcome_returns_error():
    assert _rollup_outcome(["passed", "error"]) == "error"
    assert _rollup_outcome(["error", "not_supported"]) == "error"


def test_recorder_setup_passed_guard_and_workbook_exact_refs(report_tmp_path, monkeypatch):
    output = report_tmp_path / "reports" / "cu-coverage-report.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_file.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    captured_workbook_inputs = {}

    def workbook_report(**kwargs):
        captured_workbook_inputs.update(kwargs)
        return {"by_cu": {}}

    monkeypatch.setattr("helpers.cu_coverage_report.workbook_traceability_report", workbook_report)

    class _WorkbookMarker(_Marker):
        def __init__(self):
            super().__init__("CU_001", 5, name="workbook_ref")
            self.kwargs = {}

    recorder = CuCoverageReportRecorder(root=report_tmp_path, all_cus=["single_result"], supported_cus=None)
    items = [
        _Item(
            nodeid="specification_tests/test_file.py::test_case",
            fspath=test_file,
            name="test_case",
            markers=[_Marker("single_result"), _WorkbookMarker()],
        )
    ]

    recorder.pytest_collection_modifyitems(None, None, items)
    # A passed setup report is ignored even when classification is unexpectedly passed.
    with monkeypatch.context() as patch:
        patch.setattr("helpers.cu_coverage_report._classify_report", lambda _r: "passed")
        recorder.pytest_runtest_logreport(
            _Report(nodeid="specification_tests/test_file.py::test_case", when="setup", passed=False)
        )

    recorder.pytest_runtest_logreport(
        _Report(nodeid="specification_tests/test_file.py::test_case", when="call", passed=True)
    )
    recorder.pytest_sessionfinish(None, 0)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["by_cu"]["single_result"]["passed"] == 1
    assert captured_workbook_inputs["exact_refs_by_row"] == {"CU_001!R5": {items[0].nodeid}}


def test_recorder_marks_a_claimed_but_unsupported_cu_as_failed(report_tmp_path, monkeypatch):
    """A claimed CU that reports Not Supported is a canonical Failed, not an informational note."""
    output = report_tmp_path / "reports" / "claimed-gap.json"
    monkeypatch.setenv("IJT_CU_COVERAGE_REPORT_FILE", str(output))
    test_file = report_tmp_path / "conformance" / "test_claimed.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# test placeholder\n", encoding="utf-8")

    recorder = CuCoverageReportRecorder(
        root=report_tmp_path,
        all_cus=["acknowledge_results"],
        supported_cus=["acknowledge_results"],
    )
    items = [
        _Item(
            nodeid="specification_tests/test_claimed.py::test_claimed_gap",
            fspath=test_file,
            name="test_claimed_gap",
            markers=[_Marker("acknowledge_results")],
        )
    ]
    recorder.pytest_collection_modifyitems(None, None, items)
    recorder.pytest_runtest_logreport(
        _Report(
            nodeid="specification_tests/test_claimed.py::test_claimed_gap",
            skipped=True,
            longrepr=("file.py", 9, "Skipped: AcknowledgeResults method: Not Supported"),
        )
    )
    recorder.pytest_sessionfinish(None, 1)

    payload = json.loads(output.read_text(encoding="utf-8"))
    entry = payload["by_cu"]["acknowledge_results"]
    assert entry["claimed"] is True
    assert entry["compliance"] == "not_supported"  # detailed vocabulary is preserved
    assert entry["canonical_outcome"] == "failed"  # claimed behaviour missing -> Failed
    assert payload["tests"][0]["outcome"] == "not_supported"
    assert payload["tests"][0]["canonical_outcome"] == "failed"


def test_manual_required_cus_defer_in_automated_mode_but_remain_incomplete_in_guided_mode():
    base_by_cu = {
        "supported_cu": {
            "claimed": True,
            "manual_required": False,
            "compliance": "supported",
            "passed": 2,
            "test_count": 2,
        },
        "physical_event_cu": {
            "claimed": True,
            "manual_required": True,
            "compliance": "blocked",
            "passed": 0,
            "blocked": 2,
            "test_count": 2,
        },
    }
    automated = {
        "execution_mode": "automated",
        "allow_manual_steps": False,
        "supported_cus": ["supported_cu", "physical_event_cu"],
        "manual_required_cus": ["physical_event_cu"],
        "by_cu": base_by_cu,
    }
    disp_auto = qualification_disposition(automated)
    assert disp_auto["outcome"] == "passed"
    assert disp_auto["incomplete_cus"] == []
    assert disp_auto["manual_deferred_cus"] == ["physical_event_cu"]
    assert run_assessment(automated, 0) == {
        "execution_health": "passed",
        "requirement_qualification": "passed",
        "scope_completeness": "complete",
    }

    guided = {
        **automated,
        "execution_mode": "guided",
        "allow_manual_steps": True,
    }
    disp_guided = qualification_disposition(guided)
    assert disp_guided["outcome"] == "incomplete"
    assert disp_guided["incomplete_cus"] == ["physical_event_cu"]
    assert "manual_deferred_cus" not in disp_guided

    failing_manual = {
        **automated,
        "by_cu": {
            **base_by_cu,
            "physical_event_cu": {
                **base_by_cu["physical_event_cu"],
                "failed": 1,
                "compliance": "action_needed",
            },
        },
    }
    disp_failed = qualification_disposition(failing_manual)
    assert disp_failed["outcome"] == "failed"
    assert disp_failed["failed_cus"] == ["physical_event_cu"]
