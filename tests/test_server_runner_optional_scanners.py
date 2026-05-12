from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_server_runner():
    root = Path(__file__).resolve().parents[1]
    runner_path = root / "OPC_UA_Servers" / "Release2" / "run_all_tests.py"
    spec = importlib.util.spec_from_file_location(
        "ijt_server_runner_optional_scanners", runner_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_optional_scanner_skips_are_deferred_and_consolidated(monkeypatch):
    runner = _load_server_runner()
    printed: list[str] = []
    results: list[tuple] = []
    monkeypatch.setattr(runner, "_print", printed.append)

    runner._record(
        results,
        1,
        "Dockerfile (hadolint)",
        True,
        "SKIP (hadolint not installed)",
        optional=True,
    )
    runner._record(results, 1, "server_configuration.json", True, "PASS")
    runner._print_optional_scanner_status(results)

    assert "[PHASE 1] Dockerfile (hadolint)" not in "\n".join(printed)
    assert "[PHASE 1] server_configuration.json .. PASS" in printed
    assert "[PHASE 1] Optional scanner status" in printed
    assert "  | Dockerfile (hadolint) | SKIP (hadolint not installed) |" in printed


def test_required_skip_still_prints_inline(monkeypatch):
    runner = _load_server_runner()
    printed: list[str] = []
    results: list[tuple] = []
    monkeypatch.setattr(runner, "_print", printed.append)

    runner._record(results, 1, "Required future check", True, "SKIP (temporarily unavailable)")

    assert printed == ["[PHASE 1] Required future check .. SKIP (temporarily unavailable)"]
    assert results == [(1, "Required future check", True, "SKIP (temporarily unavailable)", False)]


def test_optional_scanner_summary_preserves_exit_code_semantics():
    runner = _load_server_runner()

    assert runner._all_results_ok([(1, "Image scan (trivy)", True, "SKIP (trivy missing)", True)])
    assert not runner._all_results_ok(
        [
            (1, "Image scan (trivy)", True, "SKIP (trivy missing)", True),
            (1, "Packages present", False, "FAIL (missing Linux package zip)", False),
        ]
    )
