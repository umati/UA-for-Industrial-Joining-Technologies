"""
JUnit XML Reporter: Generates standard test-results XML for CI test dashboards.
Encodes latency percentiles, pool coverage status, and worker failure states.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from ..attribution import DiagnosticVerdict
from ..result_transfer_latency import LatencySample, compute_statistics


def write_junit_xml(
    output_path: str | Path,
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    failed_threshold_msg: str | None = None,
    coverage_valid: bool = True,
    coverage_msg: str = "",
    worker_errors: list[str] | None = None,
    total_endpoints: int = 1,
    connected_count: int = 1,
) -> None:
    """Write standard JUnit XML file containing perf properties and failure cases."""
    totals = [s.total_result_transfer_time_ms for s in samples if s.total_result_transfer_time_ms is not None]
    transports = [s.network_transport_time_ms for s in samples if s.network_transport_time_ms is not None]

    st_total = compute_statistics(totals)
    st_transport = compute_statistics(transports)

    # Determine failures
    failures: list[str] = []
    if failed_threshold_msg:
        failures.append(failed_threshold_msg)
    if not coverage_valid:
        failures.append(f"Endpoint Coverage Violation: {coverage_msg}")
    if worker_errors:
        failures.append(f"Worker Errors: {'; '.join(worker_errors)}")
    if not samples:
        failures.append("No result event samples were collected during benchmark.")

    testsuites = ET.Element("testsuites", name="IJT_Performance_Suite")
    testsuite = ET.SubElement(
        testsuites,
        "testsuite",
        name=f"Performance_{pool_name}",
        tests="1",
        failures=str(len(failures)),
        errors="0",
        skipped="0",
    )

    properties = ET.SubElement(testsuite, "properties")

    def add_prop(name: str, val: str) -> None:
        ET.SubElement(properties, "property", name=name, value=val)

    add_prop("perf_sample_count", str(len(samples)))
    add_prop("perf_total_endpoints", str(total_endpoints))
    add_prop("perf_connected_endpoints", str(connected_count))
    add_prop("perf_coverage_valid", str(coverage_valid))
    add_prop("perf_coverage_msg", coverage_msg)
    add_prop("perf_min_total_ms", f"{st_total['min']:.2f}" if totals else "0.00")
    add_prop("perf_mean_total_ms", f"{st_total['mean']:.2f}" if totals else "0.00")
    add_prop("perf_p90_total_result_transfer_time_ms", f"{st_total['p90']:.2f}" if totals else "0.00")
    add_prop("perf_p99_total_result_transfer_time_ms", f"{st_total['p99']:.2f}" if totals else "0.00")
    add_prop("perf_max_total_ms", f"{st_total['max']:.2f}" if totals else "0.00")
    add_prop("perf_p90_network_transport_time_ms", f"{st_transport['p90']:.2f}" if transports else "0.00")
    add_prop("perf_primary_bottleneck", verdict.primary_bottleneck)

    testcase = ET.SubElement(
        testsuite,
        "testcase",
        classname="ijt_performance_client",
        name=f"test_pool_latency_{pool_name}",
        time=f"{(st_total['mean'] / 1000.0) if totals else 0.0:.3f}",
    )

    if failures:
        combined_failure_msg = " | ".join(failures)
        failure_elem = ET.SubElement(testcase, "failure", message=combined_failure_msg)
        failure_elem.text = "\n".join(failures)

    tree = ET.ElementTree(testsuites)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
