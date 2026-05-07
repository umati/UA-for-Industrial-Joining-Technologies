/**
 * Full UI regression test.
 *
 * Covers the complete user journey in one test: connect → run all simulations →
 * Joint Demo cycle → verify Events → verify all three result types in the
 * Consolidated Result view.
 *
 * Requires:
 *   - Python backend running on WS_TEST_URL
 *   - OPC UA IJT Server running on OPCUA_TEST_ENDPOINT
 *
 * Run: npx playwright test --project=regression
 */
import { test, expect } from './e2e-fixtures.mjs'
import { RESULT_TYPE } from './page-objects.mjs'

test('full UI regression — connect, simulate, events, all result types', async ({ connected: app }) => {
  test.setTimeout(240_000)

  // ── 1. Simulate all four result/event types ─────────────────────────────
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.runAllSimulations()

  // ── 2. Joint demo cycle ─────────────────────────────────────────────────
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })
  await demo.runFullDemoCycle()

  // ── 3. Events tab — must show ResultEvent entries ───────────────────────
  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 60_000 })

  const count = await events.getEventCount()
  expect(count).toBeGreaterThan(0)

  const hasResult = await events.hasEventContaining('ResultEvent')
  expect(hasResult, 'Expected at least one ResultEvent in the events list').toBe(true)

  // ── 4. Consolidated Result — Single tightenings ──────────────────────────
  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })

  await results.selectResultType(RESULT_TYPE.TIGHTENING)
  const singleCount = await results.getResultOptionCount()
  expect(singleCount, 'Expected ≥ 4 single-result options (Unresolved+Latest+results)').toBeGreaterThanOrEqual(4)

  await results.selectResult(RESULT_TYPE.LATEST)
  await results.waitForResultBox({ timeout: 60_000 })
  const tighteningNodes = await results.countResultNodes('.resTightening')
  expect(tighteningNodes).toBeGreaterThanOrEqual(1)

  // ── 5. Consolidated Result — Job results with nested tree ────────────────
  await results.selectResultType(RESULT_TYPE.JOB)
  const jobCount = await results.getResultOptionCount()
  expect(jobCount, 'Expected ≥ 3 job-result options').toBeGreaterThanOrEqual(3)

  await results.selectResult(RESULT_TYPE.LATEST)
  await results.waitForResultBox({ timeout: 60_000 })
  const jobNodes = await results.countResultNodes('.resJob')
  expect(jobNodes, 'Job result should contain nested .resJob nodes').toBeGreaterThanOrEqual(1)

  // ── 6. Consolidated Result — Batch results ───────────────────────────────
  await results.selectResultType(RESULT_TYPE.BATCH)
  const batchCount = await results.getResultOptionCount()
  // Batch simulation was called — at least Unresolved + Latest + 1 batch
  expect(batchCount).toBeGreaterThanOrEqual(3)
})
