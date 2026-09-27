"""
JSON Reporter: Generates structured, machine-readable metrics for telemetry dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics


def export_json_report(
    output_path: str | Path,
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    """Export benchmark telemetry as structured JSON."""
    totals = [s.total_result_transfer_time_ms for s in samples if s.total_result_transfer_time_ms is not None]
    transports = [s.network_transport_time_ms for s in samples if s.network_transport_time_ms is not None]
    servers = [s.server_processing_time_ms for s in samples if s.server_processing_time_ms is not None]
    joinings = [s.joining_duration_ms for s in samples if s.joining_duration_ms is not None]

    from collections import defaultdict

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    per_server = {}
    for ep, ep_samples in sorted(by_endpoint.items()):
        ep_totals = [s.total_result_transfer_time_ms for s in ep_samples if s.total_result_transfer_time_ms is not None]
        ep_transports = [s.network_transport_time_ms for s in ep_samples if s.network_transport_time_ms is not None]
        ep_servers = [s.server_processing_time_ms for s in ep_samples if s.server_processing_time_ms is not None]
        skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
        per_server[ep] = {
            "sample_count": len(ep_samples),
            "clock_skew_ms": skews[0] if skews else 0.0,
            "total_result_transfer_time_ms": compute_statistics(ep_totals),
            "network_transport_time_ms": compute_statistics(ep_transports),
            "server_processing_time_ms": compute_statistics(ep_servers),
        }

    report = {
        "pool_name": pool_name,
        "sample_count": len(samples),
        "distinct_servers": len(by_endpoint),
        "per_server_statistics": per_server,
        "statistics": {
            "total_result_transfer_time_ms": compute_statistics(totals),
            "network_transport_time_ms": compute_statistics(transports),
            "server_processing_time_ms": compute_statistics(servers),
            "joining_duration_ms": compute_statistics(joinings),
        },
        "verdict": {
            "primary_bottleneck": verdict.primary_bottleneck,
            "headline": verdict.headline,
            "explanation": verdict.explanation,
            "recommendation": verdict.recommendation,
            "warnings": verdict.warnings,
        },
        "samples": [
            {
                "sample_id": s.sample_id,
                "endpoint": s.endpoint,
                "total_result_transfer_time_ms": s.total_result_transfer_time_ms,
                "server_processing_time_ms": s.server_processing_time_ms,
                "network_transport_time_ms": s.network_transport_time_ms,
                "joining_duration_ms": s.joining_duration_ms,
                "clock_skew_ms": s.clock_skew_ms,
            }
            for s in samples
        ],
        "metadata": extra_metadata or {},
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
