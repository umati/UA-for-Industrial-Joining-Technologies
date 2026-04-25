import { test, expect, BASE_URL } from './e2e-fixtures.mjs'

/**
 * Servers tab — the default view shown on load.
 *
 * The Servers tab is always visible (no OPC UA connection required).
 * It manages the list of known OPC UA endpoints and their connection state.
 */
test.describe('Servers tab', () => {
  test('page loads without error', async ({ page }) => {
    const response = await page.goto(BASE_URL)
    expect(response.status()).toBeLessThan(400)
  })

  test('"Add new server" button is visible on load', async ({ page }) => {
    await page.goto(BASE_URL)
    await expect(
      page.locator('button').filter({ hasText: /add new server/i })
    ).toBeVisible()
  })

  test('"Save" button is visible on load', async ({ page }) => {
    await page.goto(BASE_URL)
    await expect(
      page.locator('button').filter({ hasText: /^save$/i })
    ).toBeVisible()
  })

  test('EndpointUrl column label is present in header row', async ({ page }) => {
    await page.goto(BASE_URL)
    const body = await page.locator('body').textContent()
    expect(body).toMatch(/EndpointUrl/i)
  })

  test('"Add new server" inserts a new editable row', async ({ page }) => {
    await page.goto(BASE_URL)
    const before = await page.locator('.server-row').count()
    await page.locator('button').filter({ hasText: /add new server/i }).click()
    await page.waitForTimeout(200)
    const after = await page.locator('.server-row').count()
    expect(after).toBeGreaterThan(before)
  })

  test('new server row has editable name and address fields', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.locator('button').filter({ hasText: /add new server/i }).click()
    await page.waitForTimeout(200)
    // Each server data row has two text inputs: name and endpoint URL
    const inputs = page.locator('.server-name input, .server-endpoint input')
    const count = await inputs.count()
    expect(count).toBeGreaterThanOrEqual(2)
    // Should be able to type a custom endpoint URL
    const addrInput = page.locator('.server-endpoint input').last()
    await addrInput.fill('opc.tcp://my-server:4840')
    expect(await addrInput.inputValue()).toBe('opc.tcp://my-server:4840')
  })

  test('new server row has a "Delete" button', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.locator('button').filter({ hasText: /add new server/i }).click()
    await page.waitForTimeout(200)
    await expect(
      page.locator('button').filter({ hasText: /delete/i }).first()
    ).toBeVisible()
  })

  test('"Delete" removes the row', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.locator('button').filter({ hasText: /add new server/i }).click()
    await page.waitForTimeout(200)
    const before = await page.locator('.server-row').count()
    await page.locator('button').filter({ hasText: /delete/i }).first().click()
    await page.waitForTimeout(200)
    const after = await page.locator('.server-row').count()
    expect(after).toBeLessThan(before)
  })
})
