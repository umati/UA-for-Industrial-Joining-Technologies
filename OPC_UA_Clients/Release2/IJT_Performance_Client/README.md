# IJT Performance Client

Performance testing and Result Transfer Time benchmarking client for OPC UA Industrial Joining Technologies (OPC 40450-1 / OPC 40451-1).

This client measures how quickly joining results (tightening, riveting, clinching, etc.) travel from industrial joining systems, machines, and servers to your application. Its process-sharded asyncio design targets controlled tests from one endpoint to large fleets; validate the intended endpoint count on the target environment.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- An OPC UA IJT server for benchmarks: use local simulators or your own server

**Default endpoint:** `opc.tcp://localhost:40451` (the simulator's default port; CI uses port 40485 via profile configuration)

## Quick Start

Run these commands from this client directory. `run_fleet.py` and
`run_all_tests.py` prepare Python dependencies and uv automatically in isolated
environments. No manual uv installation or shell activation is needed:

```bash
python run_fleet.py                 # benchmark a local simulator fleet
python run_all_tests.py --phase1     # static checks and unit tests; no server needed
```

## Usage

### Choose the Runner

| Goal | Command |
|------|---------|
| Benchmark local simulators and produce reports | `python run_fleet.py` |
| Check code without starting servers | `python run_all_tests.py --phase1` |
| Run regression checks plus live single-server tests | `python run_all_tests.py` |
| Include a local fleet in regression testing | `python run_all_tests.py --fleet 50 -w 8` |
| Benchmark an existing server or controller | Use `main.py` in a prepared runtime environment; see the [Performance Guide](docs/PERFORMANCE_GUIDE.md#6-practical-execution-scenarios). |

`run_fleet.py` is the configurable benchmark launcher; `run_all_tests.py` is
the regression-test runner. Their options are not interchangeable.

### Local Fleet Benchmark

Launch 50 local server instances, collect 10 results per server (500 total samples across 50 subscriptions), and export reports:

```bash
python run_fleet.py
```

Run it with any Python 3.14+: on first use it creates its own `.venv` via `uv sync --locked --no-dev`
and restarts itself there.

Common options:

```bash
python run_fleet.py --servers 25 -w 6           # Scale to 25 servers with 6 worker processes
python run_fleet.py --burst-delay 0.2           # Rapid burst testing (200 ms delay between rounds)
python run_fleet.py --keep-running              # Keep servers running to inspect in Task Manager
python run_fleet.py --fail-p90 100              # Fail if the 90%-under Delivery Time is above 100 ms
```

| Option | Meaning | Default |
|--------|---------|---------|
| `--servers N` | Number of local simulator processes | 50 |
| `-w N` / `--workers N` | Client worker processes, not simulator count; choose for available CPU | Automatic; explicit range 1-32 |
| `--samples-per-server N` | Target result count per server | 10 |
| `--burst-delay S` | Seconds between trigger rounds; smaller values increase load | 1 |
| `--settle-timeout S` | Wait after the final trigger round for late results | 5 seconds |
| `--start-port P` | First simulator TCP port; subsequent servers use consecutive ports | 40001 |
| `--duration S` | Measurement window; allow enough time for the requested rounds | Automatically calculated |
| `--fail-p90 MS` | Fail if P90 Delivery Time exceeds this limit | No limit |
| `--fail-p90-client-ready MS` | Fail if P90 decoded/client-ready time exceeds this limit | No limit |
| `--keep-running` | Keep simulators available for inspection after the benchmark; press Enter to stop | Off |

### Advanced: 500-Server Load Test

On a machine with sufficient CPU, memory, and available ports:

```bash
python run_fleet.py --servers 500 -w 20 --samples-per-server 50 --settle-timeout 15 --fail-p90 300
```

This launches 500 simulator processes on ports 40001-40500 and targets 25,000
results, using 20 client worker processes. It waits up to 15 seconds for late
results after the final trigger round and fails if P90 Delivery Time exceeds
300 ms. Client-ready time is not gated unless you also specify
`--fail-p90-client-ready`.

Start with a smaller fleet, then increase scale. For a new machine, first omit
`--fail-p90` to measure its baseline. The 300 ms limit and 20-worker setting are
example choices, not guaranteed capacity or a recommended production SLA.
Local simulators and client workers compete for the same host resources.

Time limits are off unless you pass them. Pick a limit that fits the setup: single-machine runs measure this machine's CPU, so larger fleets need larger limits.

See the [Performance Guide](docs/PERFORMANCE_GUIDE.md) for single-server
benchmarks, profiles, fleet options, and choosing a suitable time limit.
Use `python run_fleet.py --help` or `python run_all_tests.py --help` for the
complete options supported by each entry point.

Outputs are automatically generated under `test-results/`:
- `perf-fleet.md`: Markdown summary (Fastest, Average, 90% under, 99% under, Slowest), integrity result and per-server table
- `perf-fleet.csv`: Detailed sample-by-sample latency metrics log with controller ResultId and trace audit verification (without heavy raw trace float curves)
- `perf-fleet.json`: Machine-readable JSON metrics and sample timeline
- `junit-fleet.xml`: Automated CI/CD gate pass/fail report

## Testing

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

## Integration

Using pip or benchmarking servers from your own application? See the
[Python Client Integration Guide](../../../docs/PYTHON_CLIENT_INTEGRATION.md).
It covers locked dependency exports and installing the optional `ijt-perf`
command. The fleet launcher additionally needs simulator assets.

## Learn More

- [Performance & Benchmarking Guide](docs/PERFORMANCE_GUIDE.md) — complete guide covering latency definitions, architecture, clock offset calibration, the Benchmark Integrity Gate, Likely Cause of Delay rules, profiles, and export formats.
- [Glossary](docs/PERFORMANCE_GUIDE.md#9-glossary) — plain report names (for example "90% under", "Clock offset") mapped to technical terms and JSON/CSV keys.
- [Developer reference](docs/SKILLS.md)
