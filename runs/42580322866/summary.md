## IJT OPC UA — CI

> ✅ **1 / 13 Jobs Passed · 0 Skipped**
> **Branch:** `main` &nbsp;·&nbsp; **Commit:** `38324e47` &nbsp;·&nbsp; **Run:** [#1330](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42580322866)

> Full report below: [Outcome](#ci-outcome-overview) · [Validation](#ci-validation-results) · [Code Quality](#ci-code-quality-checks) · [Security](#ci-source-dependency-security) · [Infrastructure](#ci-infrastructure) · [Timing](#ci-performance-timings) · [Skip Details](#ci-skip-details)

---

<a id="ci-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Coverage Warnings &nbsp;·&nbsp; 0 Skip-Budget Warnings &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome |  Count |
| :-: | :------ | -----: |
| ✅  | Passed  |  4,210 |
| ❌  | Failed  |      0 |
| ⏭️  | Skipped |      0 |
| 🧮  | Total   |  4,210 |
| 🛠️  | Jobs    | 1 / 13 |

---

<a id="ci-validation-results"></a>

### 🧪 Validation Results — 8 checks

| Component | Validation Scope | Test Cases | Skipped | Coverage / Threshold |
|:----------|:-----------------|----------:|--------:|:---------------------:|
| Web Client — Python | Ubuntu Release 2 Python unit suite | Not Reported | Not Reported | Not Reported |
| Web Client — JavaScript | Ubuntu Release 2 JavaScript unit suite | 783 Passed ✅ | 0 Skipped | 99.9% / 95% ✅ |
| Console Client — Python | Ubuntu Python unit suite | Not Reported | Not Reported | Not Reported |
| Performance Client — Python | Ubuntu Python unit suite | 400 Passed ✅ | 0 Skipped | 99.2% / 95% ✅ |
| Node Client — Legacy JavaScript | Ubuntu Release 1 JavaScript unit suite | 902 Passed ✅ | 0 Skipped | 99.4% / 95% ✅ |
| C# Client — Unit (xUnit) | Windows C# xUnit unit suite | Not Reported | Not Reported | Not Reported |
| Test Client — Python (Unit) | Ubuntu Python unit suite | 2,125 Passed ✅ | 0 Skipped | 99.9% / 95% ✅ |
| OPC UA Server — Smoke | Windows native server smoke check | Not Reported | Not Reported | ➖ Not Applicable |

---

<a id="ci-code-quality-checks"></a>

### 🧹 Code Quality Checks — 6 components

| 🚦 | Component | Validation Scope | Lint / Format | Type Check / Build |
|:--:|:----------|:-----------------|:--------------|:-------------------|
| 🚫 | Web Client | Python and JavaScript static quality | 🚫 ruff<br>✅ eslint | 🚫 mypy |
| ⏭️ | Console Client | Python static quality | ⏭️ ruff (Not Reported) | ⏭️ mypy (Not Reported) |
| 🚫 | Performance Client | Python static quality | ✅ ruff | 🚫 mypy |
| ⏭️ | Node Client — Legacy JavaScript | JavaScript static quality | ⏭️ eslint (Not Run) | ➖ Not Applicable |
| ⏭️ | C# Client | Build and formatting quality | ⏭️ build (Not Run)<br>⏭️ format (Not Run) | ➖ Not Applicable |
| ⏭️ | Test Client | Python static quality | ⏭️ ruff (Not Run) | ⏭️ mypy (Not Run) |

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
| ⏭️ | Console Client | ⏭️ bandit (Not Reported) | ⏭️ pip-audit (Not Reported) |
| ⏭️ | Node Client — Legacy JavaScript | ➖ Out of scope — legacy check | ⏭️ npm-audit (Not Reported) |
| 🚫 | C# Client | ℹ️ CodeQL source scan runs in Security workflow | 🚫 nuget |
| ⏭️ | Test Client | ⏭️ bandit (Not Reported) | ⏭️ pip-audit (Not Reported) |

---

<a id="ci-infrastructure"></a>

### ⚙️ CI Infrastructure — 4 checks

| Check | Status |
|:------|:------:|
| Web Client — Docker Smoke (HTTP + WebSocket) | 🚫 |
| GHA Workflow Lint (actionlint)               | 🚫 |
| GHA Security Audit (zizmor)                  | 🚫 |
| Pre-commit Hooks                             | 🚫 |

---

<a id="ci-performance-timings"></a>

### ⏱️ Timing

| Job | Duration | Status |
|:----|---------:|:-------|
| Web Client - Python | 41.0 s | Unknown ⚠️ |
| Node Client | 40.0 s | Unknown ⚠️ |
| OPC UA Server - Windows Smoke | 32.0 s | Unknown ⚠️ |
| Test Client | 32.0 s | Unknown ⚠️ |
| Performance Client | 30.0 s | Unknown ⚠️ |
| C# Client - NuGet Vuln Scan | 29.0 s | Unknown ⚠️ |
| Console Client | 27.0 s | Unknown ⚠️ |
| GHA Security Audit (zizmor) | 27.0 s | Unknown ⚠️ |
| GHA Workflow Lint (actionlint) | 27.0 s | Unknown ⚠️ |
| Pre-commit hooks (all files) | 27.0 s | Unknown ⚠️ |

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
Reports (no sign-in): [Runs](https://umati.github.io/UA-for-Industrial-Joining-Technologies/) · [CI](https://umati.github.io/UA-for-Industrial-Joining-Technologies/runs/42580322866/) · [System Tests](https://umati.github.io/UA-for-Industrial-Joining-Technologies/latest/integration/)
