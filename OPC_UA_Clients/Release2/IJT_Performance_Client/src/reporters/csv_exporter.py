"""
CSV Reporter: Exports detailed sample-by-sample latency metrics to CSV.
Excludes massive trace curve arrays for fast, lightweight analytics and reporting.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from ..results import LatencySample


def _ms(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else ""


def export_csv_report(
    output_path: str | Path,
    samples: Sequence[LatencySample],
) -> None:
    """Export individual result samples (timing metrics, no raw curves) to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "sample_id",
        "endpoint",
        "result_id",
        "result_evaluation",
        "trace_curves",
        "trace_points",
        "trace_declared_points",
        "trace_decoded_points",
        "trace_is_incomplete",
        "bytes_received_time",
        "decoded_time",
        "client_received_time",
        "timing_source",
        "event_time",
        "creation_time",
        "start_time",
        "end_time",
        "joining_duration_ms",
        "server_processing_time_ms",
        "network_transport_time_ms",
        "total_result_transfer_time_ms",
        "delivery_time_ms",
        "client_ready_time_ms",
        "client_decode_time_ms",
        "dispatch_delay_ms",
        "raw_network_transport_time_ms",
        "raw_total_result_transfer_time_ms",
        "raw_delivery_time_ms",
        "raw_client_ready_time_ms",
        "is_clamped_to_zero",
        "clock_skew_ms",
        "clock_warning",
        "integrity_status",
        "integrity_reason",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in samples:
            writer.writerow(
                {
                    "sample_id": s.sample_id,
                    "endpoint": s.endpoint,
                    "result_id": s.result_id or "",
                    "result_evaluation": s.result_evaluation or "",
                    "trace_curves": s.trace_curves_count,
                    "trace_points": s.trace_total_points,
                    "trace_declared_points": s.trace_declared_points,
                    "trace_decoded_points": s.trace_decoded_points,
                    "trace_is_incomplete": "UNKNOWN"
                    if s.trace_is_incomplete is None
                    else ("TRUE" if s.trace_is_incomplete else "FALSE"),
                    "bytes_received_time": s.bytes_received_time.isoformat() if s.bytes_received_time else "",
                    "decoded_time": s.decoded_time.isoformat() if s.decoded_time else "",
                    "client_received_time": s.client_received_time.isoformat() if s.client_received_time else "",
                    "timing_source": s.timing_source,
                    "event_time": s.event_time.isoformat() if s.event_time else "",
                    "creation_time": s.creation_time.isoformat() if s.creation_time else "",
                    "start_time": s.start_time.isoformat() if s.start_time else "",
                    "end_time": s.end_time.isoformat() if s.end_time else "",
                    "joining_duration_ms": f"{s.joining_duration_ms:.2f}" if s.joining_duration_ms is not None else "",
                    "server_processing_time_ms": f"{s.server_processing_time_ms:.2f}"
                    if s.server_processing_time_ms is not None
                    else "",
                    "network_transport_time_ms": f"{s.network_transport_time_ms:.2f}"
                    if s.network_transport_time_ms is not None
                    else "",
                    "total_result_transfer_time_ms": f"{s.total_result_transfer_time_ms:.2f}"
                    if s.total_result_transfer_time_ms is not None
                    else "",
                    "delivery_time_ms": _ms(s.delivery_time_ms),
                    "client_ready_time_ms": _ms(s.client_ready_time_ms),
                    "client_decode_time_ms": _ms(s.client_decode_time_ms),
                    "dispatch_delay_ms": _ms(s.dispatch_delay_ms),
                    "raw_delivery_time_ms": _ms(s.raw_delivery_time_ms),
                    "raw_client_ready_time_ms": _ms(s.raw_client_ready_time_ms),
                    "clock_warning": "TRUE" if s.clock_warning else "FALSE",
                    "raw_network_transport_time_ms": f"{s.raw_network_transport_time_ms:.2f}"
                    if s.raw_network_transport_time_ms is not None
                    else "",
                    "raw_total_result_transfer_time_ms": f"{s.raw_total_result_transfer_time_ms:.2f}"
                    if s.raw_total_result_transfer_time_ms is not None
                    else "",
                    "is_clamped_to_zero": "TRUE" if s.is_clamped_to_zero else "FALSE",
                    "clock_skew_ms": f"{s.clock_skew_ms:.2f}",
                    "integrity_status": s.integrity_status,
                    "integrity_reason": s.integrity_reason,
                }
            )
