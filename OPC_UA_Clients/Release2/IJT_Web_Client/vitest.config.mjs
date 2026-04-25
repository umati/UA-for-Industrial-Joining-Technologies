import { defineConfig } from 'vitest/config'
import { resolve } from 'path'
import { fileURLToPath } from 'url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  resolve: {
    alias: {
      // Maps the bare 'ijt-support/...' specifier used in source modules to
      // the actual directory so Vitest can resolve it without a browser import map.
      'ijt-support': resolve(__dirname, 'src/javascripts/ijt-support')
    }
  },
  test: {
    include: ['tests/js/unit/**/*.test.mjs'],
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'cobertura'],
      reportsDirectory: 'test-results/coverage',
      include: ['src/javascripts/ijt-support/**/*.mjs'],
      exclude: ['src/javascripts/views/**/*.mjs'],  // views require DOM
      thresholds: { lines: 80 }
    }
  }
})
