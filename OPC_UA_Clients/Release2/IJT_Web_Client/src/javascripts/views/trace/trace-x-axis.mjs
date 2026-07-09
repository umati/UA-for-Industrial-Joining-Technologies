export function getStepXAxisValues (step, xAxisName) {
  if (xAxisName === 'time') {
    return Array.isArray(step?.time) ? step.time : []
  }
  return Array.isArray(step?.angle) ? step.angle : []
}

export function getCanonicalX (step, sampleIndex, xAxisName) {
  const values = getStepXAxisValues(step, xAxisName)
  const rawX = Number(values[sampleIndex])
  if (!Number.isFinite(rawX)) {
    return null
  }
  if (xAxisName === 'time') {
    const startTimeOffset = Number(step?.startTimeOffset)
    return rawX + (Number.isFinite(startTimeOffset) ? startTimeOffset : 0)
  }
  return rawX
}

export function getStepCanonicalXValues (step, xAxisName) {
  const values = getStepXAxisValues(step, xAxisName)
  const canonicalValues = []
  for (let index = 0; index < values.length; index++) {
    const canonicalX = getCanonicalX(step, index, xAxisName)
    if (canonicalX !== null) {
      canonicalValues.push(canonicalX)
    }
  }
  return canonicalValues
}

export function getStepCanonicalXRange (step, xAxisName) {
  const values = getStepCanonicalXValues(step, xAxisName)
  if (values.length === 0) {
    return null
  }
  return {
    min: Math.min(...values),
    max: Math.max(...values)
  }
}
