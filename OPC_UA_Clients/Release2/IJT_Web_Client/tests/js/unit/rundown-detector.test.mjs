import { describe, expect, it } from 'vitest'
import { detectRundownZoomRange } from '../../../src/javascripts/views/trace/rundown-detector.mjs'

function makeStep ({ torque, angle, time, startTimeOffset = '0' }) {
  return {
    torque,
    angle,
    time,
    startTimeOffset
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
})
