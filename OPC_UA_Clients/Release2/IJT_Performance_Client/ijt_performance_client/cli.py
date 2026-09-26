"""
CLI Entrypoint for IJT Performance Client.
Run via: python -m ijt_performance_client --config profiles/ci_multi_server.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

from .attribution import evaluate_diagnostics
from .config import OpcUaPoolConfig, load_config
from .opcua_client_pool import OpcUaClientPool
from .reporters import (
    export_json_report,
    generate_markdown_report,
    print_console_report,
    write_junit_xml,
)

logger = logging.getLogger("ijt_performance_client")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OPC UA IJT High-Scale Performance & Latency Benchmark Client")
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
        "--skip-clock-skew",
        action="store_true",
        help="Skip clock skew calibration (use when on localhost or PTP/NTP synchronized network)",
    )
    parser.add_argument(
        "--junit",
        type=str,
        default="junit-perf.xml",
        help="Path to export JUnit XML report (default: junit-perf.xml)",
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
        help="Fail with non-zero exit code if P90 total latency exceeds this SLA (ms)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Filter verbose asyncua library logs unless verbose is requested
    if not args.verbose:
        logging.getLogger("asyncua").setLevel(logging.ERROR)

    # 1. Load base configuration
    if args.config:
        cfg = load_config(args.config)
    else:
        cfg = OpcUaPoolConfig()

    # 2. Apply CLI overrides
    if args.endpoints:
        cfg.endpoints = [ep.strip() for ep in args.endpoints.split(",") if ep.strip()]
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
    if args.skip_clock_skew:
        cfg.skip_clock_skew = True

    if not cfg.endpoints:
        cfg.endpoints = ["opc.tcp://localhost:40451"]

    # Re-validate after overrides
    cfg.validate()
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

    coverage_valid, coverage_msg = pool.verify_coverage(samples)
    logger.info(coverage_msg)

    # 5. Run heuristic attribution diagnostics
    totals = [s.total_result_transfer_time_ms for s in samples if s.total_result_transfer_time_ms is not None]
    transports = [s.network_transport_time_ms for s in samples if s.network_transport_time_ms is not None]
    servers = [s.server_processing_time_ms for s in samples if s.server_processing_time_ms is not None]
    skews = [s.clock_skew_ms for s in samples]

    verdict = evaluate_diagnostics(
        network_transport_latencies=transports,
        server_processing_latencies=servers,
        total_latencies=totals,
        clock_skews=skews,
        measured_thread_count=real_thread_count,
        measured_process_count=real_process_count,
    )

    # 6. Output reporting
    print_console_report(samples, verdict, cfg.name)

    if args.markdown:
        md_text = generate_markdown_report(samples, verdict, cfg.name)
        Path(args.markdown).write_text(md_text, encoding="utf-8")
        logger.info(f"Wrote Markdown summary to {args.markdown}")

    fail_msg = None
    if cfg.fail_p90_ms is not None and totals and verdict.metrics_summary["total_p90_ms"] > cfg.fail_p90_ms:
        fail_msg = (
            f"P90 latency ({verdict.metrics_summary['total_p90_ms']:.1f}ms) "
            f"exceeded SLA threshold ({cfg.fail_p90_ms:.1f}ms)"
        )

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
            },
        )
        logger.info(f"Wrote JSON metrics to {args.json}")

    if fail_msg or not coverage_valid or not samples:
        if fail_msg:
            logger.error(f"SLA BREACH: {fail_msg}")
        if not coverage_valid:
            logger.error(f"COVERAGE FAILURE: {coverage_msg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
