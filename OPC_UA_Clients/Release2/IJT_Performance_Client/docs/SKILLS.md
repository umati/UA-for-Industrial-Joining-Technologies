# IJT Performance Client — Developer Reference & Architecture Skills

This document details the engineering architecture, design rationale, concurrency model, and testing patterns for `IJT_Performance_Client`.

---

## 1. Concurrency Architecture: Why Process Sharding?

### The 1,000-Thread Failure in CPython
In previous experiments (such as testing 500 virtual tools), the test client ran in a single Python process and created 1 to 2 OS threads per connection. At 500 tools, this spawned **1,000 OS threads**.

Because of Python's **Global Interpreter Lock (GIL)**:
1. Python threads cannot run CPU-intensive tasks (such as binary deserialization of nested OPC UA structures) in true parallel.
2. The operating system kernel spends massive CPU cycles context-switching between 1,000 threads.
3. Threads reading from network sockets are starved of CPU timeslices, causing incoming result events to sit in memory buffers for 5–7 seconds before the callback executes.
4. Downstream reports falsely concluded that "OPC UA is 20x slower than legacy protocols."

### The Solution: Multi-Process Sharding + AsyncIO (`OpcUaClientPool`)
`IJT_Performance_Client` solves this by decoupling connections across independent processes:
- Automatically scales worker processes based on endpoint count and host CPU threads: $\text{workers} = \min\left(\max\left(4, \left\lfloor\frac{N + 19}{20}\right\rfloor\right), \min(\text{cpu\_count}, 32)\right)$ (yielding 8 workers for 150 endpoints when $\ge 8$ cores are available); operators may explicitly configure 1–32 workers via `-w` / `--workers` or `OPCUA_WORKERS` (for example, `-w 12` was an explicitly configured benchmark setting on a 20-thread host).
- Each process runs its own CPython interpreter with its own completely independent GIL, preventing event loop decode queue backlogs.
- Type definition and browse caching: `load_ijt_type_definitions` is loaded once per worker process (cached across endpoints sharing identical namespace layouts; single-worker namespace mismatches are rejected at connect time to prevent process-global type collisions); method NodeIds are cached to eliminate hundreds of redundant `Browse` requests.
- Operation models: Supports virtual simulation stimulation (`SimulateSingleResult`) for synthetic benchmarking, and passive production monitoring (`--mode passive`) where external line controllers trigger physical joining operations without client interference.
- Inside each worker process, a single non-blocking `asyncio` event loop manages the assigned sockets via OS kernel multiplexing (`epoll` on Linux, `IOCP` on Windows).
- Thread, CPU, and latency behavior must be measured on the target host at each intended endpoint count.

---

## 2. Standardized Result Transfer Timing Model

To separate the observable timing stages, every sample measures:

$$\text{Total Result Transfer Time} = T_{\text{client}} - T_{\text{end}} + \Delta t_{\text{skew}} = \text{server_processing_time_ms} + \text{network_transport_time_ms}$$

- **`joining_duration_ms` ($T_{\text{end}} - T_{\text{start}}$):**
  Duration of physical tool operation (e.g. tightening, riveting, clinching).
- **`server_processing_time_ms` ($T_{\text{event}} - T_{\text{end}}$):**
  Time taken by the joining controller firmware and OPC UA server to assemble the result structure and dispatch the event. Default diagnostic target: **< 30 ms**.
- **`network_transport_time_ms` ($T_{\text{client}} - T_{\text{event}} + \Delta t_{\text{skew}}$):**
  Combined network transit, socket buffering, event-loop dispatch, and asyncua deserialization. Default diagnostic target: **< 40 ms**.
- **`total_result_transfer_time_ms` ($T_{\text{client}} - T_{\text{end}} + \Delta t_{\text{skew}}$):**
  Observed elapsed time from physical joining completion to client callback receipt after clock-offset correction. Default diagnostic target: **< 100 ms**.

### Headline client-side metrics (wire timing)

When timing hooks are installed, each sample also records when its bytes reached the client and when decoding finished:

- **`delivery_time_ms`** (headline): operation end until the result is on the client's wire. Gated by `--fail-p90`.
- **`client_decode_time_ms`**: client decoding only (single clock, no offset).
- **`client_ready_time_ms`**: operation end until the result is decoded and usable. Gated by `--fail-p90-client-ready`.
- **`dispatch_delay_ms`**: time waiting for the client to be free after decoding.

`timing_source` shows whether wire timing or the callback-time fallback was used. Negative offset-corrected values are clamped to 0, flagged with `is_clamped_to_zero`, and kept unclamped in `raw_*` fields.

### Benchmark Integrity Gate (summary)

- Each result is `VALID`, `INCOMPLETE`, `DUPLICATE` or `UNMATCHED`; only `VALID` results feed statistics and pass/fail limits.
- `active_burst`: VALID results must equal successful trigger calls per endpoint. `both`: fewer fails, extra results are counted as external events (warning). `passive`: no call matching.
- A different IJT namespace version across endpoints fails the run; a missing one is reported as "unverified".
- `--settle-timeout` (default 5 s) waits for late results; `--allow-partial-samples` relaxes only the sample-count target.

Full rules: [Performance Guide, Integrity Gate](PERFORMANCE_GUIDE.md). Report names vs. keys: [Glossary](PERFORMANCE_GUIDE.md#9-glossary).

---

## 3. Pre-Run Clock Offset (Skew) Calibration ($\Delta t_{\text{skew}}$) via Cristian's Algorithm

When benchmarking across physical controllers, unsynchronized clocks can materially distort cross-machine latency calculations.

Before running tests, `calibrate_clock_skew(client)`:
1. Records client UTC timestamp $T_{\text{before}}$.
2. Reads `ServerStatus.CurrentTime` over OPC UA.
3. Records client UTC timestamp $T_{\text{after}}$.
4. Computes midpoint $T_{\text{mid}} = T_{\text{before}} + (T_{\text{after}} - T_{\text{before}}) / 2$.
5. Determines $\Delta t_{\text{skew}} = T_{\text{server}} - T_{\text{mid}}$.
6. Applies the estimated offset: $\text{network\_transport\_time\_ms} = \text{raw\_wire} + \Delta t_{\text{skew}}$. Network asymmetry and calibration age remain sources of uncertainty.

It probes several times, keeps the probe with the lowest round-trip time (RTT), and returns a `ClockCalibration(skew_ms, rtt_ms)`. `rtt_ms` is `None` when no probe succeeded, in which case the skew is 0. Local endpoints and `--skip-clock-skew` skip probing.

The RTT feeds a clock-health check: an event whose skew-corrected `Time` is earlier than collection start by more than `--clock-tolerance-ms` (default 1000) plus half the round-trip time sets `clock_warning` on the sample. This is only a warning and never changes the integrity status.

---

## 4. Reusability Guide

### Running via CLI
```bash
# 1 server baseline (direct source execution)
python main.py --endpoints "opc.tcp://localhost:40451" --samples 10

# Scalable multi-server fleet run (against existing plant servers)
python main.py --config profiles/multi_server_fleet.yaml

# Standalone automated fleet launcher (spawns 50 local servers, tests, and tears down)
python run_fleet.py

# Large-scale fleet launcher (150 servers, 12 workers, 1,500 samples with full traces)
python run_fleet.py --servers 150 -w 12 --samples-per-server 10

# Cadence-controlled fleet run (200ms burst delay vs 5s factory takt emulation)
python run_fleet.py --servers 150 -w 12 --burst-delay 0.2
python run_fleet.py --servers 100 -w 8 --burst-delay 5.0

# Integrity and pass/fail options
python run_fleet.py --settle-timeout 15 --fail-p90 100 --fail-p90-client-ready 150

# Test suite runner with automated fleet orchestration
python run_all_tests.py --phase2 --fleet 50 -w 8

# Custom endpoints
python main.py -e "opc.tcp://10.0.1.11:40451,opc.tcp://10.0.1.12:40451" -d 30 -s 100

# When installed as a package
ijt-perf --config profiles/multi_server_fleet.yaml
```

### Importing as Python SDK
```python
from src.engine import OpcUaClientPool
from src.diagnostics import evaluate_diagnostics

# Or when installed via pip:
# from ijt_performance_client import OpcUaClientPool, evaluate_diagnostics

pool = OpcUaClientPool(endpoints=["opc.tcp://10.0.0.1:40451"], max_workers=2)
pool.start()
samples = pool.collect_samples(duration_seconds=15.0)
pool.stop()
```

---

## 5. Authoritative References
- [Performance & Benchmarking Guide](PERFORMANCE_GUIDE.md)
