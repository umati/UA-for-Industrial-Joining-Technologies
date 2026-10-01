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

from . import __version__
from .config import OpcUaPoolConfig, is_loopback_endpoint, load_config
from .diagnostics import evaluate_diagnostics
from .engine import FleetIntegritySummary, OpcUaClientPool
from .reporters import (
    export_csv_report,
    export_json_report,
    generate_markdown_report,
    print_console_report,
    write_junit_xml,
)
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Filter verbose asyncua library logs unless verbose is requested
    if not args.verbose:
        logging.getLogger("asyncua").setLevel(logging.CRITICAL)

    # 1. Load base configuration
    if args.config:
        cfg = load_config(args.config)
    else:
        cfg = OpcUaPoolConfig()

    # 2. Apply CLI overrides
    if args.endpoints:
        cfg.endpoints = [ep.strip() for ep in args.endpoints.split(",") if ep.strip()]
    elif not args.config:
        env_fleet = os.environ.get("OPCUA_FLEET_ENDPOINTS")
        env_single = os.environ.get("OPCUA_SERVER_URL")
        if env_fleet:
            cfg.endpoints = [ep.strip() for ep in env_fleet.split(",") if ep.strip()]
        elif env_single:
            cfg.endpoints = [env_single.strip()]
    if args.duration is not None:
        cfg.duration_seconds = args.duration
    if args.samples is not None:
        cfg.target_sample_count = args.samples
    if args.burst is not None:
        cfg.burst_trigger_count = args.burst
    if args.mode:
        cfg.mode = args.mode
    if args.require_full_coverage:
        cfg.require_full_coverage = True
    if args.allow_partial_coverage:
        cfg.require_full_coverage = False
    if args.require_full_coverage and args.allow_partial_coverage:
        parser.error("--require-full-coverage and --allow-partial-coverage are mutually exclusive")
    if args.fail_p90 is not None:
        cfg.fail_p90_ms = args.fail_p90
    if args.fail_p90_client_ready is not None:
        cfg.fail_p90_client_ready_ms = args.fail_p90_client_ready
    if args.workers is not None:
        cfg.max_worker_processes = args.workers
    elif cfg.max_worker_processes is None:
        env_workers = os.environ.get("OPCUA_WORKERS")
        if env_workers:
            try:
                cfg.max_worker_processes = int(env_workers)
            except ValueError:
                pass
    if args.burst_delay is not None:
        cfg.burst_delay_seconds = args.burst_delay
    elif os.environ.get("OPCUA_BURST_DELAY"):
        try:
            cfg.burst_delay_seconds = float(os.environ["OPCUA_BURST_DELAY"])
        except ValueError:
            pass
    if args.skip_clock_skew:
        cfg.skip_clock_skew = True
    if args.clock_tolerance_ms is not None:
        cfg.clock_tolerance_ms = args.clock_tolerance_ms
    if args.settle_timeout is not None:
        cfg.settle_timeout_seconds = args.settle_timeout

    if not cfg.endpoints:
        cfg.endpoints = ["opc.tcp://localhost:40451"]

    # Re-validate after overrides; report invalid values as usage errors (exit 2), not tracebacks.
    try:
        cfg.validate()
    except ValueError as exc:
        parser.error(str(exc))
    if cfg.require_full_coverage is None:
        cfg.require_full_coverage = len(cfg.endpoints) > 1

    logger.info(f"Loaded config: '{cfg.name}' targeting {len(cfg.endpoints)} endpoints")

    # 3. Instantiate and run OpcUaClientPool
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
        # pool.stop drains in-flight batches and returns all collected samples
        shutdown_samples = pool.stop()
        if isinstance(shutdown_samples, list) and len(shutdown_samples) >= len(samples):
            samples = shutdown_samples

    # 4. Measure real runtime telemetry
    real_thread_count = threading.active_count()
    real_process_count = pool._num_workers_started

    coverage_valid, coverage_msg = pool.verify_coverage(
        samples,
        target_sample_count=cfg.target_sample_count,
        target_samples_per_endpoint=args.samples_per_endpoint,
        allow_partial_samples=bool(args.allow_partial_samples),
    )
    logger.info(coverage_msg)

    # 5. Run heuristic attribution diagnostics on VALID results only; invalid results carry no timing proof.
    valid = [s for s in samples if s.integrity_status == INTEGRITY_VALID]

    def _metric(name: str) -> list[float]:
        return [v for s in valid if (v := getattr(s, name)) is not None]

    timing_fn = getattr(pool, "timing_summary", None)
    timing_summary = timing_fn() if callable(timing_fn) else {}
    if not isinstance(timing_summary, dict):
        timing_summary = {}

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

    # 6. Output reporting
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

    if args.junit:
        write_junit_xml(
            output_path=args.junit,
            samples=samples,
            verdict=verdict,
            pool_name=cfg.name,
            failed_threshold_msg=fail_msg,
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
            },
        )
        logger.info(f"Wrote JSON metrics to {args.json}")

    if args.csv:
        export_csv_report(args.csv, samples)
        logger.info(f"Wrote detailed metrics CSV to {args.csv}")

    if fail_msg or not coverage_valid or not samples:
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
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
