"""OPC UA root-cause latency bottleneck diagnostics."""

from .attribution import DiagnosticVerdict, evaluate_diagnostics

__all__ = [
    "DiagnosticVerdict",
    "evaluate_diagnostics",
]
