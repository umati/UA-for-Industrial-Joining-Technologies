import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  resolve: {
    alias: [
      { find: 'ijt-support', replacement: path.resolve(__dirname, 'javascripts/ijt-support') },
      { find: 'views', replacement: path.resolve(__dirname, 'javascripts/views') },
      // Redirect the browser-side vendor bundle to a lightweight test stub so
      // tests that import chart-handler.mjs don't need the actual UMD file.
      { find: '/vendor/chart.umd.js', replacement: path.resolve(__dirname, 'tests/__mocks__/chart-vendor.mjs') },
    ]
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/js/unit/**/*.test.mjs'],
    coverage: {
      reportsDirectory: 'test-results/coverage',
      provider: 'v8',
      // The views/ layer is tested in jsdom (unit) as well as Playwright (E2E).
      include: ['javascripts/ijt-support/**/*.mjs', 'javascripts/views/**/*.mjs'],
      all: true,
      // cobertura: parsed by CI report job (parse_coverage function expects line-rate attribute)
      // text-summary: human-readable output in the CI log
      reporter: ['text-summary', 'cobertura']
    }
  },
})
