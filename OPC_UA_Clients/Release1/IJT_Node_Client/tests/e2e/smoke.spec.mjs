import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

test.describe('Smoke tests', () => {
  test('page loads successfully', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })

  test('page title contains IJT or OPC', async ({ page }) => {
    await page.goto(BASE_URL)
    const title = await page.title()
    expect(title.toLowerCase()).toMatch(/ijt|opc|tightening/i)
  })

  test('no JavaScript errors on initial load', async ({ page }) => {
    const errors = []
    page.on('pageerror', err => errors.push(err.message))
    await page.goto(BASE_URL)
    await page.waitForTimeout(1000)
    expect(errors).toEqual([])
  })

  test('page has visible content', async ({ page }) => {
    await page.goto(BASE_URL)
    const body = await page.locator('body').textContent()
    expect(body.trim().length).toBeGreaterThan(10)
  })
})
