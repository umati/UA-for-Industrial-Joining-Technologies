## IJT OPC UA — CI

> ✅ **All 12 / 12 jobs passed** &nbsp;·&nbsp; 39 tests  ·  0 failed  ·  18 skipped
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `12345678` &nbsp;·&nbsp; **Run:** [#42](https://github.example/ijt/actions/runs/42)

---

### 🧪 Test Results

| Component | Platform | Tests | Skipped | Coverage / Threshold |
|:----------|:--------:|------:|--------:|:--------:|
| Web Client — Python      | Ubuntu  | ✅ 4 | 2 | 97.0% / 95% ✅ |
| Web Client — JavaScript  | Ubuntu  | ✅ 3 | 0 | 96.0% / 95% ✅ |
| Console Client — Python  | Ubuntu  | ✅ 2 | 0 | 99.0% / 95% ✅ |
| Node Client — JavaScript | Ubuntu  | ✅ 2 | 1 | 95.0% / 95% ✅ |
| C# Client — Unit (xUnit) | Windows | ✅ 16 | 15 | 95.0% / 95% ✅ |
| Test Client — Python (Unit) | Ubuntu | ✅ 2 | 0 | 98.0% / 95% ✅ |
| OPC UA Server — Smoke    | Windows | ✅ 10 | 0 | Not Applicable |

---

### 🛡️ Code Quality

| Component | Lint | Type Check | Security | Dependencies |
|:----------|:-----|:----------:|:--------:|:------------:|
| Web Client     | ruff ✅ · eslint ⚠️ (1 warnings) | mypy ✅ | ✅ No issues | ✅ No issues |
| Console Client | ruff ✅ | mypy ✅ | ✅ No issues | Not Applicable |
| Node Client    | eslint ✅ | Not Applicable | Not Configured | ✅ No issues |
| C# Client      | build ✅ · format ✅ | Not Applicable | nuget ✅ | Not Applicable |
| Test Client    | ruff ✅ | mypy ✅ | ✅ No issues | Not Applicable |

---

### 🏗️ Infrastructure

| Check | Status |
|:------|:------:|
| Web Client — Docker Smoke (HTTP + WebSocket) | ✅ |
| GHA Workflow Lint (actionlint)               | ✅ |
| GHA Security Audit (zizmor)                  | ✅ |
| Pre-commit Hooks                             | ✅ |

---

> 📦 **Artifacts** — JUnit XML · Coverage XML · ESLint JSON · Bandit JSON &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down
> Coverage key: ✅ meets declared threshold &nbsp;·&nbsp; ⚠️ below threshold but ≥ 80% &nbsp;·&nbsp; ❌ < 80% &nbsp;·&nbsp; thresholds come from `pyproject.toml`, `vitest.config.mjs`, and the C# coverage gate

---

### ⏭️ Skip Details

<details><summary>⏭️ <b>Web Client — Python</b> — 2 skipped</summary>

| Reason | Count |
|:-------|------:|
| node_modules absent in split Python lane | 1 |
| eslint runs in JavaScript lane | 1 |

</details>

<details><summary>⏭️ <b>Node Client — JavaScript</b> — 1 skipped</summary>

| Reason | Count |
|:-------|------:|
| git unavailable in CI fixture | 1 |

</details>

<details><summary>⏭️ <b>C# Client — Unit</b> — 15 skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 14 |
| IJT_PHASE1_ONLY filter | 1 |

</details>
