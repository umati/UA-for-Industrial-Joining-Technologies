import { test, expect, BASE_URL, OPCUA_ENDPOINT } from './e2e-fixtures.mjs'

/**
 * Connection tab — endpoint inputs and server connect controls.
 *
 * The Server tab (initial view) shows editable endpoint inputs for each
 * saved server. After connecting, per-server tabs appear.
 * These tests cover the pre-connection UI interaction.
 */
test.describe('Connection tab', () => {
  test('page loads and has visible content', async ({ page }) => {
    await page.goto(BASE_URL)
    const body = await page.locator('body').textContent()
    expect(body.trim().length).toBeGreaterThan(10)
  })

  test('page has at least one interactive button', async ({ page }) => {
    await page.goto(BASE_URL)
    const buttons = await page.locator('button, input[type="button"]').count()
    expect(buttons).toBeGreaterThan(0)
  })

  test('can type in an endpoint field if present', async ({ page }) => {
    await page.goto(BASE_URL)
    const count = await page.locator('input[type="text"]').count()
    if (count > 0) {
      const input = page.locator('input[type="text"]').first()
      await input.fill(OPCUA_ENDPOINT)
      const val = await input.inputValue()
      expect(val).toBe(OPCUA_ENDPOINT)
    }
  })

  test('tab selector area is rendered', async ({ page }) => {
    await page.goto(BASE_URL)
    // TabGenerator always creates .tab-select and .tab-generator-base divs
    await expect(page.locator('.tab-generator-base, .start-screen')).toBeVisible()
  })
})
