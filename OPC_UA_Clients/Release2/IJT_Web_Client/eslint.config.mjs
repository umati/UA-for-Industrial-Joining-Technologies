import neostandard from 'neostandard'

export default neostandard({
  languageOptions: {
    globals: {
      alert: 'readonly',
      self: 'readonly',
      myChart: 'readonly',
      traceHandler: 'readonly',
      stepHandler: 'readonly',
      polynomialObject: 'readonly',
      degree: 'readonly',
    },
  },
})
