from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_root_runner():
    root = Path(__file__).resolve().parents[1]
    runner_path = root / "run_all_tests.py"
    spec = importlib.util.spec_from_file_location("ijt_root_run_all_tests", runner_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_runner = _load_root_runner()


def test_zizmor_rc13_medium_findings_is_pass() -> None:
    result = _runner._parse_zizmor_output(
        '[{"determinations":{"severity":"Medium"}},{"determinations":{"severity":"Medium"}}]',
        13,
    )
    assert result.status == "PASS"
    assert result.detail == "2 finding(s), none high/critical"


def test_zizmor_rc13_high_finding_is_fail() -> None:
    result = _runner._parse_zizmor_output('[{"determinations":{"severity":"High"}}]', 13)
    assert result.status == "FAIL"
    assert result.detail == "1 high/critical finding(s)"


def test_zizmor_rc1_tool_error_is_skip() -> None:
    result = _runner._parse_zizmor_output("", 1)
    assert result.status == "SKIP"
    assert result.detail == "zizmor error — skipping"


def test_zizmor_non_list_json_is_skip() -> None:
    non_list_payload = '{"results":[{"determinations":{"severity":"High"}}]}'
    result = _runner._parse_zizmor_output(non_list_payload, 13)
    assert result.status == "SKIP"
    assert result.detail == "Could not parse output — zizmor version mismatch"


def test_zizmor_empty_stdout_with_findings_exit_is_zero_findings_pass() -> None:
    result = _runner._parse_zizmor_output("", 13)
    assert result.status == "PASS"
    assert result.detail == "0 finding(s), none high/critical"


def test_zizmor_clean_run_is_zero_findings_pass() -> None:
    result = _runner._parse_zizmor_output("", 0)
    assert result.status == "PASS"
    assert result.detail == "0 finding(s), none high/critical"
