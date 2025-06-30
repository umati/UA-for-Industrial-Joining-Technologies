/* jshint esversion:6 */
import math from './math.min.js'

function adjust () {
  function getMaxDiscrepancy (polynomial, values, top) {
    let maxDiscrepancy = 0
    for (const value of values) {
      const discrepancy = value[1] - polynomial.value(value[0])
      if (top) {
        if (discrepancy > maxDiscrepancy) {
          maxDiscrepancy = discrepancy
        }
      } else {
        if (discrepancy < maxDiscrepancy) {
          maxDiscrepancy = discrepancy
        }
      }
    }
    return maxDiscrepancy
  }

  const steps = stepHandler.fixSteps()

  for (const thisStep of steps) {
    let discrepancy = getMaxDiscrepancy(thisStep.upperPolynomial, thisStep.maxValues, true) + 0.001

    thisStep.upperPolynomial[thisStep.upperPolynomial.length - 1] =
      parseFloat(thisStep.upperPolynomial[thisStep.upperPolynomial.length - 1] + discrepancy)

    discrepancy = getMaxDiscrepancy(thisStep.lowerPolynomial, thisStep.minValues, false) - 0.001
    thisStep.lowerPolynomial[thisStep.lowerPolynomial.length - 1] =
      parseFloat(thisStep.lowerPolynomial[thisStep.lowerPolynomial.length - 1] + discrepancy)

    if (steps.length > 1) {
      thisStep.showLimits(traceHandler.activeTrace)
    } else {
      thisStep.showLimits()
    }
  }
  myChart.update()
}

function automate () {
  const steps = stepHandler.fixSteps()

  for (const thisStep of steps) {
    const stepTraceArray = createAngelSortedArrays(thisStep)
    const [minVals, maxVals] = minMax(stepTraceArray, 1)
    // let b = math.transpose(math.matrix(minVals))

    const upperPolynomial = polynomialObject.calculateLeastSquaresPolynomial(
      math.transpose(math.matrix(maxVals)),
      degree)
    const lowerPolynomial = polynomialObject.calculateLeastSquaresPolynomial(
      math.transpose(math.matrix(minVals)),
      degree)

    thisStep.upperPolynomial = upperPolynomial
    thisStep.maxValues = maxVals
    thisStep.lowerPolynomial = lowerPolynomial
    thisStep.minValues = minVals
    if (steps.length > 1) {
      thisStep.showLimits(traceHandler.activeTrace)
    } else {
      thisStep.showLimits()
    }
  }
  myChart.update()
}

function minMax (stepTraceArray, segmentLength) {
  const resMax = []
  const resMin = []
  let angle = 0
  for (const tr of stepTraceArray) {
    if (tr && tr.length > 0 && tr[0][0] < angle) {
      angle = tr[0][0]
    }
  }
  while (stepTraceArray.length > 0) {
    const [vals, tmp] = findAllBetween(angle, angle + segmentLength, stepTraceArray)
    stepTraceArray = tmp
    const maxV = vals.reduce(function (a, b) {
      if (a[1] > b[1]) {
        return a
      } else {
        return b
      }
    })
    const minV = vals.reduce(function (a, b) {
      if (a[1] < b[1]) {
        return a
      } else {
        return b
      }
    })
    if (resMax.length === 0) {
      resMax.push([maxV[0] - segmentLength, maxV[1]])
      resMin.push([minV[0] - segmentLength, minV[1]])
    }
    resMax.push(maxV)
    resMin.push(minV)
    angle += segmentLength
  }
  return [resMin, resMax]
}

function findAllBetween (start, end, traces) {
  const trs = []
  const res = []
  for (const el of traces) {
    let index = 0
    // const thisValue = el[index]
    while (index < el.length && el[index][0] >= start && el[index][0] <= end) {
      index++
    }
    const vals = el.slice(0, index)
    const rest = el.slice(index, el.length)
    res.push(...vals)
    if (rest.length) {
      trs.push(rest)
    }
  }
  return [res, trs]
}

function createAngelSortedArrays (thisStep) {
  const resList = []
  for (const el of traceHandler.traceList) {
    if (el.trace.legalTrace) {
      const segment = math.transpose(
        el.trace.getIntervalIndex(
          el.trace.steps[thisStep.name].start,
          el.trace.steps[thisStep.name].end,
          true)
      ).valueOf()
      const sortedSegment = sortAngleTrace(segment)
      resList.push(sortedSegment)
    }
  }
  return resList
}

function anglePointToTrace (trace, thisValue) {
  if (trace.length === 0) {
    trace.push(thisValue)
  } else {
    let position = 0
    while (position < trace.length && thisValue[0] < trace[position][0]) {
      position++
    }
    trace.splice(position, 0, thisValue)
  }
}

function sortAngleTrace (limitValues) {
  const res = []
  for (const thisValue of limitValues) {
    anglePointToTrace(res, thisValue)
  }
  return res.reverse()
}
