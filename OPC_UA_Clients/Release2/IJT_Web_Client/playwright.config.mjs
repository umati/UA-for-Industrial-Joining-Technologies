import { defineConfig, devices } from '@playwright/test'

const UI_PORT = process.env.UI_TEST_PORT ?? '3000'
const UI_BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL ?? process.env.UI_TEST_BASE_URL ?? `http://127.0.0.1:${UI_PORT}`
const TEST_RESULTS_DIR = process.env.IJT_WEB_TEST_RESULTS_DIR ?? 'test-results'
const PLAYWRIGHT_WORKERS = Number.parseInt(
  process.env.IJT_PLAYWRIGHT_WORKERS ?? (process.env.CI ? '2' : '1'),
  10
)

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
  outputDir: `${TEST_RESULTS_DIR}/artifacts`,

  /* Global test timeout */
  timeout: 90_000,

  /* Assertion timeout */
  expect: { timeout: 15_000 },

  /* Flakes are product or infrastructure bugs; do not retry them into green. */
  retries: 0,

  /* Parallelism is enabled only by suites that provision isolated backend workers. */
  workers: PLAYWRIGHT_WORKERS,

  reporter: [
    ['html', { open: 'never', outputFolder: `${TEST_RESULTS_DIR}/html` }],
    ['json', { outputFile: `${TEST_RESULTS_DIR}/results.json` }],
    ['line'],
  ],

  use: {
    baseURL: UI_BASE_URL,
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
    command: `npx --yes serve --listen tcp://127.0.0.1:${UI_PORT} --no-clipboard --no-request-logging .`,
    url: UI_BASE_URL,
    reuseExistingServer: false,
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
      testMatch: /(connection|methods|events|results|joint-demo|ok-rate|address-space|servers)\.spec\.mjs/,
      fullyParallel: true,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
