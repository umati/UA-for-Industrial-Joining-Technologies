# Test Results Guide

This document explains how to read test reports and what each test status means.

## Report Locations

After a test run the following files are produced:

| File | Format | Contents |
|---|---|---|
| `test-results/pytest.xml` | JUnit XML | Machine-readable results (used by CI and the Excel generator) |
| `test-results/report.xlsx` | Excel | Human-readable coloured summary by test area, full detail, filtered views |
| `test-results/report.html` | HTML | In-browser report (open in any browser, no server needed) |
| `test-results/smoke-sanity.xml` | JUnit XML | Quick server reachability smoke test (CI only) |

In CI, all four files are uploaded as the `results-testclient` artifact at the end of each run.

---

## How to Generate Reports Locally

**Run tests and produce XML + HTML:**
```bash
python -m pytest conformance/ assets/ joining_process/ results/ joint/ events/ common/ \
  -v --tb=short -rs --timeout=120 \
  --junitxml=test-results/pytest.xml \
  --html=test-results/report.html --self-contained-html
```

**Generate Excel from XML:**
```bash
python scripts/make_excel_report.py
# or with custom paths:
python scripts/make_excel_report.py --xml test-results/pytest.xml --out test-results/report.xlsx
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
| Trace data absent | `No trace values in result — simulator does not populate trace data` | Simulator never includes trace data in results |
| Missing prerequisite | `SetCalibration absent — cannot test downstream behaviour` | Cascading skip: an earlier optional feature was absent |
| Namespace absent | `App namespace not registered` | Server does not expose the simulation namespace (expected for non-simulators) |
| Event not triggered | `No JoiningProcessStartedEvent received within timeout` | Optional event was not fired; real controllers may not fire these |

---

## Expected Failure (Xfail) Reasons

All current xfail tests are in `assets/test_asset_interfaces.py` and `assets/test_asset_associations.py`.

| Xfail area | Reason |
|---|---|
| `HasInterface` references | The server does not emit `HasInterface` references on asset instance nodes for interface types (IControllerType, IToolType, etc.). This is a server-side gap, not a spec violation. Tests will auto-promote to passing once the server adds these references. |
| `AssociatedWith` references | The server does not expose symmetric `AssociatedWith` references between asset nodes. Same root cause as above. |

---

## CI Nightly Run

The CI nightly job (`int-testclient`) runs at 2am UTC and produces a `results-testclient` artifact.

To view results after a CI run:
1. Go to the **Actions** tab on GitHub
2. Click **CI Extended** → most recent nightly run
3. Click **results-testclient** in the Artifacts section
4. Download and open `report.xlsx` or `report.html`

If the job is red: check the `Failures (N)` sheet in the Excel report for full failure messages.
