import { describe, expect, it, vi } from 'vitest'

let traceDisplayConstructorPromise = null

class FakeClassList {
  constructor () {
    this.classes = new Set()
  }

  add (...classNames) {
    for (const className of classNames) {
      this.classes.add(className)
    }
  }

  remove (...classNames) {
    for (const className of classNames) {
      this.classes.delete(className)
    }
  }

  contains (className) {
    return this.classes.has(className)
  }
}

class FakeElement {
  constructor () {
    this.classList = new FakeClassList()
    this.attributes = {}
    this.title = ''
  }

  setAttribute (name, value) {
    this.attributes[name] = value
  }

  querySelector () {
    return null
  }

  dispatchEvent () {}
}

function installFakeDom () {
  const previous = {
    window: globalThis.window,
    document: globalThis.document,
    CustomEvent: globalThis.CustomEvent,
    Chart: globalThis.Chart
  }
  globalThis.window = {
    performance,
    requestAnimationFrame (callback) {
      callback()
      return 1
    },
    setTimeout (callback) {
      callback()
      return 1
    },
    clearTimeout () {}
  }
  globalThis.document = {
    body: new FakeElement(),
    querySelector: () => null,
    querySelectorAll: () => []
  }
  globalThis.CustomEvent = class CustomEvent {
    constructor (type, options = {}) {
      this.type = type
      this.detail = options.detail
    }
  }
  globalThis.Chart = class Chart {}

  return () => {
    restoreGlobal('window', previous.window)
    restoreGlobal('document', previous.document)
    restoreGlobal('CustomEvent', previous.CustomEvent)
    restoreGlobal('Chart', previous.Chart)
  }
}

function restoreGlobal (name, value) {
  if (value === undefined) {
    delete globalThis[name]
    return
  }
  globalThis[name] = value
}

async function loadTraceDisplayConstructor () {
  if (!traceDisplayConstructorPromise) {
    traceDisplayConstructorPromise = import('../../../src/javascripts/views/trace/trace-display.mjs')
      .then((module) => module.default)
  }
  return traceDisplayConstructorPromise
}

function makeTraceDisplay (TraceDisplay, allTraces, xDimensionName = 'angle') {
  const zoomCalls = []
  const traceDisplay = Object.create(TraceDisplay.prototype)
  traceDisplay.canvasCoverLayer = new FakeElement()
  traceDisplay.fullscreenButton = new FakeElement()
  traceDisplay.fullscreenResizeTimer = null
  traceDisplay.allTraces = allTraces
  traceDisplay.xDimensionName = xDimensionName
  traceDisplay.traceManager = {}
  traceDisplay.chartManager = {
    myChart: {
      resize: vi.fn()
    },
    update: vi.fn(),
    setXZoom (minX, maxX) {
      zoomCalls.push({ minX, maxX })
    }
  }
  traceDisplay.zoomCalls = zoomCalls
  return traceDisplay
}

function makeTrace ({ displayOffset = 0, steps }) {
  return { displayOffset, steps }
}

describe('TraceDisplay fullscreen x-axis zoom', () => {
  it('zooms the expanded trace screen to the latest trace x-range', async () => {
    const restoreDom = installFakeDom()
    try {
      const TraceDisplay = await loadTraceDisplayConstructor()
      const olderTrace = makeTrace({
        steps: [{ angle: [-200, 400], time: [0, 1] }]
      })
      const latestTrace = makeTrace({
        displayOffset: 100,
        steps: [
          { angle: [100, 110], time: [0, 1] },
          { angle: [120, 150], time: [2, 3] }
        ]
      })
      const traceDisplay = makeTraceDisplay(TraceDisplay, [olderTrace, latestTrace])

      traceDisplay.enterFullscreen()

      expect(traceDisplay.zoomCalls).toEqual([{ minX: 0, maxX: 50 }])
      expect(traceDisplay.canvasCoverLayer.classList.contains('is-trace-fullscreen')).toBe(true)
    } finally {
      restoreDom()
    }
  })

  it('includes time offsets when expanding a torque-over-time trace screen', async () => {
    const restoreDom = installFakeDom()
    try {
      const TraceDisplay = await loadTraceDisplayConstructor()
      const latestTrace = makeTrace({
        displayOffset: 10,
        steps: [
          { angle: [0, 1], time: [0, 5], startTimeOffset: '20' },
          { angle: [2, 3], time: [0, 7], startTimeOffset: '30' }
        ]
      })
      const traceDisplay = makeTraceDisplay(TraceDisplay, [latestTrace], 'time')

      traceDisplay.enterFullscreen()

      expect(traceDisplay.zoomCalls).toEqual([{ minX: 10, maxX: 27 }])
    } finally {
      restoreDom()
    }
  })
})
