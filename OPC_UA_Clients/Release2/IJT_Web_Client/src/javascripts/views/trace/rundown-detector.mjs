import { getCanonicalX } from './trace-x-axis.mjs'

const RUNDOWN_THRESHOLD_RATIO = 0.05

function toNumber (value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

function buildOrderedSamples (trace) {
  const samples = []
  for (const step of trace?.steps ?? []) {
    const torqueValues = Array.isArray(step?.torque) ? step.torque : []
    for (let i = 0; i < torqueValues.length; i++) {
      const torque = toNumber(torqueValues[i])
      if (torque === null) {
        continue
      }
      samples.push({
        step,
        sampleIndex: i,
        torque
      })
    }
  }
  return samples
}

/**
 * Find snug-point x-position and end of x-range when an initial rundown exists.
 * Rundown: initial contiguous torque samples below 5% of max torque.
 * Snug: first sample where torque rises above that threshold.
 *
 * @param {*} trace single displayed trace object
 * @param {'angle'|'time'} xDimensionName displayed x-axis dimension
 * @returns {{ minX: number, snugX: number, maxX: number }|null}
 */
export function detectRundownZoomRange (trace, xDimensionName) {
  const samples = buildOrderedSamples(trace)
  if (samples.length < 2) {
    return null
  }

  const maxTorque = Math.max(...samples.map((sample) => sample.torque))
  if (!Number.isFinite(maxTorque) || maxTorque <= 0) {
    return null
  }

  const threshold = maxTorque * RUNDOWN_THRESHOLD_RATIO
  const snugIndex = samples.findIndex((sample) => sample.torque > threshold)

  if (snugIndex <= 0) {
    return null
  }

  const snugX = getCanonicalX(samples[snugIndex].step, samples[snugIndex].sampleIndex, xDimensionName)
  if (snugX === null) {
    return null
  }

  let minX = Infinity
  let maxX = -Infinity
  for (const sample of samples) {
    const xValue = getCanonicalX(sample.step, sample.sampleIndex, xDimensionName)
    if (xValue !== null) {
      if (xValue < minX) {
        minX = xValue
      }
      if (xValue > maxX) {
        maxX = xValue
      }
    }
  }

  if (!Number.isFinite(minX) || !Number.isFinite(maxX) || maxX <= snugX) {
    return null
  }

  return { minX, snugX, maxX }
}
