import { describe, it, expect, vi, beforeEach } from 'vitest'

// Must mock chart-handler.mjs (it pulls in Chart.js which can't run in jsdom).
vi.mock('../../../../javascripts/views/trace/chart-handler.mjs', () => ({
  default: class MockChartManager {
    constructor () { this._datasets = [] }
    createDataset (name) {
      const ds = {
        label: name, data: [], hidden: false,
        show () { this.hidden = false },
        hide () { this.hidden = true },
        setBackgroundColor: vi.fn(),
        setBorderColor: vi.fn(),
        setBorderWidth: vi.fn(),
        setRadius: vi.fn(),
        setPoints (p) { this.data = p },
        select () {},
        deselect () {}
      }
      this._datasets.push(ds)
      return ds
    }

    update = vi.fn()
    filterOut (list) { this._datasets = this._datasets.filter(d => !list.includes(d)) }
    putInFront (list) { this.filterOut(list); list.forEach(d => this._datasets.push(d)) }
  }
}))

import TraceGraphics from '../../../../javascripts/views/trace/trace-graphics.mjs'

function makeAddressSpace () {
  const subs = []
  return {
    connectionManager: {
      subscribe: vi.fn((trigger, cb) => subs.push({ trigger, cb })),
      _trigger (t, v) { subs.filter(s => s.trigger === t).forEach(s => s.cb(v)) }
    }
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TraceGraphics — setupEventListeners branch coverage', () => {
  let tg, as, rm

  beforeEach(() => {
    as = makeAddressSpace()
    rm = { subscribe: vi.fn() }
    tg = new TraceGraphics(['angle', 'torque'], as, rm)
  })

  // ── valueShower click ─────────────────────────────────────────────────────────

  it('valueShower click calls showPoints with the selected option value', () => {
    const spy = vi.spyOn(tg, 'showPoints')
    tg.traceInterface.valueShower.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalledWith(
      tg.traceInterface.valueShower.options[tg.traceInterface.valueShower.selectedIndex].value
    )
  })

  // ── limitShower click ─────────────────────────────────────────────────────────

  it('limitShower click calls showLimits with the selected option value', () => {
    const spy = vi.spyOn(tg, 'showLimits')
    tg.traceInterface.limitShower.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalledWith(
      tg.traceInterface.limitShower.options[tg.traceInterface.limitShower.selectedIndex].value
    )
  })

  // ── deleteButton click ────────────────────────────────────────────────────────

  it('deleteButton click calls deleteSelected', () => {
    const spy = vi.spyOn(tg, 'deleteSelected').mockImplementation(() => {})
    tg.traceInterface.deleteButton.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalledOnce()
  })

  // ── alignButton click ─────────────────────────────────────────────────────────

  it('alignButton click calls align', () => {
    const spy = vi.spyOn(tg, 'align').mockImplementation(() => {})
    tg.traceInterface.alignButton.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalledOnce()
  })

  // ── absoluteSelect click — absolute branch ────────────────────────────────────

  it('absoluteSelect click with "absolute" option calls setAbsolutes', () => {
    const spy = vi.spyOn(tg, 'setAbsolutes')
    // The second option (index 1) has value 'absolute'
    tg.traceInterface.absoluteSelect.selectedIndex = 1
    tg.traceInterface.absoluteSelect.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalled()
  })

  // ── absoluteSelect click — normal branch ──────────────────────────────────────

  it('absoluteSelect click with "normal" option calls removeAbsolutes', () => {
    const spy = vi.spyOn(tg, 'removeAbsolutes')
    // The first option (index 0) has value 'normal'
    tg.traceInterface.absoluteSelect.selectedIndex = 0
    tg.traceInterface.absoluteSelect.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalled()
  })

  // ── traceTypeSelect click ─────────────────────────────────────────────────────

  it('traceTypeSelect click calls decideTraceType with selected value', () => {
    const spy = vi.spyOn(tg, 'decideTraceType')
    tg.traceInterface.traceTypeSelect.selectedIndex = 0 // 'toa'
    tg.traceInterface.traceTypeSelect.dispatchEvent(new Event('click'))
    expect(spy).toHaveBeenCalledWith('toa')
  })

  // ── clicked() — different resultId ───────────────────────────────────────────

  it('clicked() calls selectTrace when resultId differs from selectedTrace', () => {
    const mockTrace = {
      result: { resultId: 'r-1' },
      steps: [],
      resultId: 'r-1',
      displayName: 'Trace 1',
      select: vi.fn(),
      deselect: vi.fn(),
      highLight: vi.fn(),
      deHighLight: vi.fn()
    }
    tg.allTraces = [mockTrace]
    tg.selectedTrace = { ...mockTrace, resultId: 'r-other', result: { resultId: 'r-other' } }
    const spy = vi.spyOn(tg, 'selectTrace').mockImplementation(() => {})
    tg.clicked('r-1', 'step-1')
    expect(spy).toHaveBeenCalled()
  })

  // ── clicked() — same resultId ─────────────────────────────────────────────────

  it('clicked() calls selectStep when resultId matches selectedTrace', () => {
    tg.selectedTrace = {
      resultId: 'r-same',
      steps: [],
      deHighLight: vi.fn(),
      select: vi.fn(),
      deselect: vi.fn()
    }
    const spy = vi.spyOn(tg, 'selectStep').mockImplementation(() => {})
    tg.clicked('r-same', 'step-99')
    expect(spy).toHaveBeenCalledWith('step-99')
  })
})
