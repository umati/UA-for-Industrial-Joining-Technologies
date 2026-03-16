import { test, expect } from '@playwright/test'

test('home page smoke loads', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/OPC UA IJT Demo/)
})
