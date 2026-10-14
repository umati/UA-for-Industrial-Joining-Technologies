import { defineConfig } from 'vitest/config'
import { cpus } from 'node:os'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Cap vitest workers under loaded hosts (root Phase 1a runs many suites at once).
 * Override with IJT_VITEST_MAX_WORKERS. Standalone default: half cores, max 8.
 */
function resolveMaxWorkers () {
  const raw = process.env.IJT_VITEST_MAX_WORKERS
  if (raw != null && raw.trim() !== '') {
    const parsed = Number.parseInt(raw, 10)
    if (Number.isFinite(parsed) && parsed >= 1) {
      return parsed
    }
  }
  const count = cpus()?.length || 4
  return Math.max(1, Math.min(8, Math.floor(count / 2)))
}

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
    silent: true,
    include: ['tests/js/unit/**/*.test.mjs'],
    testTimeout: 15_000,
    hookTimeout: 15_000,
    maxWorkers: resolveMaxWorkers(),
    coverage: {
      reportsDirectory: 'test-results/coverage',
      provider: 'v8',
      // The views/ layer is tested in jsdom (unit) as well as Playwright (E2E).
      include: ['javascripts/ijt-support/**/*.mjs', 'javascripts/views/**/*.mjs'],
      all: true,
      // cobertura: parsed by CI report job (parse_coverage function expects line-rate attribute)
      // text-summary: human-readable output in the CI log
      reporter: ['text-summary', 'cobertura'],
      thresholds: { lines: 95 }
    }
  },
})
