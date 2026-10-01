# IJT Performance Client

Performance testing and Result Transfer Time benchmarking client for OPC UA Industrial Joining Technologies (OPC 40450-1 / OPC 40451-1).

This client measures how quickly joining results (tightening, riveting, clinching, etc.) travel from industrial joining systems, machines, and servers to your application. Its process-sharded asyncio design targets controlled tests from one endpoint to large fleets; validate the intended endpoint count on the target environment.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451` (the simulator's default port; CI uses port 40485 via profile configuration)

## Quick Start

### Option 1 — Single Machine / Server Benchmark

Measure Result Transfer Time from a single OPC UA server (collects 10 results):

```bash
python main.py --endpoints "opc.tcp://localhost:40451" --samples 10
```

To fail the run when the 90%-under (P90) Delivery Time is above 100 ms, and export a report:

```bash
python main.py --endpoints "opc.tcp://localhost:40451" --samples 50 --fail-p90 100.0 --markdown test-results/summary.md
```

### Option 2 — Multi-Server Fleet Benchmark (Standalone Launcher)

Launch 50 local server instances, collect 10 results per server (500 total samples across 50 subscriptions), and export reports:

```bash
python run_fleet.py
```

Run it with any Python 3.14+: on first use it creates its own `.venv` (`requirements.txt` only,
exact versions from `requirements.lock`) and restarts itself there; it reinstalls automatically
when the requirements or the lock change.

Custom fleet scale and manual inspection options:

```bash
python run_fleet.py --servers 25 -w 6           # Scale to 25 servers with 6 worker processes
python run_fleet.py --servers 150 -w 12         # Scale to 150 servers (1,500 samples with full traces)
python run_fleet.py --burst-delay 0.2           # Rapid burst testing (200 ms delay between rounds)
python run_fleet.py --burst-delay 5.0           # Factory cadence emulation (5s takt time between joining operations)
python run_fleet.py --samples-per-server 10     # 10 samples per server
python run_fleet.py --start-port 40001          # Custom starting port
python run_fleet.py --keep-running              # Keep servers running to inspect in Task Manager
python run_fleet.py --settle-timeout 15         # Wait longer for late results (slow servers, large traces)
python run_fleet.py --fail-p90 100              # Fail if the 90%-under Delivery Time is above 100 ms
```

Time limits are off unless you pass them. Pick a limit that fits the setup: single-machine runs measure this machine's CPU, so larger fleets need larger limits.

| Setup | Suggested `--fail-p90` |
|---|---|
| Up to ~50 servers on this machine | 100 ms |
| ~150 servers on this machine | 150–200 ms |
| ~500 servers on this machine | 250–300 ms |
| Servers on other hosts (real network) | 100–150 ms |

See [Choosing a time limit](docs/PERFORMANCE_GUIDE.md#choosing-a-time-limit) for details.

Outputs are automatically generated under `test-results/`:
- `perf-fleet.md`: Markdown summary (Fastest, Average, 90% under, 99% under, Slowest), integrity result and per-server table
- `perf-fleet.csv`: Detailed sample-by-sample latency metrics log with controller ResultId and trace audit verification (without heavy raw trace float curves)
- `perf-fleet.json`: Machine-readable JSON metrics and sample timeline
- `junit-fleet.xml`: Automated CI/CD gate pass/fail report

### Option 3 — Pre-Configured Profile

Run against physical controllers or container fleets already running on your network:

```bash
python main.py --config profiles/multi_server_fleet.yaml
```

When installed via `pip install .`, you can also use the CLI command directly:

```bash
ijt-perf --config profiles/multi_server_fleet.yaml
```

## Testing

`run_all_tests.py` creates and uses its own `.venv_test` (`.venv_ci` when `CI` is set locally),
installing `requirements.txt` + `requirements-dev.txt` with exact versions from the generated
`requirements.lock`. It reinstalls automatically when any of these files change. Regenerate the
lock with `python scripts/update_python_locks.py` from the repo root; never edit it by hand.

Run all static analysis and unit tests (no server required):

```bash
python run_all_tests.py --phase1
```

Run all tests with live single-server integration (auto-starts simulator on port 40485):

```bash
python run_all_tests.py
```

Run live multi-server fleet test with automated local simulator orchestration:

```bash
# Auto-starts 50 servers concurrently (ports 40001..40050), benchmarks, and cleanly stops
python run_all_tests.py --fleet 50 -w 8

# Run live benchmark tests only (skip Phase 1 static/unit tests)
python run_all_tests.py --phase2 --fleet 50 -w 8
```

## Learn More

- [Performance & Benchmarking Guide](docs/PERFORMANCE_GUIDE.md) — complete guide covering latency definitions, architecture, clock offset calibration, the Benchmark Integrity Gate, Likely Cause of Delay rules, profiles, and export formats.
- [Glossary](docs/PERFORMANCE_GUIDE.md#9-glossary) — plain report names (for example "90% under", "Clock offset") mapped to technical terms and JSON/CSV keys.
