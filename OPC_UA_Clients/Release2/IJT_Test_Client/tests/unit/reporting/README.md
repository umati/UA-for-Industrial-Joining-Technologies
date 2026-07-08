# Specification Test Renderer Tests

Byte-identity regression tests for the specification test summary renderer
(`scripts/reporting/specification_test_summary.py`).

The byte-identity test
([`test_render_specification_test_summary.py`](test_render_specification_test_summary.py))
calls `render_specification_test_summary(...)` against each fixture under
[`fixtures/`](fixtures/) and asserts that the produced Markdown matches
the corresponding file under [`fixtures/expected/`](fixtures/expected/)
**byte-for-byte**. This test is the regression oracle that locks the
renderer's output during refactors.

> Audience: contributors who modify the renderer or refresh fixtures.
> End users of the IJT Test Client never need this directory.

## Determinism inputs

The byte-identity test calls the renderer with frozen inputs taken from
[`_frozen_env.py`](_frozen_env.py), which is also imported by the
regenerator ([`_capture_expected_summaries.py`](_capture_expected_summaries.py))
so both sides cannot drift:

| Input | Value | Why frozen |
|---|---|---|
| `run_ts` | `2026-05-13 14:00 UTC` | Avoids `datetime.now()` injection into the rendered header |
| `server_url` | `opc.tcp://fixture.ijt.test:40451` | Avoids env leak from `OPCUA_SERVER_URL` |
| `report_environment` | `FROZEN_ENV` (a `ReportEnvironment` instance) | Bundles every runtime-derived value the renderer would otherwise read live: short git SHA, Python version, `asyncua` version, host OS string, `GITHUB_*` run-logs URL, and `now_utc` for age math. Production callers leave the kwarg as `None` and the renderer captures these via `ReportEnvironment.from_runtime()`. |

The renderer routes **every** runtime-derived value through the
`ReportEnvironment` seam (no `datetime.now()`, `platform.*`,
`importlib.metadata`, git, or `os.environ.get("GITHUB_*")` calls outside
that seam). Two companion tests in
[`test_render_specification_test_summary.py`](test_render_specification_test_summary.py)
guard the seam:

- `test_renderer_ignores_live_environment_when_frozen_env_passed` —
  monkeypatches every live-state reader to a sentinel and asserts the
  output stays byte-identical to the expected fixture. Any future
  bypass of the seam fails this test.
- `test_runtime_report_environment_reads_live_state` —
  asserts `ReportEnvironment.from_runtime()` actually reads the
  patched live values, so the seam is not a no-op.

If the renderer ever needs to consume a new runtime-derived input, add
it to `ReportEnvironment` (with a `from_runtime` capture), update
`_frozen_env.FROZEN_ENV` with a frozen value, and update this README in
the same commit.

## Fixtures

### `ci_unit_no_cu_payload/`

**Scenario:** Renderer's **degraded path** — a CI unit pytest run where no
`cu_results.json` is produced. The renderer must fall back to a minimal
summary that doesn't reference any CU coverage data.

This fixture's only job is to lock the no-CU-payload path. It is **not**
a complete branch-coverage oracle for the renderer.

| File | Origin | Purpose |
|---|---|---|
| `pytest.xml` | extracted verbatim from the `results-test-client` artifact of GitHub Actions run id `25794958154` (`ci.yml` / Test Client unit job, captured 2026-05-13) | JUnit input to `render_specification_test_summary(...)` |

`cu_results.json` and `baseline.json` are **deliberately absent** — that
absence is the entire point of this scenario.

### `system_tests_full_specification_coverage/`

**Scenario:** Renderer's **full path** — a System Tests live specification test run with the complete CU coverage payload and a baseline file present.
This is the **canonical real-world specification test regression fixture** for
the renderer: it exercises authentic scale, profile/facet groups,
not-supported handling, with-notes / partial outcomes, truncation, and
the action-first CUs Needing Review table. The Markdown summary shows
review-needed CUs first, then the short IJT Facet Support summary, then
the collapsed IJT Facet Breakdown. Full CU detail remains in Excel.

This fixture is **not** a complete branch-coverage oracle. Targeted
Failed / Blocked / error-path tests remain the responsibility of small
dedicated fixtures when branch semantics need their own coverage lens.

| File | Origin | Purpose |
|---|---|---|
| `pytest.xml` | extracted from `results-testclient` artifact of GitHub Actions run id `25794967225` (`integration.yml`, captured 2026-05-13) | JUnit input |
| `cu_results.json` | from a representative local specification test run (the upstream artifact did not contain `cu-coverage-report.json`); coherent with the `baseline.json` below | per-CU coverage payload |
| `baseline.json` | from the same local specification test run as `cu_results.json` | satisfies the renderer's optional `baseline` kwarg; not consumed by the renderer (no baseline-driven UI) |

**Coherence note.** The upstream GitHub Actions artifact for run
`25794967225` only included `pytest.xml`. The specification test JSON files
(`cu-coverage-report.json` and `report-baseline.json`) are not
currently uploaded by the workflow. To get a coherent fixture set, the
JSON files were taken from a representative local specification test run that
shares the same renderer implementation context. They are internally consistent
with each other; the `pytest.xml` is shape-compatible (same suite/test
ids). If/when the workflow uploads JSON artifacts, re-capture this
fixture from one CI run so all inputs share a single provenance source.

`cu_results.json` is ~2.3 MB; regenerating creates a same-size delta in
git history. Only refresh when truly needed.

## How to refresh

Only refresh when an intentional renderer change requires it:

```powershell
cd OPC_UA_Clients/Release2/IJT_Test_Client
python tests/unit/reporting/_capture_expected_summaries.py
```

Then review the diff against the matching files under
`fixtures/expected/` before committing.

## Why directory names don't include the run id

The run id is provenance metadata, not part of the test contract.
Naming the directory by scenario keeps it stable across refreshes —
only this README changes when the source run changes.
