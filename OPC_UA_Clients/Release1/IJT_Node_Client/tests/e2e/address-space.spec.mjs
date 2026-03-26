import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

test.describe('Address Space', () => {
  test('page loads without error', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })
})
