const RUNDOWN_THRESHOLD_RATIO = 0.05

function toNumber (value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

function resolveXValue (step, sampleIndex, xDimensionName) {
  if (xDimensionName === 'time') {
    const baseTime = toNumber(step.time?.[sampleIndex])
    if (baseTime === null) {
      return null
    }
    const startTimeOffset = toNumber(step.startTimeOffset) ?? 0
    return baseTime + startTimeOffset
  }
  return toNumber(step.angle?.[sampleIndex])
}

export function isRundownStep (step) {
  const candidates = [
    step?.name,
    step?.stepType,
    step?.stepId?.link?.Name,
    step?.stepId?.link?.StepType,
    step?.stepId?.link?.ProgramStepId,
    step?.stepId?.link?.StepResultId,
    step?.StepResultId?.link?.Name,
    step?.StepResultId?.link?.StepType,
    step?.StepResultId?.link?.ProgramStepId,
    step?.StepResultId?.link?.StepResultId
  ]
  return candidates.some((value) => typeof value === 'string' && value.toLowerCase().includes('rundown'))
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

  const snugX = resolveXValue(samples[snugIndex].step, samples[snugIndex].sampleIndex, xDimensionName)
  if (snugX === null) {
    return null
  }

  let minX = Infinity
  let maxX = -Infinity
  for (const sample of samples) {
    const xValue = resolveXValue(sample.step, sample.sampleIndex, xDimensionName)
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

export function detectRundownEndX (trace, xDimensionName) {
  const rundownStep = (trace?.steps ?? []).find(isRundownStep)
  if (!rundownStep) {
    return null
  }
  const sourceValues = xDimensionName === 'time' ? rundownStep.time : rundownStep.angle
  if (!Array.isArray(sourceValues) || sourceValues.length === 0) {
    return null
  }
  for (let index = sourceValues.length - 1; index >= 0; index--) {
    const xValue = resolveXValue(rundownStep, index, xDimensionName)
    if (xValue !== null) {
      return xValue
    }
  }
  return null
}
