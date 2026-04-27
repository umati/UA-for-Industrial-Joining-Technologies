import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('views/trace/chart-handler.mjs', () => {
  class MockChartManager {
    constructor () { this._datasets = [] }

    createDataset (name) {
      const ds = {
        label: name,
        data: [],
        show: vi.fn(),
        hide: vi.fn(),
        setResultId: vi.fn(),
        setStepId: vi.fn(),
        setBackgroundColor: vi.fn(),
        setBorderColor: vi.fn(),
        setBorderWidth: vi.fn(),
        setRadius: vi.fn(),
        setPoints: vi.fn(),
        select: vi.fn(),
        deselect: vi.fn()
      }
      this._datasets.push(ds)
      return ds
    }

    update = vi.fn()
    filterOut (list) { this._datasets = this._datasets.filter(d => !list.includes(d)) }
    putInFront (list) { this.filterOut(list); list.forEach(d => this._datasets.push(d)) }
  }
  return { default: MockChartManager }
})

import Step from '../../../../javascripts/views/trace/step.mjs'

// Minimal owner chain:
//   step.owner       = SingleTraceData-like (has resultId, chartManager, displayOffset)
//   step.owner.owner = TraceGraphics-like   (has xDimensionName, yDimensionName, absoluteFunction)
function makeOwnerChain (xDim = 'angle') {
  const chartManager = {
    _datasets: [],
    createDataset (name) {
      const ds = {
        label: name,
        data: [],
        show: vi.fn(),
        hide: vi.fn(),
        setResultId: vi.fn(),
        setStepId: vi.fn(),
        setBackgroundColor: vi.fn(),
        setBorderColor: vi.fn(),
        setBorderWidth: vi.fn(),
        setRadius: vi.fn(),
        setPoints: vi.fn(),
        select: vi.fn(),
        deselect: vi.fn()
      }
      this._datasets.push(ds)
      return ds
    },
    update: vi.fn(),
    filterOut: vi.fn(),
    putInFront: vi.fn()
  }

  const traceGraphics = {
    xDimensionName: xDim,
    yDimensionName: xDim === 'time' ? 'torque' : 'torque',
    absoluteFunction: v => v,
    chartManager
  }
  const singleTraceData = {
    resultId: 'r-step-test',
    chartManager,
    displayOffset: 0,
    showValuesSelected: true,
    showLimitSelected: false,
    owner: traceGraphics
  }
  return { singleTraceData, traceGraphics, chartManager }
}

// A value descriptor understood by interpretPoint
function makeValue (physicalQuantity, valueNum = 5.0, name = 'Val', id = 'v1') {
  return {
    physicalQuantity,
    value: valueNum,
    highLimit: valueNum + 1,
    lowLimit: valueNum - 1,
    targetValue: valueNum,
    name,
    valueId: id
  }
}

// Full stepData object (Step constructor takes this, not just the stepResultId)
function makeStepData (programStepId = 'pX', name = 'StepX', values = []) {
  return {
    startTimeOffset: 0,
    samplingInterval: 100,
    stepResultId: {
      value: 'sv-' + programStepId,
      link: { name, programStepId, stepResultValues: values }
    }
  }
}

describe('Step — createPoints and createDatasets coverage', () => {
  let singleTraceData, chartManager

  beforeEach(() => {
    const chain = makeOwnerChain('angle')
    singleTraceData = chain.singleTraceData
    chartManager = chain.chartManager
  })

  // ── createPoints (lines 97-108) ───────────────────────────────────────────

  describe('createPoints(color)', () => {
    it('iterates values and calls createDatasets for each — angle xDim', () => {
      const torqueValue = makeValue(2, 5.0, 'Torque', 'v-torque') // PHYS_TORQUE
      const sd = makeStepData('p1', 'StepA', [torqueValue])
      const step = new Step(sd, singleTraceData)
      step.angle = [10, 20, 30]
      step.createPoints('#ff0000')
      // 3 datasets per value (value, limits, target)
      expect(chartManager._datasets.length).toBe(3)
    })

    it('works with PHYS_ANGLE (physicalQuantity=3) value', () => {
      const angleValue = makeValue(3, 15.0, 'Angle', 'v-angle') // PHYS_ANGLE
      const sd = makeStepData('p2', 'StepB', [angleValue])
      const step = new Step(sd, singleTraceData)
      step.angle = [5, 10, 15]
      step.createPoints('#00ff00')
      expect(chartManager._datasets.length).toBeGreaterThan(0)
    })

    it('works with PHYS_TIME (physicalQuantity=1) value', () => {
      const timeValue = makeValue(1, 100.0, 'Time', 'v-time') // PHYS_TIME
      const sd = makeStepData('p3', 'StepC', [timeValue])
      const step = new Step(sd, singleTraceData)
      step.time = [0, 100, 200]
      step.angle = [5, 10, 15]
      step.createPoints('#0000ff')
      expect(chartManager._datasets.length).toBeGreaterThan(0)
    })

    it('stores datasetMapping entry per value', () => {
      const v = makeValue(2, 5.0, 'Tq', 'v-map')
      const sd = makeStepData('p4', 'StepD', [v])
      const step = new Step(sd, singleTraceData)
      step.angle = [0, 10]
      step.createPoints('#aabbcc')
      expect(step.datasetMapping['v-map']).toBeDefined()
      expect(step.datasetMapping['v-map'].valueDataset).toBeDefined()
      expect(step.datasetMapping['v-map'].limitsDataset).toBeDefined()
      expect(step.datasetMapping['v-map'].targetDataset).toBeDefined()
    })

    it('creates datasets for multiple values', () => {
      const v1 = makeValue(2, 5.0, 'Tq', 'v1')
      const v2 = makeValue(3, 15.0, 'An', 'v2')
      const sd = makeStepData('p5', 'StepE', [v1, v2])
      const step = new Step(sd, singleTraceData)
      step.angle = [5, 10]
      step.createPoints('#112233')
      // 3 datasets per value × 2 values = 6
      expect(chartManager._datasets.length).toBe(6)
    })
  })

  // ── createDatasets (lines 222-240) ────────────────────────────────────────

  describe('createDatasets(name, points, color)', () => {
    let step

    beforeEach(() => {
      const sd = makeStepData('pDs', 'StepDs', [])
      step = new Step(sd, singleTraceData)
    })

    const samplePoints = () => ({
      value: { x: 1, y: 2, type: '' },
      limits: [{ x: 1, y: 3, name: '[limit]', type: 'limit' }],
      target: { x: 1, y: 4, name: '[target]', type: 'target' }
    })

    it('returns an object with value, limits, target datasets', () => {
      const result = step.createDatasets('myDs', samplePoints(), '#abcdef')
      expect(result.value).toBeDefined()
      expect(result.limits).toBeDefined()
      expect(result.target).toBeDefined()
    })

    it('calls chartManager.createDataset for value, limits, and target', () => {
      step.createDatasets('base', samplePoints(), '#ffffff')
      const names = chartManager._datasets.map(d => d.label)
      expect(names).toContain('base')
      expect(names).toContain('base[limit]')
      expect(names).toContain('base[target]')
    })

    it('calls setPoints on each dataset', () => {
      const pts = samplePoints()
      step.createDatasets('pts', pts, '#ff0000')
      const valueDs = chartManager._datasets.find(d => d.label === 'pts')
      expect(valueDs.setPoints).toHaveBeenCalledWith([pts.value])
      const limitsDs = chartManager._datasets.find(d => d.label === 'pts[limit]')
      expect(limitsDs.setPoints).toHaveBeenCalledWith(pts.limits)
    })

    it('calls setBackgroundColor and setBorderColor on each dataset', () => {
      step.createDatasets('color', samplePoints(), '#123456')
      chartManager._datasets.forEach(ds => {
        expect(ds.setBackgroundColor).toHaveBeenCalled()
        expect(ds.setBorderColor).toHaveBeenCalled()
      })
    })

    it('calls show() on each created dataset', () => {
      step.createDatasets('shown', samplePoints(), '#999999')
      chartManager._datasets.forEach(ds => {
        expect(ds.show).toHaveBeenCalled()
      })
    })

    it('works when limits array is empty', () => {
      const pts = { value: { x: 1, y: 2, type: '' }, limits: [], target: undefined }
      expect(() => step.createDatasets('empty', pts, '#000000')).not.toThrow()
    })
  })
})
