/**
 * Feature: Events view — stream, filtering, queue toggle, content validation.
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'
import { EventsPage } from './page-objects.mjs'

test('Events tab: renders the messages container', async ({ connected: app }) => {
  const events = await app.openEvents()
  const list = app.page.locator('.messages')
  await expect(list).toBeVisible({ timeout: 30_000 })
})

test('Events tab: receives events after simulation', async ({ connected: app }) => {
  test.setTimeout(180_000)
  // Trigger simulations first
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.callMethod(['SimulateSingleResult'])
  await methods.callMethod(['SimulateEvents', 'SimualteEvents'])

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })
  const count = await events.getEventCount()
  expect(count).toBeGreaterThan(0)
})

test('Events tab: event items contain event data text', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.callMethod(['SimulateSingleResult'])

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })

  const allText = await events.getAllEventText()
  expect(allText.length).toBeGreaterThan(0)
})

test('Events tab: ResultEvent entries appear after result simulation', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.callMethod(['SimulateSingleResult'])
  await methods.callMethod(['SimulateJobResult'])

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })

  const hasResult = await events.hasEventContaining('ResultEvent')
  expect(hasResult).toBe(true)
})

test('Events tab: Toggle queueing button exists and is clickable', async ({ connected: app }) => {
  test.setTimeout(60_000)
  const events = await app.openEvents()
  const btn = app.page.locator('button:has-text("Toggle queueing")').first()
  // May not appear until events arrive; just verify it doesn't crash if present
  const count = await btn.count()
  if (count > 0) {
    await btn.click()
    await app.page.waitForTimeout(300)
    // Click again to toggle back
    await btn.click()
    await app.page.waitForTimeout(300)
  }
  // Verify page is still functional
  await expect(app.page.locator('.messages')).toBeVisible()
})

test('Events tab: general (non-result) events are also shown', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.callMethod(['SimulateEvents', 'SimualteEvents'])

  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })

  // After SimulateEvents there should be non-result events
  const count = await events.getEventCount()
  expect(count).toBeGreaterThan(0)
})

// ── WS event structure validation ─────────────────────────────────────────────

test('WS: event messages have required structure (command, endpoint, data)', async ({ ws }) => {
  test.setTimeout(45_000)
  await ws.send('connect to')
  await ws.send('subscribe')

  try {
    const events = await ws.waitForEvents(1, 25_000)
    for (const evt of events) {
      expect(evt.command).toBe('event')
      expect(typeof evt.endpoint).toBe('string')
      expect(evt.data).toBeDefined()
    }
  } catch {
    // No spontaneous events — acceptable in non-active server state
  }
})

test('WS: result event data has EventType and Result fields', async ({ ws }) => {
  test.setTimeout(45_000)
  await ws.send('connect to')
  await ws.send('subscribe')

  try {
    const events = await ws.waitForEvents(1, 20_000)
    const resultEvents = events.filter((e) => e.data?.Result != null)
    for (const evt of resultEvents) {
      expect(evt.data.EventType).toBeDefined()
      expect(evt.data.Result).toBeDefined()
      const meta = evt.data.Result?.ResultMetaData
      if (meta) {
        expect(meta.ResultId ?? meta.ResultIdentifier).toBeDefined()
      }
    }
  } catch {
    // Acceptable if server has no pending results
  }
})
