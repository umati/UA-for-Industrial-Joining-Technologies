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
      'Javascripts/ijt-support/Client/NodeOPCUAInterface.mjs',
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
  }
]
