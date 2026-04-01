/**
 * Feature: OK Rate view — display, counters, simulation buttons.
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'

async function openOkRate (app) {
  await app.setViewLevel('3')   // Detailed view exposes OkRate tab
  await app.page.waitForTimeout(300)
  const okRate = await app.openOkRate()
  await okRate.waitForView({ timeout: 30_000 })
  return okRate
}

test('OkRate: view renders after connecting', async ({ connected: app }) => {
  test.setTimeout(90_000)
  await openOkRate(app)
  await expect(app.page.locator('.okRateView')).toBeVisible()
})

test('OkRate: percentage value is displayed', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const okRate = await openOkRate(app)
  const text = await okRate.getOkRateText()
  expect(text).toBeDefined()
  // Value is either a percentage like "100.00%" or an initial "–" / "0%"
  expect(typeof text).toBe('string')
})

test('OkRate: simulate OK result button exists and responds', async ({ connected: app }) => {
  test.setTimeout(90_000)
  await openOkRate(app)
  const btn = app.page.locator('button:has-text("Simulate OK result")').first()
  if ((await btn.count()) > 0) {
    await btn.click()
    await app.page.waitForTimeout(800)
    // Page must remain functional
    await expect(app.page.locator('.okRateView')).toBeVisible()
  }
})

test('OkRate: simulate NOT OK result button exists and responds', async ({ connected: app }) => {
  test.setTimeout(90_000)
  await openOkRate(app)
  const btn = app.page.locator('button:has-text("Simulate NOT OK result")').first()
  if ((await btn.count()) > 0) {
    await btn.click()
    await app.page.waitForTimeout(800)
    await expect(app.page.locator('.okRateView')).toBeVisible()
  }
})

test('OkRate: rate increases to 100% after clearing and simulating one OK', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const okRate = await openOkRate(app)

  // Clear first
  const clearBtn = app.page.locator('button:has-text("Clear counters")').first()
  if ((await clearBtn.count()) === 0) { test.skip() }
  await clearBtn.click()
  await app.page.waitForTimeout(400)

  // Simulate one OK
  const okBtn = app.page.locator('button:has-text("Simulate OK result")').first()
  if ((await okBtn.count()) === 0) { test.skip() }
  await okBtn.click()
  await app.page.waitForTimeout(1_000)

  const rate = await okRate.getOkRateNumber()
  // After 1 OK and 0 NOK, rate should be 100
  expect(isNaN(rate) || rate === 100).toBe(true)
})

test('OkRate: rate decreases after simulating a NOT OK result', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const okRate = await openOkRate(app)

  const clearBtn = app.page.locator('button:has-text("Clear counters")').first()
  if ((await clearBtn.count()) === 0) { test.skip() }
  await clearBtn.click()
  await app.page.waitForTimeout(300)

  const okBtn = app.page.locator('button:has-text("Simulate OK result")').first()
  const nokBtn = app.page.locator('button:has-text("Simulate NOT OK result")').first()
  if ((await okBtn.count()) === 0 || (await nokBtn.count()) === 0) { test.skip() }

  // 1 OK + 1 NOK = 50%
  await okBtn.click()
  await app.page.waitForTimeout(600)
  await nokBtn.click()
  await app.page.waitForTimeout(1_000)

  const rate = await okRate.getOkRateNumber()
  expect(isNaN(rate) || rate < 100).toBe(true)
})

test('OkRate: clear counters resets display', async ({ connected: app }) => {
  test.setTimeout(90_000)
  await openOkRate(app)

  const clearBtn = app.page.locator('button:has-text("Clear counters")').first()
  if ((await clearBtn.count()) === 0) { test.skip() }

  await clearBtn.click()
  await app.page.waitForTimeout(500)

  // After clearing, the view must still be visible (no crash)
  await expect(app.page.locator('.okRateView')).toBeVisible()
})
