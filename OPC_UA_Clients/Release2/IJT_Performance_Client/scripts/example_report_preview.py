"""Example preview script to inspect Performance Client console & markdown reports.

Can be run from repository root or client root:
    python OPC_UA_Clients/Release2/IJT_Performance_Client/scripts/example_report_preview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
client_dir = Path(__file__).resolve().parent.parent
if str(client_dir) not in sys.path:
    sys.path.insert(0, str(client_dir))

from src.diagnostics import DiagnosticVerdict
from src.reporters import print_console_report
from src.results import LatencySample


def run_preview() -> None:
    """Generate and display sample diagnostic console output."""
    verdict = DiagnosticVerdict(
        primary_bottleneck="NONE (OPC UA PIPELINE HEALTHY)",
        headline="Healthy Fleet",
        explanation="All endpoints nominal across 500 servers with low jitter",
        recommendation="No action required",
        metrics_summary={"delivery_p90_ms": 18.7, "client_ready_p90_ms": 21.7},
        warnings=[],
    )

    samples: list[LatencySample] = []
    for i in range(1, 501):
        for j in range(50):
            samples.append(
                LatencySample(
                    sample_id=len(samples) + 1,
                    endpoint=f"opc.tcp://127.0.0.1:{40000 + i}",
                    delivery_time_ms=12.0 + (i % 15) * 0.5 + (j % 5) * 0.1,
                    client_ready_time_ms=15.0 + (i % 15) * 0.5 + (j % 5) * 0.1,
                    total_result_transfer_time_ms=20.0 + (i % 15) * 0.5,
                    server_processing_time_ms=2.0,
                    network_transport_time_ms=18.0,
                    clock_skew_ms=0.5,
                    timing_source="wire",
                )
            )

    timing = {"workers_reported": 20, "loop_lag_max_ms": 45.2, "loop_lag_worst_mean_ms": 6.1}
    print_console_report(samples, verdict, "Fleet-500-Benchmark", timing=timing)


if __name__ == "__main__":
    run_preview()
