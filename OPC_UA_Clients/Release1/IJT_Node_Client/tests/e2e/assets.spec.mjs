import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

/**
 * Assets view — appears as a sub-tab after connecting to an OPC UA server.
 *
 * The Assets tab renders the physical asset hierarchy (controllers, tools,
 * sensors, feeders, cables, etc.) using AssetGraphics. It is only created
 * after a successful OPC UA connection, so most tests require a live server.
 *
 * Tests that require OPC UA skip gracefully via test.skip() when the tab
 * is not present. Basic page-stability tests run without any connection.
 */
test.describe('Assets view', () => {
  test('page loads without error', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })

  test('no fatal JavaScript errors on initial load', async ({ page }) => {
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

  test('Assets tab shows asset area when connected', async ({ page }) => {
    await page.goto(BASE_URL)
    const tab = page.locator('input[type="button"]').filter({ hasText: /assets?/i })
    if (await tab.count() === 0) {
      test.skip(true, 'Assets tab only visible after connecting to an OPC UA server')
    }
    await tab.click()
    // AssetGraphics renders inside a .draw-asset-box container
    await expect(page.locator('.draw-asset-box, .basescreen')).toBeVisible()
  })

  test('asset area renders controller boxes when assets are loaded', async ({ page }) => {
    await page.goto(BASE_URL)
    const tab = page.locator('input[type="button"]').filter({ hasText: /assets?/i })
    if (await tab.count() === 0) {
      test.skip(true, 'Assets tab only visible after connecting to an OPC UA server')
    }
    await tab.click()
    // Wait for async asset load — AssetGraphics.initiate() calls assetManager.setupAndLoadAllAssets()
    await page.waitForTimeout(2000)
    const assetBoxes = await page.locator('.asset-area').count()
    // At least one controller box should be rendered
    expect(assetBoxes).toBeGreaterThan(0)
  })
})
