import js from '@eslint/js'
import globals from 'globals'
import pluginN from 'eslint-plugin-n'

export default [
  {
    ignores: [
      'node_modules/**'
    ]
  },
  js.configs.recommended,
  pluginN.configs['flat/recommended-script'],
  {
    files: [
      'index.js',
      'javascripts/ijt-support/client/node-opcua-interface.mjs',
      'scripts/**/*.mjs'
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node
      }
    },
    rules: {
      'n/no-process-exit': 'off',
      'n/no-unpublished-import': 'off'
    }
  },
  {
    files: [
      'javascripts/**/*.mjs'
    ],
    ignores: [
      'javascripts/ijt-support/client/node-opcua-interface.mjs'
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser
      }
    },
    rules: {
      'n/no-unpublished-import': 'off',
      'n/no-missing-import': 'off',
      'n/no-unsupported-features/es-builtins': 'off',
      'n/no-unsupported-features/es-syntax': 'off',
      'no-unused-vars': ['error', { 'args': 'none', 'caughtErrors': 'none' }]
    }
  },
  {
    files: [
      'tests/**/*.mjs',
      'vitest.config.mjs',
      'playwright.config.mjs'
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node
      }
    },
    rules: {
      'n/no-unpublished-import': 'off',
      'n/no-missing-import': 'off',
      'n/no-unsupported-features/es-builtins': 'off',
      'n/no-unsupported-features/es-syntax': 'off',
      'no-unused-vars': ['error', { 'args': 'none', 'caughtErrors': 'none' }]
    }
  }
]
