import neostandard from 'neostandard'

export default neostandard({
  ignores: [
    'node_modules/**',
    'venv/**',
    '.tmp-pip/**'
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
    'space-before-function-paren': ['error', 'always']
  }
})
