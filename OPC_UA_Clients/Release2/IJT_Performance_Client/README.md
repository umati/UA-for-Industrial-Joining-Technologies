# IJT Performance Client

Performance testing and Result Transfer Time benchmarking client for OPC UA Industrial Joining Technologies (OPC 40450-1 / OPC 40451-1).

This client measures how quickly joining results (tightening, riveting, clinching, etc.) travel from industrial controllers to your application. Its process-sharded asyncio design targets controlled tests from one endpoint to large fleets; validate the intended endpoint count on the target environment.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451` (the simulator's default port; CI uses port 40485 via profile configuration)

## Quick Start

### Option 1 — Single Controller Benchmark

Measure Result Transfer Time from a single controller (collects 10 results):

```bash
python -m ijt_performance_client --endpoints "opc.tcp://localhost:40451" --samples 10
```

To enforce a 100 ms maximum delivery time (SLA gate) and export a report:

```bash
python -m ijt_performance_client --endpoints "opc.tcp://localhost:40451" --samples 50 --fail-p90 100.0 --markdown test-results/summary.md
```

### Option 2 — Multi-Controller Benchmark

Benchmark multiple controllers simultaneously (connections are distributed across worker processes):

```bash
python -m ijt_performance_client --endpoints "opc.tcp://10.0.1.11:40451,opc.tcp://10.0.1.12:40451" --duration 30
```

### Option 3 — Pre-Configured Profile

Run with a profile configuration file:

```bash
python -m ijt_performance_client --config profiles/single_server.yaml
```

## Testing

Run all static analysis and unit tests:

```bash
python run_all_tests.py --phase1
```

Or run all tests with live server integration:

```bash
python run_all_tests.py
```

## Learn More

- [Performance & Benchmarking Guide](docs/PERFORMANCE_GUIDE.md) — complete guide covering latency definitions, architecture, clock skew calibration, attribution matrix, profiles, and export formats.
