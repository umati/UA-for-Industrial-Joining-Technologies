## IJT OPC UA — CI

> ✅ **All 13 / 13 Jobs Passed**
> **Branch:** `main` &nbsp;·&nbsp; **Commit:** `a8c59a75` &nbsp;·&nbsp; **Run:** [#1355](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42981053149)

> Full report below: [Outcome](#ci-outcome-overview) · [Validation](#ci-validation-results) · [Code Quality](#ci-code-quality-checks) · [Security](#ci-source-dependency-security) · [Infrastructure](#ci-infrastructure) · [Timing](#ci-performance-timings) · [Skip Details](#ci-skip-details)

---

<a id="ci-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Coverage Warnings &nbsp;·&nbsp; 0 Skip-Budget Warnings &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome |   Count |
| :-: | :------ | ------: |
| ✅  | Passed  |   6,841 |
| ❌  | Failed  |       0 |
| ⏭️  | Skipped |       0 |
| 🧮  | Total   |   6,841 |
| 🛠️  | Jobs    | 13 / 13 |

---

<a id="ci-validation-results"></a>

### 🧪 Validation Results — 8 checks

| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |
|:----------|:-----------------|----------:|--------:|:---------------------:|
| Web Client — Python | Ubuntu Release 2 Python unit suite | 906 Passed ✅ | 0 Skipped | 98.7% / 95% ✅ |
| Web Client — JavaScript | Ubuntu Release 2 JavaScript unit suite | 783 Passed ✅ | 0 Skipped | 99.9% / 95% ✅ |
| Console Client — Python | Ubuntu Python unit suite | 652 Passed ✅ | 0 Skipped | 98.7% / 95% ✅ |
| Performance Client — Python | Ubuntu Python unit suite | 400 Passed ✅ | 0 Skipped | 99.2% / 95% ✅ |
| Node Client — Legacy JavaScript | Ubuntu Release 1 JavaScript unit suite | 902 Passed ✅ | 0 Skipped | 99.4% / 95% ✅ |
| C# Client — Unit (xUnit) | Windows C# xUnit unit suite | 1,063 Passed ✅ | 0 Skipped | 99.0% / 95% ✅ |
| Test Client — Python (Unit) | Ubuntu Python unit suite | 2,125 Passed ✅ | 0 Skipped | 99.9% / 95% ✅ |
| OPC UA Server — Smoke | Windows native server smoke check | 10 Passed ✅ | 0 Skipped | ➖ Not Applicable |

---

<a id="ci-code-quality-checks"></a>

### 🧹 Code Quality Checks — 6 components

| 🚦 | Component | Validation Scope | Lint / Format | Type Check / Build |
|:--:|:----------|:-----------------|:--------------|:-------------------|
| ✅ | Web Client | Python and JavaScript static quality | ✅ ruff<br>✅ eslint | ✅ mypy |
| ✅ | Console Client | Python static quality | ✅ ruff | ✅ mypy |
| ✅ | Performance Client | Python static quality | ✅ ruff | ✅ mypy |
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
  - Pre-commit Hooks runs zizmor (High+) for workflow security on every PR.
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

| Job | Duration | Status |
|:----|---------:|:-------|
| Web Client - Docker Smoke | 3.1 min | Success ✅ |
| C# Client - Unit Tests | 3.0 min | Success ✅ |
| Web Client - Python | 1.6 min | Success ✅ |
| C# Client - NuGet Vuln Scan | 1.4 min | Success ✅ |
| Pre-commit hooks (all files) | 1.1 min | Success ✅ |
| Console Client | 50.0 s | Success ✅ |
| Test Client | 48.0 s | Success ✅ |
| OPC UA Server - Windows Smoke | 42.0 s | Success ✅ |
| Web Client - JavaScript | 33.0 s | Success ✅ |
| Performance Client | 30.0 s | Success ✅ |

---

<a id="ci-raw-data"></a>

### Where to find raw data

- JUnit XML
- Coverage XML
- ESLint JSON
- Bandit JSON
- pip-audit / npm-audit JSON
- Failed-test detail: Failed Tests section of this summary

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

### ⏭️ Skip Details — 0 suites, 0 skips

No skipped tests reported.

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

---
Reports (no sign-in): [Runs](https://umati.github.io/UA-for-Industrial-Joining-Technologies/) · [CI](https://umati.github.io/UA-for-Industrial-Joining-Technologies/runs/42981053149/) · [System Tests](https://umati.github.io/UA-for-Industrial-Joining-Technologies/latest/integration/)
