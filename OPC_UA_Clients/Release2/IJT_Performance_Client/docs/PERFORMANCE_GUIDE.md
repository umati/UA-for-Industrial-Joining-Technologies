# IJT Performance & Benchmarking Guide

A comprehensive, authoritative engineering guide covering concurrency architecture, Total Result Transfer Time, Cristian's clock skew calibration, benchmarking scenarios, profiles, and root-cause attribution using the **IJT Performance Client**.

---

## 1. What is "Total Result Transfer Time"?

When an industrial joining system (e.g. tightening tool, riveting press, clinching device, or adhesive dispensing tool) finishes a physical joining operation on an assembly line, the joining result (process variables, step results, curves, pass/fail status) must be delivered to quality databases, MES (Manufacturing Execution Systems), or line PLC controllers.

**Total Result Transfer Time (`total_result_transfer_time_ms`)** is the total elapsed time from the moment the physical joining operation completes (`ProcessingTimes.EndTime`) until the client application has completely received, decoded, and dispatched the result event callback (`JoiningSystemResultReadyEvent`).

```
[Physical Joining Tool Operation]
        │
        ▼ (T_end: Joining operation completes — ProcessingTimes.EndTime)
[Server Result Assembly & Event Dispatch] ── (server_processing_time_ms: Controller aggregates data & emits event)
        │
        ▼ (T_event: Event published to OPC UA socket — Event.Time)
[Network & Transport Layer]                ── (network_transport_time_ms: TCP/IP wire transit, socket read, asyncua decoding)
        │
        ▼ (T_client: Client application event handler callback fires)
[Client Application Handler]
```

### The Standardized Timing Breakdown

$$\text{Total Result Transfer Time} = T_{\text{client}} - T_{\text{end}} + \Delta t_{\text{skew}} = \text{server_processing_time_ms} + \text{network_transport_time_ms}$$

| Metric | Variable Name | Math Formula | OPC UA Specification Source | Industrial Target |
|---|---|---|---|---|
| **Joining Duration** | `joining_duration_ms` | $T_{\text{end}} - T_{\text{start}}$ | `ProcessingTimes.EndTime - ProcessingTimes.StartTime` | Process-dependent (e.g. 200–2,000 ms) |
| **Server Processing Duration** | `server_processing_time_ms` | $T_{\text{event}} - T_{\text{end}}$ | `Event.Time - ProcessingTimes.EndTime` | **< 30 ms** |
| **Network Transport Latency** | `network_transport_time_ms` | $T_{\text{client}} - T_{\text{event}} + \Delta t_{\text{skew}}$ | `ClientReceived - Event.Time + Skew` | **< 40 ms** |
| **Total Result Transfer Time** | `total_result_transfer_time_ms` | $T_{\text{client}} - T_{\text{end}} + \Delta t_{\text{skew}}$ | `ClientReceived - ProcessingTimes.EndTime + Skew` | **< 100 ms** (Automotive line standard) |

---

## 2. Concurrency Architecture: Why Process Sharding?

The `IJT_Performance_Client` targets controlled scale tests in which a central software system connects to many joining controllers. Claims at 50 to 500+ endpoints require validation on the intended host, network, and controllers.

### The Problem: OS Thread Exhaustion in CPython

A synchronous client-per-connection design can create one or more operating system threads for every endpoint. At high endpoint counts, GIL contention and operating system context switching can delay callback processing. This was a plausible contributor to multi-second latency observed in one scale-test environment, but server, network, and workload effects must still be measured separately.

### The Solution: Process-Sharded AsyncIO Client Pool (`OpcUaClientPool`)

```
[Pytest Runner / CLI Entrypoint]
       │
       ├── Spawns up to 4 Process Workers by default (configurable from 1 to 32)
       │
       ├── [Worker 0] ──> Single AsyncIO Event Loop ──> 125 Non-Blocking Sockets
       ├── [Worker 1] ──> Single AsyncIO Event Loop ──> 125 Non-Blocking Sockets
       ├── [Worker 2] ──> Single AsyncIO Event Loop ──> 125 Non-Blocking Sockets
       └── [Worker 3] ──> Single AsyncIO Event Loop ──> 125 Non-Blocking Sockets
```

Key architectural mechanisms:
1. **Multi-Core Sharding:** Controllers are evenly partitioned across worker processes (`OpcUaClientPool`), each with an independent CPython interpreter and GIL.
2. **Cooperative Multiplexing:** Each worker manages its assigned connections inside a single non-blocking `asyncio` event loop using OS kernel multiplexing (`epoll` on Linux, `IOCP` on Windows).
3. **Paced TCP Ramp-Up:** Connections are acquired through an `asyncio.Semaphore(connect_concurrency)` to reduce simultaneous connection pressure and refusal risk.
4. **Bounded Worker Buffering:** Event callbacks append samples to bounded process-local memory and flush batches through an IPC queue. Overflow is counted and fails strict coverage checks; lossless delivery is not assumed.
5. **Subscription Lifecycle Protection:** Subscriptions are explicitly deleted before client disconnection to reduce the risk of leaked server sessions (`BadTooManySessions`).

---

## 3. Clock Skew Calibration ($\Delta t_{\text{skew}}$) via Cristian's Algorithm

When client PC and joining controller run on separate clocks without IEEE 1588 PTP or NTP synchronization, cross-machine timestamp math is vulnerable to clock drift. The Performance Client uses **Cristian's Algorithm** to calibrate relative clock skew before benchmark runs:

```
Client PC (t_client)                               OPC UA Server (t_server)
      │                                                     │
 1.   ├─ t_before = datetime.now(UTC)                       │
      │                                                     │
      │── OPC UA ReadRequest (ns=0;i=2258) ────────────────>│
      │   (ServerStatus.CurrentTime)                        │
      │                                                     │ 2. Server reads clock:
      │                                                     │    server_now = ServerStatus.CurrentTime
      │                                                     │
      │<─ OPC UA ReadResponse ──────────────────────────────┤
      │                                                     │
 3.   ├─ t_after = datetime.now(UTC)                        │
      │                                                     │
```

1. **Round-Trip Time (RTT):**
   $$\text{RTT} = t_{\text{after}} - t_{\text{before}}$$
2. **Client Midpoint (Accounting for Read Call Time):**
   Under symmetric network transit ($\text{transit}_{\text{req}} \approx \text{transit}_{\text{res}}$), the server read its clock midway through the round trip:
   $$t_{\text{client\_midpoint}} = t_{\text{before}} + \frac{\text{RTT}}{2}$$
3. **Clock Skew Calculation:**
   $$\Delta t_{\text{skew}} = \text{server_now} - t_{\text{client\_midpoint}}$$
4. **Uncertainty Estimate:**
   Half the measured RTT is a useful lower-order uncertainty indicator under symmetric transit and negligible server processing. It is not a strict bound when request/response paths are asymmetric or the server delays the clock read.
5. **Multi-Probe Minimum Filtering:**
   The client executes 3 probes and selects the one with minimum RTT to reject momentary network jitter or OS scheduling pauses.
6. **Bypassing Calibration:**
   When client and server use the same clock, or external synchronization accuracy has been independently verified, pass `--skip-clock-skew` to avoid calibration.

---

## 4. Heuristic Root-Cause Attribution Matrix

The client applies advisory heuristics to timing distributions. These indicators guide investigation; they do not identify a root cause without supporting host, server, and network evidence:

| Metric Profile | Diagnostic Indicator | Suggested Investigation |
|---|---|---|
| `total P90 < 100ms`, `transport P90 < 50ms` | `NONE (OPC UA PIPELINE HEALTHY)` | Measurements are below the configured default warning thresholds; confirm application-specific acceptance limits. |
| `server P90 > 200ms`, `transport P90 < 100ms` | `SERVER_PROCESSING_DURATION` | Inspect controller firmware, CPU saturation, result construction, and step evaluation. |
| `transport P90 > 300ms` | `NETWORK_OR_TRANSPORT` | Inspect network paths, switch queueing, MTU behavior, socket buffering, event-loop delay, and deserialization cost. |
| `transport P90 > 100ms`, `threads > 200` | `CLIENT_SIDE_THREAD_STARVATION` | Inspect client scheduling and context switching, then compare with a process-sharded run under the same workload. |
| Elevated across multiple stages | `APPLICATION_OR_MIXED` | Mixed pipeline delay. Review client deserialization speed, event loop lag, and controller CPU load. |
| Zero samples received | `NO_DATA` | Verify server event generation, subscription filters, and tool triggers. |

---

## 5. Testing Scenarios & Pre-Configured Profiles

The Performance Client provides a unified multi-process architecture (`OpcUaClientPool`) supporting both **single-station SLA validation** and **large-scale multi-controller fleet benchmarking**.

### Scenario A — Single Controller, Several Results (Single-Station SLA Test)

Use this scenario when validating an individual joining system controller or running factory acceptance testing (FAT) on a single station.

#### Quick 10-Result Smoke Test
Connect to 1 server and collect 10 results:
```bash
python -m ijt_performance_client --endpoints "opc.tcp://localhost:40451" --samples 10
```

#### 50-Result Benchmark with 100ms SLA Gate
Collect 50 joining results from 1 controller. Fail with exit code 1 if the P90 Total Result Transfer Time exceeds 100ms:
```bash
python -m ijt_performance_client --endpoints "opc.tcp://192.168.1.100:40451" --samples 50 --fail-p90 100.0 --markdown test-results/single-station.md --json test-results/single-station.json
```

#### Using the Pre-Configured Profile (`profiles/single_server.yaml`)
```bash
python -m ijt_performance_client --config profiles/single_server.yaml
```

---

### Scenario B — Multiple Controllers, Several Results per Controller (Fleet Scale)

Use this scenario when validating how an entire production line or factory cell behaves under concurrent joining operations (e.g. 4, 10, or 500 controllers delivering results simultaneously).

#### 4-Controller Joining Cell
Collect results from 4 controllers in parallel with full coverage verification:
```bash
python -m ijt_performance_client --endpoints "opc.tcp://10.0.1.11:40451,opc.tcp://10.0.1.12:40451,opc.tcp://10.0.1.13:40451,opc.tcp://10.0.1.14:40451" --duration 30 --require-full-coverage
```

#### CI Multi-Server Fleet (`profiles/ci_multi_server.yaml`)
Used in automated CI environments to connect to 3 virtual servers in parallel (`40451..40453`):
```bash
python -m ijt_performance_client --config profiles/ci_multi_server.yaml
```

#### High-Scale Fleet Template (50 to 500+ Controllers) (`profiles/multi_server_template.yaml`)
Template for configuring 50 to 500+ plant floor IP addresses and port ranges:
```yaml
fleet:
  name: "Factory Fleet Benchmark"
  endpoints:
    - "opc.tcp://10.10.1.1:40451"
    - "opc.tcp://10.10.1.2:40451"
    # ... up to 500 controllers
  connect_concurrency: 20
  sub_period_ms: 50
  mode: "passive"
  duration_seconds: 60.0
  require_full_coverage: true
  fail_p90_ms: 50.0
```

Run with:
```bash
python -m ijt_performance_client \
  --config profiles/multi_server_template.yaml \
  --duration 60 \
  --junit test-results/junit-perf.xml \
  --markdown test-results/summary.md \
  --json test-results/metrics.json
```

---

### Scenario C — Passive Listening vs Active Simulation

You can control how joining result load is generated:

| Mode | Flag | Description | When to Use |
|---|---|---|---|
| **Passive Listening** | `--mode passive` | Client only subscribes to OPC UA events. It does not trigger server simulation methods. | On live production assembly lines where tools are physically executing joining operations. |
| **Active Burst** | `--mode active_burst` | Client actively invokes `SimulateSingleResult` / `SimulateResults` on the server in rapid bursts. | Laboratory or pre-deployment stress testing to find maximum controller throughput. |
| **Combined** | `--mode both` | Client listens for incoming events while simultaneously invoking simulated operations. | Default mode for simulated controller environments. |

---

## 6. How to Interpret Benchmark Reports

### 1. Percentile Statistics
Average latency often conceals industrial problems. The client computes:
- **Min / Mean / Median:** Central tendency of result delivery time.
- **P90 (90th Percentile):** 90% of all joining results arrived faster than this number. This is the primary SLA standard in manufacturing quality systems.
- **P99 (99th Percentile):** Highlights rare tail-latency spikes (e.g. memory garbage collection, socket queue backpressure, or packet loss).
- **Max:** The single slowest result recorded during the benchmark.

### 2. Available Export Formats
- **Console Table:** Clean ANSI-formatted terminal summary.
- **JUnit XML (`--junit PATH`):** CI/CD pipeline integration with embedded latency properties and failure tags.
- **Markdown (`--markdown PATH`):** GitHub Actions Step Summary format.
- **JSON (`--json PATH`):** Machine-readable telemetry format for dashboards (Grafana, Kibana, Datadog).
