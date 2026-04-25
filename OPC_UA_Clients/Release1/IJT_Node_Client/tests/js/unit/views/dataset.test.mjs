import { describe, it, expect, vi, beforeEach } from 'vitest'
import Dataset from '../../../../javascripts/views/trace/dataset.mjs'

describe('Dataset', () => {
  let ds

  beforeEach(() => {
    ds = new Dataset('myDataset')
  })

  it('sets label from constructor', () => {
    expect(ds.label).toBe('myDataset')
  })

  it('defaults radius to 0', () => {
    expect(ds.radius).toBe(0)
  })

  it('defaults borderWidth to 1', () => {
    expect(ds.borderWidth).toBe(1)
  })

  it('show() sets hidden to false', () => {
    ds.hidden = true
    ds.show()
    expect(ds.hidden).toBe(false)
  })

  it('hide() sets hidden to true', () => {
    ds.show()
    ds.hide()
    expect(ds.hidden).toBe(true)
  })

  it('setBackgroundColor() stores the color', () => {
    ds.setBackgroundColor('red')
    expect(ds.backgroundColor).toBe('red')
  })

  it('setRadius() stores the radius', () => {
    ds.setRadius(5)
    expect(ds.radius).toBe(5)
  })

  it('setBorderColor() stores the color', () => {
    ds.setBorderColor('blue')
    expect(ds.borderColor).toBe('blue')
  })

  it('setBorderWidth() stores the width', () => {
    ds.setBorderWidth(3)
    expect(ds.borderWidth).toBe(3)
  })

  it('setPoints() assigns the data array', () => {
    const pts = [{ x: 1, y: 2 }]
    ds.setPoints(pts)
    expect(ds.data).toBe(pts)
  })

  it('setResultId() stores the id', () => {
    ds.setResultId('result-42')
    expect(ds.resultId).toBe('result-42')
  })

  it('setStepId() stores the id', () => {
    const id = { value: 'step-1' }
    ds.setStepId(id)
    expect(ds.stepId).toBe(id)
  })

  it('select() sets borderWidth to 2', () => {
    ds.select()
    expect(ds.borderWidth).toBe(2)
  })

  it('deselect() resets borderWidth to 1', () => {
    ds.select()
    ds.deselect()
    expect(ds.borderWidth).toBe(1)
  })
})
