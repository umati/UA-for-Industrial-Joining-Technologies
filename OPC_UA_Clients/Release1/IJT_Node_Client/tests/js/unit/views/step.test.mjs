import { describe, it, expect, vi, beforeEach } from 'vitest'
import Step from '../../../../javascripts/views/trace/step.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeMockDataset (label = 'ds') {
  return {
    label,
    data: [],
    hidden: false,
    borderWidth: 1,
    show () { this.hidden = false },
    hide () { this.hidden = true },
    setBackgroundColor: vi.fn(),
    setBorderColor: vi.fn(),
    setBorderWidth (w) { this.borderWidth = w },
    setRadius: vi.fn(),
    setPoints (p) { this.data = p },
    setResultId: vi.fn(),
    setStepId: vi.fn(),
    select () { this.borderWidth = 2 },
    deselect () { this.borderWidth = 1 }
  }
}

function makeMockChartManager () {
  const cm = {
    _datasets: [],
    createDataset: vi.fn(name => {
      const ds = makeMockDataset(name)
      cm._datasets.push(ds)
      return ds
    }),
    update: vi.fn(),
    filterOut: vi.fn(list => {
      cm._datasets = cm._datasets.filter(d => !list.includes(d))
    })
  }
  return cm
}

/**
 * Build the two-level owner chain that Step expects:
 *   Step.owner  = SingleTraceData-like object
 *   Step.owner.owner = TraceGraphics-like object
 */
function makeOwnerChain ({
  xDim = 'angle',
  yDim = 'torque',
  displayOffset = 0,
  absoluteFunction = x => x,
  showValuesSelected = false,
  showLimitSelected = false
} = {}) {
  const cm = makeMockChartManager()
  const traceGraphicsMock = {
    xDimensionName: xDim,
    yDimensionName: yDim,
    absoluteFunction,
    chartManager: cm
  }
  const singleTraceMock = {
    displayOffset,
    showValuesSelected,
    showLimitSelected,
    chartManager: cm,
    owner: traceGraphicsMock
  }
  return { owner: singleTraceMock, cm }
}

function makeStepData ({
  name = 'Tighten',
  stepId = 'step-01',
  programStepId = 'prog-01',
  startTimeOffset = 0,
  values = []
} = {}) {
  return {
    stepResultId: {
      value: stepId,
      link: {
        name,
        programStepId,
        stepResultValues: values
      }
    },
    startTimeOffset
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Step', () => {
  let step, cm, owner

  beforeEach(() => {
    const chain = makeOwnerChain()
    cm = chain.cm
    owner = chain.owner
    const data = makeStepData()
    step = new Step(data, owner)
    // Give the step a pre-built dataset (normally set by SingleTraceData.generateTrace)
    step.dataset = makeMockDataset('main')
    step.angle = [0, 10, 20, 30]
    step.torque = [5, 10, 15, 20]
    step.time = [0, 100, 200, 300]
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('stores step name from stepResultId.link.name', () => {
    expect(step.name).toBe('Tighten')
  })

  it('stores stepId from stepResultId', () => {
    expect(step.stepId.value).toBe('step-01')
  })

  it('starts with color = ""', () => {
    expect(step.color).toBe('')
  })

  it('starts with hidden = false', () => {
    expect(step.hidden).toBe(false)
  })

  it('stores values array from stepResultId.link.stepResultValues', () => {
    expect(step.values).toBeInstanceOf(Array)
  })

  // ── Getters ─────────────────────────────────────────────────────────────────

  it('displayOffset delegates to owner.displayOffset', () => {
    owner.displayOffset = 42
    expect(step.displayOffset).toBe(42)
  })

  it('xDimensionName delegates to owner.owner.xDimensionName', () => {
    owner.owner.xDimensionName = 'time'
    expect(step.xDimensionName).toBe('time')
  })

  it('yDimensionName delegates to owner.owner.yDimensionName', () => {
    expect(step.yDimensionName).toBe('torque')
  })

  it('absoluteFunction delegates to owner.owner.absoluteFunction', () => {
    expect(step.absoluteFunction(-3)).toBe(-3)
  })

  it('chartManager delegates to owner.chartManager', () => {
    expect(step.chartManager).toBe(cm)
  })

  it('showValuesSelected delegates to owner.showValuesSelected', () => {
    owner.showValuesSelected = true
    expect(step.showValuesSelected).toBe(true)
  })

  // ── calculateData ────────────────────────────────────────────────────────────

  describe('calculateData — angle vs torque (default)', () => {
    it('populates dataset.data with {x,y} pairs', () => {
      step.calculateData()
      expect(step.dataset.data.length).toBe(4)
      expect(step.dataset.data[0]).toHaveProperty('x')
      expect(step.dataset.data[0]).toHaveProperty('y')
    })

    it('x values come from angle (offset by displayOffset)', () => {
      owner.displayOffset = 5
      step.calculateData()
      expect(step.dataset.data[0].x).toBe(0 - 5) // angle[0] - displayOffset
    })

    it('y values come from torque passed through absoluteFunction', () => {
      owner.owner.absoluteFunction = x => Math.abs(x)
      step.torque = [-5, -10, -15, -20]
      step.calculateData()
      expect(step.dataset.data[0].y).toBe(5)
    })

    it('sets last.x and last.y to the final point', () => {
      step.calculateData()
      expect(step.last.x).toBe(30)
      expect(step.last.y).toBe(20)
    })

    it('copies data to highLightDataset.data when it exists', () => {
      const hlDs = makeMockDataset('hl')
      step.highLightDataset = hlDs
      step.calculateData()
      expect(hlDs.data).toBe(step.dataset.data)
    })

    it('throws when x and y arrays have different lengths', () => {
      step.angle = [1, 2, 3]
      step.torque = [10, 20]
      expect(() => step.calculateData()).toThrow('not the same in X and Y')
    })
  })

  describe('calculateData — time dimension', () => {
    beforeEach(() => {
      owner.owner.xDimensionName = 'time'
    })

    it('adds startTimeOffset to time values when xDimension is time', () => {
      step.startTimeOffset = 1000
      step.calculateData()
      // time[0]=0 + startTimeOffset=1000 - displayOffset=0 → 1000
      expect(step.dataset.data[0].x).toBe(1000)
    })
  })

  // ── highLight / deHighLight ──────────────────────────────────────────────────

  describe('highLight', () => {
    beforeEach(() => {
      step.calculateData()
    })

    it('creates highLightDataset on first call', () => {
      step.highLight()
      expect(step.highLightDataset).toBeDefined()
    })

    it('reuses existing highLightDataset on second call', () => {
      step.highLight()
      const first = step.highLightDataset
      step.highLight()
      expect(step.highLightDataset).toBe(first)
    })

    it('highLightDataset shows when not hidden', () => {
      step.hidden = false
      step.highLight()
      expect(step.highLightDataset.hidden).toBe(false)
    })

    it('highLightDataset hides when step is hidden', () => {
      step.hidden = true
      step.highLight()
      expect(step.highLightDataset.hidden).toBe(true)
    })

    it('sets points on the highLightDataset', () => {
      step.highLight()
      expect(step.highLightDataset.data).toBeDefined()
    })
  })

  describe('deHighLight', () => {
    it('hides existing highLightDataset', () => {
      step.calculateData()
      step.highLight()
      step.deHighLight()
      expect(step.highLightDataset.hidden).toBe(true)
    })

    it('does nothing when highLightDataset is absent', () => {
      expect(() => step.deHighLight()).not.toThrow()
    })
  })

  // ── select / deselect ───────────────────────────────────────────────────────

  describe('select', () => {
    it('calls dataset.select()', () => {
      const spy = vi.spyOn(step.dataset, 'select')
      step.select()
      expect(spy).toHaveBeenCalled()
    })
  })

  describe('deselect', () => {
    it('calls dataset.deselect()', () => {
      const spy = vi.spyOn(step.dataset, 'deselect')
      step.deselect()
      expect(spy).toHaveBeenCalled()
    })
  })

  // ── hideStepTrace / showStepTrace ────────────────────────────────────────────

  describe('hideStepTrace', () => {
    it('sets hidden = true', () => {
      step.hideStepTrace()
      expect(step.hidden).toBe(true)
    })

    it('hides the dataset', () => {
      step.hideStepTrace()
      expect(step.dataset.hidden).toBe(true)
    })
  })

  describe('showStepTrace', () => {
    it('sets hidden = false', () => {
      step.hidden = true
      step.showStepTrace()
      expect(step.hidden).toBe(false)
    })

    it('shows the dataset', () => {
      step.dataset.hide()
      step.showStepTrace()
      expect(step.dataset.hidden).toBe(false)
    })
  })

  // ── createHighlightDataset ──────────────────────────────────────────────────

  describe('createHighlightDataset', () => {
    beforeEach(() => {
      step.calculateData()
    })

    it('returns undefined when step is hidden', () => {
      step.hidden = true
      expect(step.createHighlightDataset()).toBeUndefined()
    })

    it('creates and returns a dataset when not hidden', () => {
      const ds = step.createHighlightDataset()
      expect(ds).toBeDefined()
    })
  })

  // ── delete ───────────────────────────────────────────────────────────────────

  describe('delete', () => {
    it('calls chartManager.filterOut for each dataset in datasetMapping', () => {
      step.values = [{ valueId: 'v1' }]
      step.datasetMapping['v1'] = {
        valueDataset: makeMockDataset(),
        limitsDataset: makeMockDataset(),
        targetDataset: makeMockDataset()
      }
      step.delete()
      expect(cm.filterOut).toHaveBeenCalled()
    })

    it('does not throw when datasetMapping is empty', () => {
      expect(() => step.delete()).not.toThrow()
    })
  })

  // ── interpretPoint ─────────────────────────────────────────────────────────

  describe('interpretPoint', () => {
    it('handles PHYS_TORQUE (2) — y is set from value', () => {
      const value = { physicalQuantity: 2, value: 15, highLimit: 20, lowLimit: 5, targetValue: 17 }
      const result = step.interpretPoint(value)
      expect(result.value.y).toBe(15)
    })

    it('handles PHYS_ANGLE (3) — x is set from value', () => {
      step.angle = [0]
      const value = { physicalQuantity: 3, value: 45, highLimit: 90, lowLimit: 0, targetValue: 45 }
      const result = step.interpretPoint(value)
      expect(result.value.x).toBeDefined()
    })

    it('handles PHYS_TIME (1) — includes startTimeOffset', () => {
      step.startTimeOffset = 100
      const value = { physicalQuantity: 1, value: 50, highLimit: 200, lowLimit: 0, targetValue: 150 }
      const result = step.interpretPoint(value)
      expect(result.value.x).toBeDefined()
    })

    it('handles PHYS_CURRENT (11) — no crash', () => {
      const value = { physicalQuantity: 11, value: 3 }
      expect(() => step.interpretPoint(value)).not.toThrow()
    })

    it('throws for unknown physicalQuantity', () => {
      expect(() => step.interpretPoint({ physicalQuantity: 99 })).toThrow()
    })

    it('returns limits array', () => {
      step.calculateData()
      const value = { physicalQuantity: 2, value: 10, highLimit: 20, lowLimit: 5, targetValue: 15 }
      const result = step.interpretPoint(value)
      expect(Array.isArray(result.limits)).toBe(true)
    })
  })
})
