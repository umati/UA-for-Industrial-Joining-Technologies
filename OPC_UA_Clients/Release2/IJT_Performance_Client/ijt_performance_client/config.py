"""
Configuration and YAML Manifest Loader for IJT Performance Client.
Supports explicit endpoint lists, port ranges, and strict configuration validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

VALID_MODES = {"passive", "active_burst", "both"}
VALID_LIFECYCLES = {"external", "auto_simulator", "production"}

ALLOWED_TOP_KEYS = {"schema_version", "name", "description", "fleet", "execution", "engine", "thresholds", "meta"}
ALLOWED_FLEET_KEYS = {"lifecycle", "endpoints", "url_template", "port_range"}
ALLOWED_EXECUTION_KEYS = {
    "mode",
    "duration_seconds",
    "target_sample_count",
    "burst_trigger_count",
    "require_full_coverage",
    "skip_clock_skew",
}
ALLOWED_ENGINE_KEYS = {"max_worker_processes", "connect_concurrency", "sub_period_ms", "skip_clock_skew"}
ALLOWED_THRESHOLDS_KEYS = {"warn_p90_ms", "fail_p90_ms"}
ALLOWED_META_KEYS = {"name", "description", "lifecycle"}

ENDPOINT_RE = re.compile(r"^opc\.tcp://(?P<host>[a-zA-Z0-9_\-\.]+):(?P<port>[0-9]{1,5})(?P<path>/.*)?$")


@dataclass
class OpcUaPoolConfig:
    """Validated configuration for an OPC UA multi-endpoint benchmark run."""

    name: str = "IJT Performance Fleet Test"
    description: str = ""
    lifecycle: str = "external"  # 'external', 'auto_simulator', or 'production'
    endpoints: list[str] = field(default_factory=list)
    mode: str = "passive"  # 'passive', 'active_burst', or 'both'
    duration_seconds: float = 15.0
    target_sample_count: int | None = 20
    burst_trigger_count: int = 5
    max_worker_processes: int | None = None
    connect_concurrency: int = 20
    sub_period_ms: int = 100
    warn_p90_ms: float = 100.0
    fail_p90_ms: float | None = None
    require_full_coverage: bool | None = None  # None defaults to strict coverage for fleets
    skip_clock_skew: bool = False  # If True, bypasses Cristian's RTT clock skew probes (e.g. on localhost)

    def validate(self) -> None:
        """Strict validation of all configuration parameters before execution."""
        if not self.name or not self.name.strip():
            raise ValueError("Configuration 'name' cannot be empty.")

        if self.lifecycle not in VALID_LIFECYCLES:
            raise ValueError(f"Invalid lifecycle '{self.lifecycle}'. Must be one of: {sorted(VALID_LIFECYCLES)}")

        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid execution mode '{self.mode}'. Must be one of: {sorted(VALID_MODES)}")

        if self.duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be positive, got {self.duration_seconds}")

        if self.target_sample_count is not None and self.target_sample_count <= 0:
            raise ValueError(f"target_sample_count must be positive or None, got {self.target_sample_count}")

        if self.burst_trigger_count < 0:
            raise ValueError(f"burst_trigger_count cannot be negative, got {self.burst_trigger_count}")

        if self.max_worker_processes is not None and (self.max_worker_processes < 1 or self.max_worker_processes > 32):
            raise ValueError(
                f"max_worker_processes must be positive and between 1 and 32, got {self.max_worker_processes}"
            )

        if self.connect_concurrency <= 0:
            raise ValueError(f"connect_concurrency must be positive, got {self.connect_concurrency}")

        if self.sub_period_ms <= 0:
            raise ValueError(f"sub_period_ms must be positive, got {self.sub_period_ms}")

        if self.warn_p90_ms <= 0:
            raise ValueError(f"warn_p90_ms must be positive, got {self.warn_p90_ms}")

        if self.fail_p90_ms is not None and self.fail_p90_ms <= 0:
            raise ValueError(f"fail_p90_ms must be positive, got {self.fail_p90_ms}")

        # Validate endpoints
        if not self.endpoints:
            raise ValueError("No endpoints configured. At least one endpoint is required.")

        seen_endpoints = set()
        for idx, ep in enumerate(self.endpoints):
            if not isinstance(ep, str) or not ep.strip():
                raise ValueError(f"Endpoint #{idx + 1} is empty or not a string.")
            ep_clean = ep.strip()
            match = ENDPOINT_RE.match(ep_clean)
            if not match:
                raise ValueError(
                    f"Malformed endpoint '{ep_clean}'. All endpoints must start with 'opc.tcp://' "
                    f"and have valid host:port syntax."
                )
            port_num = int(match.group("port"))
            if port_num < 1 or port_num > 65535:
                raise ValueError(f"Endpoint '{ep_clean}' has invalid port {port_num}. Must be in range 1-65535.")

            if ep_clean in seen_endpoints:
                raise ValueError(
                    f"Duplicate endpoint detected: '{ep_clean}'. Each endpoint in the fleet must be unique."
                )
            seen_endpoints.add(ep_clean)


def _validate_section_keys(section_dict: dict[str, Any], allowed_keys: set[str], section_name: str) -> None:
    """Helper to reject unknown keys in a configuration section."""
    for key in section_dict:
        if key not in allowed_keys:
            raise ValueError(f"Unknown key in '{section_name}' section: '{key}'. Allowed: {sorted(allowed_keys)}")


def load_config(file_path: str | Path) -> OpcUaPoolConfig:
    """Load and strictly validate a YAML performance configuration profile."""
    path = Path(file_path)
    if not path.is_file():
        # Installed wheels can provide bundled profiles without a source checkout.
        bundled = files("ijt_performance_client").joinpath(str(file_path).replace("\\", "/"))
        if path.is_absolute() or not bundled.is_file():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        source = bundled
    else:
        source = path

    with source.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Configuration file must contain a YAML mapping, got {type(data).__name__}")

    # Top-level key validation
    for key in data:
        if key not in ALLOWED_TOP_KEYS:
            raise ValueError(f"Unknown configuration key: '{key}'. Allowed: {sorted(ALLOWED_TOP_KEYS)}")

    config = OpcUaPoolConfig()

    # Meta section (optional alias for name/description/lifecycle)
    if "meta" in data:
        meta_sec = data["meta"]
        if isinstance(meta_sec, dict):
            _validate_section_keys(meta_sec, ALLOWED_META_KEYS, "meta")
            config.name = meta_sec.get("name", config.name)
            config.description = meta_sec.get("description", config.description)
            config.lifecycle = meta_sec.get("lifecycle", config.lifecycle)

    config.name = data.get("name", config.name)
    config.description = data.get("description", config.description)

    # Fleet section
    if "fleet" in data:
        fleet_sec = data["fleet"]
        if isinstance(fleet_sec, dict):
            _validate_section_keys(fleet_sec, ALLOWED_FLEET_KEYS, "fleet")
            config.lifecycle = fleet_sec.get("lifecycle", config.lifecycle)

            endpoints = list(fleet_sec.get("endpoints", []))
            url_template = fleet_sec.get("url_template")
            port_range = fleet_sec.get("port_range")
            if url_template and port_range:
                if not isinstance(port_range, list) or len(port_range) != 2:
                    raise ValueError("port_range must be a list of two integers [start_port, end_port].")
                start_p, end_p = port_range[0], port_range[1]
                if not isinstance(start_p, int) or not isinstance(end_p, int):
                    raise ValueError("port_range boundaries must be integers.")
                if start_p > end_p:
                    raise ValueError(f"port_range start ({start_p}) cannot be greater than end ({end_p}).")
                if start_p <= 0 or end_p > 65535:
                    raise ValueError(f"port_range out of valid TCP port bounds (1-65535): {port_range}")

                for p in range(start_p, end_p + 1):
                    endpoints.append(url_template.format(port=p))

            config.endpoints = endpoints

    # Execution section
    if "execution" in data:
        exec_sec = data["execution"]
        if isinstance(exec_sec, dict):
            _validate_section_keys(exec_sec, ALLOWED_EXECUTION_KEYS, "execution")
            config.mode = exec_sec.get("mode", config.mode)
            if "duration_seconds" in exec_sec:
                config.duration_seconds = float(exec_sec["duration_seconds"])
            if "target_sample_count" in exec_sec:
                config.target_sample_count = int(exec_sec["target_sample_count"])
            if "burst_trigger_count" in exec_sec:
                config.burst_trigger_count = int(exec_sec["burst_trigger_count"])
            if "require_full_coverage" in exec_sec:
                config.require_full_coverage = bool(exec_sec["require_full_coverage"])
            if "skip_clock_skew" in exec_sec:
                config.skip_clock_skew = bool(exec_sec["skip_clock_skew"])

    # Engine section
    if "engine" in data:
        eng_sec = data["engine"]
        if isinstance(eng_sec, dict):
            _validate_section_keys(eng_sec, ALLOWED_ENGINE_KEYS, "engine")
            if "max_worker_processes" in eng_sec:
                config.max_worker_processes = int(eng_sec["max_worker_processes"])
            if "connect_concurrency" in eng_sec:
                config.connect_concurrency = int(eng_sec["connect_concurrency"])
            if "sub_period_ms" in eng_sec:
                config.sub_period_ms = int(eng_sec["sub_period_ms"])
            if "skip_clock_skew" in eng_sec:
                config.skip_clock_skew = bool(eng_sec["skip_clock_skew"])

    # Thresholds section
    if "thresholds" in data:
        thresh_sec = data["thresholds"]
        if isinstance(thresh_sec, dict):
            _validate_section_keys(thresh_sec, ALLOWED_THRESHOLDS_KEYS, "thresholds")
            if "warn_p90_ms" in thresh_sec:
                config.warn_p90_ms = float(thresh_sec["warn_p90_ms"])
            if "fail_p90_ms" in thresh_sec:
                config.fail_p90_ms = float(thresh_sec["fail_p90_ms"])

    # Perform strict validation
    config.validate()
    return config
