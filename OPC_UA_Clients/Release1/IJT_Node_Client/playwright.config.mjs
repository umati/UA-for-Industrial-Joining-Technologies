import { defineConfig, devices } from 'playwright/test'

/**
 * Playwright configuration for IJT Node Client E2E tests.
 *
 * Projects:
 *   smoke      - Fast structural checks (page loads, no JS errors)
 *   regression - No-OPC-UA-server regression tests
 *   views      - Per-view UI tests (require HTTP server on :3000; OPC UA optional)
 *
 * Run specific projects:
 *   npx playwright test --project=smoke
 *   npx playwright test --project=regression
 *   npx playwright test --project=views
 *   npx playwright test          (all)
 *
 * Prerequisites:
 *   node index.js    (start the IJT Node Client HTTP server on port 3000)
 *
 * Tests skip gracefully when the server is not running — see e2e-fixtures.mjs.
 */
export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: 1,
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/playwright.json' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.mjs$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'regression',
      testMatch: /regression-no-server\.spec\.mjs$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'views',
      testMatch: /(connection|events|methods|servers|address-space|trace|assets)\.spec\.mjs$/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
