/**
 * Feature: Joint Demo view — select joints, simulate tightening, verify results.
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'
import { RESULT_TYPE } from './page-objects.mjs'

test('JointDemo: demo buttons are rendered', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })

  await expect(app.page.locator('.demoActionSelectJoint1').first()).toBeVisible()
  await expect(app.page.locator('.demoActionSelectJoint2').first()).toBeVisible()
  await expect(app.page.locator('.demoActionSimulateTightening').first()).toBeVisible()
})

test('JointDemo: selecting joint 1 does not crash the page', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons()
  await demo.selectJoint1()
  // Verify page is still responsive
  await expect(app.page.locator('.demoActionSelectJoint1').first()).toBeVisible()
})

test('JointDemo: selecting joint 2 does not crash the page', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons()
  await demo.selectJoint2()
  await expect(app.page.locator('.demoActionSelectJoint2').first()).toBeVisible()
})

test('JointDemo: simulate tightening for joint 1 produces an event', async ({ connected: app }) => {
  test.setTimeout(150_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })
  await demo.selectJoint1()
  await demo.simulateTightening()

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })
  const count = await events.getEventCount()
  expect(count).toBeGreaterThan(0)
})

test('JointDemo: full demo cycle (j1→tighten→j2→tighten) produces results', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })
  await demo.runFullDemoCycle()

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 2, timeout: 30_000 })

  const hasResult = await events.hasEventContaining('ResultEvent')
  expect(hasResult).toBe(true)
})

test('JointDemo: results from demo cycle appear in Consolidated Result view', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })
  await demo.runFullDemoCycle()

  const results = await app.openResults()
  await results.waitForHeader({ timeout: 60_000 })

  await results.selectResultType(RESULT_TYPE.TIGHTENING)
  // The result option list refreshes from subscription updates after the
  // demo cycle completes; wait until both demo results are visible.
  // At minimum: Unresolved + Latest + the 2 demo results
  await expect
    .poll(async () => results.getResultOptionCount(), { timeout: 30_000 })
    .toBeGreaterThanOrEqual(4)
})

test('JointDemo: repeated demo cycles accumulate results', async ({ connected: app }) => {
  test.setTimeout(240_000)
  const demo = await app.openJointDemo()
  await demo.waitForButtons({ timeout: 60_000 })

  // Run two full cycles
  await demo.runFullDemoCycle()
  await demo.runFullDemoCycle()

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 4, timeout: 30_000 })
  const count = await events.getEventCount()
  expect(count).toBeGreaterThanOrEqual(4)
})
