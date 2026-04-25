import { describe, it, expect, vi, beforeEach } from 'vitest'
import SingleTraceData from '../../../../javascripts/views/trace/single-trace-data.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeMockDataset () {
  return {
    label: '',
    data: [],
    hidden: false,
    resultId: null,
    stepId: null,
    backgroundColor: null,
    borderColor: null,
    borderWidth: 1,
    show () { this.hidden = false },
    hide () { this.hidden = true },
    setResultId (id) { this.resultId = id },
    setStepId (id) { this.stepId = id },
    setBackgroundColor (c) { this.backgroundColor = c },
    setBorderColor (c) { this.borderColor = c },
    setBorderWidth (w) { this.borderWidth = w },
    setRadius (r) { this.radius = r },
    setPoints (p) { this.data = p },
    select () { this.borderWidth = 2 },
    deselect () { this.borderWidth = 1 }
  }
}

function makeMockChartManager () {
  const datasets = []
  return {
    datasets,
    createDataset: vi.fn((name) => {
      const ds = makeMockDataset()
      ds.label = name
      datasets.push(ds)
      return ds
    }),
    update: vi.fn(),
    filterOut: vi.fn()
  }
}

function makeMockOwner () {
  return {
    chartManager: makeMockChartManager(),
    showValuesSelected: false,
    showLimitSelected: false,
    xDimensionName: 'angle',
    yDimensionName: 'torque',
    absoluteFunction: x => x
  }
}

function makeResult (overrides = {}) {
  return {
    resultId: 'result-001',
    creationTime: '2024-06-15T08:42:33Z',
    ...overrides
  }
}

function makeMockStep (name = 'Step A', stepId = 's1') {
  return {
    name,
    color: 'red',
    stepId: { value: stepId, link: { programStepId: 'p1' } },
    dataset: null,
    calculateData: vi.fn(),
    createPoints: vi.fn(),
    calculatePoints: vi.fn(),
    highLight: vi.fn(),
    deHighLight: vi.fn(),
    select: vi.fn(),
    deselect: vi.fn(),
    delete: vi.fn()
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('SingleTraceData', () => {
  let owner, result, trace

  beforeEach(() => {
    owner = makeMockOwner()
    result = makeResult()
    trace = new SingleTraceData(result, owner)
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('stores result', () => {
    expect(trace.result).toBe(result)
  })

  it('stores resultId from result.resultId', () => {
    expect(trace.resultId).toBe('result-001')
  })

  it('sets displayName from creationTime substring (HH:MM)', () => {
    expect(trace.displayName).toBe('08:42')
  })

  it('starts with empty steps array', () => {
    expect(trace.steps).toHaveLength(0)
  })

  it('starts with selected = false', () => {
    expect(trace.selected).toBe(false)
  })

  it('starts with displayOffset = 0', () => {
    expect(trace.displayOffset).toBe(0)
  })

  it('chartManager getter delegates to owner.chartManager', () => {
    expect(trace.chartManager).toBe(owner.chartManager)
  })

  it('showValuesSelected getter delegates to owner', () => {
    owner.showValuesSelected = true
    expect(trace.showValuesSelected).toBe(true)
  })

  it('showLimitSelected getter delegates to owner', () => {
    owner.showLimitSelected = true
    expect(trace.showLimitSelected).toBe(true)
  })

  // ── addStep ─────────────────────────────────────────────────────────────────

  it('addStep appends a step to the steps array', () => {
    const step = makeMockStep()
    trace.addStep(step)
    expect(trace.steps).toHaveLength(1)
    expect(trace.steps[0]).toBe(step)
  })

  // ── generateTrace ──────────────────────────────────────────────────────────

  describe('generateTrace', () => {
    it('calls createDataset on the chartManager for each step', () => {
      const step = makeMockStep('MyStep', 's1')
      trace.addStep(step)
      trace.generateTrace()
      expect(owner.chartManager.createDataset).toHaveBeenCalledWith('MyStep')
    })

    it('assigns the dataset to the step', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.generateTrace()
      expect(step.dataset).not.toBeNull()
    })

    it('calls step.calculateData, createPoints, calculatePoints', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.generateTrace()
      expect(step.calculateData).toHaveBeenCalled()
      expect(step.createPoints).toHaveBeenCalled()
      expect(step.calculatePoints).toHaveBeenCalled()
    })
  })

  // ── select / deselect ───────────────────────────────────────────────────────

  describe('select', () => {
    it('sets selected = true', () => {
      trace.select()
      expect(trace.selected).toBe(true)
    })

    it('calls highLight on each step', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.select()
      expect(step.highLight).toHaveBeenCalled()
    })
  })

  describe('deselect', () => {
    it('sets selected = false', () => {
      trace.select()
      trace.deselect()
      expect(trace.selected).toBe(false)
    })

    it('calls deHighLight on each step', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.deselect()
      expect(step.deHighLight).toHaveBeenCalled()
    })

    it('calls deselect on each step', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.deselect()
      expect(step.deselect).toHaveBeenCalled()
    })
  })

  // ── highLight / deHighLight ─────────────────────────────────────────────────

  describe('highLight', () => {
    it('calls highLight on each step', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.highLight()
      expect(step.highLight).toHaveBeenCalled()
    })

    it('calls deHighLight first (via deHighLight)', () => {
      const step = makeMockStep()
      trace.addStep(step)
      // deHighLight called before highLight
      const order = []
      step.deHighLight.mockImplementation(() => order.push('de'))
      step.highLight.mockImplementation(() => order.push('hi'))
      trace.highLight()
      expect(order).toEqual(['de', 'hi'])
    })
  })

  describe('deHighLight', () => {
    it('calls deHighLight on all steps', () => {
      const s1 = makeMockStep('S1', 's1')
      const s2 = makeMockStep('S2', 's2')
      trace.addStep(s1)
      trace.addStep(s2)
      trace.deHighLight()
      expect(s1.deHighLight).toHaveBeenCalled()
      expect(s2.deHighLight).toHaveBeenCalled()
    })
  })

  // ── delete ──────────────────────────────────────────────────────────────────

  describe('delete', () => {
    it('calls delete on all steps', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.delete()
      expect(step.delete).toHaveBeenCalled()
    })
  })

  // ── refreshTraceData ─────────────────────────────────────────────────────────

  describe('refreshTraceData', () => {
    it('calls calculateData and calculatePoints on all steps', () => {
      const step = makeMockStep()
      trace.addStep(step)
      trace.refreshTraceData()
      expect(step.calculateData).toHaveBeenCalled()
      expect(step.calculatePoints).toHaveBeenCalled()
    })
  })

  // ── findStepByStepId ────────────────────────────────────────────────────────

  describe('findStepByStepId', () => {
    it('returns "all" when id === "all"', () => {
      expect(trace.findStepByStepId('all')).toBe('all')
    })

    it('finds a step by stepId.value', () => {
      const step = makeMockStep('S', 'target-id')
      trace.addStep(step)
      expect(trace.findStepByStepId('target-id')).toBe(step)
    })

    it('returns undefined when not found', () => {
      expect(trace.findStepByStepId('missing')).toBeUndefined()
    })
  })

  // ── findStepByProgramStepId ─────────────────────────────────────────────────

  describe('findStepByProgramStepId', () => {
    it('returns "all" when id === "all"', () => {
      expect(trace.findStepByProgramStepId('all')).toBe('all')
    })

    it('finds a step by stepId.link.programStepId', () => {
      const step = makeMockStep()
      step.stepId.link.programStepId = 'prog-42'
      trace.addStep(step)
      expect(trace.findStepByProgramStepId('prog-42')).toBe(step)
    })

    it('returns undefined when not found', () => {
      expect(trace.findStepByProgramStepId('ghost')).toBeUndefined()
    })
  })
})
