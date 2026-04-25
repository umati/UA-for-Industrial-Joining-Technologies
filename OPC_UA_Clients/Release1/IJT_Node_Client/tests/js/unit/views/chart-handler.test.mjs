import { describe, it, expect, vi, beforeEach } from 'vitest'

// chart-handler.mjs imports '/vendor/chart.umd.js' which is aliased in
// vitest.config.mjs → tests/__mocks__/chart-vendor.mjs (sets globalThis.Chart).
// The mock file also imports Dataset and ijtLog via relative paths which resolve
// normally, so we can test ChartManager directly.
import ChartManager from '../../../../javascripts/views/trace/chart-handler.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeCanvas () {
  const canvas = document.createElement('canvas')
  // getContext is not in jsdom canvas — stub it so Chart ctor does not throw
  canvas.getContext = vi.fn(() => ({
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    getImageData: vi.fn(() => ({ data: [] })),
    putImageData: vi.fn(),
    createImageData: vi.fn(() => ({ data: [] })),
    setTransform: vi.fn(),
    drawImage: vi.fn(),
    save: vi.fn(),
    fillText: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    stroke: vi.fn(),
    translate: vi.fn(),
    scale: vi.fn(),
    rotate: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    measureText: vi.fn(() => ({ width: 0 })),
    transform: vi.fn(),
    rect: vi.fn(),
    clip: vi.fn()
  }))
  return canvas
}

function makeTraceManager (canvas) {
  return {
    traceInterface: { canvas },
    clicked: vi.fn()
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ChartManager', () => {
  let canvas, traceManager, cm

  beforeEach(() => {
    canvas = makeCanvas()
    traceManager = makeTraceManager(canvas)
    cm = new ChartManager(canvas, traceManager)
  })

  it('stores context (canvas)', () => {
    expect(cm.context).toBe(canvas)
  })

  it('stores traceManager', () => {
    expect(cm.traceManager).toBe(traceManager)
  })

  it('creates a myChart instance', () => {
    expect(cm.myChart).toBeDefined()
  })

  it('myChart.data.datasets starts as an array', () => {
    expect(Array.isArray(cm.myChart.data.datasets)).toBe(true)
  })

  // ── createDataset ───────────────────────────────────────────────────────────

  describe('createDataset', () => {
    it('returns a Dataset instance', () => {
      const ds = cm.createDataset('TestDS')
      expect(ds).toBeDefined()
    })

    it('pushes the dataset into myChart.data.datasets', () => {
      cm.createDataset('DS1')
      expect(cm.myChart.data.datasets.length).toBeGreaterThan(0)
    })

    it('dataset has the supplied label', () => {
      const ds = cm.createDataset('MyLabel')
      expect(ds.label).toBe('MyLabel')
    })
  })

  // ── update ──────────────────────────────────────────────────────────────────

  describe('update', () => {
    it('calls myChart.update()', () => {
      const spy = vi.spyOn(cm.myChart, 'update')
      cm.update()
      expect(spy).toHaveBeenCalled()
    })
  })

  // ── filterOut ───────────────────────────────────────────────────────────────

  describe('filterOut', () => {
    it('removes listed datasets from myChart.data.datasets', () => {
      const ds1 = cm.createDataset('DS1')
      const ds2 = cm.createDataset('DS2')
      cm.filterOut([ds1])
      expect(cm.myChart.data.datasets).not.toContain(ds1)
      expect(cm.myChart.data.datasets).toContain(ds2)
    })

    it('leaves the list unchanged if no match', () => {
      const ds = cm.createDataset('DS')
      const foreign = { label: 'foreign' }
      cm.filterOut([foreign])
      expect(cm.myChart.data.datasets).toContain(ds)
    })
  })

  // ── putInFront ───────────────────────────────────────────────────────────────

  describe('putInFront', () => {
    it('moves datasets to the end of the datasets array', () => {
      const ds1 = cm.createDataset('First')
      const ds2 = cm.createDataset('Second')
      cm.putInFront([ds1])
      const arr = cm.myChart.data.datasets
      expect(arr[arr.length - 1]).toBe(ds1)
      expect(arr).toContain(ds2)
    })
  })

  // ── canvas click handler ────────────────────────────────────────────────────

  describe('canvas onclick', () => {
    it('calls traceManager.clicked when a point is found', () => {
      const ds = cm.createDataset('clickDS')
      ds.resultId = 'r1'
      ds.stepId = { value: 'step-1' }
      // Make the Chart stub return a hit
      cm.myChart.getElementsAtEventForMode = vi.fn(() => [{ datasetIndex: 0 }])
      canvas.onclick({})
      expect(traceManager.clicked).toHaveBeenCalledWith('r1', 'step-1')
    })

    it('does nothing when no points hit', () => {
      cm.myChart.getElementsAtEventForMode = vi.fn(() => [])
      canvas.onclick({})
      expect(traceManager.clicked).not.toHaveBeenCalled()
    })
  })
})
