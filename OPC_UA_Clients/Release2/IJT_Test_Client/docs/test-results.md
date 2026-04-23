# Test Results Guide

This document explains how to read test reports and what each test status means.

## Report Locations

After a `run_all_tests.py` run the following files are produced:

| File | Format | Contents |
|---|---|---|
| `test-results/pytest-live.xml` | JUnit XML | Live test results from `run_all_tests.py` Phase 2 (default XML input for Excel) |
| `test-results/pytest-unit.xml` | JUnit XML | Unit test results from `run_all_tests.py` Phase 1 |
| `test-results/report.xlsx` | Excel | Human-readable coloured summary by test area, full detail, filtered views |
| `test-results/smoke-sanity.xml` | JUnit XML | Quick server reachability smoke test (CI only) |

> `report.html` is **not** produced by `run_all_tests.py`. Use the manual `pytest --html=...` command below if you need an HTML report.

In CI, report files are uploaded as run artifacts.

---

## How to Generate Reports Locally

**Run tests and produce XML + HTML:**
```bash
python -m pytest conformance/ assets/ joining_process/ results/ joint/ events/ common/ \
  -v --tb=short -rs --timeout=120 \
  --junitxml=test-results/pytest-live.xml \
  --html=test-results/report.html --self-contained-html
```

**Generate Excel from XML:**
```bash
python scripts/make_excel_report.py --xml test-results/pytest-live.xml --out test-results/report.xlsx
# or with custom paths:
python scripts/make_excel_report.py --xml test-results/pytest-live.xml --out test-results/custom-report.xlsx
```

**Generate Excel automatically from `run_all_tests.py` (non-fatal post-step):**
```bash
# default local behavior: generate only when tests pass
python run_all_tests.py

# always generate (recommended when end users consume Excel)
python run_all_tests.py --excel=always

# custom Excel output path
python run_all_tests.py --excel=always --excel-out test-results/my-report.xlsx
```

---

## Excel Workbook Sheets

| Sheet | Contents |
|---|---|
| **Summary** | Total counts (passed/failed/skipped/xfailed) by test area |
| **All Tests** | Every test: name, file, status, duration, reason |
| **Failures (N)** | Failed tests only — with full failure message |
| **Skipped (N)** | Skipped tests only — with skip reason |
| **Expected Fail (N)** | Xfailed/xpassed — expected failures with reason |

Row colours: 🟢 green = passed, 🔴 red = failed, 🟡 yellow = skipped, 🟠 orange = xfailed.

---

## Test Status Meanings

| Status | Meaning |
|---|---|
| **PASSED** | Test ran and all assertions succeeded |
| **FAILED** | Test ran and at least one assertion failed — this is a real problem |
| **SKIPPED** | Test was not run — always has a documented reason (see table below) |
| **XFAILED** | Test was expected to fail and did — a known server limitation, not a bug |
| **XPASSED** | Test was expected to fail but passed — server has improved; update the xfail mark |
| **ERROR** | Test crashed before reaching assertions — likely a setup or connection issue |

---

## Skip Reason Categories

| Category | Example Reason | Meaning |
|---|---|---|
| Optional method absent | `SetCalibration method not present — optional per spec` | Server does not implement an optional OPC UA method; skip is correct |
| Optional field absent | `DeviceHealth not present — optional DI field` | Server omits an optional Device Information field |
| Simulator PIU not validated | `Server returned Good for unknown ProductInstanceUri` | Simulator accepts any PIU; real servers reject unknown ones |
| Trace data absent | `No trace values in result` | Server/device did not populate `JoiningResultDataType.Trace` for this run; verify trigger settings (`includeTraces`) and server profile |
| Missing prerequisite | `SetCalibration absent — cannot test downstream behaviour` | Cascading skip: an earlier optional feature was absent |
| Namespace absent | `App namespace not registered` | Server does not expose the simulation namespace (expected for non-simulators) |
| Event not triggered | `No JoiningProcessStartedEvent received within timeout` | Optional event was not fired; real controllers may not fire these |

**What is NOT a valid skip reason:**
- Method call returned an error (method IS present) → use `pytest.fail`
- Timing race / stale result after trigger → retry up to 4× then `pytest.fail` (real server) or `return None` → caller `pytest.skip` (known simulator limitation)
- Wrong result type returned after trigger → retry up to 4× then: real server = `pytest.fail`; simulator = `return None` (caller skips)

---

## Expected Failure (Xfail) Reasons

Do not keep permanent `xfail` markers for behavior that is now implemented.
If a previously xfailed test starts passing, remove the marker immediately and
convert it back to a normal pass/fail test.

---

## CI Nightly Run

The CI nightly job (`int-testclient`) runs at 2am UTC and produces a `results-testclient` artifact.

To view results after a CI run:
1. Go to the **Actions** tab on GitHub
2. Click **Integration** → most recent nightly run
3. Click **results-testclient** in the Artifacts section
4. Download and open `report.xlsx`

If the job is red: check the `Failures (N)` sheet in the Excel report for full failure messages.
