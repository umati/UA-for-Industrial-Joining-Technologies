import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for IJT Web Client E2E + UI regression tests.
 *
 * Projects:
 *   smoke      - Fast structural checks (no backend required)
 *   regression - Full UI regression flow
 *   features   - Per-feature test files (require backend + OPC UA server)
 *
 * Run specific projects:
 *   npx playwright test --project=smoke
 *   npx playwright test --project=regression
 *   npx playwright test --project=features
 *   npx playwright test          (all)
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Global test timeout */
  timeout: 90_000,

  /* Assertion timeout */
  expect: { timeout: 15_000 },

  /* Retry failed tests once locally, twice on CI */
  retries: process.env.CI ? 2 : 1,

  /* Parallel workers - run serially when using a single browser tab against live server */
  workers: process.env.CI ? 2 : 1,

  reporter: [
    ['html', { open: 'never', outputFolder: 'test-results/html' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['line'],
  ],

  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL ?? 'http://127.0.0.1:3000',
    // Use chromium (installed via `npx playwright install chromium`)
    // Works on Windows, Linux, macOS and Docker without a Chrome install.
    browserName: 'chromium',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    /* Capture artefacts on failure for debugging */
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },

  /* Start a lightweight static file server to serve index.html */
  webServer: {
    command: 'npx --yes serve --listen tcp://127.0.0.1:3000 --no-clipboard --no-request-logging .',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: true,
    timeout: 120_000,
  },

  projects: [
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.mjs/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'regression',
      testMatch: /regression-ui\.spec\.mjs/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'features',
      testMatch: /\.(connection|methods|events|results|joint-demo|ok-rate|address-space|servers)\.spec\.mjs/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
