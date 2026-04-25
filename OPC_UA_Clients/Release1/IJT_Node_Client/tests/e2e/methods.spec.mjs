import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

/**
 * Methods view — appears as a sub-tab after connecting to an OPC UA server.
 *
 * Basic load tests run without OPC UA. Tests that invoke IJT methods
 * (GetJoiningProcessList, GetJointDesignList, etc.) require an active
 * OPC UA connection — they skip gracefully when the tab is not present.
 */
test.describe('Methods view', () => {
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

  test('Methods tab shows method controls when connected', async ({ page }) => {
    await page.goto(BASE_URL)
    const tab = page.locator('input[type="button"]').filter({ hasText: /methods?/i })
    if (await tab.count() === 0) {
      test.skip(true, 'Methods tab only visible after connecting to an OPC UA server')
    }
    await tab.click()
    await expect(page.locator('button, input[type="button"]')).toBeVisible()
  })
})
