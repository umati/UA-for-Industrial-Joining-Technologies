"""
JSON Reporter: Generates structured, machine-readable metrics for telemetry dashboards.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..diagnostics import DiagnosticVerdict
from ..results import LatencySample, compute_statistics
from ._metrics import METRIC_ROWS, integrity_counts, metric_values, valid_samples, wire_timing_count


def export_json_report(
    output_path: str | Path,
    samples: list[LatencySample],
    verdict: DiagnosticVerdict,
    pool_name: str,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    """Export benchmark telemetry as structured JSON.

    ``statistics`` and ``per_server_statistics`` use VALID samples only; ``samples`` lists every
    received result with its integrity status.
    """
    valid = valid_samples(samples)

    from collections import defaultdict

    by_endpoint: dict[str, list[LatencySample]] = defaultdict(list)
    for s in samples:
        by_endpoint[s.endpoint].append(s)

    per_server = {}
    for ep, ep_samples in sorted(by_endpoint.items()):
        ep_valid = valid_samples(ep_samples)
        skews = [s.clock_skew_ms for s in ep_samples if s.clock_skew_ms is not None]
        per_server[ep] = {
            "sample_count": len(ep_samples),
            "valid_count": len(ep_valid),
            "clock_skew_ms": skews[0] if skews else 0.0,
            **{attr: compute_statistics(metric_values(ep_valid, attr)) for attr, _, _ in METRIC_ROWS},
        }

    report = {
        "pool_name": pool_name,
        "sample_count": len(samples),
        "valid_sample_count": len(valid),
        "integrity_counts": dict(integrity_counts(samples)),
        "wire_timing_sample_count": wire_timing_count(valid),
        "statistics_basis": "VALID samples only",
        "headline_metric": "delivery_time_ms",
        "distinct_servers": len(by_endpoint),
        "per_server_statistics": per_server,
        "statistics": {attr: compute_statistics(metric_values(valid, attr)) for attr, _, _ in METRIC_ROWS},
        "verdict": {
            "primary_bottleneck": verdict.primary_bottleneck,
            "headline": verdict.headline,
            "explanation": verdict.explanation,
            "recommendation": verdict.recommendation,
            "warnings": verdict.warnings,
        },
        "samples": [s.to_dict() for s in samples],
        "metadata": extra_metadata or {},
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
