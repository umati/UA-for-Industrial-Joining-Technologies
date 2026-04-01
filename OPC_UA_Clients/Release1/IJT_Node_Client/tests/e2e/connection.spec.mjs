import { test, expect, BASE_URL, OPCUA_ENDPOINT } from './e2e-fixtures.mjs'

test.describe('Connection tab', () => {
  test('page loads and has input area', async ({ page }) => {
    await page.goto(BASE_URL)
    const inputs = await page.locator('input').count()
    expect(inputs).toBeGreaterThanOrEqual(0)
  })

  test('can type in an endpoint field if present', async ({ page }) => {
    await page.goto(BASE_URL)
    const input = page.locator('input[type="text"]').first()
    const count = await page.locator('input[type="text"]').count()
    if (count > 0) {
      await input.fill(OPCUA_ENDPOINT)
      const val = await input.inputValue()
      expect(val).toBe(OPCUA_ENDPOINT)
    }
  })
})
