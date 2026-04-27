import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Mocks (hoisted before imports) ───────────────────────────────────────────

vi.mock('views/trace/chart-handler.mjs', () => {
  class MockChartManager {
    constructor () { this._datasets = [] }

    createDataset (name) {
      const ds = {
        label: name, data: [], hidden: false, resultId: null, stepId: null,
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
      this._datasets.push(ds)
      return ds
    }

    update = vi.fn()
    filterOut (list) { this._datasets = this._datasets.filter(d => !list.includes(d)) }
    putInFront (list) { this.filterOut(list); list.forEach(d => this._datasets.push(d)) }
  }
  return { default: MockChartManager }
})

// Mock SingleTraceData so createNewTrace produces controllable trace objects
vi.mock('views/trace/single-trace-data.mjs', () => {
  class MockSingleTraceData {
    constructor (result, owner) {
      this.result = result
      this.resultId = result.resultId
      this.displayOffset = 0
      this.steps = []
      this.selected = false
      this.displayName = result.creationTime.substr(11, 5)
      this.owner = owner
    }

    addStep (step) { this.steps.push(step) }
    generateTrace () {}
    select () {}
    deselect () {}
    delete () {}
    highLight () {}
    deHighLight () {}
    refreshTraceData () {}

    findStepByProgramStepId (id) {
      if (id === 'all') return 'all'
      return this.steps.find(s => s.stepId.link.programStepId === id)
    }
  }
  return { default: MockSingleTraceData }
})

// Mock Step so createNewTrace produces controllable step objects
vi.mock('views/trace/step.mjs', () => {
  class MockStep {
    constructor (step, owner) {
      this.name = step.stepResultId.link.name
      this.stepId = step.stepResultId
      this.color = ''
      this.time = null
      this.torque = null
      this.angle = null
      this.hidden = false
      this.values = step.stepResultId.link.stepResultValues
      this.owner = owner
    }

    showStepTrace () { this.hidden = false }
    hideStepTrace () { this.hidden = true }
    select () {}
    deselect () {}
  }
  return { default: MockStep }
})

import TraceGraphics from '../../../../javascripts/views/trace/trace-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAddressSpace () {
  const subs = []
  return {
    connectionManager: {
      subscribe: vi.fn((trigger, cb) => subs.push({ trigger, cb })),
      _trigger (t, v) { subs.filter(s => s.trigger === t).forEach(s => s.cb(v)) }
    }
  }
}

let _stepId = 0
let _traceId = 0

function makeStepData (programStepId = 'p1', values = []) {
  const id = 'step-' + (++_stepId)
  return {
    startTimeOffset: 0,
    samplingInterval: 100,
    stepResultId: {
      value: id,
      link: { name: 'Step' + _stepId, programStepId, stepResultValues: values }
    }
  }
}

function makeModel (stepDataList, resultId) {
  return {
    resultId: resultId || ('r-adv-' + (++_traceId)),
    creationTime: '2024-01-01T10:20:30Z',
    resultContent: {
      trace: {
        stepTraces: stepDataList.map(sd => ({
          startTimeOffset: sd.startTimeOffset,
          samplingInterval: sd.samplingInterval,
          stepResultId: sd.stepResultId,
          stepTraceContent: sd.stepTraceContent || []
        }))
      }
    }
  }
}

// Build a mock trace for use in direct-method tests (not via createNewTrace)
function makeTestTrace (steps) {
  const resultId = 'r-direct-' + (++_traceId)
  return {
    result: { resultId },
    resultId,
    displayName: 'TestTrace',
    displayOffset: 0,
    steps,
    select: vi.fn(),
    deselect: vi.fn(),
    highLight: vi.fn(),
    deHighLight: vi.fn(),
    delete: vi.fn(),
    refreshTraceData: vi.fn(),
    findStepByProgramStepId (id) {
      if (id === 'all') return 'all'
      return steps.find(s => s.stepId.link.programStepId === id)
    }
  }
}

// Build a mock step for use in direct-method tests
function makeTestStep (id, programStepId, angle = [0, 1, 2], time = [0, 100, 200]) {
  return {
    name: 'Step-' + id,
    stepId: { value: id, link: { name: 'Step-' + id, programStepId } },
    angle,
    time,
    hidden: false,
    showStepTrace () { this.hidden = false },
    hideStepTrace () { this.hidden = true },
    select: vi.fn(),
    deselect: vi.fn()
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TraceGraphics — advanced coverage', () => {
  let as, rm, tg

  beforeEach(() => {
    _stepId = 0
    _traceId = 0
    as = makeAddressSpace()
    rm = { subscribe: vi.fn() }
    tg = new TraceGraphics(['angle', 'torque'], as, rm)
  })

  // ── createNewTrace — physicalQuantity switch cases ────────────────────────────

  describe('createNewTrace with step data', () => {
    it('physicalQuantity=2 (torque): sets step.torque', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [
        { physicalQuantity: 2, values: [10, 20, 30, 40] },
        { physicalQuantity: 3, values: [0, 5, 10, 15] }
      ]
      tg.createNewTrace(makeModel([sd]))
      expect(tg.allTraces[0].steps[0].torque).toEqual([10, 20, 30, 40])
    })

    it('physicalQuantity=3 (angle): sets step.angle', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [
        { physicalQuantity: 2, values: [10, 20, 30, 40] },
        { physicalQuantity: 3, values: [0, 5, 10, 15] }
      ]
      tg.createNewTrace(makeModel([sd]))
      expect(tg.allTraces[0].steps[0].angle).toEqual([0, 5, 10, 15])
    })

    it('physicalQuantity=1 (time): sets step.time', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [
        { physicalQuantity: 1, values: [0, 100, 200, 300] },
        { physicalQuantity: 2, values: [10, 20, 30, 40] }
      ]
      tg.createNewTrace(makeModel([sd]))
      expect(tg.allTraces[0].steps[0].time).toEqual([0, 100, 200, 300])
    })

    it('physicalQuantity=11 (current): no-op, no error', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [
        { physicalQuantity: 11, values: [] },
        { physicalQuantity: 2, values: [10, 20, 30] }
      ]
      expect(() => tg.createNewTrace(makeModel([sd]))).not.toThrow()
    })

    it('unknown physicalQuantity throws', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [{ physicalQuantity: 99, values: [] }]
      expect(() => tg.createNewTrace(makeModel([sd]))).toThrow('Unknown physicalQuantity')
    })

    it('auto-generates time from samplingInterval when time is not present', () => {
      const sd = makeStepData('p1')
      sd.samplingInterval = 200
      sd.stepTraceContent = [{ physicalQuantity: 2, values: [10, 20, 30] }]
      tg.createNewTrace(makeModel([sd]))
      const step = tg.allTraces[0].steps[0]
      expect(step.time).not.toBeNull()
      expect(step.time.length).toBe(3)
    })

    it('adds the step to the trace steps array', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [{ physicalQuantity: 2, values: [1, 2] }]
      tg.createNewTrace(makeModel([sd]))
      expect(tg.allTraces[0].steps).toHaveLength(1)
    })

    it('time is not auto-generated when physicalQuantity=1 is present', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [
        { physicalQuantity: 1, values: [0, 50, 100] },
        { physicalQuantity: 2, values: [5, 10, 15] }
      ]
      tg.createNewTrace(makeModel([sd]))
      // time was set from physicalQuantity=1, not auto-generated
      expect(tg.allTraces[0].steps[0].time).toEqual([0, 50, 100])
    })
  })

  // ── selectTrace — inner loop for steps ────────────────────────────────────────

  describe('selectTrace with steps', () => {
    it('addStepInGUI is called for each step (button appears in stepDiv)', () => {
      const sd = makeStepData('p1')
      sd.stepTraceContent = [{ physicalQuantity: 2, values: [1, 2] }]
      tg.createNewTrace(makeModel([sd]))
      // stepDiv should contain the "All" button plus one step button
      const buttons = tg.traceInterface.stepDiv.querySelectorAll('button')
      expect(buttons.length).toBeGreaterThan(1)
    })

    it('direct selectTrace with a mock trace having steps covers inner loop', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.selectTrace(trace)
      expect(tg.selectedTrace).toBe(trace)
    })

    it('selectTrace calls trace.select()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.selectTrace(trace)
      expect(trace.select).toHaveBeenCalled()
    })

    it('selectTrace deselectes existing trace before selecting new one', () => {
      const stepA = makeTestStep('sa', 'pa')
      const traceA = makeTestTrace([stepA])
      const stepB = makeTestStep('sb', 'pb')
      const traceB = makeTestTrace([stepB])
      tg.allTraces = [traceA, traceB]
      tg.selectTrace(traceA)
      tg.selectTrace(traceB)
      expect(traceA.deselect).toHaveBeenCalled()
    })
  })

  // ── selectStep ────────────────────────────────────────────────────────────────

  describe('selectStep', () => {
    let traceWithSteps, step1, step2

    beforeEach(() => {
      step1 = makeTestStep('s1', 'p1')
      step2 = makeTestStep('s2', 'p2')
      traceWithSteps = makeTestTrace([step1, step2])
      tg.allTraces = [traceWithSteps]
      tg.selectedTrace = traceWithSteps
    })

    it('sets selectedStep to the matching step', () => {
      tg.selectStep('s1')
      expect(tg.selectedStep).toBe(step1)
    })

    it('calls select() on the matching step', () => {
      tg.selectStep('s1')
      expect(step1.select).toHaveBeenCalled()
    })

    it('calls deselect() on non-matching steps', () => {
      tg.selectStep('s1')
      expect(step2.deselect).toHaveBeenCalled()
    })

    it('sets selectedStep null when no step matches', () => {
      tg.selectStep('nonexistent')
      expect(tg.selectedStep).toBeNull()
    })

    it('calls chartManager.update() for each step', () => {
      tg.selectStep('s1')
      // update is called once per step in the loop
      expect(tg.chartManager.update).toHaveBeenCalled()
    })

    it('calls deHighLight on selectedTrace', () => {
      tg.selectStep('s1')
      expect(traceWithSteps.deHighLight).toHaveBeenCalled()
    })
  })

  // ── applyToAll — error case ───────────────────────────────────────────────────

  describe('applyToAll', () => {
    it('throws when trace.steps is empty', () => {
      const emptyTrace = { steps: [] }
      expect(() => tg.applyToAll(emptyTrace, null, () => {})).toThrow('No trace selected for applyToAll')
    })
  })

  // ── align → applyToAll → alignByProgramStepId ─────────────────────────────────

  describe('align', () => {
    it('align(trace, null) sets displayOffset to 0 for all traces', () => {
      const step = makeTestStep('s1', 'p1', [3, 5, 7])
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.align(trace, null) // null → programStepId='all' → displayOffset=0
      expect(trace.displayOffset).toBe(0)
    })

    it('align with specific step sets displayOffset to findExtremes.min (angle)', () => {
      const innerStep = makeTestStep('s1', 'p1', [3, 5, 7])
      const trace = makeTestTrace([innerStep])
      tg.allTraces = [trace]
      const refStep = { stepId: { link: { programStepId: 'p1' } } }
      tg.align(trace, refStep)
      // xDimensionName='angle', angle=[3,5,7] → min=3
      expect(trace.displayOffset).toBe(3)
    })

    it('align with specific step uses time when xDimensionName is "time"', () => {
      tg.xDimensionName = 'time'
      const innerStep = makeTestStep('s1', 'p1', [10, 20], [2, 4, 6])
      const trace = makeTestTrace([innerStep])
      tg.allTraces = [trace]
      const refStep = { stepId: { link: { programStepId: 'p1' } } }
      tg.align(trace, refStep)
      // time=[2,4,6] → min=2
      expect(trace.displayOffset).toBe(2)
    })

    it('align calls trace.highLight()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.align(trace, null)
      expect(trace.highLight).toHaveBeenCalled()
    })

    it('align calls refreshAllData()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      const spy = vi.spyOn(tg, 'refreshAllData')
      tg.align(trace, null)
      expect(spy).toHaveBeenCalled()
    })

    it('align calls chartManager.update()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.align(trace, null)
      expect(tg.chartManager.update).toHaveBeenCalled()
    })
  })

  // ── zoom → applyToAll → zoomByProgramStepId ──────────────────────────────────

  describe('zoom', () => {
    it('zoom(trace, null) shows ALL steps', () => {
      const step1 = makeTestStep('s1', 'p1')
      const step2 = makeTestStep('s2', 'p2')
      step1.hidden = true
      step2.hidden = true
      const trace = makeTestTrace([step1, step2])
      tg.allTraces = [trace]
      tg.zoom(trace, null)
      expect(step1.hidden).toBe(false)
      expect(step2.hidden).toBe(false)
    })

    it('zoom with specific step shows matching step and hides others', () => {
      const step1 = makeTestStep('s1', 'p1')
      const step2 = makeTestStep('s2', 'p2')
      const trace = makeTestTrace([step1, step2])
      tg.allTraces = [trace]
      const refStep = { stepId: { link: { programStepId: 'p1' } } }
      tg.zoom(trace, refStep)
      expect(step1.hidden).toBe(false) // matches 'p1' → shown
      expect(step2.hidden).toBe(true) // doesn't match → hidden
    })

    it('zoom calls trace.highLight()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.zoom(trace, null)
      expect(trace.highLight).toHaveBeenCalled()
    })

    it('zoom calls chartManager.update()', () => {
      const step = makeTestStep('s1', 'p1')
      const trace = makeTestTrace([step])
      tg.allTraces = [trace]
      tg.zoom(trace, null)
      expect(tg.chartManager.update).toHaveBeenCalled()
    })
  })

  // ── deleteSelected — remaining trace branch ───────────────────────────────────

  describe('deleteSelected with remaining traces', () => {
    it('selects the last remaining trace after deleting the current one', () => {
      const trace1 = makeTestTrace([])
      const trace2 = makeTestTrace([])
      tg.allTraces = [trace1, trace2]
      tg.selectedTrace = trace1
      tg.deleteSelected()
      expect(tg.selectedTrace).toBe(trace2)
    })

    it('calls select() on the newly selected trace', () => {
      const trace1 = makeTestTrace([])
      const trace2 = makeTestTrace([])
      tg.allTraces = [trace1, trace2]
      tg.selectedTrace = trace1
      tg.deleteSelected()
      expect(trace2.select).toHaveBeenCalled()
    })

    it('removes the deleted trace from allTraces', () => {
      const trace1 = makeTestTrace([])
      const trace2 = makeTestTrace([])
      tg.allTraces = [trace1, trace2]
      tg.selectedTrace = trace1
      tg.deleteSelected()
      expect(tg.allTraces).not.toContain(trace1)
      expect(tg.allTraces).toContain(trace2)
    })
  })
})
