"""
OPC UA IJT Performance Client package.
Multi-controller, high-scale performance benchmarking and latency diagnostics.
"""

from .attribution import DiagnosticVerdict, evaluate_diagnostics
from .config import OpcUaPoolConfig, load_config
from .opcua_client_pool import OpcUaClientPool
from .reporters import (
    export_json_report,
    generate_markdown_report,
    print_console_report,
    write_junit_xml,
)
from .result_transfer_latency import LatencySample, calibrate_clock_skew, compute_statistics

__all__ = [
    "OpcUaClientPool",
    "OpcUaPoolConfig",
    "load_config",
    "LatencySample",
    "compute_statistics",
    "calibrate_clock_skew",
    "evaluate_diagnostics",
    "DiagnosticVerdict",
    "print_console_report",
    "generate_markdown_report",
    "write_junit_xml",
    "export_json_report",
]
