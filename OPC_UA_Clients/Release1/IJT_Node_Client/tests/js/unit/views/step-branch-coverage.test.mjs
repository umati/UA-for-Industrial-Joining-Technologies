import { describe, it, expect, vi, beforeEach } from 'vitest'
import Step from '../../../../javascripts/views/trace/step.mjs'

// Helpers mirror those in step.test.mjs (declared here because we cannot
// import from another test file; Vitest does not expose test-file helpers).

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

function makeOwnerChain ({
  xDim = 'angle',
  yDim = 'torque',
  displayOffset = 0,
  absoluteFunction = x => x,
  showValuesSelected = false,
  showLimitSelected = false
} = {}) {
  const cm = makeMockChartManager()
  const traceGraphicsMock = { xDimensionName: xDim, yDimensionName: yDim, absoluteFunction, chartManager: cm }
  const singleTraceMock = { displayOffset, showValuesSelected, showLimitSelected, chartManager: cm, owner: traceGraphicsMock }
  return { owner: singleTraceMock, cm }
}

function makeValue (valueId = 'v1') {
  return { valueId, name: 'Torque', physicalQuantity: 2, value: 15, highLimit: 20, lowLimit: 5, targetValue: 17 }
}

function makeStepWithValue (ownerOptions = {}) {
  const chain = makeOwnerChain(ownerOptions)
  const stepData = {
    stepResultId: {
      value: 'step-01',
      link: { name: 'Tighten', programStepId: 'prog-01', stepResultValues: [makeValue()] }
    },
    startTimeOffset: 0
  }
  const step = new Step(stepData, chain.owner)
  step.dataset = makeMockDataset('main')
  step.angle = [0, 10, 20, 30]
  step.torque = [5, 10, 15, 20]
  step.time = [0, 100, 200, 300]
  const valueDataset = makeMockDataset('v1-value')
  const limitsDataset = makeMockDataset('v1-limits')
  const targetDataset = makeMockDataset('v1-target')
  step.datasetMapping['v1'] = { valueDataset, limitsDataset, targetDataset }
  return { step, cm: chain.cm, valueDataset, limitsDataset, targetDataset, owner: chain.owner }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Step — branch coverage: methods with non-empty values', () => {
  // ── hideValue ─────────────────────────────────────────────────────────────────

  describe('hideValue()', () => {
    it('hides valueDataset', () => {
      const { step, valueDataset } = makeStepWithValue()
      step.hideValue({ valueId: 'v1' })
      expect(valueDataset.hidden).toBe(true)
    })

    it('hides limitsDataset', () => {
      const { step, limitsDataset } = makeStepWithValue()
      step.hideValue({ valueId: 'v1' })
      expect(limitsDataset.hidden).toBe(true)
    })

    it('hides targetDataset', () => {
      const { step, targetDataset } = makeStepWithValue()
      step.hideValue({ valueId: 'v1' })
      expect(targetDataset.hidden).toBe(true)
    })
  })

  // ── hideValues ────────────────────────────────────────────────────────────────

  describe('hideValues()', () => {
    it('iterates values and hides each one', () => {
      const { step, valueDataset } = makeStepWithValue()
      step.hideValues()
      expect(valueDataset.hidden).toBe(true)
    })
  })

  // ── showStepTrace — with non-empty values ─────────────────────────────────────

  describe('showStepTrace() with a populated values array', () => {
    it('calls displayValuesAccordingToSettings for each value', () => {
      const { step } = makeStepWithValue()
      const spy = vi.spyOn(step, 'displayValuesAccordingToSettings')
      step.showStepTrace()
      expect(spy).toHaveBeenCalledOnce()
    })

    it('shows valueDataset when showValuesSelected is true', () => {
      const { step, valueDataset } = makeStepWithValue({ showValuesSelected: true })
      step.showStepTrace()
      expect(valueDataset.hidden).toBe(false)
    })
  })

  // ── displayValuesAccordingToSettings ──────────────────────────────────────────

  describe('displayValuesAccordingToSettings()', () => {
    it('hides everything when showValue=false', () => {
      const { step, valueDataset, limitsDataset, targetDataset } = makeStepWithValue()
      valueDataset.show()
      limitsDataset.show()
      targetDataset.show()
      step.displayValuesAccordingToSettings({ valueId: 'v1' }, false, false)
      expect(valueDataset.hidden).toBe(true)
      expect(limitsDataset.hidden).toBe(true)
      expect(targetDataset.hidden).toBe(true)
    })

    it('shows valueDataset when showValue=true, hides limits when showLimits=false', () => {
      const { step, valueDataset, limitsDataset } = makeStepWithValue()
      step.displayValuesAccordingToSettings({ valueId: 'v1' }, true, false)
      expect(valueDataset.hidden).toBe(false)
      expect(limitsDataset.hidden).toBe(true)
    })

    it('shows all datasets when showValue=true and showLimits=true', () => {
      const { step, valueDataset, limitsDataset, targetDataset } = makeStepWithValue()
      step.displayValuesAccordingToSettings({ valueId: 'v1' }, true, true)
      expect(valueDataset.hidden).toBe(false)
      expect(limitsDataset.hidden).toBe(false)
      expect(targetDataset.hidden).toBe(false)
    })
  })

  // ── calculatePoints ───────────────────────────────────────────────────────────

  describe('calculatePoints()', () => {
    it('hides the dataset when showValuesSelected=false', () => {
      const { step, valueDataset } = makeStepWithValue({ showValuesSelected: false })
      step.calculatePoints()
      expect(valueDataset.hidden).toBe(true)
    })

    it('shows the value when showValuesSelected=true and physicalQuantity matches', () => {
      const { step, valueDataset } = makeStepWithValue({ showValuesSelected: true })
      // physicalQuantity=2 (TORQUE) and xDimensionName='angle' → NOT hidden
      step.calculatePoints()
      expect(valueDataset.hidden).toBe(false)
    })

    it('hides when angle dimension filters out PHYS_TIME value', () => {
      const chain = makeOwnerChain({ showValuesSelected: true })
      const stepData = {
        stepResultId: {
          value: 's1',
          link: { name: 'N', programStepId: 'p', stepResultValues: [{ valueId: 'vt', physicalQuantity: 1, value: 5 }] }
        },
        startTimeOffset: 0
      }
      const step = new Step(stepData, chain.owner)
      step.dataset = makeMockDataset('main')
      step.angle = [0]; step.torque = [1]; step.time = [0]
      const vds = makeMockDataset('vds')
      const lds = makeMockDataset('lds')
      const tds = makeMockDataset('tds')
      step.datasetMapping['vt'] = { valueDataset: vds, limitsDataset: lds, targetDataset: tds }
      // xDimensionName='angle' and physicalQuantity=PHYS_TIME → hide=true
      step.calculatePoints()
      expect(vds.hidden).toBe(true)
    })
  })
})
