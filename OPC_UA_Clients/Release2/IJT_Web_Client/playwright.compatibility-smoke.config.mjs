import { defineConfig, devices } from '@playwright/test'

const UI_PORT = process.env.UI_TEST_PORT ?? '3007'
const UI_BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL ?? process.env.UI_TEST_BASE_URL ?? `http://127.0.0.1:${UI_PORT}`
const TEST_RESULTS_DIR = process.env.IJT_WEB_TEST_RESULTS_DIR ?? 'test-results'
const PLAYWRIGHT_WORKERS = Number.parseInt(process.env.IJT_PLAYWRIGHT_WORKERS ?? '1', 10)

/**
 * Web Client Compatibility Smoke.
 *
 * This config intentionally uses the configured real browser channel rather than
 * the pinned Linux Chromium image. The bulk browser suite owns deterministic
 * browser logic coverage; this smoke detects customer-visible browser file
 * handling regressions for the two audited Web Client surfaces.
 */
export default defineConfig({
  testDir: './tests/e2e-compatibility-smoke',
  outputDir: `${TEST_RESULTS_DIR}/compatibility-smoke-artifacts`,

  timeout: 90_000,
  expect: { timeout: 15_000 },

  retries: 0,
  workers: PLAYWRIGHT_WORKERS,

  reporter: [
    ['html', { open: 'never', outputFolder: `${TEST_RESULTS_DIR}/compatibility-smoke-html` }],
    ['json', { outputFile: `${TEST_RESULTS_DIR}/compatibility-smoke-results.json` }],
    ['junit', { outputFile: `${TEST_RESULTS_DIR}/compatibility-smoke.xml` }],
    ['line'],
  ],

  use: {
    baseURL: UI_BASE_URL,
    browserName: 'chromium',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },

  webServer: {
    command: `npx --yes serve --listen tcp://127.0.0.1:${UI_PORT} --no-clipboard --no-request-logging .`,
    url: UI_BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
  },

  projects: [
    {
      name: 'compatibility-smoke',
      testMatch: /edge-result-.*\.spec\.mjs/,
      use: {
        ...devices['Desktop Chrome'],
        channel: 'msedge',
      },
    },
  ],
})
