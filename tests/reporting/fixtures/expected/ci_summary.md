## IJT OPC UA — CI

> ✅ **All 12 / 12 Jobs Passed**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `12345678` &nbsp;·&nbsp; **Run:** [#42](https://github.example/ijt/actions/runs/42)

> Full report below: [Outcome](#ci-outcome-overview) · [Validation](#ci-validation-results) · [Code Quality](#ci-code-quality-checks) · [Security](#ci-source-dependency-security) · [Infrastructure](#ci-infrastructure) · [Timing](#ci-performance-timings) · [Skip Details](#ci-skip-details)

---

<a id="ci-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Coverage Warnings &nbsp;·&nbsp; 0 Skip-Budget Warnings &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome |   Count |
| :-: | :------ | ------: |
| ✅  | Passed  |      21 |
| ❌  | Failed  |       0 |
| ⏭️  | Skipped |      18 |
| 🧮  | Total   |      39 |
| 🛠️  | Jobs    | 12 / 12 |

---

<a id="ci-validation-results"></a>

### 🧪 Validation Results — 7 checks

| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |
|:----------|:-----------------|----------:|--------:|:---------------------:|
| Web Client — Python | Ubuntu Release 2 Python unit suite | 2 Passed ✅ | 2 Skipped | 97.0% / 95% ✅ |
| Web Client — JavaScript | Ubuntu Release 2 JavaScript unit suite | 3 Passed ✅ | 0 Skipped | 96.0% / 95% ✅ |
| Console Client — Python | Ubuntu Python unit suite | 2 Passed ✅ | 0 Skipped | 99.0% / 95% ✅ |
| Node Client — Legacy JavaScript | Ubuntu Release 1 JavaScript unit suite | 1 Passed ✅ | 1 Skipped | 95.0% / 95% ✅ |
| C# Client — Unit (xUnit) | Windows C# xUnit unit suite | 1 Passed ✅ | 15 Skipped | 95.0% / 95% ✅ |
| Test Client — Python (Unit) | Ubuntu Python unit suite | 2 Passed ✅ | 0 Skipped | 98.0% / 95% ✅ |
| OPC UA Server — Smoke | Windows native server smoke check | 10 Passed ✅ | 0 Skipped | ➖ Not Applicable |

---

<a id="ci-code-quality-checks"></a>

### 🧹 Code Quality Checks — 5 components

| 🚦 | Component | Validation Scope | Lint / Format | Type Check / Build |
|:--:|:----------|:-----------------|:--------------|:-------------------|
| ⚠️ | Web Client | Python and JavaScript static quality | ✅ ruff<br>⚠️ eslint (1 warnings) | ✅ mypy |
| ✅ | Console Client | Python static quality | ✅ ruff | ✅ mypy |
| ✅ | Node Client — Legacy JavaScript | JavaScript static quality | ✅ eslint | ➖ Not Applicable |
| ✅ | C# Client | Build and formatting quality | ✅ build<br>✅ format | ➖ Not Applicable |
| ✅ | Test Client | Python static quality | ✅ ruff | ✅ mypy |

---

<a id="ci-source-dependency-security"></a>

### 🔒 Source and Dependency Security — 5 components

- **Audit and Code Scanning**
  - Bandit scans Python source for security issues.
  - pip-audit, npm audit, and NuGet audit scan package dependencies for known vulnerabilities.
- **Related Security Checks**
  - CI Infrastructure runs zizmor for GitHub Actions workflow security.
  - Pre-commit Hooks runs detect-secrets for committed secret detection.
  - Security — CodeQL runs semantic code analysis.

| 🚦 | Component | Security Scan | Dependency Audit |
|:--:|:----------|:--------------|:-----------------|
| ✅ | Web Client | ✅ bandit (0 issues) | ✅ pip-audit (0 CVEs)<br>✅ npm-audit (0 critical) |
| ✅ | Console Client | ✅ bandit (0 issues) | ✅ pip-audit (0 CVEs) |
| ✅ | Node Client — Legacy JavaScript | ➖ Out of scope — legacy check | ✅ npm-audit (0 critical) |
| ✅ | C# Client | ℹ️ CodeQL source scan runs in Security workflow | ✅ nuget (0 vulnerable) |
| ✅ | Test Client | ✅ bandit (0 issues) | ✅ pip-audit (0 CVEs) |

---

<a id="ci-infrastructure"></a>

### ⚙️ CI Infrastructure — 4 checks

| Check | Status |
|:------|:------:|
| Web Client — Docker Smoke (HTTP + WebSocket) | ✅ |
| GHA Workflow Lint (actionlint)               | ✅ |
| GHA Security Audit (zizmor)                  | ✅ |
| Pre-commit Hooks                             | ✅ |

---

<a id="ci-performance-timings"></a>

### ⏱️ Timing

No reliable job duration source was available. Job durations require the current-run Jobs API.

---

<a id="ci-raw-data"></a>

### Where to find raw data

- JUnit XML
- Coverage XML
- ESLint JSON
- Bandit JSON
- pip-audit / npm-audit JSON
- Per-test drill-down: Checks tab

<a id="ci-coverage-legend"></a>

### Coverage Legend

| Icon | Meaning |
|:-----|:--------|
| ✅ | Meets the declared threshold |
| ⚠️ | Below threshold but at least 80% |
| ❌ | Below 80% |

Thresholds come from `pyproject.toml`, `vitest.config.mjs`, and the C# coverage gate.

---

<a id="ci-skip-details"></a>

### ⏭️ Skip Details — 3 suites, 18 skips

<details><summary>⏭️ <b>Web Client — Python</b> — 2 Skipped</summary>

| Reason | Count |
|:-------|------:|
| node_modules absent in Web Client - Python check. chart.js vendoring is gated by sibling 'Web Client - JavaScript' check | 1 |
| ESLint binary absent in Web Client - Python check. JS lint is gated by sibling 'Web Client - JavaScript' check | 1 |

</details>

<details><summary>⏭️ <b>Node Client — Legacy JavaScript</b> — 1 Skipped</summary>

| Reason | Count |
|:-------|------:|
| git unavailable in CI fixture | 1 |

</details>

<details><summary>⏭️ <b>C# Client — Unit</b> — 15 Skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 14 |
| IJT_PHASE1_ONLY filter | 1 |

</details>

---

<a id="ci-per-client-quick-index"></a>

### 📚 Per-Client Quick Index — 6 entries

| Client / Component | Appears In |
|:-------------------|:-----------|
| Web Client | [Validation Results](#ci-validation-results) · [Code Quality Checks](#ci-code-quality-checks) · [Source and Dependency Security](#ci-source-dependency-security) · [Timing](#ci-performance-timings) |
| Console Client | [Validation Results](#ci-validation-results) · [Code Quality Checks](#ci-code-quality-checks) · [Source and Dependency Security](#ci-source-dependency-security) · [Timing](#ci-performance-timings) |
| Node Client — Legacy JavaScript | [Validation Results](#ci-validation-results) · [Code Quality Checks](#ci-code-quality-checks) · [Source and Dependency Security](#ci-source-dependency-security) · [Timing](#ci-performance-timings) |
| C# Client | [Validation Results](#ci-validation-results) · [Code Quality Checks](#ci-code-quality-checks) · [Source and Dependency Security](#ci-source-dependency-security) · [Timing](#ci-performance-timings) |
| Test Client | [Validation Results](#ci-validation-results) · [Code Quality Checks](#ci-code-quality-checks) · [Source and Dependency Security](#ci-source-dependency-security) · [Timing](#ci-performance-timings) |
| OPC UA Server | [Validation Results](#ci-validation-results) · [CI Infrastructure](#ci-infrastructure) · [Timing](#ci-performance-timings) |
