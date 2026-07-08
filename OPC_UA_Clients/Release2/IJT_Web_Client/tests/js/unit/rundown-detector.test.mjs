import { describe, expect, it, vi } from 'vitest'
import { detectRundownEndX, detectRundownZoomRange } from '../../../src/javascripts/views/trace/rundown-detector.mjs'
import TraceDisplay from '../../../src/javascripts/views/trace/trace-display.mjs'

function makeStep ({ torque, angle, time, startTimeOffset = '0', name = 'Step', stepType = null }) {
  return {
    torque,
    angle,
    time,
    startTimeOffset,
    name,
    stepId: {
      link: {
        Name: name,
        StepType: stepType,
        ProgramStepId: name
      }
    }
  }
}

function makeTrace (steps) {
  return { steps }
}

describe('detectRundownZoomRange', () => {
  it('returns snug and max x for torque-over-angle when rundown exists', () => {
    const trace = makeTrace([
      makeStep({
        torque: [0, 1, 2, 6, 30, 60],
        angle: [0, 1, 2, 3, 4, 5],
        time: [0, 1, 2, 3, 4, 5]
      })
    ])

    const range = detectRundownZoomRange(trace, 'angle')

    expect(range).toEqual({ minX: 0, snugX: 3, maxX: 5 })
  })

  it('returns snug and max x for torque-over-time and includes step offsets', () => {
    const trace = makeTrace([
      makeStep({
        torque: [0, 0, 1, 2],
        angle: [0, 1, 2, 3],
        time: [0, 1, 2, 3],
        startTimeOffset: '10'
      }),
      makeStep({
        torque: [8, 40],
        angle: [0, 1],
        time: [0, 1],
        startTimeOffset: '20'
      })
    ])

    const range = detectRundownZoomRange(trace, 'time')

    expect(range).toEqual({ minX: 10, snugX: 20, maxX: 21 })
  })

  it('returns null when no initial rundown exists', () => {
    const trace = makeTrace([
      makeStep({
        torque: [7, 20, 40],
        angle: [0, 1, 2],
        time: [0, 1, 2]
      })
    ])

    expect(detectRundownZoomRange(trace, 'angle')).toBeNull()
  })

  it('returns null when no snug point can be found from a non-positive torque curve', () => {
    const trace = makeTrace([
      makeStep({
        torque: [0, 0, 0, 0, 0],
        angle: [0, 1, 2, 3, 4],
        time: [0, 1, 2, 3, 4]
      })
    ])

    expect(detectRundownZoomRange(trace, 'angle')).toBeNull()
  })

  it('aligns displayed traces on rundown end when available', () => {
    const traceWithRundown = makeTrace([
      makeStep({
        torque: [0, 1, 2, 6, 30, 60],
        angle: [0, 1, 2, 3, 4, 5],
        time: [0, 1, 2, 3, 4, 5],
        name: 'Rundown'
      }),
      makeStep({
        torque: [70, 80],
        angle: [5, 6],
        time: [5, 6],
        name: 'Tightening'
      })
    ])
    const traceWithoutRundown = makeTrace([
      makeStep({
        torque: [10, 20, 30],
        angle: [0, 1, 2],
        time: [0, 1, 2]
      })
    ])
    const display = Object.create(TraceDisplay.prototype)
    const onRundownAlignmentUpdated = vi.fn()
    Object.assign(display, {
      allTraces: [traceWithRundown, traceWithoutRundown],
      xDimensionName: 'angle',
      refreshAllData: vi.fn(),
      traceManager: { onRundownAlignmentUpdated }
    })

    expect(display.alignTracesOnRundownEnd()).toBe(true)
    expect(traceWithRundown.displayOffset).toBe(5)
    expect(traceWithoutRundown.displayOffset).toBe(0)
    expect(display.refreshAllData).toHaveBeenCalledOnce()
    expect(onRundownAlignmentUpdated).toHaveBeenCalledWith([
      expect.objectContaining({ rundownEndX: 5, displayOffset: 5 }),
      expect.objectContaining({ rundownEndX: null, displayOffset: 0 })
    ])
  })

  it('detects the explicit rundown step end for angle and time axes', () => {
    const trace = makeTrace([
      makeStep({
        torque: [0, 1],
        angle: [2, 7],
        time: [0, 3],
        startTimeOffset: '10',
        name: 'Initial Rundown'
      }),
      makeStep({
        torque: [30, 50],
        angle: [7, 8],
        time: [0, 1],
        startTimeOffset: '20',
        name: 'Tightening'
      })
    ])

    expect(detectRundownEndX(trace, 'angle')).toBe(7)
    expect(detectRundownEndX(trace, 'time')).toBe(13)
  })

  it('detects rundown steps from StepType metadata even when the display name is generic', () => {
    const trace = makeTrace([
      makeStep({
        torque: [0, 1],
        angle: [0, 466.93],
        time: [0, 1],
        name: 'Step 2',
        stepType: 'rundown'
      })
    ])

    expect(detectRundownEndX(trace, 'angle')).toBe(466.93)
  })
})
