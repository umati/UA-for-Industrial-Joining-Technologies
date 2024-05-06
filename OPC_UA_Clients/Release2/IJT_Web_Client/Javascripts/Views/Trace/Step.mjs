// import ChartManager from './ChartHandler.mjs'
import ResultValueHandler from './ResultValueHandler.mjs'

export default class Step {
  constructor (step, owner, nr, chartManager, resultId, color, displayOffset) {
    this.name = step.StepResultId.link.Name
    this.stepId = step.StepResultId
    this.resultId = resultId
    this.nr = nr
    this.chartManager = chartManager
    this.color = color
    this.time = null
    this.torque = null
    this.angle = null
    this.hidden = false
    this.last = {}
    this.startTimeOffset = step.StartTimeOffset
    this.graphic = []
    this.owner = owner
    this.resultValueHandler = new ResultValueHandler(this, step.StepResultId.link.StepResultValues, chartManager)

    for (const data of step.StepTraceContent) {
      switch (parseInt(data.PhysicalQuantity)) {
        case 1: // Time
          this.time = data.Values
          break
        case 2: // Torque
          this.torque = data.Values
          break
        case 3: // Angle
          this.angle = data.Values
          break
        case 11: // Current
          break
        default:
          throw new Error('Unknown physicalQuantity in trace')
      }
    }
    if (!this.time) {
      this.time = Array.from(Array(this.torque.length), (_, x) => parseFloat(step.SamplingInterval * x / 1000))
    }

    this.graphic = chartManager.createGraphic(this.name, this.resultId, this.stepId, this.color)
    this.graphic.display(!this.hidden, !this.hidden && this.showValuesSelected, !this.hidden && this.showLimitSelected)

    this.calculateData(displayOffset)
    this.resultValueHandler.createStepValues(this.graphic, this.color, displayOffset)
    this.resultValueHandler.calculatePoints(0, this.showLimitSelected)
  }

  get xDimensionName () {
    return this.owner.owner.xDimensionName
  }

  get yDimensionName () {
    return this.owner.owner.yDimensionName
  }

  get absoluteFunction () {
    return this.owner.owner.absoluteFunction
  }

  get showValuesSelected () {
    return this.owner.showValuesSelected
  }

  get showLimitSelected () {
    return this.owner.showLimitSelected
  }

  fade (fractionFade) {
    this.graphic.fade(fractionFade)
  }

  /**
   * This function changes the angle values in the graph if offset
   * is set to some other point than the start value.
   * displayOffset is used to calculate this and taken from the owner of this class
   * For example snug is often used as 0 angle
   * @date 2/16/2024 - 9:18:15 AM
   *
   * @param {*} displayOffset the angle you want all x values to decrease
   */
  calculateData (displayOffset) {
    let xValues = this[this.xDimensionName]
    const yValues = this[this.yDimensionName].map(this.absoluteFunction)

    if (this.xDimensionName === 'time') {
      const startTimeOffset = parseFloat(this.startTimeOffset)
      xValues = xValues.map((x) => { return x + startTimeOffset })
    }
    this.graphic.clearPoints()

    if (xValues.length !== yValues.length) { // Error handling
      if (!this.name) {
        this.name = 'number ' + this.nr
      }
      throw new Error('In step ' + this.name +
      ' there are not the same number of trace sample points in the ' + this.xDimensionName +
      ' and ' + this.yDimensionName + ' lists')
    }

    for (let i = 0; i < xValues.length; i++) {
      this.graphic.addPoint({
        x: xValues[i] - displayOffset,
        y: parseFloat(yValues[i])
      })
    }

    this.last.x = xValues[xValues.length - 1]
    this.last.y = yValues[yValues.length - 1]
  }

  /**
   * Refresh all the data by recalculating based on new offset
   * @param {*} offset
   */
  refresh (offset) {
    this.graphic.display(!this.hidden, !this.hidden && this.showValuesSelected, !this.hidden && this.showLimitSelected)
    this.calculateData(offset) // Trace
    this.resultValueHandler.calculatePoints(offset) // Step values
  }

  /// ////////////////////////////////////////////////////
  //                                                   //
  //    Support functions                              //
  //                                                   //
  /// ////////////////////////////////////////////////////

  delete () {
    // this.resultValueHandler.deleteValues()
    this.chartManager.filterOutGraphic(this.graphic)
  }

  select () {
    this.graphic.select()
  }

  deselect () {
    this.graphic.deselect()
  }

  /*
  highLight () {

  }

  deHighLight () {

  } */

  /// //////////////////////////////////////////////////////////////////////
  //                                                                     //
  //    These methods help with hiding or showing traces and values      //
  //                                                                     //
  /// //////////////////////////////////////////////////////////////////////

  hideStepTrace () {
    this.hidden = true
    this.graphic.display(!this.hidden, false, false) // Hide the trace curve
    // this.resultValueHandler.hideValues() // Hide the reported step values
  }

  showStepTrace () {
    this.hidden = false
    this.graphic.display(!this.hidden, this.showValuesSelected, this.showLimitSelected) // Show the trace curve
  }
}
