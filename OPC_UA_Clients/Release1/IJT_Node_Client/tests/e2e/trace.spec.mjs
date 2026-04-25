import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

/**
 * Trace view — appears as a sub-tab after connecting to an OPC UA server.
 *
 * Basic load tests run without OPC UA. The chart/trace display and
 * live tightening result subscription require an active OPC UA connection —
 * tests skip gracefully when the tab is not present.
 */
test.describe('Trace view', () => {
  test('page loads without error', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })

  test('no fatal JavaScript errors on load', async ({ page }) => {
    const errors = []
    page.on('pageerror', err => errors.push(err.message))
    await page.goto(BASE_URL)
    await page.waitForTimeout(500)
    const fatal = errors.filter(e =>
      e.includes('Cannot read properties of undefined') ||
      e.includes('is not a function') ||
      e.includes('is not defined')
    )
    expect(fatal).toEqual([])
  })

  test('Trace tab shows chart container when connected', async ({ page }) => {
    await page.goto(BASE_URL)
    const tab = page.locator('input[type="button"]').filter({ hasText: /trace/i })
    if (await tab.count() === 0) {
      test.skip(true, 'Trace tab only visible after connecting to an OPC UA server')
    }
    await tab.click()
    // Trace view renders a canvas (Chart.js) or a message area
    await expect(page.locator('canvas, .messages, .basescreen')).toBeVisible()
  })
})
