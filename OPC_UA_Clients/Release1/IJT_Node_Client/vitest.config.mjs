import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      'ijt-support': path.resolve(__dirname, 'javascripts/ijt-support')
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/js/unit/**/*.test.mjs'],
    coverage: {
      reportsDirectory: 'test-results/coverage',
      provider: 'v8',
      // Scope to the testable business-logic layer only.
      // The views/ layer requires a real browser (DOM + canvas + chart libs) and
      // is exercised by Playwright E2E tests, not Vitest unit tests.
      include: ['javascripts/ijt-support/**/*.mjs'],
      all: true,
      // cobertura: parsed by CI report job (parse_coverage function expects line-rate attribute)
      // text-summary: human-readable output in the CI log
      reporter: ['text-summary', 'cobertura']
    }
  },
})
