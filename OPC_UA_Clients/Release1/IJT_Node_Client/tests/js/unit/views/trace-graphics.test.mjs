import { describe, it, expect, vi, beforeEach } from 'vitest'

// chart-handler.mjs must be mocked so we avoid the real Chart.js canvas
// rendering path in TraceGraphics.
vi.mock('../../../../javascripts/views/trace/chart-handler.mjs', () => {
  class MockChartManager {
    constructor (canvas, traceManager) {
      this.canvas = canvas
      this.traceManager = traceManager
      this._datasets = []
    }

    createDataset (name) {
      const ds = {
        label: name,
        data: [],
        hidden: false,
        resultId: null,
        stepId: null,
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

    filterOut (list) {
      this._datasets = this._datasets.filter(d => !list.includes(d))
    }

    putInFront (list) {
      this.filterOut(list)
      list.forEach(d => this._datasets.push(d))
    }
  }

  return { default: MockChartManager }
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

function makeResultManager () {
  return { subscribe: vi.fn() }
}

function makeMinimalModel () {
  return {
    resultId: 'r-1',
    creationTime: '2024-01-01T10:20:30Z',
    resultContent: {
      trace: {
        stepTraces: [] // empty — no Step objects needed
      }
    }
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TraceGraphics', () => {
  let as, rm, tg

  beforeEach(() => {
    as = makeAddressSpace()
    rm = makeResultManager()
    tg = new TraceGraphics(['angle', 'torque'], as, rm)
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('title is "Traces"', () => {
    expect(tg.title).toBe('Traces')
  })

  it('xDimensionName is the first dimension', () => {
    expect(tg.xDimensionName).toBe('angle')
  })

  it('yDimensionName is the second dimension', () => {
    expect(tg.yDimensionName).toBe('torque')
  })

  it('allTraces starts empty', () => {
    expect(tg.allTraces).toHaveLength(0)
  })

  it('selectedTrace starts null', () => {
    expect(tg.selectedTrace).toBeNull()
  })

  it('subscribes to "subscription" on connectionManager', () => {
    expect(as.connectionManager.subscribe).toHaveBeenCalledWith(
      'subscription', expect.any(Function)
    )
  })

  // ── activate ────────────────────────────────────────────────────────────────

  describe('activate', () => {
    it('calls resultManager.subscribe', () => {
      tg.activate()
      expect(rm.subscribe).toHaveBeenCalledOnce()
    })

    it('subscription fires true triggers activate', () => {
      as.connectionManager._trigger('subscription', true)
      expect(rm.subscribe).toHaveBeenCalled()
    })
  })

  // ── initiate ────────────────────────────────────────────────────────────────

  it('initiate() is a no-op', () => {
    expect(() => tg.initiate()).not.toThrow()
  })

  // ── setAbsolutes / removeAbsolutes ───────────────────────────────────────────

  describe('setAbsolutes', () => {
    it('makes absoluteFunction return Math.abs', () => {
      tg.setAbsolutes()
      expect(tg.absoluteFunction(-5)).toBe(5)
    })
  })

  describe('removeAbsolutes', () => {
    it('makes absoluteFunction return identity', () => {
      tg.setAbsolutes()
      tg.removeAbsolutes()
      expect(tg.absoluteFunction(-5)).toBe(-5)
    })
  })

  // ── convertDimension ─────────────────────────────────────────────────────────

  describe('convertDimension', () => {
    it('returns "x" for xDimensionName', () => {
      expect(tg.convertDimension('angle')).toBe('x')
    })

    it('returns "y" for yDimensionName', () => {
      expect(tg.convertDimension('torque')).toBe('y')
    })

    it('throws for unknown dimension', () => {
      expect(() => tg.convertDimension('speed')).toThrow('Dimension does not match trace axis')
    })
  })

  // ── findExtremes ─────────────────────────────────────────────────────────────

  describe('findExtremes', () => {
    it('returns min/max from step.angle when xDimensionName is angle', () => {
      const step = { angle: [5, 2, 8, 1], time: [0, 1, 2, 3] }
      const result = tg.findExtremes(step)
      expect(result.min).toBe(1)
      expect(result.max).toBe(8)
    })

    it('returns min/max from step.time when xDimensionName is time', () => {
      tg.xDimensionName = 'time'
      const step = { angle: [5, 2, 8], time: [10, 3, 7] }
      const result = tg.findExtremes(step)
      expect(result.min).toBe(3)
      expect(result.max).toBe(10)
    })
  })

  // ── showPoints / showLimits ──────────────────────────────────────────────────

  describe('showPoints', () => {
    it('sets showValuesSelected=true when "yes"', () => {
      tg.showPoints('yes')
      expect(tg.showValuesSelected).toBe(true)
    })

    it('sets showValuesSelected=false when not "yes"', () => {
      tg.showPoints('yes')
      tg.showPoints('no')
      expect(tg.showValuesSelected).toBe(false)
    })
  })

  describe('showLimits', () => {
    it('sets showLimitSelected=true when "yes"', () => {
      tg.showLimits('yes')
      expect(tg.showLimitSelected).toBe(true)
    })

    it('sets showLimitSelected=false when not "yes"', () => {
      tg.showLimits('no')
      expect(tg.showLimitSelected).toBe(false)
    })
  })

  // ── decideTraceType ──────────────────────────────────────────────────────────

  describe('decideTraceType', () => {
    it('"toa" sets xDimensionName to "angle"', () => {
      tg.decideTraceType('toa')
      expect(tg.xDimensionName).toBe('angle')
    })

    it('"tot" sets xDimensionName to "time"', () => {
      tg.decideTraceType('tot')
      expect(tg.xDimensionName).toBe('time')
    })

    it('unknown type throws', () => {
      expect(() => tg.decideTraceType('xyz')).toThrow('No matching type of trace')
    })
  })

  // ── deselectTrace ────────────────────────────────────────────────────────────

  describe('deselectTrace', () => {
    it('returns early when no selectedTrace', () => {
      expect(() => tg.deselectTrace()).not.toThrow()
    })

    it('clears selectedTrace and calls chartManager.update', () => {
      const mockTrace = {
        steps: [],
        resultId: 'r1',
        select: vi.fn(),
        deselect: vi.fn(),
        deHighLight: vi.fn(),
        highLight: vi.fn()
      }
      tg.selectedTrace = mockTrace
      tg.deselectTrace()
      expect(tg.selectedTrace).toBeNull()
      expect(tg.chartManager.update).toHaveBeenCalled()
    })
  })

  // ── deleteSelected ───────────────────────────────────────────────────────────

  describe('deleteSelected', () => {
    it('throws when no trace is selected', () => {
      expect(() => tg.deleteSelected()).toThrow('No trace selected')
    })

    it('removes selected trace from allTraces', () => {
      const mockTrace = {
        steps: [],
        resultId: 'r1',
        select: vi.fn(),
        deselect: vi.fn(),
        deHighLight: vi.fn(),
        highLight: vi.fn(),
        delete: vi.fn()
      }
      tg.allTraces = [mockTrace]
      tg.selectedTrace = mockTrace
      tg.deleteSelected()
      expect(tg.allTraces).toHaveLength(0)
    })

    it('calls chartManager.update when no traces remain', () => {
      const mockTrace = {
        steps: [],
        resultId: 'r1',
        select: vi.fn(),
        deselect: vi.fn(),
        deHighLight: vi.fn(),
        highLight: vi.fn(),
        delete: vi.fn()
      }
      tg.allTraces = [mockTrace]
      tg.selectedTrace = mockTrace
      tg.deleteSelected()
      expect(tg.chartManager.update).toHaveBeenCalled()
    })
  })

  // ── findTrace ────────────────────────────────────────────────────────────────

  describe('findTrace', () => {
    it('finds a trace by resultId', () => {
      const t = { result: { resultId: 'r-42' }, steps: [] }
      tg.allTraces = [t]
      expect(tg.findTrace('r-42')).toBe(t)
    })

    it('returns undefined when not found', () => {
      expect(tg.findTrace('ghost')).toBeUndefined()
    })
  })

  // ── createNewTrace ───────────────────────────────────────────────────────────

  describe('createNewTrace', () => {
    it('ignores models without a trace', () => {
      tg.createNewTrace({ resultId: 'x', resultContent: {} })
      expect(tg.allTraces).toHaveLength(0)
    })

    it('ignores models where resultContent is absent', () => {
      tg.createNewTrace({})
      expect(tg.allTraces).toHaveLength(0)
    })

    it('adds a trace entry for a valid model with empty stepTraces', () => {
      tg.createNewTrace(makeMinimalModel())
      expect(tg.allTraces).toHaveLength(1)
    })

    it('sets the selectedTrace to the newly created trace', () => {
      tg.createNewTrace(makeMinimalModel())
      expect(tg.selectedTrace).not.toBeNull()
    })

    it('increments identityCounter for each trace', () => {
      tg.createNewTrace(makeMinimalModel())
      tg.createNewTrace({ ...makeMinimalModel(), resultId: 'r-2' })
      expect(tg.identityCounter).toBe(2)
    })
  })

  // ── refreshAllData ────────────────────────────────────────────────────────────

  describe('refreshAllData', () => {
    it('does nothing when allTraces is empty', () => {
      expect(() => tg.refreshAllData()).not.toThrow()
    })

    it('calls refreshTraceData on every trace', () => {
      const trace = { refreshTraceData: vi.fn() }
      tg.allTraces = [trace]
      tg.refreshAllData()
      expect(trace.refreshTraceData).toHaveBeenCalled()
    })
  })
})
