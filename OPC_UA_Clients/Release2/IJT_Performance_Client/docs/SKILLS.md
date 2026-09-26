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
- Uses up to 4 worker processes by default; operators may explicitly configure 1–32 workers for the target host and endpoint count.
- Each process runs its own CPython interpreter with its own completely independent GIL.
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

---

## 3. Pre-Run Clock Drift Calibration ($\Delta t_{\text{skew}}$) via Cristian's Algorithm

When benchmarking across physical controllers, unsynchronized clocks can materially distort cross-machine latency calculations.

Before running tests, `calibrate_clock_skew(client)`:
1. Records client UTC timestamp $T_{\text{before}}$.
2. Reads `ServerStatus.CurrentTime` over OPC UA.
3. Records client UTC timestamp $T_{\text{after}}$.
4. Computes midpoint $T_{\text{mid}} = T_{\text{before}} + (T_{\text{after}} - T_{\text{before}}) / 2$.
5. Determines $\Delta t_{\text{skew}} = T_{\text{server}} - T_{\text{mid}}$.
6. Applies the estimated offset: $\text{network\_transport\_time\_ms} = \text{raw\_wire} + \Delta t_{\text{skew}}$. Network asymmetry and calibration age remain sources of uncertainty.

---

## 4. Reusability Guide

### Running via CLI
```bash
# 1 server baseline
python -m ijt_performance_client --config profiles/single_server.yaml

# Multi-server CI run
python -m ijt_performance_client --config profiles/ci_multi_server.yaml

# Custom endpoints
python -m ijt_performance_client -e "opc.tcp://10.0.0.1:40451,opc.tcp://10.0.0.2:40451" -d 30 -s 100
```

### Importing as Python SDK
```python
from ijt_performance_client import OpcUaClientPool, evaluate_diagnostics

pool = OpcUaClientPool(endpoints=["opc.tcp://10.0.0.1:40451"], max_workers=2)
pool.start()
samples = pool.collect_samples(duration_seconds=15.0)
pool.stop()
```

---

## 5. Authoritative References
- [Performance & Benchmarking Guide](PERFORMANCE_GUIDE.md)
