"""
JSON Reporter: Generates structured, machine-readable metrics for telemetry dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..attribution import DiagnosticVerdict
from ..result_transfer_latency import LatencySample, compute_statistics


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

    report = {
        "pool_name": pool_name,
        "sample_count": len(samples),
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
