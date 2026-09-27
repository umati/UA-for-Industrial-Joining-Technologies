"""
OPC UA IJT Performance Client package.
Multi-server, high-scale performance benchmarking and latency diagnostics.
"""

__version__ = "1.0.0"

from .config import OpcUaPoolConfig, load_config
from .diagnostics import DiagnosticVerdict, evaluate_diagnostics
from .engine import (
    OpcUaClientPool,
    apply_session_policy,
    disconnect_client,
    load_ijt_type_definitions,
    patch_asyncua_subtype_serializer,
)
from .reporters import (
    export_json_report,
    generate_markdown_report,
    print_console_report,
    write_junit_xml,
)
from .results import LatencySample, calibrate_clock_skew, compute_statistics

__all__ = [
    "OpcUaClientPool",
    "OpcUaPoolConfig",
    "load_config",
    "LatencySample",
    "compute_statistics",
    "calibrate_clock_skew",
    "evaluate_diagnostics",
    "DiagnosticVerdict",
    "apply_session_policy",
    "disconnect_client",
    "load_ijt_type_definitions",
    "patch_asyncua_subtype_serializer",
    "print_console_report",
    "generate_markdown_report",
    "write_junit_xml",
    "export_json_report",
]
