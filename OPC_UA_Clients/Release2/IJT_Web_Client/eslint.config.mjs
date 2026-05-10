import neostandard from 'neostandard'

export default [
  ...neostandard({
    ignores: [
      'node_modules/**',
      'venv/**',
      '.venv/**',
      '.state/**',
      '.tmp-pip/**',
      'src/javascripts/views/envelope/**'
    ],
    languageOptions: {
      globals: {
        alert: 'readonly',
        self: 'readonly',
        myChart: 'readonly',
        traceHandler: 'readonly',
        stepHandler: 'readonly',
        polynomialObject: 'readonly',
        degree: 'readonly',
        Chart: 'readonly'
      }
    },
    rules: {
      'space-before-function-paren': ['error', 'always'],
      'no-unused-vars': ['error', { 'args': 'none', 'caughtErrors': 'none' }]
    }
  }),
  {
    files: [
      'src/javascripts/ijt-support/connection/connection-manager.mjs',
      'src/javascripts/ijt-support/connection/auth/**/*.mjs',
      'src/javascripts/ijt-support/connection/token/**/*.mjs',
      'src/javascripts/ijt-support/connection/nonce/**/*.mjs'
    ],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: 'CallExpression[callee.object.name="Math"][callee.property.name="random"]',
          message: 'Use Web Crypto APIs for connection/session identifiers.'
        }
      ]
    }
  }
]
