# Industrial Joining Technologies (IJT) — Performance & Benchmarking Guide

A clear, comprehensive guide to understanding, measuring, and optimizing OPC UA joining result delivery speed, scale testing, and automated diagnostics using the **IJT Performance Client**.

---

## Quick Reference Glossary: Key Terms & Abbreviations

Before diving into the details, here is a simple translation of the common terms used in this guide:

| Term / Abbreviation | What It Stands For | What It Means in Plain English |
|---|---|---|
| **OPC UA** | Open Platform Communications Unified Architecture | The universal, secure industrial communication standard that allows manufacturing machines and computers from different vendors to talk to each other. |
| **IJT** | Industrial Joining Technologies | The standardized OPC UA companion specifications (OPC 40450-1 and OPC 40451-1) specifically designed for tools that join parts (e.g. tightening bolts, pressing rivets, dispensing glue). |
| **Result Transfer Time** | Total Result Transfer Time | The total time (in milliseconds) it takes from the moment a tool finishes a joining operation until the computer receives and decodes the result. |
| **MES** | Manufacturing Execution System | The central factory software system that manages and tracks production lines, work orders, and vehicle assembly history. |
| **PLC** | Programmable Logic Controller | The rugged industrial computer on an assembly line that controls conveyor belts, safety gates, and robot arms. |
| **SLA** | Service Level Agreement | The contractual or operational performance target (e.g. *"90% of results must arrive in under 100 milliseconds"*). |
| **P90 / P95 / P99** | 90th, 95th, 99th Percentiles | Statistical metrics showing tail performance. For example, P90 is the time within which 90% of all results were delivered. |
| **RTT** | Round-Trip Time | The time it takes for a message to travel from the computer to the controller and back. |
| **Clock Skew** | Time Offset Between Two Clocks | The time difference between the clock inside the tool controller and the clock inside the computer. |
| **GIL** | Global Interpreter Lock | An internal mechanism in standard Python (CPython) that allows only one thread to execute Python code at a time, which can create a bottleneck if not managed properly. |
| **Process Sharding** | Multi-Process Architecture | Running multiple independent worker processes (each with its own CPU core and memory) to handle hundreds of tools without slowdowns. |

---

## 1. What is "Total Result Transfer Time"?

### In Plain English

Imagine an automated automotive assembly line. A robotic tool tightens a critical suspension bolt on a car chassis. The moment the bolt is torqued, the tool controller records key data: final torque, angle, timestamp, and whether the operation passed or failed.

That result must travel across the factory network to the quality database and line PLC. The line PLC cannot release the conveyor belt to move the car to the next workstation until it knows the bolt was tightened properly.

**Total Result Transfer Time (`total_result_transfer_time_ms`)** is the stopwatch measurement of that entire journey:
> **The elapsed time from the exact millisecond the physical tool stops joining (`ProcessingTimes.EndTime`) to the millisecond the software application receives, decodes, and processes the result event (`JoiningSystemResultReadyEvent`).**

```
[Physical Joining Tool Operation]
        │
        ▼ (T_end: Joining operation finishes — ProcessingTimes.EndTime)
[Server Result Assembly & Event Dispatch] ── (Server Processing Duration: Controller formats data & emits event)
        │
        ▼ (T_event: Event published to OPC UA network socket — Event.Time)
[Network & Transport Layer]                ── (Network Transport Latency: Wire transit, packet arrival, client decoding)
        │
        ▼ (T_client: Client application event handler callback executes)
[Client Quality / MES Application]
```

### Why It Matters on the Factory Floor

1. **Cycle Time & Line Bottlenecks:** Modern assembly lines operate on cycle times as fast as 30 to 60 seconds per workstation. If result delivery takes several seconds, operators stand idle and production lines halt.
2. **Quality & Traceability:** Fast delivery ensures that any defective joint (e.g. cross-threaded bolt) is flagged immediately before the product moves to an inaccessible station.
3. **Reliability at Scale:** A single tool delivering results in 50 ms might perform well, but when 200 tools on the same production line fire simultaneously at the end of a shift, network buffering or software lockups must not cause results to queue up or get lost.

---

## 2. The Standardized Timing Breakdown

To fix latency problems, you need to know *where* the time is spent. The IJT standard divides Total Result Transfer Time into distinct, measurable stages:

$$\text{Total Result Transfer Time} = (T_{\text{client}} - T_{\text{end}}) + \Delta t_{\text{skew}} = T_{\text{server}} + T_{\text{network}}$$

| Metric | Code Variable | How It Is Measured | OPC UA Source Field | Target for Production |
|---|---|---|---|---|
| **1. Joining Duration** | `joining_duration_ms` | $T_{\text{end}} - T_{\text{start}}$ | `ProcessingTimes.EndTime` minus `ProcessingTimes.StartTime` | Process-dependent (typically 200 ms to 2,000 ms) |
| **2. Server Processing Duration** | `server_processing_time_ms` | $T_{\text{event}} - T_{\text{end}}$ | `Event.Time` minus `ProcessingTimes.EndTime` | **< 30 ms** |
| **3. Network Transport Latency** | `network_transport_time_ms` | $(T_{\text{client}} - T_{\text{event}}) + \Delta t_{\text{skew}}$ | Client receive time minus `Event.Time` plus clock skew | **< 40 ms** |
| **4. Total Result Transfer Time** | `total_result_transfer_time_ms` | $(T_{\text{client}} - T_{\text{end}}) + \Delta t_{\text{skew}}$ | Client receive time minus `ProcessingTimes.EndTime` plus clock skew | **< 100 ms** (Standard automotive SLA) |

*Note: All calculations account for relative clock drift ($\Delta t_{\text{skew}}$) between the controller and the client computer, ensuring physical elapsed duration is always accurate.*

---

## 3. Concurrency Architecture: Why Process Sharding?

### The Challenge: Managing Hundreds of Industrial Tools

In modern smart factories, a single computer or edge gateway often monitors dozens or hundreds of tightening tools simultaneously (from 50 to 500+ virtual stations).

### The Problem with Traditional Threading

In standard Python applications, developers often create one operating system thread per tool connection. However, the standard Python interpreter has a **Global Interpreter Lock (GIL)**:
- When 200 or 500 threads try to run at once, they fight for access to a single CPU core.
- The operating system spends more time switching between threads (context switching) than actually reading network packets.
- In test environments, this thread starvation has caused artificial delays of 2 to 5 seconds—not because the industrial tool or network was slow, but because the client computer was stuck in thread queues.

### The Solution: Process-Sharded Client Pool (`OpcUaClientPool`)

The IJT Performance Client solves this with a multi-process architecture:

```
[IJT Performance Client — Benchmark Orchestrator]
       │
       ├── Spawns 4 Independent Worker Processes (one per CPU core)
       │
       ├── [Worker Process 0] ──> Single Event Loop ──> Manages 125 Non-Blocking Sockets
       ├── [Worker Process 1] ──> Single Event Loop ──> Manages 125 Non-Blocking Sockets
       ├── [Worker Process 2] ──> Single Event Loop ──> Manages 125 Non-Blocking Sockets
       └── [Worker Process 3] ──> Single Event Loop ──> Manages 125 Non-Blocking Sockets
```

### Why This Architecture Works Better:

1. **True Multi-Core Parallelism:** Each worker process runs its own independent Python interpreter and its own GIL. Four workers utilize four physical CPU cores simultaneously.
2. **Cooperative Multiplexing (AsyncIO):** Within each worker process, a single lightweight event loop manages 100+ open sockets using OS kernel multiplexing (`IOCP` on Windows, `epoll` on Linux). There is zero OS thread contention.
3. **Paced Connection Setup:** When connecting to 500 tools, the client connects in controlled batches (semaphore-limited) to prevent overwhelming the network with a simultaneous connection surge.
4. **Isolated Memory Buffering:** Results are collected in fast process-local memory during tests and streamed in bulk, eliminating queue lock delays during rapid joining bursts.

---

## 4. Clock Skew Calibration: Solving Time Drift

### What is Clock Skew?

The tool controller has its own internal clock, and the client PC has its own internal clock. Even if both clocks are synchronized over a local network, they can easily drift apart by 10 to 100 milliseconds due to network latency, virtualization overhead, or NTP sync intervals.

If the controller's clock is 50 ms ahead of the PC's clock, a result that took 20 ms to arrive might mathematically look like it took 70 ms. Conversely, if the controller's clock is behind, the math could show an impossible negative number.

### The Solution: Cristian's Clock Synchronization Algorithm

Before running any benchmark, the client automatically measures the exact time offset between the PC and the controller using Cristian's Algorithm:

```
Client PC (Local Clock)                            Joining Controller (Server Clock)
       │                                                          │
  1.   ├─ t_before = Current PC Time (UTC)                        │
       │                                                          │
       │── Send OPC UA Read Request for ServerStatus.CurrentTime ─>│
       │                                                          │ 2. Controller reads its clock:
       │                                                          │    server_now = Current Controller Time
       │<─ Send OPC UA Read Response with server_now ─────────────┤
       │                                                          │
  3.   ├─ t_after = Current PC Time (UTC)                         │
       │                                                          │
```

### Step-by-Step Calculation:

1. **Measure Round-Trip Time (RTT):**
   $$\text{RTT} = t_{\text{after}} - t_{\text{before}}$$
   *(This tells us how long the network request took in total).*

2. **Estimate the Midpoint:**
   $$t_{\text{midpoint}} = t_{\text{before}} + \frac{\text{RTT}}{2}$$
   *(Because network transit is generally symmetric, the controller read its clock halfway through the round trip).*

3. **Calculate the Clock Offset ($\Delta t_{\text{skew}}$):**
   $$\Delta t_{\text{skew}} = t_{\text{server}} - t_{\text{midpoint}}$$
   *(If positive, the controller clock is ahead; if negative, the controller clock is behind).*

4. **Multi-Probe Filter:**
   The client performs 3 quick probes and selects the one with the lowest RTT to eliminate momentary network hiccups.

5. **Normalized Results:**
   The measured clock skew is added to raw timestamps, guaranteeing that reported Result Transfer Times reflect true physical latency.

---

## 5. How to Read Benchmark Reports: Percentiles & Diagnostics

### Why Averages Can Be Misleading

In factory automation, **the average is dangerous**.

Imagine a production line where 99 bolts arrive in 20 milliseconds, but 1 bolt gets stuck in a buffer and takes 5,000 milliseconds (5 seconds).
- The *average* looks fine (~70 ms).
- But in reality, **the assembly line stopped for 5 seconds** waiting for that one single bolt!

That is why the IJT Performance Client reports percentiles:

- **Median (50th Percentile):** The typical performance experienced by half of all results.
- **P90 (90th Percentile):** 90% of results arrived faster than this time. This is the primary industrial Service Level Agreement (SLA) threshold.
- **P95 / P99 (Tail Latency):** Reveals rare spikes caused by memory cleanups, network packet retransmissions, or storage write delays.
- **Max:** The single slowest result recorded during the entire run.

---

### Automated Root-Cause Diagnostic Assistant

When tests finish, the Performance Client automatically evaluates the timing breakdown and tells you where the bottleneck lies:

| What the Data Shows | What the System Reports | Plain English Meaning & What to Do |
|---|---|---|
| P90 < 100 ms, Transport P90 < 50 ms | `OPC_UA_PIPELINE_HEALTHY` | **System is healthy.** Results are arriving comfortably within automotive production targets. |
| Server Processing P90 > 200 ms | `SERVER_PROCESSING_DURATION` | **The controller is taking too long to create the result.** Check controller CPU load, internal database save operations, or heavy step calculations. |
| Transport P90 > 300 ms | `NETWORK_OR_TRANSPORT` | **The delay is on the physical network or socket.** Inspect network switches, Ethernet cables, MTU settings, or TCP buffer sizes. |
| Transport P90 > 100 ms with > 200 client threads | `CLIENT_SIDE_THREAD_STARVATION` | **The client computer is overwhelmed by too many threads.** Switch to the process-sharded `OpcUaClientPool` to distribute load across CPU cores. |
| Delays across multiple stages | `APPLICATION_OR_MIXED` | **Mixed delay.** Both server processing and network transport are elevated. Review both controller CPU and network infrastructure. |
| 0 samples collected | `NO_DATA` | **No results arrived.** Verify that the tool is connected, subscriptions are active, and tightening operations were actually triggered. |

---

## 6. How to Run: Practical Step-by-Step Scenarios

The Performance Client provides ready-to-run commands for common testing needs.

### Scenario A: Testing 1 Controller (Single-Station SLA Check)

Use this scenario during factory commissioning or when verifying an individual tool before deploying it to production.

#### 1. Quick 10-Result Smoke Test
Connects to 1 controller and verifies that 10 results arrive cleanly:
```bash
python -m ijt_performance_client --endpoints "opc.tcp://localhost:40451" --samples 10
```

#### 2. Strict 50-Result Benchmark with 100 ms SLA Gate
Collects 50 results from a live controller. If the P90 latency exceeds 100 ms, the command exits with an error code (perfect for automated pass/fail CI pipelines):
```bash
python -m ijt_performance_client \
  --endpoints "opc.tcp://192.168.1.100:40451" \
  --samples 50 \
  --fail-p90 100.0 \
  --markdown test-results/single-station.md \
  --json test-results/single-station.json
```

#### 3. Using a Pre-Configured Profile File
Instead of typing command-line arguments, you can pass a YAML configuration file:
```bash
python -m ijt_performance_client --config profiles/single_server.yaml
```

---

### Scenario B: Testing a Production Cell (Multiple Controllers in Parallel)

Use this scenario to verify how multiple tools in the same production station behave when operating simultaneously.

#### 4-Tool Production Station
Connects to 4 controllers in parallel and monitors results for 30 seconds, verifying that every single controller delivers data:
```bash
python -m ijt_performance_client \
  --endpoints "opc.tcp://10.0.1.11:40451,opc.tcp://10.0.1.12:40451,opc.tcp://10.0.1.13:40451,opc.tcp://10.0.1.14:40451" \
  --duration 30 \
  --require-full-coverage
```

#### Pre-Configured CI Fleet Test (`profiles/ci_multi_server.yaml`)
Runs 3 virtual controllers on ports 40451, 40452, and 40453:
```bash
python -m ijt_performance_client --config profiles/ci_multi_server.yaml
```

---

### Scenario C: Large-Scale Plant Fleet Benchmark (50 to 500+ Tools)

Use this scenario when designing or stress-testing plant-wide infrastructure to find out how many simultaneous tools the network and client system can support.

Use the provided template [`profiles/multi_server_template.yaml`](../profiles/multi_server_template.yaml) to list all your tool IP addresses and ports, then execute:

```bash
python -m ijt_performance_client \
  --config profiles/multi_server_template.yaml \
  --duration 60 \
  --junit test-results/junit-perf.xml \
  --markdown test-results/summary.md \
  --json test-results/metrics.json
```

---

### Passive Listening vs. Active Simulation

You can configure how the client interacts with the joining tools:

| Mode | Command Flag | How It Works | When to Use It |
|---|---|---|---|
| **Passive Listening** | `--mode passive` | The client quietly listens for incoming result events without triggering any operations. | On live factory lines where physical tools are being operated by assembly workers or robots. |
| **Active Burst** | `--mode active_burst` | The client actively triggers the server's simulation methods (`SimulateSingleResult` / `SimulateResults`) in rapid succession. | In test laboratories or staging environments to stress-test maximum throughput limits. |
| **Combined** | `--mode both` | Listens for events while simultaneously triggering simulated operations. | Standard automated test runs against virtual simulator environments. |

---

## 7. Report Formats & Integration

The Performance Client automatically generates multiple report formats:

1. **Console Summary:** A clean terminal table showing min, mean, median, P90, P95, P99, max, sample counts, and diagnostic verdicts.
2. **Markdown (`--markdown report.md`):** Ready for direct copy-paste into pull request summaries, GitHub Actions step summaries, or project documentation.
3. **JUnit XML (`--junit results.xml`):** Directly consumed by Jenkins, GitLab CI, or GitHub Actions to display visual test pass/fail charts and latency trends over time.
4. **JSON (`--json metrics.json`):** Machine-readable telemetry format ready for automated ingestion into Grafana, Kibana, or enterprise database dashboards.
