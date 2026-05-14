## IJT OPC UA — Integration

> ✅ **All 7 / 7 jobs passed &nbsp;·&nbsp; 2,586 tests &nbsp;·&nbsp; 0 failed &nbsp;·&nbsp; 154 skipped**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `abcdef12` &nbsp;·&nbsp; **Run:** [#84](https://github.example/ijt/actions/runs/84)
> Nightly integration and live tests — full OPC UA stack on Windows + Linux browser container + Docker

---

### 🐳 Docker Tests

> Platform: Ubuntu latest — containerized OPC UA server

| Suite | Tests | Skipped |
|:------|------:|--------:|
| OPC UA Server — Smoke    | ✅ 10 | 0 |
| Web Client — Python unit | ✅ 680 | 0 |
| Web Client — JavaScript  | ✅ 522 | 0 |

---

### 🖥️ Live Integration Tests

> Platform: Windows Server — native OPC UA server (dedicated ports per client)

| Suite | Port | Tests | Skipped | Notes |
|:------|-----:|------:|--------:|:------|
| Test Client — Smoke sanity       | 40462 | ✅ 10 | 0 | Server and namespace reachability |
| Test Client — Conformance (live) | 40462 | ✅ 1,043 | 154 | Not Implemented fixture marker |
| Web Client — Python/WebSocket    | 40463/40466/40467 | ✅ 127 | 0 | OPC UA subscriptions + WebSocket |
| Console Client — Live            | 40461 | ✅ 18 | 0 | — |
| C# Client — Live (xUnit)         | 40464 | ✅ 110 | 0 | Nightly drift detection |

---

### Browser E2E Tests

> Platform: Ubuntu latest — runs inside the owned `ijt-browser-ci` image (digest-pinned via `.github/docker/ijt-browser-ci/image-pin.json`); Chromium + system libs are baked at image-build time and the container runs with `--network=none`

| Suite | Surface | Tests | Skipped | Notes |
|:------|:--------|------:|--------:|:------|
| Web Client — Browser E2E | Chromium DOM/JS + OPC UA WebSocket + result/event UX | ✅ 66 | 0 | Headless Chromium baked into the IJT Browser CI image |

### Browser Features Timing

> Source: Web Client `timing-latest.json` artifacts for the Browser Features matrix rows.

| Shard | Total | pip-install | npm-install | Playwright install | Playwright features | Other |
|:------|------:|------------:|------------:|-------------------:|--------------------:|------:|
| full | 2.1 min | 10.0 s | 20.0 s | 30.0 s | 1.0 min | 3.4 s |

### C# Live Timing

> Source: C# Live `tests.trx`; timings exclude restore, build, and server startup.

| Class | Tests | Total | Avg | Max |
|:------|------:|------:|----:|----:|
| SlowTests | 1 | 1.2 min | 1.2 min | 1.2 min |
| FastTests | 1 | 5.5 s | 5.5 s | 5.5 s |

#### Top C# Live Tests

| Test | Duration | Outcome |
|:-----|---------:|:--------|
| RunsJoiningCycle | 1.2 min | Passed |
| ReadsServerStatus | 5.5 s | Passed |

---

### ⏭️ Skip Details

<details><summary>⏭️ <b>Test Client — Conformance</b> — 154 skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 153 |
| Not Implemented fixture marker | 1 |

</details>

---

> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down
> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning
