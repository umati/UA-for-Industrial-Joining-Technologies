import Violation from './Violation.mjs'

/**
 * Description placeholder
 *
 * @export
 * @class Limit
 * @typedef {Limit}
 */
export default class Limit {
  /**
   * Creates an instance of Limit.
   *
   * @constructor
   * @param {*} trigger Decides where the check is triggered
   * @param {*} polynomial The curve to check against
   * @param {*} check How is a violation decided (above, below, many times, etc)
   * @param {*} rangeDimension What should the unit should the axis have
   * @param {*} range negative and positive extension of the checked range
   * @param {*} severity a value between 0 and 100 to put on the violation
   * @param {*} tag a string tag to put on the violation
   */
  constructor (name, trigger, polynomial, check, rangeDimension, range, severity, tag) {
    this.name = name
    this.trigger = trigger
    this.polynomial = polynomial
    this.check = check
    this.rangeDimension = rangeDimension
    this.range = new Range(rangeDimension, range[0], range[1])
    this.severity = severity
    this.tag = tag
  }

  get firstTrigger () {
    return -1
  }

  checkResult (result) {
    if (result?.ResultMetaData.Classification !== '1') {
      throw new Error('Only check single results')
    }

    if (!result?.ResultContent[0].Trace) {
      throw new Error('No trace in result')
    }

    this.check.reset() // The check might be stateful

    const simplifiedTrace = result.simplifyAllTracePoints()

    const triggerIndex = this.trigger.firstTriggerIndex(result, simplifiedTrace)

    const xAxisValues = simplifiedTrace[this.rangeDimension]
    const xAxisZero = xAxisValues[triggerIndex]

    this.range.setOffset(xAxisZero, triggerIndex)
    this.range.findLimitingIndicies(xAxisValues)

    for (let i = this.range.startIndex; i < this.range.endIndex; i++) {
      const v = this.check.violation(i, simplifiedTrace, this.rangeDimension, this.polynomial)
      if (v) {
        const stepData = result.simplifiedTraceToStepAndIndex(i)
        return new Violation(this.name, this.tag, stepData, v)
      }
    }
  }
}

class Range {
  constructor (dimension, backwards, forwards, index) {
    this.dimension = dimension
    this.backwards = backwards
    this.forwards = forwards
    this.start = null
    this.startIndex = null
    this.end = null
    this.endIndex = null
    this.offset = null
    this.offsetIndex = index
  }

  setOffset (offset, index) {
    this.offset = offset
    this.offsetIndex = index
    this.start = parseFloat(offset) + this.backwards
    this.end = parseFloat(offset) + this.forwards
  }

  findLimitingIndicies (trace) {
    let back = this.offsetIndex
    while ((back >= 0) && (trace[back] > this.start) && (trace[back] < this.end)) {
      back--
    }
    let forward = this.offsetIndex
    while ((forward < trace.length) && (trace[forward] > this.start) && (trace[forward] < this.end)) {
      forward++
    }
    this.startIndex = back
    this.endIndex = forward
  }
}
