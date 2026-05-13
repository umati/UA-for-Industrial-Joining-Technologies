# Conformance Renderer Tests

Byte-identity regression tests for the conformance summary renderer
(`scripts/reporting/conformance_summary.py`).

The byte-identity test
([`test_render_conformance_summary.py`](test_render_conformance_summary.py))
calls `render_conformance_summary(...)` against each fixture under
[`fixtures/`](fixtures/) and asserts that the produced Markdown matches
the corresponding file under [`fixtures/expected/`](fixtures/expected/)
**byte-for-byte**. This test is the regression oracle that locks the
renderer's output during refactors.

> Audience: contributors who modify the renderer or refresh fixtures.
> End users of the IJT Test Client never need this directory.

## Determinism inputs

The byte-identity test calls the renderer with frozen inputs (kept in
sync with the regenerator, [`_capture_expected_summaries.py`](_capture_expected_summaries.py)):

| Input | Value | Why frozen |
|---|---|---|
| `run_ts` | `2026-05-13 14:00 UTC` | Avoids `datetime.now()` injection |
| `server_url` | `opc.tcp://fixture.ijt.test:40451` | Avoids env leak from `OPCUA_SERVER_URL` |

If the renderer ever starts reading another non-deterministic input,
this README and the test must be updated together.

## Fixtures

### `ci_unit_no_cu_payload/`

**Scenario:** Renderer's **degraded path** — a CI unit pytest run where no
`cu_results.json` is produced. The renderer must fall back to a minimal
summary that doesn't reference any CU compliance data.

This fixture's only job is to lock the no-CU-payload path. It is **not**
a complete branch-coverage oracle for the renderer.

| File | Origin | Purpose |
|---|---|---|
| `pytest.xml` | extracted verbatim from the `results-test-client` artifact of GitHub Actions run id `25794958154` (`ci.yml` / Test Client unit job, captured 2026-05-13) | JUnit input to `render_conformance_summary(...)` |

`cu_results.json` and `baseline.json` are **deliberately absent** — that
absence is the entire point of this scenario.

### `system_tests_full_conformance/`

**Scenario:** Renderer's **full path** — a System Tests live conformance
run with the complete CU compliance payload and a previous baseline.
This is the **canonical real-world conformance regression fixture** for
the renderer: it exercises authentic scale, profile/facet rollups, the Δ
Since Last Run delta path, not-supported handling, with-notes / partial
outcomes, truncation, and the full CU coverage table.

This fixture is **not** a complete branch-coverage oracle. Targeted
Action Needed / Blocked / error-path tests remain the responsibility of
small dedicated fixtures (added in Phase 4 when branch semantics get
their own coverage lens).

| File | Origin | Purpose |
|---|---|---|
| `pytest.xml` | extracted from `results-testclient` artifact of GitHub Actions run id `25794967225` (`integration.yml`, captured 2026-05-13) | JUnit input |
| `cu_results.json` | from a representative local conformance run (the upstream artifact did not contain `cu-compliance-report.json`); coherent with the `baseline.json` below | per-CU compliance payload |
| `baseline.json` | from the same local conformance run as `cu_results.json` | enables the Δ Since Last Run block |

**Coherence note.** The upstream GitHub Actions artifact for run
`25794967225` only included `pytest.xml`. The conformance JSON files
(`cu-compliance-report.json` and `report-baseline.json`) are not
currently uploaded by the workflow. To get a coherent fixture set, the
JSON files were taken from a representative local conformance run in
the same Phase 1 implementation context. They are internally consistent
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
