import { defineConfig } from 'vitest/config'
import { cpus } from 'node:os'
import { resolve } from 'path'
import { fileURLToPath } from 'url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

/**
 * Cap vitest workers so unit runs stay stable under a loaded host
 * (root Phase 1a already runs many suites in parallel).
 *
 * Override with IJT_VITEST_MAX_WORKERS (root runner sets a nested budget).
 * Standalone default: half cores, max 8.
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
    alias: {
      // Maps the bare 'ijt-support/...' specifier used in source modules to
      // the actual directory so Vitest can resolve it without a browser import map.
      'ijt-support': resolve(__dirname, 'src/javascripts/ijt-support')
    }
  },
  test: {
    include: [
      'tests/js/unit/**/*.test.mjs',
      'src/javascripts/views/envelope/tests/unit/**/*.test.mjs'
    ],
    // Requires private Envelope data/itbp.json; run only via
    // `npm run test:unit:js:performance` (Phase 1b). Keep lockstep with
    // package.json test:unit:js --exclude and Envelope vitest.config.mjs.
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      ...(process.argv.some((arg) => arg.includes('automatic-stepwise-performance'))
        ? []
        : ['src/javascripts/views/envelope/tests/unit/automatic-stepwise-performance.test.mjs'])
    ],
    environment: 'node',
    silent: true,
    // Absorb import/scheduling stalls under parallel monorepo load (not slow assertions).
    testTimeout: 15_000,
    hookTimeout: 15_000,
    maxWorkers: resolveMaxWorkers(),
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'cobertura'],
      reportsDirectory: 'test-results/coverage',
      include: ['src/javascripts/ijt-support/**/*.mjs'],
      exclude: ['src/javascripts/views/**/*.mjs'],  // views require DOM
      thresholds: { lines: 95 }
    }
  }
})
