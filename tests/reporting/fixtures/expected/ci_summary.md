## IJT OPC UA — CI

> ✅ **All 12 / 12 jobs passed**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `12345678` &nbsp;·&nbsp; **Run:** [#42](https://github.example/ijt/actions/runs/42)

---

<a id="ci-outcome-overview"></a>

### 📊 Outcome Overview

✅ Passed: 21 · ❌ Failed: 0 · ⏭️ Skipped: 18

| Outcome | Count |
|:--------|------:|
| Passed | 21 |
| Failed | 0 |
| Skipped | 18 |

---

<a id="ci-validation-results"></a>

### 🧪 Validation Results

| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |
|:----------|:-----------------|----------:|--------:|:---------------------:|
| Web Client — Python | Ubuntu Release 2 Python unit lane | ✅ 4 passed | 2 skipped | 97.0% / 95% ✅ |
| Web Client — JavaScript | Ubuntu Release 2 JavaScript unit lane | ✅ 3 passed | 0 skipped | 96.0% / 95% ✅ |
| Console Client — Python | Ubuntu Python unit lane | ✅ 2 passed | 0 skipped | 99.0% / 95% ✅ |
| Node Client — Legacy JavaScript | Ubuntu Release 1 JavaScript unit lane | ✅ 2 passed | 1 skipped | 95.0% / 95% ✅ |
| C# Client — Unit (xUnit) | Windows C# xUnit unit lane | ✅ 16 passed | 15 skipped | 95.0% / 95% ✅ |
| Test Client — Python (Unit) | Ubuntu Python unit lane | ✅ 2 passed | 0 skipped | 98.0% / 95% ✅ |
| OPC UA Server — Smoke | Windows native server smoke lane | ✅ 10 passed | 0 skipped | Not measured (smoke) |

---

<a id="ci-code-quality-checks"></a>

### 🧹 Code Quality Checks

| Component | Validation Scope | Lint / Format | Type Check / Build |
|:----------|:-----------------|:--------------|:-------------------|
| Web Client | Python and JavaScript static quality | ruff ✅ · eslint ⚠️ (1 warnings) | mypy ✅ |
| Console Client | Python static quality | ruff ✅ | mypy ✅ |
| Node Client — Legacy JavaScript | JavaScript static quality | eslint ✅ | Not Applicable |
| C# Client | Build and formatting quality | build ✅ · format ✅ | Not Applicable |
| Test Client | Python static quality | ruff ✅ | mypy ✅ |

---

<a id="ci-source-dependency-security"></a>

### 🔒 Source and Dependency Security

Static source analysis (bandit) and dependency vulnerability audit (pip-audit, npm-audit, nuget).

For workflow security see CI Infrastructure → zizmor; for secret scanning see Pre-commit Hooks → detect-secrets; for deep semantic analysis see the Security — CodeQL workflow.

| Component | Security Scan | Dependency Audit |
|:----------|:--------------|:-----------------|
| Web Client | bandit ✅ 0 issues | pip-audit ✅ 0 CVEs · npm-audit ✅ 0 critical |
| Console Client | bandit ✅ 0 issues | pip-audit ✅ 0 CVEs |
| Node Client — Legacy JavaScript | Not Configured (no eslint-plugin-security) | npm-audit ✅ 0 critical |
| C# Client | CodeQL source scan runs in Security workflow | nuget ✅ 0 vulnerable |
| Test Client | bandit ✅ 0 issues | pip-audit ✅ 0 CVEs |

---

<a id="ci-infrastructure"></a>

### ⚙️ CI Infrastructure

| Check | Status |
|:------|:------:|
| Web Client — Docker Smoke (HTTP + WebSocket) | ✅ |
| GHA Workflow Lint (actionlint)               | ✅ |
| GHA Security Audit (zizmor)                  | ✅ |
| Pre-commit Hooks                             | ✅ |

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

### ⏭️ Skip Details

<details><summary>⏭️ <b>Web Client — Python</b> — 2 skipped</summary>

| Reason | Count |
|:-------|------:|
| node_modules absent in Web Client - Python lane; chart.js vendoring is gated by sibling 'Web Client - JavaScript' lane | 1 |
| ESLint binary absent in Web Client - Python lane; JS lint is gated by sibling 'Web Client - JavaScript' lane | 1 |

</details>

<details><summary>⏭️ <b>Node Client — Legacy JavaScript</b> — 1 skipped</summary>

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

---

<a id="ci-per-client-quick-index"></a>

### Per-Client Quick Index

| Client / Component | Appears In |
|:-------------------|:-----------|
| Web Client | [Validation Results](#ci-validation-results); [Code Quality Checks](#ci-code-quality-checks); [Source and Dependency Security](#ci-source-dependency-security) |
| Console Client | [Validation Results](#ci-validation-results); [Code Quality Checks](#ci-code-quality-checks); [Source and Dependency Security](#ci-source-dependency-security) |
| Node Client — Legacy JavaScript | [Validation Results](#ci-validation-results); [Code Quality Checks](#ci-code-quality-checks); [Source and Dependency Security](#ci-source-dependency-security) |
| C# Client | [Validation Results](#ci-validation-results); [Code Quality Checks](#ci-code-quality-checks); [Source and Dependency Security](#ci-source-dependency-security) |
| Test Client | [Validation Results](#ci-validation-results); [Code Quality Checks](#ci-code-quality-checks); [Source and Dependency Security](#ci-source-dependency-security) |
| OPC UA Server | [Validation Results](#ci-validation-results); [CI Infrastructure](#ci-infrastructure) |
