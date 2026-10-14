"""
Configuration and YAML Manifest Loader for IJT Performance Client.
Supports explicit endpoint lists, port ranges, and strict configuration validation.
"""

from __future__ import annotations

import ipaddress
import math
import re
from dataclasses import dataclass, field
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

VALID_MODES = {"passive", "active_burst", "both"}
VALID_LIFECYCLES = {"external", "auto_simulator", "production"}
VALID_ROLES = {"colocated", "serve-fleet", "client-only"}
VALID_CLAIM_INTENDED = {"auto", "capacity", "split_path"}

ALLOWED_TOP_KEYS_V1 = {"schema_version", "name", "description", "fleet", "execution", "engine", "thresholds", "meta"}
ALLOWED_TOP_KEYS_V2 = ALLOWED_TOP_KEYS_V1 | {"role", "claim", "inventory", "gates", "report"}
ALLOWED_TOP_KEYS = ALLOWED_TOP_KEYS_V2  # reject unknown; schema_version gates which extras are meaningful

ALLOWED_FLEET_KEYS = {"lifecycle", "endpoints", "url_template", "port_range"}
ALLOWED_EXECUTION_KEYS = {
    "mode",
    "duration_seconds",
    "target_sample_count",
    "burst_trigger_count",
    "burst_delay_seconds",
    "require_full_coverage",
    "skip_clock_skew",
}
ALLOWED_ENGINE_KEYS = {
    "max_worker_processes",
    "connect_concurrency",
    "sub_period_ms",
    "skip_clock_skew",
    "burst_delay_seconds",
    "clock_tolerance_ms",
    "settle_timeout_seconds",
}
ALLOWED_THRESHOLDS_KEYS = {"warn_p90_ms", "fail_p90_ms", "fail_p90_client_ready_ms"}
ALLOWED_META_KEYS = {"name", "description", "lifecycle"}
ALLOWED_CLAIM_KEYS = {"intended"}
ALLOWED_INVENTORY_KEYS = {
    "write_file",
    "path",
    "http",
    "http_host",
    "http_port",
    "http_token",
    "source",
    "ttl_seconds",
}
ALLOWED_GATES_KEYS = {
    "min_coverage",
    "max_disconnects",
    "fail_on_delivery_p90_ms",
    "fail_on_client_ready_p90_ms",
}
ALLOWED_REPORT_KEYS = {"host_fingerprint", "include_network", "redact"}

ENDPOINT_RE = re.compile(r"^opc\.tcp://(?P<host>[a-zA-Z0-9_\-\.]+):(?P<port>[0-9]{1,5})(?P<path>/.*)?$")


def is_loopback_endpoint(url: str) -> bool:
    """True when the endpoint is on this machine (localhost, 127.0.0.0/8 or ::1)."""
    host = (urlparse(url).hostname or "").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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
    burst_delay_seconds: float = 1.0
    max_worker_processes: int | None = None
    connect_concurrency: int = 20
    sub_period_ms: int = 100
    warn_p90_ms: float = 100.0
    fail_p90_ms: float | None = None  # SLA on P90 delivery time (result bytes on the client)
    fail_p90_client_ready_ms: float | None = None  # SLA on P90 client-ready time (result decoded)
    require_full_coverage: bool | None = None  # None defaults to strict coverage for fleets
    skip_clock_skew: bool = False  # If True, bypasses Cristian's RTT clock skew probes (e.g. on localhost)
    clock_tolerance_ms: float = 1000.0  # Clock-health warning tolerance (plus RTT/2); never fails the gate
    settle_timeout_seconds: float = 5.0  # Max wait after the last trigger round for results to arrive
    # --- schema v2 / modular plan fields (defaults preserve colocated Profile A) ---
    schema_version: int = 1
    role: str = "colocated"  # colocated | serve-fleet | client-only
    claim_intended: str = "auto"  # auto | capacity | split_path
    # v1 default False preserves legacy side-effect-free runs; v2 profiles set write_file: true
    inventory_write_file: bool = False
    inventory_path: str = "test-results/fleet-inventory.json"
    inventory_http: bool = False
    inventory_http_host: str = "127.0.0.1"
    inventory_http_port: int = 8765
    inventory_http_token: str | None = None
    inventory_source: str | None = None  # file path or URL for client-only
    inventory_ttl_seconds: int = 3600
    report_host_fingerprint: bool = True
    report_include_network: bool = False
    report_redact: bool = True
    min_coverage: float | None = None
    max_disconnects: int | None = None
    # Fields explicitly set by the loaded YAML (for accurate effective-config provenance)
    explicit_profile_fields: frozenset[str] = field(default_factory=frozenset, repr=False, compare=False)

    def validate(self) -> None:
        """Strict validation of all configuration parameters before execution."""
        if not self.name or not self.name.strip():
            raise ValueError("Configuration 'name' cannot be empty.")

        if self.lifecycle not in VALID_LIFECYCLES:
            raise ValueError(f"Invalid lifecycle '{self.lifecycle}'. Must be one of: {sorted(VALID_LIFECYCLES)}")

        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid execution mode '{self.mode}'. Must be one of: {sorted(VALID_MODES)}")

        if not math.isfinite(self.duration_seconds) or self.duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be a finite positive number, got {self.duration_seconds}")

        if self.target_sample_count is not None and self.target_sample_count <= 0:
            raise ValueError(f"target_sample_count must be positive or None, got {self.target_sample_count}")

        if self.burst_trigger_count < 0:
            raise ValueError(f"burst_trigger_count cannot be negative, got {self.burst_trigger_count}")

        if not math.isfinite(self.burst_delay_seconds) or self.burst_delay_seconds < 0:
            raise ValueError(
                f"burst_delay_seconds must be a finite non-negative number, got {self.burst_delay_seconds}"
            )

        if not math.isfinite(self.clock_tolerance_ms) or self.clock_tolerance_ms < 0:
            raise ValueError(f"clock_tolerance_ms must be a finite non-negative number, got {self.clock_tolerance_ms}")

        if not math.isfinite(self.settle_timeout_seconds) or self.settle_timeout_seconds < 0:
            raise ValueError(
                f"settle_timeout_seconds must be a finite non-negative number, got {self.settle_timeout_seconds}"
            )

        if self.max_worker_processes is not None and (self.max_worker_processes < 1 or self.max_worker_processes > 32):
            raise ValueError(
                f"max_worker_processes must be positive and between 1 and 32, got {self.max_worker_processes}"
            )

        if self.connect_concurrency <= 0:
            raise ValueError(f"connect_concurrency must be positive, got {self.connect_concurrency}")

        if self.sub_period_ms <= 0:
            raise ValueError(f"sub_period_ms must be positive, got {self.sub_period_ms}")

        if not math.isfinite(self.warn_p90_ms) or self.warn_p90_ms <= 0:
            raise ValueError(f"warn_p90_ms must be a finite positive number, got {self.warn_p90_ms}")

        for key in ("fail_p90_ms", "fail_p90_client_ready_ms"):
            value = getattr(self, key)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{key} must be a finite positive number, got {value}")

        # Validate endpoints
        if self.schema_version not in (1, 2):
            raise ValueError(
                f"Unsupported schema_version {self.schema_version}. Supported: 1 (legacy), 2 (modular roles/claims)."
            )

        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of: {sorted(VALID_ROLES)}")

        if self.claim_intended not in VALID_CLAIM_INTENDED:
            raise ValueError(
                f"Invalid claim.intended '{self.claim_intended}'. Must be one of: {sorted(VALID_CLAIM_INTENDED)}"
            )

        if self.role == "client-only" and not self.endpoints and not self.inventory_source:
            raise ValueError("role=client-only requires inventory.source or endpoints")

        if self.role != "client-only" and not self.endpoints:
            raise ValueError("No endpoints configured. At least one endpoint is required.")

        if self.inventory_ttl_seconds <= 0:
            raise ValueError(f"inventory.ttl_seconds must be positive, got {self.inventory_ttl_seconds}")

        if self.min_coverage is not None and (
            not math.isfinite(self.min_coverage) or not 0.0 <= self.min_coverage <= 1.0
        ):
            raise ValueError(f"min_coverage must be in [0, 1], got {self.min_coverage}")

        if self.max_disconnects is not None and self.max_disconnects < 0:
            raise ValueError(f"max_disconnects cannot be negative, got {self.max_disconnects}")

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


_ROOT_PROFILES_DIR = Path(__file__).resolve().parents[1] / "profiles"
_PKG_PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

_PACKAGED_PROFILE_BASELINES = frozenset(
    {"work_pc_colocated.yaml", "serve_fleet.yaml", "client_only.yaml", "single_server.yaml", "multi_server_fleet.yaml"}
)


def verify_packaged_profiles(required: frozenset[str] | None = None) -> list[str]:
    """Return basenames missing from src/profiles (wheel package data)."""
    need = required or _PACKAGED_PROFILE_BASELINES
    missing: list[str] = []
    for name in sorted(need):
        if not (_PKG_PROFILES_DIR / name).is_file():
            missing.append(name)
    return missing


def load_config(file_path: str | Path) -> OpcUaPoolConfig:
    """Load and strictly validate a YAML performance configuration profile.

    Supports:
    1. Direct file path on disk (relative or absolute)
    2. Bare filename or relative name inside root profiles/ directory (e.g. 'multi_server_fleet.yaml')
    3. Package-bundled profiles when installed via wheel/pip
    """
    path = Path(file_path)
    source: Path | Traversable

    # 1. Direct path check
    if path.is_file():
        source = path
    # 2. Check root profiles/ directory (direct or by filename)
    elif (_ROOT_PROFILES_DIR / path).is_file():
        source = _ROOT_PROFILES_DIR / path
    elif (_ROOT_PROFILES_DIR / path.name).is_file():
        source = _ROOT_PROFILES_DIR / path.name
    elif (_PKG_PROFILES_DIR / path).is_file():
        source = _PKG_PROFILES_DIR / path
    elif (_PKG_PROFILES_DIR / path.name).is_file():
        source = _PKG_PROFILES_DIR / path.name
    else:
        # 3. Check installed package resources
        bundled = None
        for pkg in ("profiles", "ijt_performance_client.profiles", "ijt_performance_client"):
            try:
                candidate = files(pkg).joinpath(path.name)
                if candidate.is_file():
                    bundled = candidate
                    break
                candidate = files(pkg).joinpath(str(file_path).replace("\\", "/"))
                if candidate.is_file():
                    bundled = candidate
                    break
            except Exception:
                continue

        if bundled is None or not bundled.is_file():
            raise FileNotFoundError(
                f"Configuration profile not found: '{file_path}'. "
                f"Checked disk, '{_ROOT_PROFILES_DIR}', and packaged resources."
            )
        source = bundled

    with source.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Configuration file must contain a YAML mapping, got {type(data).__name__}")

    raw_schema = data.get("schema_version", 1)
    try:
        schema_version = int(raw_schema)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"schema_version must be an integer, got {raw_schema!r}") from exc
    if schema_version not in (1, 2):
        raise ValueError(f"Unsupported schema_version {schema_version}. This client supports 1 and 2 only.")

    allowed_top = ALLOWED_TOP_KEYS_V1 if schema_version == 1 else ALLOWED_TOP_KEYS_V2
    # v1 profiles must not contain v2-only sections
    for key in data:
        if key not in allowed_top:
            if schema_version == 1 and key in ALLOWED_TOP_KEYS_V2 - ALLOWED_TOP_KEYS_V1:
                raise ValueError(f"Key '{key}' requires schema_version: 2 (profile declares schema_version: 1).")
            raise ValueError(f"Unknown configuration key: '{key}'. Allowed: {sorted(allowed_top)}")

    config = OpcUaPoolConfig()
    explicit: set[str] = set()
    config.schema_version = schema_version
    if "schema_version" in data:
        explicit.add("schema_version")

    def _set(name: str, value: Any) -> None:
        setattr(config, name, value)
        explicit.add(name)

    # Meta section (optional alias for name/description/lifecycle)
    if "meta" in data:
        meta_sec = data["meta"]
        if isinstance(meta_sec, dict):
            _validate_section_keys(meta_sec, ALLOWED_META_KEYS, "meta")
            if "name" in meta_sec:
                _set("name", meta_sec["name"])
            if "description" in meta_sec:
                _set("description", meta_sec["description"])
            if "lifecycle" in meta_sec:
                _set("lifecycle", meta_sec["lifecycle"])

    if "name" in data:
        _set("name", data["name"])
    if "description" in data:
        _set("description", data["description"])

    # Fleet section
    if "fleet" in data:
        fleet_sec = data["fleet"]
        if isinstance(fleet_sec, dict):
            _validate_section_keys(fleet_sec, ALLOWED_FLEET_KEYS, "fleet")
            if "lifecycle" in fleet_sec:
                _set("lifecycle", fleet_sec["lifecycle"])

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

            if endpoints or "endpoints" in fleet_sec or (url_template and port_range):
                _set("endpoints", endpoints)

    # Execution section
    if "execution" in data:
        exec_sec = data["execution"]
        if isinstance(exec_sec, dict):
            _validate_section_keys(exec_sec, ALLOWED_EXECUTION_KEYS, "execution")
            if "mode" in exec_sec:
                _set("mode", exec_sec["mode"])
            if "duration_seconds" in exec_sec:
                _set("duration_seconds", float(exec_sec["duration_seconds"]))
            if "target_sample_count" in exec_sec:
                _set("target_sample_count", int(exec_sec["target_sample_count"]))
            if "burst_trigger_count" in exec_sec:
                _set("burst_trigger_count", int(exec_sec["burst_trigger_count"]))
            if "burst_delay_seconds" in exec_sec:
                _set("burst_delay_seconds", float(exec_sec["burst_delay_seconds"]))
            if "require_full_coverage" in exec_sec:
                _set("require_full_coverage", bool(exec_sec["require_full_coverage"]))
            if "skip_clock_skew" in exec_sec:
                _set("skip_clock_skew", bool(exec_sec["skip_clock_skew"]))

    # Engine section
    if "engine" in data:
        eng_sec = data["engine"]
        if isinstance(eng_sec, dict):
            _validate_section_keys(eng_sec, ALLOWED_ENGINE_KEYS, "engine")
            if "max_worker_processes" in eng_sec:
                _set("max_worker_processes", int(eng_sec["max_worker_processes"]))
            if "burst_delay_seconds" in eng_sec:
                _set("burst_delay_seconds", float(eng_sec["burst_delay_seconds"]))
            if "connect_concurrency" in eng_sec:
                _set("connect_concurrency", int(eng_sec["connect_concurrency"]))
            if "sub_period_ms" in eng_sec:
                _set("sub_period_ms", int(eng_sec["sub_period_ms"]))
            if "skip_clock_skew" in eng_sec:
                _set("skip_clock_skew", bool(eng_sec["skip_clock_skew"]))
            if "clock_tolerance_ms" in eng_sec:
                _set("clock_tolerance_ms", float(eng_sec["clock_tolerance_ms"]))
            if "settle_timeout_seconds" in eng_sec:
                _set("settle_timeout_seconds", float(eng_sec["settle_timeout_seconds"]))

    # Thresholds section
    if "thresholds" in data:
        thresh_sec = data["thresholds"]
        if isinstance(thresh_sec, dict):
            _validate_section_keys(thresh_sec, ALLOWED_THRESHOLDS_KEYS, "thresholds")
            if "warn_p90_ms" in thresh_sec:
                _set("warn_p90_ms", float(thresh_sec["warn_p90_ms"]))
            if "fail_p90_ms" in thresh_sec:
                _set("fail_p90_ms", float(thresh_sec["fail_p90_ms"]))
            if "fail_p90_client_ready_ms" in thresh_sec:
                _set("fail_p90_client_ready_ms", float(thresh_sec["fail_p90_client_ready_ms"]))

    # --- schema v2 sections ---
    if schema_version >= 2:
        if "role" in data:
            _set("role", str(data["role"]).strip())
        if "claim" in data and isinstance(data["claim"], dict):
            _validate_section_keys(data["claim"], ALLOWED_CLAIM_KEYS, "claim")
            if "intended" in data["claim"]:
                _set("claim_intended", str(data["claim"]["intended"]).strip().lower())
        if "inventory" in data and isinstance(data["inventory"], dict):
            inv = data["inventory"]
            _validate_section_keys(inv, ALLOWED_INVENTORY_KEYS, "inventory")
            if "write_file" in inv:
                _set("inventory_write_file", bool(inv["write_file"]))
            if "path" in inv:
                _set("inventory_path", str(inv["path"]))
            if "http" in inv:
                _set("inventory_http", bool(inv["http"]))
            if "http_host" in inv:
                _set("inventory_http_host", str(inv["http_host"]))
            if "http_port" in inv:
                _set("inventory_http_port", int(inv["http_port"]))
            if "http_token" in inv and inv["http_token"] is not None:
                _set("inventory_http_token", str(inv["http_token"]))
            if "source" in inv and inv["source"] is not None:
                _set("inventory_source", str(inv["source"]))
            if "ttl_seconds" in inv:
                _set("inventory_ttl_seconds", int(inv["ttl_seconds"]))
        if "gates" in data and isinstance(data["gates"], dict):
            gates = data["gates"]
            _validate_section_keys(gates, ALLOWED_GATES_KEYS, "gates")
            if "min_coverage" in gates and gates["min_coverage"] is not None:
                _set("min_coverage", float(gates["min_coverage"]))
            if "max_disconnects" in gates and gates["max_disconnects"] is not None:
                _set("max_disconnects", int(gates["max_disconnects"]))
            if "fail_on_delivery_p90_ms" in gates and gates["fail_on_delivery_p90_ms"] is not None:
                _set("fail_p90_ms", float(gates["fail_on_delivery_p90_ms"]))
            if "fail_on_client_ready_p90_ms" in gates and gates["fail_on_client_ready_p90_ms"] is not None:
                _set("fail_p90_client_ready_ms", float(gates["fail_on_client_ready_p90_ms"]))
        if "report" in data and isinstance(data["report"], dict):
            rep = data["report"]
            _validate_section_keys(rep, ALLOWED_REPORT_KEYS, "report")
            if "host_fingerprint" in rep:
                _set("report_host_fingerprint", bool(rep["host_fingerprint"]))
            if "include_network" in rep:
                _set("report_include_network", bool(rep["include_network"]))
            if "redact" in rep:
                _set("report_redact", bool(rep["redact"]))

    config.explicit_profile_fields = frozenset(explicit)
    # Perform strict validation
    config.validate()
    return config
