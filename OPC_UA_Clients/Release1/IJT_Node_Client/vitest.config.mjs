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
  },
})
