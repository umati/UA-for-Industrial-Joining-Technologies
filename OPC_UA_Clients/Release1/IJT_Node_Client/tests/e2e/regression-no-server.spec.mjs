import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

test.describe('Regression: no OPC UA server', () => {
  test('page loads even without OPC UA server', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })

  test('page does not crash on load without OPC UA', async ({ page }) => {
    const errors = []
    page.on('pageerror', err => errors.push(err.message))
    await page.goto(BASE_URL)
    await page.waitForTimeout(500)
    const fatalErrors = errors.filter(e => e.includes('Cannot read') && e.includes('undefined'))
    expect(fatalErrors).toEqual([])
  })
})
