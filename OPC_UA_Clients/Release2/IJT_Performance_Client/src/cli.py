"""
CLI Entrypoint for IJT Performance Client.
Run via: python -m ijt_performance_client --config profiles/multi_server_fleet.yaml
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from . import __version__
from .claim import resolve_claim
from .config import OpcUaPoolConfig, is_loopback_endpoint, load_config
from .diagnostics import evaluate_diagnostics
from .effective_config import EffectiveConfigTracker, parse_env_float, parse_env_int
from .engine import FleetIntegritySummary, OpcUaClientPool
from .host_fingerprint import collect_host_fingerprint
from .inventory import (
    InventoryHttpServer,
    build_inventory,
    load_inventory,
    preflight_http_port,
    remaining_ttl_seconds,
    write_inventory_atomic,
)
from .reporters import (
    export_csv_report,
    export_json_report,
    generate_markdown_report,
    print_console_report,
    write_junit_xml,
)
from .reporters._metrics import wire_timing_count
from .results import INTEGRITY_VALID

logger = logging.getLogger("ijt_performance_client")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OPC UA IJT High-Scale Performance & Latency Benchmark Client")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to YAML configuration profile (e.g. profiles/single_server.yaml)",
    )
    parser.add_argument(
        "-e",
        "--endpoints",
        type=str,
        help="Comma-separated list of OPC UA server URLs (overrides config file)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        help="Measurement duration in seconds",
    )
    parser.add_argument(
        "-s",
        "--samples",
        type=int,
        help="Target sample count across the fleet",
    )
    parser.add_argument(
        "--samples-per-endpoint",
        type=int,
        help="Number of VALID results required from each server (per-server target)",
    )
    parser.add_argument(
        "-b",
        "--burst",
        type=int,
        help="Number of active burst stimulation rounds to trigger",
    )
    parser.add_argument(
        "--mode",
        choices=["passive", "active_burst", "both"],
        help="Execution mode",
    )
    parser.add_argument(
        "--require-full-coverage",
        action="store_true",
        help="Fail if any connected endpoint produces 0 samples",
    )
    parser.add_argument(
        "--allow-partial-coverage",
        action="store_true",
        help="Allow endpoints without samples and dropped samples (explicit fleet override)",
    )
    parser.add_argument(
        "--allow-partial-samples",
        action="store_true",
        help="Allow benchmark run to succeed even if collected samples are fewer than target count",
    )
    parser.add_argument(
        "--skip-clock-skew",
        action="store_true",
        help="Skip clock offset (skew) calibration (use on localhost or a PTP/NTP synchronized network)",
    )
    parser.add_argument(
        "--clock-tolerance-ms",
        type=float,
        help=(
            "Clock-health tolerance in ms (default: 1000). Events that appear older than collection start "
            "by more than this plus half the round-trip time are counted as clock warnings; warnings never fail the run"
        ),
    )
    parser.add_argument(
        "--settle-timeout",
        type=float,
        help=(
            "Seconds to wait after the last trigger round for results of successful calls to arrive "
            "before correlation (default: 5)"
        ),
    )
    parser.add_argument(
        "--junit",
        type=str,
        default="test-results/junit-perf.xml",
        help="Path to export JUnit XML report (default: test-results/junit-perf.xml)",
    )
    parser.add_argument(
        "--markdown",
        type=str,
        help="Path to export Markdown report (e.g. GITHUB_STEP_SUMMARY)",
    )
    parser.add_argument(
        "--json",
        type=str,
        help="Path to export JSON metrics report",
    )
    parser.add_argument(
        "--fail-p90",
        type=float,
        help=(
            "Fail with non-zero exit code if the 90%%-under (P90) delivery time (operation end to result bytes on the client) "
            "of VALID results exceeds this SLA (ms)"
        ),
    )
    parser.add_argument(
        "--fail-p90-client-ready",
        type=float,
        help=(
            "Fail with non-zero exit code if the 90%%-under (P90) client-ready time (operation end to result decoded) "
            "of VALID results exceeds this SLA (ms)"
        ),
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        help="Number of background worker processes for the client pool",
    )
    parser.add_argument(
        "--burst-delay",
        type=float,
        help="Delay in seconds between burst stimulation rounds (default: 1.0)",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to export detailed sample-by-sample metrics CSV (without heavy trace curves)",
    )
    parser.add_argument(
        "--role",
        choices=["colocated", "serve-fleet", "client-only"],
        help="Deployment role (colocated | serve-fleet | client-only)",
    )
    parser.add_argument(
        "--claim-intended",
        choices=["auto", "capacity", "split_path"],
        help="Claim profile intent: auto, capacity (Profile A), or split_path (Profile B attempt)",
    )
    parser.add_argument(
        "--inventory-source",
        type=str,
        help="Inventory file path or URL (required for client-only when endpoints are not set)",
    )
    parser.add_argument(
        "--inventory-path",
        type=str,
        help="Path to write fleet inventory JSON (colocated / serve-fleet producers)",
    )
    parser.add_argument(
        "--inventory-http",
        action="store_true",
        help="Serve inventory over loopback HTTP while the run is active",
    )
    parser.add_argument(
        "--no-inventory-http",
        action="store_true",
        help="Disable inventory HTTP even when the profile enables it",
    )
    parser.add_argument(
        "--inventory-http-port",
        type=int,
        help="TCP port for optional inventory HTTP server (default from profile or 8765)",
    )
    redact_group = parser.add_mutually_exclusive_group()
    redact_group.add_argument("--redact", action="store_true", help="Redact host fingerprint network fields (default)")
    redact_group.add_argument("--no-redact", action="store_true", help="Include raw hostname/IP in host fingerprint")
    parser.add_argument(
        "--include-network-fingerprint",
        action="store_true",
        help="Include network fields in host fingerprint (respects --redact unless --no-redact)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def _integrity_summary_json(fi: object) -> dict[str, object]:
    """Serialize the Benchmark Integrity Gate summary without optimistic defaults.

    When no summary was produced (for example the run aborted before verification),
    the gate is reported as not evaluated and not passed.
    """
    if not isinstance(fi, FleetIntegritySummary):
        return {"evaluated": False, "passed": False, "failure_reasons": ["Integrity gate was not evaluated"]}
    data = dataclasses.asdict(fi)
    data["endpoints"] = list(data["endpoints"].values())
    return {"evaluated": True, **data}


def _compute_receive_timing_coverage(valid: list[Any], timing_summary: dict[str, Any]) -> float | None:
    if not valid:
        return None
    wire_timed = timing_summary.get("wire_timed_valid")
    if wire_timed is None:
        wire_timed = wire_timing_count(valid)
    else:
        wire_timed = int(wire_timed)
    return wire_timed / len(valid)


def _resolve_configuration(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[OpcUaPoolConfig, EffectiveConfigTracker, str | None]:
    """Apply CLI > env > profile > default precedence; return cfg, tracker, producer_host_id."""
    tracker = EffectiveConfigTracker()
    producer_host_id: str | None = None

    if args.config:
        cfg = load_config(args.config)
        tracker.mark_many(sorted(cfg.explicit_profile_fields), "profile")
    else:
        cfg = OpcUaPoolConfig()

    had_profile_endpoints = bool(args.config and "endpoints" in cfg.explicit_profile_fields)
    endpoints_from_cli_or_env = False
    if args.endpoints:
        cfg.endpoints = [ep.strip() for ep in args.endpoints.split(",") if ep.strip()]
        tracker.mark("endpoints", "cli")
        endpoints_from_cli_or_env = True
    elif os.environ.get("OPCUA_FLEET_ENDPOINTS"):
        if had_profile_endpoints:
            logger.warning(
                "OPCUA_FLEET_ENDPOINTS overrides endpoints from profile %s (precedence: CLI > env > profile)",
                args.config,
            )
        cfg.endpoints = [ep.strip() for ep in os.environ["OPCUA_FLEET_ENDPOINTS"].split(",") if ep.strip()]
        tracker.mark("endpoints", "env")
        endpoints_from_cli_or_env = True
    elif os.environ.get("OPCUA_SERVER_URL"):
        if had_profile_endpoints or (args.config and len(cfg.endpoints) > 1):
            logger.warning(
                "OPCUA_SERVER_URL overrides fleet endpoints from profile %s (precedence: CLI > env > profile)",
                args.config,
            )
        cfg.endpoints = [os.environ["OPCUA_SERVER_URL"].strip()]
        tracker.mark("endpoints", "env")
        endpoints_from_cli_or_env = True

    if args.duration is not None:
        cfg.duration_seconds = args.duration
        tracker.mark("duration_seconds", "cli")
    if args.samples is not None:
        cfg.target_sample_count = args.samples
        tracker.mark("target_sample_count", "cli")
    if args.burst is not None:
        cfg.burst_trigger_count = args.burst
        tracker.mark("burst_trigger_count", "cli")
    if args.mode:
        cfg.mode = args.mode
        tracker.mark("mode", "cli")
    if args.require_full_coverage:
        cfg.require_full_coverage = True
        tracker.mark("require_full_coverage", "cli")
    if args.allow_partial_coverage:
        cfg.require_full_coverage = False
        tracker.mark("require_full_coverage", "cli")
    if args.require_full_coverage and args.allow_partial_coverage:
        parser.error("--require-full-coverage and --allow-partial-coverage are mutually exclusive")
    if args.fail_p90 is not None:
        cfg.fail_p90_ms = args.fail_p90
        tracker.mark("fail_p90_ms", "cli")
    if args.fail_p90_client_ready is not None:
        cfg.fail_p90_client_ready_ms = args.fail_p90_client_ready
        tracker.mark("fail_p90_client_ready_ms", "cli")
    if args.workers is not None:
        cfg.max_worker_processes = args.workers
        tracker.mark("max_worker_processes", "cli")
    elif os.environ.get("OPCUA_WORKERS"):
        # CLI > env > profile: env must beat profile when -w is omitted
        try:
            cfg.max_worker_processes = parse_env_int("OPCUA_WORKERS", os.environ["OPCUA_WORKERS"])
            tracker.mark("max_worker_processes", "env")
        except ValueError as exc:
            parser.error(str(exc))
    if args.burst_delay is not None:
        cfg.burst_delay_seconds = args.burst_delay
        tracker.mark("burst_delay_seconds", "cli")
    elif os.environ.get("OPCUA_BURST_DELAY"):
        try:
            cfg.burst_delay_seconds = parse_env_float("OPCUA_BURST_DELAY", os.environ["OPCUA_BURST_DELAY"])
            tracker.mark("burst_delay_seconds", "env")
        except ValueError as exc:
            parser.error(str(exc))
    if args.skip_clock_skew:
        cfg.skip_clock_skew = True
        tracker.mark("skip_clock_skew", "cli")
    if args.clock_tolerance_ms is not None:
        cfg.clock_tolerance_ms = args.clock_tolerance_ms
        tracker.mark("clock_tolerance_ms", "cli")
    if args.settle_timeout is not None:
        cfg.settle_timeout_seconds = args.settle_timeout
        tracker.mark("settle_timeout_seconds", "cli")

    if args.role:
        cfg.role = args.role
        tracker.mark("role", "cli")
    if args.claim_intended:
        cfg.claim_intended = args.claim_intended
        tracker.mark("claim_intended", "cli")
    if args.inventory_source:
        cfg.inventory_source = args.inventory_source
        tracker.mark("inventory_source", "cli")
    if args.inventory_path:
        cfg.inventory_path = args.inventory_path
        cfg.inventory_write_file = True
        tracker.mark("inventory_path", "cli")
        tracker.mark("inventory_write_file", "cli")
    if args.inventory_http:
        cfg.inventory_http = True
        cfg.inventory_write_file = True
        tracker.mark("inventory_http", "cli")
        tracker.mark("inventory_write_file", "cli")
    if args.no_inventory_http:
        cfg.inventory_http = False
        tracker.mark("inventory_http", "cli")
    if args.inventory_http_port is not None:
        cfg.inventory_http_port = args.inventory_http_port
        tracker.mark("inventory_http_port", "cli")
    if args.redact:
        cfg.report_redact = True
        tracker.mark("report_redact", "cli")
    if args.no_redact:
        cfg.report_redact = False
        tracker.mark("report_redact", "cli")
    if args.include_network_fingerprint:
        cfg.report_include_network = True
        tracker.mark("report_include_network", "cli")

    inventory_source = cfg.inventory_source
    if cfg.role == "client-only" and inventory_source:
        try:
            inv = load_inventory(inventory_source, token=cfg.inventory_http_token)
        except (OSError, ValueError, FileNotFoundError, TypeError, KeyError) as exc:
            parser.error(f"Failed to load inventory from {inventory_source}: {exc}")
        remaining = remaining_ttl_seconds(inv)
        if remaining is not None and remaining < 300:
            logger.warning(
                "Inventory TTL remaining is only %.0fs — refresh the producer inventory before a long client-only run",
                remaining,
            )
        inv_endpoints = inv.endpoint_urls()
        if not inv_endpoints:
            parser.error(f"Inventory at {inventory_source} contains no endpoints")
        if endpoints_from_cli_or_env:
            logger.warning(
                "CLI/env endpoints take precedence over inventory.source (precedence: CLI > env > inventory/profile); "
                "producer_host_id from inventory is still used for claim evidence"
            )
        else:
            cfg.endpoints = inv_endpoints
            tracker.mark("endpoints", "inventory")
        producer_host_id = inv.producer_host_id

    if not cfg.endpoints:
        if cfg.role == "client-only":
            parser.error("role=client-only requires --inventory-source or inventory.source in the profile")
        cfg.endpoints = ["opc.tcp://localhost:40451"]
        tracker.mark("endpoints", "default")

    if cfg.role == "serve-fleet" and not cfg.inventory_write_file:
        parser.error(
            "role=serve-fleet requires publishing inventory "
            "(--inventory-path / --inventory-http, or inventory.write_file in the profile)"
        )

    try:
        cfg.validate()
    except ValueError as exc:
        parser.error(str(exc))
    if cfg.require_full_coverage is None:
        cfg.require_full_coverage = len(cfg.endpoints) > 1

    return cfg, tracker, producer_host_id


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.verbose:
        logging.getLogger("asyncua").setLevel(logging.CRITICAL)

    cfg, tracker, producer_host_id = _resolve_configuration(args, parser)

    logger.info(f"Loaded config: '{cfg.name}' targeting {len(cfg.endpoints)} endpoints (role={cfg.role})")

    inventory_http: InventoryHttpServer | None = None
    written_inventory_path: Path | None = None

    if cfg.role in ("colocated", "serve-fleet") and cfg.inventory_write_file:
        if cfg.role == "serve-fleet" and cfg.inventory_ttl_seconds < 600:
            logger.warning(
                "serve-fleet inventory TTL is %ss — remote client-only runs may expire while simulators stay up; "
                "raise inventory.ttl_seconds (recommended >= 3600)",
                cfg.inventory_ttl_seconds,
            )
        inv = build_inventory(
            cfg.endpoints,
            ttl_seconds=cfg.inventory_ttl_seconds,
            role=cfg.role,
            extras={"claim_intended": cfg.claim_intended},
        )
        # Producer id for colocated is local self-assertion — do not treat as topology proof
        written_inventory_path = write_inventory_atomic(cfg.inventory_path, inv)
        if cfg.inventory_http:
            http_conflicts = preflight_http_port(cfg.inventory_http_port, cfg.inventory_http_host)
            if http_conflicts:
                for msg in http_conflicts:
                    logger.error("%s", msg)
                return 1
            try:
                inventory_http = InventoryHttpServer(
                    inv,
                    host=cfg.inventory_http_host,
                    port=cfg.inventory_http_port,
                    token=cfg.inventory_http_token,
                )
                inventory_http.start()
            except (OSError, ValueError) as exc:
                logger.error("Inventory HTTP failed to start: %s", exc)
                return 1

    if cfg.role == "serve-fleet":
        logger.info(
            "role=serve-fleet: inventory published%s; skipping benchmark client. "
            "Prefer run_fleet.py --role serve-fleet when you also need simulator lifecycle.",
            f" at {written_inventory_path}" if written_inventory_path else "",
        )
        if inventory_http is not None:
            logger.info(
                "Inventory HTTP listening on %s — press Enter to stop (or Ctrl+C).",
                inventory_http.url,
            )
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass
            inventory_http.stop()
        return 0

    pool = OpcUaClientPool(
        endpoints=cfg.endpoints,
        max_workers=cfg.max_worker_processes,
        connect_concurrency=cfg.connect_concurrency,
        sub_period_ms=cfg.sub_period_ms,
        mode=cfg.mode,
        require_full_coverage=cfg.require_full_coverage,
        skip_clock_skew=cfg.skip_clock_skew,
        burst_delay=cfg.burst_delay_seconds,
        verbose=bool(args.verbose),
        clock_tolerance_ms=cfg.clock_tolerance_ms,
        settle_timeout_s=cfg.settle_timeout_seconds,
    )

    samples = []
    try:
        pool.start(burst_trigger_count=cfg.burst_trigger_count)
        samples = pool.collect_samples(
            duration_seconds=cfg.duration_seconds,
            target_sample_count=cfg.target_sample_count,
        )
    finally:
        shutdown_samples = pool.stop()
        if isinstance(shutdown_samples, list) and len(shutdown_samples) >= len(samples):
            samples = shutdown_samples
        if inventory_http is not None:
            inventory_http.stop()

    real_thread_count = threading.active_count()
    real_process_count = pool._num_workers_started

    coverage_valid, coverage_msg = pool.verify_coverage(
        samples,
        target_sample_count=cfg.target_sample_count,
        target_samples_per_endpoint=args.samples_per_endpoint,
        allow_partial_samples=bool(args.allow_partial_samples),
    )
    logger.info(coverage_msg)

    valid = [s for s in samples if s.integrity_status == INTEGRITY_VALID]

    def _metric(name: str) -> list[float]:
        return [v for s in valid if (v := getattr(s, name)) is not None]

    timing_fn = getattr(pool, "timing_summary", None)
    timing_summary = timing_fn() if callable(timing_fn) else {}
    if not isinstance(timing_summary, dict):
        timing_summary = {}

    receive_timing_coverage = _compute_receive_timing_coverage(valid, timing_summary)
    # Successful Cristian probe stores rtt_ms; default skew 0.0 alone is not evidence
    clock_probe_ran = (
        (not cfg.skip_clock_skew) and bool(valid) and any(getattr(s, "clock_rtt_ms", None) is not None for s in valid)
    )
    clock_quality_ok = clock_probe_ran and not any(getattr(s, "clock_warning", False) for s in valid)
    # Producer host id from consumed inventory is producer-asserted (hash ≠ authenticated proof)
    topology_verified = cfg.role == "client-only" and producer_host_id is not None

    claim = resolve_claim(
        intended=cfg.claim_intended,
        endpoints=cfg.endpoints,
        producer_host_id=producer_host_id,
        topology_verified=topology_verified,
        clock_quality_ok=clock_quality_ok,
        clock_probe_ran=clock_probe_ran,
        wire_timing_coverage=receive_timing_coverage,
    )
    if claim.achieved == "UNPROVEN":
        logger.warning("CLAIM UNPROVEN: %s (intended=%s)", claim.reason, claim.intended)
    else:
        logger.info("Claim achieved: Profile %s (%s)", claim.profile_label, claim.reason)

    host_fingerprint = (
        collect_host_fingerprint(
            include_network=cfg.report_include_network,
            redact=cfg.report_redact,
        )
        if cfg.report_host_fingerprint
        else None
    )

    effective_config = tracker.snapshot(cfg)

    all_endpoints_local = bool(cfg.endpoints) and all(is_loopback_endpoint(url) for url in cfg.endpoints)
    verdict = evaluate_diagnostics(
        network_transport_latencies=_metric("network_transport_time_ms"),
        server_processing_latencies=_metric("server_processing_time_ms"),
        total_latencies=_metric("total_result_transfer_time_ms"),
        clock_skews=[s.clock_skew_ms for s in valid],
        measured_thread_count=real_thread_count,
        measured_process_count=real_process_count,
        delivery_latencies=_metric("delivery_time_ms"),
        client_ready_latencies=_metric("client_ready_time_ms"),
        client_decode_latencies=_metric("client_decode_time_ms"),
        dispatch_delays=_metric("dispatch_delay_ms"),
        loop_lag_max_ms=timing_summary.get("loop_lag_max_ms"),
        all_endpoints_local=all_endpoints_local,
    )

    print_console_report(samples, verdict, cfg.name, timing=timing_summary)

    if args.markdown:
        md_text = generate_markdown_report(samples, verdict, cfg.name, timing=timing_summary)
        Path(args.markdown).write_text(md_text, encoding="utf-8")
        logger.info(f"Wrote Markdown summary to {args.markdown}")

    sla_breaches: list[str] = []
    for label, key, limit in (
        ("90%-under delivery time (P90)", "delivery_p90_ms", cfg.fail_p90_ms),
        ("90%-under client-ready time (P90)", "client_ready_p90_ms", cfg.fail_p90_client_ready_ms),
    ):
        if limit is not None and valid and verdict.metrics_summary[key] > limit:
            sla_breaches.append(
                f"{label} ({verdict.metrics_summary[key]:.1f}ms) exceeded SLA threshold ({limit:.1f}ms)"
            )
    fail_msg = "; ".join(sla_breaches) or None

    claim_fail = cfg.claim_intended == "split_path" and claim.achieved == "UNPROVEN"

    gate_fail = False
    if cfg.min_coverage is not None and samples:
        ratio = len(valid) / max(len(samples), 1)
        if ratio < cfg.min_coverage:
            gate_fail = True
            logger.error(
                "GATE FAILURE: valid/sample coverage %.1f%% below min_coverage %.1f%%",
                ratio * 100.0,
                cfg.min_coverage * 100.0,
            )
    if cfg.max_disconnects is not None:
        disconnects = int(getattr(pool, "burst_trigger_failures", 0) or 0)
        failed_eps = pool.failed_endpoints if isinstance(pool.failed_endpoints, dict) else {}
        disconnects += len(failed_eps)
        if disconnects > cfg.max_disconnects:
            gate_fail = True
            logger.error(
                "GATE FAILURE: disconnect/failure count %s exceeds max_disconnects %s",
                disconnects,
                cfg.max_disconnects,
            )

    junit_fail_parts = [
        p
        for p in (
            fail_msg,
            "CLAIM FAILURE: split_path intended but UNPROVEN" if claim_fail else None,
            "GATE FAILURE: min_coverage or max_disconnects" if gate_fail else None,
        )
        if p
    ]
    junit_fail_msg = "; ".join(junit_fail_parts) or None

    if args.junit:
        write_junit_xml(
            output_path=args.junit,
            samples=samples,
            verdict=verdict,
            pool_name=cfg.name,
            failed_threshold_msg=junit_fail_msg,
            coverage_valid=coverage_valid,
            coverage_msg=coverage_msg,
            worker_errors=pool.worker_errors,
            total_endpoints=len(cfg.endpoints),
            connected_count=len(pool.connected_endpoints),
        )
        logger.info(f"Wrote JUnit XML to {args.junit}")

    if args.json:
        total_dropped = getattr(pool, "total_dropped_samples", 0)
        burst_fails = getattr(pool, "burst_trigger_failures", 0)
        teardown_errs = getattr(pool, "teardown_errors", [])
        integrity_summary = _integrity_summary_json(getattr(pool, "fleet_integrity", None))

        export_json_report(
            args.json,
            samples,
            verdict,
            pool_name=cfg.name,
            extra_metadata={
                "coverage_valid": coverage_valid,
                "coverage_message": coverage_msg,
                "connected_endpoints": list(pool.connected_endpoints),
                "failed_endpoints": pool.failed_endpoints if isinstance(pool.failed_endpoints, dict) else {},
                "worker_errors": list(pool.worker_errors) if isinstance(pool.worker_errors, (list, tuple, set)) else [],
                "total_dropped_samples": total_dropped if isinstance(total_dropped, int) else 0,
                "burst_trigger_failures": burst_fails if isinstance(burst_fails, int) else 0,
                "burst_trigger_errors": list(pool.burst_trigger_errors),
                "teardown_errors": list(teardown_errs) if isinstance(teardown_errs, (list, tuple, set)) else [],
                "integrity_summary": integrity_summary,
                "timing": timing_summary,
                "effective_config": effective_config,
                "claim": claim.to_dict(),
                "host_fingerprint": host_fingerprint,
                "timing_honesty": verdict.timing_honesty_note,
                "receive_timing_coverage": receive_timing_coverage,
                "role": cfg.role,
                "schema_version": cfg.schema_version,
                "inventory_path": str(written_inventory_path) if written_inventory_path else None,
            },
        )
        logger.info(f"Wrote JSON metrics to {args.json}")

    if args.csv:
        export_csv_report(args.csv, samples)
        logger.info(f"Wrote detailed metrics CSV to {args.csv}")

    if fail_msg or not coverage_valid or not samples or claim_fail or gate_fail:
        if fail_msg:
            logger.error(f"SLA BREACH: {fail_msg}")
            if all_endpoints_local:
                logger.warning(
                    "SLA HINT: every server runs on this machine, so these times include CPU sharing between "
                    "the servers and the client. Use a single-machine limit (see 'Choosing a time limit' in "
                    "docs/PERFORMANCE_GUIDE.md) or move the servers to another host."
                )
        if not coverage_valid:
            logger.error(f"COVERAGE FAILURE: {coverage_msg}")
        if claim_fail:
            logger.error("CLAIM FAILURE: split_path intended but achieved UNPROVEN — fail-closed exit")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
