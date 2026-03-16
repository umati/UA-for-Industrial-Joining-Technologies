import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    channel: 'chrome'
  },
  webServer: {
    command: 'npx --yes serve --listen tcp://127.0.0.1:3000 --no-clipboard --no-request-logging .',
    port: 3000,
    reuseExistingServer: true,
    timeout: 120000
  }
})
