import { describe, it, expect, vi, beforeEach } from 'vitest'
import TraceInterface from '../../../../javascripts/views/trace/trace-interface.mjs'

describe('TraceInterface', () => {
  let container, ti

  beforeEach(() => {
    container = document.createElement('div')
    ti = new TraceInterface(container)
  })

  // ── generateHTML ─────────────────────────────────────────────────────────────

  describe('generateHTML', () => {
    it('creates a canvas element and stores it as this.canvas', () => {
      expect(ti.canvas.tagName).toBe('CANVAS')
    })

    it('canvas has id="my-chart"', () => {
      expect(ti.canvas.getAttribute('id')).toBe('my-chart')
    })

    it('creates traceDiv for trace buttons', () => {
      expect(ti.traceDiv).toBeDefined()
      expect(ti.traceDiv.tagName).toBe('DIV')
    })

    it('creates stepDiv for step buttons', () => {
      expect(ti.stepDiv).toBeDefined()
      expect(ti.stepDiv.tagName).toBe('DIV')
    })

    it('creates a traceTypeSelect with options', () => {
      expect(ti.traceTypeSelect.tagName).toBe('SELECT')
      expect(ti.traceTypeSelect.options.length).toBeGreaterThan(0)
    })

    it('traceTypeSelect has toa and tot options', () => {
      const values = Array.from(ti.traceTypeSelect.options).map(o => o.value)
      expect(values).toContain('toa')
      expect(values).toContain('tot')
    })

    it('creates absoluteSelect', () => {
      expect(ti.absoluteSelect.tagName).toBe('SELECT')
    })

    it('creates valueShower', () => {
      expect(ti.valueShower.tagName).toBe('SELECT')
    })

    it('creates limitShower', () => {
      expect(ti.limitShower.tagName).toBe('SELECT')
    })

    it('creates deleteButton', () => {
      expect(ti.deleteButton.tagName).toBe('BUTTON')
      expect(ti.deleteButton.innerText).toBe('Delete')
    })

    it('creates alignButton', () => {
      expect(ti.alignButton.tagName).toBe('BUTTON')
      expect(ti.alignButton.innerText).toBe('Align')
    })
  })

  // ── color helpers ─────────────────────────────────────────────────────────────

  describe('color helpers', () => {
    it('getRandomColor returns an hsl string', () => {
      const color = ti.getRandomColor()
      expect(color).toMatch(/^hsl\(/)
    })

    it('getRandomColor produces different colors on successive calls', () => {
      const c1 = ti.getRandomColor()
      const c2 = ti.getRandomColor()
      expect(c1).not.toBe(c2)
    })

    it('resetColor resets hue to 0', () => {
      ti.getRandomColor()
      ti.resetColor()
      expect(ti.hue).toBe(0)
    })

    it('getRandomColor calls resetColor when lightness drops below 0', () => {
      ti.lightness = -1 // simulate depleted lightness
      const resetSpy = vi.spyOn(ti, 'resetColor')
      ti.getRandomColor()
      expect(resetSpy).toHaveBeenCalled()
    })
  })

  // ── trace list ────────────────────────────────────────────────────────────────

  describe('updateTracesInGUI', () => {
    beforeEach(() => {
      ti.setTraceSelectEventListener(vi.fn())
    })

    it('clears existing trace buttons', () => {
      const fakeBtn = document.createElement('button')
      ti.traceDiv.appendChild(fakeBtn)
      ti.updateTracesInGUI([])
      expect(ti.traceDiv.innerHTML).toBe('')
    })

    it('creates a button for each trace', () => {
      const traces = [
        { displayName: 'T1', result: { resultId: 'r1' } },
        { displayName: 'T2', result: { resultId: 'r2' } }
      ]
      ti.updateTracesInGUI(traces)
      const buttons = ti.traceDiv.querySelectorAll('button')
      expect(buttons).toHaveLength(2)
    })

    it('assigns resultId to each button', () => {
      const traces = [{ displayName: 'T1', result: { resultId: 'r-xyz' } }]
      ti.updateTracesInGUI(traces)
      const btn = ti.traceDiv.querySelector('button')
      expect(btn.resultId).toBe('r-xyz')
    })
  })

  describe('selectTrace', () => {
    beforeEach(() => {
      ti.setTraceSelectEventListener(vi.fn())
      ti.updateTracesInGUI([
        { displayName: 'T1', result: { resultId: 'r1' } },
        { displayName: 'T2', result: { resultId: 'r2' } }
      ])
    })

    it('adds my-button-selected to the matching button', () => {
      ti.selectTrace('r1')
      const buttons = ti.traceDiv.querySelectorAll('button')
      expect(buttons[0].classList.contains('my-button-selected')).toBe(true)
    })

    it('removes my-button-selected from non-matching buttons', () => {
      ti.selectTrace('r1')
      ti.selectTrace('r2')
      const buttons = ti.traceDiv.querySelectorAll('button')
      expect(buttons[0].classList.contains('my-button-selected')).toBe(false)
      expect(buttons[1].classList.contains('my-button-selected')).toBe(true)
    })
  })

  // ── step list ─────────────────────────────────────────────────────────────────

  describe('clearSteps', () => {
    beforeEach(() => {
      ti.setStepSelectEventListener(vi.fn())
    })

    it('clears stepDiv and adds an "All" button', () => {
      ti.clearSteps()
      const buttons = ti.stepDiv.querySelectorAll('button')
      expect(buttons).toHaveLength(1)
      expect(buttons[0].innerText).toBe('All')
    })
  })

  describe('addStepInGUI', () => {
    beforeEach(() => {
      ti.setStepSelectEventListener(vi.fn())
    })

    it('appends a button to stepDiv', () => {
      const before = ti.stepDiv.children.length
      ti.addStepInGUI({ name: 'Step 1', stepId: { value: 's1' } })
      expect(ti.stepDiv.children.length).toBe(before + 1)
    })

    it('button has the step name as text', () => {
      ti.addStepInGUI({ name: 'StepA', stepId: { value: 'sa' } })
      const btn = ti.stepDiv.lastElementChild
      expect(btn.innerText).toBe('StepA')
    })

    it('button carries the stepId value', () => {
      ti.addStepInGUI({ name: 'StepX', stepId: { value: 'sx' } })
      const btn = ti.stepDiv.lastElementChild
      expect(btn.stepId).toBe('sx')
    })
  })

  describe('selectStep', () => {
    beforeEach(() => {
      ti.setStepSelectEventListener(vi.fn())
      ti.addStepInGUI({ name: 'S1', stepId: { value: 's1' } })
      ti.addStepInGUI({ name: 'S2', stepId: { value: 's2' } })
    })

    it('marks the matching step button as selected', () => {
      ti.selectStep('s1')
      const btns = ti.stepDiv.querySelectorAll('button')
      expect(btns[0].classList.contains('my-button-selected')).toBe(true)
    })

    it('unmarks non-matching step buttons', () => {
      ti.selectStep('s1')
      ti.selectStep('s2')
      const btns = ti.stepDiv.querySelectorAll('button')
      expect(btns[0].classList.contains('my-button-selected')).toBe(false)
    })
  })

  // ── event listener setters ────────────────────────────────────────────────────

  describe('setTraceSelectEventListener', () => {
    it('stores the handler on the instance', () => {
      const handler = vi.fn()
      ti.setTraceSelectEventListener(handler)
      expect(ti.selectTraceEventHandler).toBe(handler)
    })
  })

  describe('setStepSelectEventListener', () => {
    it('stores the handler on the instance', () => {
      const handler = vi.fn()
      ti.setStepSelectEventListener(handler)
      expect(ti.selectStepEventHandler).toBe(handler)
    })
  })
})
