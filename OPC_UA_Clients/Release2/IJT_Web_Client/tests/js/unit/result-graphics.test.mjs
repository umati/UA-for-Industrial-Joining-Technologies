import { describe, it, expect } from 'vitest'
import ResultGraphics from '../../../src/javascripts/views/complex-result/result-graphics.mjs'

describe('ResultGraphics result box label text', () => {
  it('shows both the result name and evaluation details when both are present', () => {
    const screen = Object.create(ResultGraphics.prototype)
    const text = screen.getResultBoxLabelText({
      name: 'Tightening result',
      ResultMetaData: {
        ResultEvaluationDetails: { Text: 'NOT (limit A OR limit B)' }
      }
    })

    expect(text).toBe('NOT (limit A OR limit B)\nTightening result')
  })

  it('falls back to evaluation details when there is no name', () => {
    const screen = Object.create(ResultGraphics.prototype)
    const text = screen.getResultBoxLabelText({
      ResultMetaData: {
        ResultEvaluationDetails: { Text: 'NOT (limit A OR limit B)' }
      }
    })

    expect(text).toBe('NOT (limit A OR limit B)')
  })
})
