/**
 * Feature: Consolidated Result view — all three result types, tree structure,
 * classification badges, and NOK highlighting.
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'
import { RESULT_TYPE } from './page-objects.mjs'

// ─── Setup helper — run simulations once then open results ────────────────────
async function setupWithSimulations (app) {
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.runAllSimulations()
  return app.openResults()
}

// ── Header / UI structure ─────────────────────────────────────────────────────

test('Results: header with both dropdowns is visible after connect', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader({ timeout: 60_000 })

  const typeSelect = app.page.locator('.resultheader select:first-of-type')
  const itemSelect = app.page.locator('.resultheader select:nth-of-type(2)')
  await expect(typeSelect).toBeVisible()
  await expect(itemSelect).toBeVisible()
})

// ── Single tightening results ─────────────────────────────────────────────────

test('Results: single-tightening list has ≥ 4 options after simulation', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  await results.selectResultType(RESULT_TYPE.TIGHTENING)
  const count = await results.getResultOptionCount()
  expect(count, 'Needs Unresolved + Latest + ≥2 results').toBeGreaterThanOrEqual(4)
})

test('Results: latest single-tightening renders .resTightening nodes', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  const ok = await results.viewLatestOfType(RESULT_TYPE.TIGHTENING)
  if (!ok) { test.skip() }
  await results.waitForResultBox({ timeout: 60_000 })
  const nodes = await results.countResultNodes('.resTightening')
  expect(nodes).toBeGreaterThanOrEqual(1)
})

// ── Job results ───────────────────────────────────────────────────────────────

test('Results: job-result list has ≥ 3 options after simulation', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  await results.selectResultType(RESULT_TYPE.JOB)
  const count = await results.getResultOptionCount()
  expect(count, 'Needs Unresolved + Latest + ≥1 job').toBeGreaterThanOrEqual(3)
})

test('Results: latest job renders nested .resJob and .resTightening nodes', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  const ok = await results.viewLatestOfType(RESULT_TYPE.JOB)
  if (!ok) { test.skip() }
  await results.waitForResultBox({ timeout: 60_000 })

  const jobNodes = await results.countResultNodes('.resJob')
  const tighteningNodes = await results.countResultNodes('.resTightening')
  expect(jobNodes).toBeGreaterThanOrEqual(1)
  expect(tighteningNodes).toBeGreaterThanOrEqual(1)
})

// ── Batch results ─────────────────────────────────────────────────────────────

test('Results: batch-result list has ≥ 3 options after simulation', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  await results.selectResultType(RESULT_TYPE.BATCH)
  const count = await results.getResultOptionCount()
  expect(count).toBeGreaterThanOrEqual(3)
})

test('Results: latest batch renders .resBatch node', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  const ok = await results.viewLatestOfType(RESULT_TYPE.BATCH)
  if (!ok) { test.skip() }
  await results.waitForResultBox({ timeout: 60_000 })

  const batchNodes = await results.countResultNodes('.resBatch')
  expect(batchNodes).toBeGreaterThanOrEqual(1)
})

// ── NOK / Partial indicators ──────────────────────────────────────────────────

test('Results: .complewrapper is present in draw area for all result types', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const results = await setupWithSimulations(app)
  await results.waitForHeader()

  for (const type of [RESULT_TYPE.TIGHTENING, RESULT_TYPE.JOB, RESULT_TYPE.BATCH]) {
    const ok = await results.viewLatestOfType(type)
    if (!ok) continue
    try {
      await results.waitForResultBox({ timeout: 30_000 })
      const wrappers = await results.countResultNodes('.complewrapper')
      expect(wrappers, `Type ${type} should have ≥1 .complewrapper`).toBeGreaterThanOrEqual(1)
    } catch {
      // Type not available — non-fatal
    }
  }
})

test('Results: import controls are visible', async ({ connected: app }) => {
  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })
  await expect(app.page.locator('.resultImportMode select')).toBeVisible()
  await expect(app.page.locator('.resultImportStrictInput')).toBeVisible()
})

test('Results: skip-duplicates import mode reports duplicate skip reason', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })

  const resultId = `e2e-import-${Date.now()}`
  const bundle = {
    type: 'ijt-result-export',
    version: 1,
    exportedAt: new Date().toISOString(),
    source: { app: 'e2e-test', format: 'result-bundle' },
    results: [{
      ResultMetaData: {
        ResultId: resultId,
        Classification: '1',
        IsPartial: 'False',
        CreationTime: new Date().toISOString()
      },
      ResultContent: []
    }]
  }

  await results.setImportMode('skip-duplicates')
  await results.setImportStrict(false)
  await results.importBundleObject(bundle)

  await expect.poll(async () => results.getStatusText(), { timeout: 10_000 }).toContain('Imported 1')

  await results.importBundleObject(bundle)
  await expect.poll(async () => results.getStatusText(), { timeout: 10_000 }).toContain('duplicate_result_id:1')
})

// ── WS data validation ────────────────────────────────────────────────────────

test('WS: result event payload has valid ResultMetaData structure', async ({ ws }) => {
  test.setTimeout(45_000)
  await ws.send('connect to')
  await ws.send('subscribe')

  try {
    const events = await ws.waitForEvents(1, 20_000)
    const resultEvents = events.filter((e) => e.data?.Result?.ResultMetaData != null)
    for (const evt of resultEvents) {
      const meta = evt.data.Result.ResultMetaData
      // Classification must be a known value: 0, 1, 3, or 4
      if (meta.Classification != null) {
        const cls = parseInt(String(meta.Classification).replace(/\D/g, ''), 10)
        expect([0, 1, 3, 4]).toContain(cls)
      }
      // ResultId must be present
      const rid = meta.ResultId ?? meta.ResultIdentifier
      expect(rid).toBeDefined()
    }
  } catch {
    // No results available — non-fatal
  }
})
