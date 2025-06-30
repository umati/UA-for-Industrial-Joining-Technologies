/**
 * This represents the result of violating a limit
 *
 * @class Trigger
 * @typedef {Violation}
 */
export default class Violation {
  constructor (name, tag, stepData, violationResult) {
    this.name = name
    this.tag = tag
    this.step = stepData.step
    this.stepTrace = stepData.steptrace
    this.stepTraceIndex = stepData.index
    this.rangeName = violationResult.rangeName
    this.rangeValue = violationResult.rangeValue
    this.valueName = violationResult.name
    this.value = violationResult.value
    this.limit = violationResult.limit
  }
}
