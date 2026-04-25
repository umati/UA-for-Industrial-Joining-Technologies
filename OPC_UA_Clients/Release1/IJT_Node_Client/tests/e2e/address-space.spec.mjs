import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

/**
 * Address Space view — appears as a sub-tab after connecting to an OPC UA server.
 *
 * Basic load tests run without OPC UA. The full address-space tree browser
 * requires an active OPC UA connection — tests skip gracefully when not connected.
 */
test.describe('Address Space view', () => {
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

  test('Address Space tab shows tree area when connected', async ({ page }) => {
    await page.goto(BASE_URL)
    const tab = page.locator('input[type="button"]').filter({ hasText: /address.?space/i })
    if (await tab.count() === 0) {
      test.skip(true, 'Address Space tab only visible after connecting to an OPC UA server')
    }
    await tab.click()
    // Address space view renders a scrollable info area or similar container
    await expect(page.locator('.scrollable-info-area, .basescreen')).toBeVisible()
  })
})
