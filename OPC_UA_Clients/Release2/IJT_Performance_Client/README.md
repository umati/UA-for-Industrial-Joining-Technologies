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

To enforce a 100 ms maximum delivery time (SLA gate) and export reports:

```bash
python main.py --endpoints "opc.tcp://localhost:40451" --samples 50 --fail-p90 100.0 --markdown test-results/summary.md
```

### Option 2 — Multi-Server Fleet Benchmark (Standalone Launcher)

Launch 50 local server instances, collect 10 results per server (500 total samples across 50 subscriptions), and export reports:

```bash
python run_fleet.py
```

Custom fleet scale and manual inspection options:

```bash
python run_fleet.py --servers 25           # Scale to 25 servers (250 samples)
python run_fleet.py --samples-per-server 5 # 5 samples per server
python run_fleet.py --start-port 41001     # Custom starting port
python run_fleet.py --keep-running         # Keep servers running to inspect in Task Manager
```

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
python run_all_tests.py --fleet 50

# Run live benchmark tests only (skip Phase 1 static/unit tests)
python run_all_tests.py --phase2 --fleet 50
```

## Learn More

- [Performance & Benchmarking Guide](docs/PERFORMANCE_GUIDE.md) — complete guide covering latency definitions, architecture, clock skew calibration, attribution matrix, profiles, and export formats.
