import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['tests/js/unit/**/*.test.mjs'],
    environment: 'node'
  }
})
