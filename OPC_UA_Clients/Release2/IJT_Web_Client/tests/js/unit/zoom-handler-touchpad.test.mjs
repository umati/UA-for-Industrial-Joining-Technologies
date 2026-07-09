import { describe, expect, it, vi } from 'vitest'
import ZoomHandler from '../../../src/javascripts/views/trace/zoom-handler.mjs'

function makeHandler () {
  const zoomCalls = []
  const chartManager = {
    getZoom: vi.fn(() => ({
      left: 0,
      right: 100,
      top: 0,
      bottom: 50
    })),
    getWindowDimensions: vi.fn(() => ({
      width: 500,
      height: 250
    })),
    zoom: vi.fn((lower, upper) => {
      zoomCalls.push({ lower, upper })
    })
  }
  const handler = new ZoomHandler({
    canvasCoverLayer: {},
    chartManager
  })
  return { handler, chartManager, zoomCalls }
}

describe('ZoomHandler touchpad wheel gestures', () => {
  it('pans the trace for touchpad two-finger scroll', () => {
    const { handler, zoomCalls } = makeHandler()

    handler.onmousewheel({ deltaX: 50, deltaY: 25, deltaMode: 0, ctrlKey: false }, { x: 50, y: 25 })

    expect(zoomCalls).toEqual([{
      lower: { x: 10, y: 5 },
      upper: { x: 110, y: 55 }
    }])
  })

  it('keeps touchpad pinch gestures as zoom', () => {
    const { handler, zoomCalls } = makeHandler()

    handler.onmousewheel({ deltaX: 0, deltaY: 20, deltaMode: 0, ctrlKey: true }, { x: 50, y: 25 })

    expect(zoomCalls).toEqual([{
      lower: { x: -10, y: -5 },
      upper: { x: 110, y: 55 }
    }])
  })

  it('allows touchpad pinch zoom to scale x and y independently when both deltas are available', () => {
    const { handler, zoomCalls } = makeHandler()

    handler.onmousewheel({ deltaX: 10, deltaY: 20, deltaMode: 0, ctrlKey: true }, { x: 50, y: 25 })

    expect(zoomCalls).toHaveLength(1)
    expect(zoomCalls[0].lower.x).toBeCloseTo(-5)
    expect(zoomCalls[0].lower.y).toBeCloseTo(-5)
    expect(zoomCalls[0].upper.x).toBeCloseTo(105)
    expect(zoomCalls[0].upper.y).toBeCloseTo(55)
  })

  it('keeps coarse mouse wheel gestures as zoom', () => {
    const { handler, zoomCalls } = makeHandler()

    handler.onmousewheel({ deltaX: 0, deltaY: 120, deltaMode: 0, ctrlKey: false }, { x: 50, y: 25 })

    expect(zoomCalls).toEqual([{
      lower: { x: -12, y: -6 },
      upper: { x: 112, y: 56 }
    }])
  })
})
