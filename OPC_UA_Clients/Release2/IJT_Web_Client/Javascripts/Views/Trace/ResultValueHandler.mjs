/**
 * The ResultValueHandler is a class that tries to display step related
 * values and their limits in the graph. FinalTorque and FinalAngle are for
 * example useful to see in a graph.
 *
 * This is not needed for displaying Traces.
 *
 * All the decisions of how to display these values relies quite a bit from
 * guesswork and might be vendor specific.
 * @date 2/23/2024 - 12:21:19 PM
 *
 * @export
 * @class ResultValueHandler
 * @typedef {ResultValueHandler}
 */
export default class ResultValueHandler {
  constructor (step, values, chartManager) {
    this.step = step
    this.values = values
    this.chartManager = chartManager
    this.graphic = null
  }

  /* ///////////////////////////////// POINT MANAGEMENT ////////////////////////////////////////////
  //                                                                                             //
  //      These functions handles displaying values as part of the results                       //
  //      They are not used to desplay the actual curves                                          //
  //                                                                                             //
  /////////////////////////////////////////////////////////////////////////////////////////////////*
  /**
   *
   * @param {*} color
   */
  createStepValues (graphic, color, displayOffset) {
    this.graphic = graphic
    if (this.values) {
      for (const value of this.values) {
        const point = this.interpretPoint(value, displayOffset)
        this.chartManager.createStepValue(value, point, color, this.graphic)
      }
    }
  }

  /**
   * Main entry for displaying a step value inside the graph.
   * Responsible for deciding if the value should be displayed or hidden
   * @date 2/23/2024 - 6:22:16 PM
   *
   * @param {*} displayOffset
   */
  calculatePoints (displayOffset) {
    for (const value of this.values) {
      if ((this.step.xDimensionName === 'angle' && parseInt(value.PhysicalQuantity) === 1) ||
        (this.step.xDimensionName === 'time' && parseInt(value.PhysicalQuantity) === 3) ||
        (!this.step.showValuesSelected)) {
        this.graphic.hideValue(value)
      }

      this.updatePoint(value, displayOffset)
    }
  }

  /**
   * Dcide if the value should be displayed, then recalculate based on offset
   * @date 2/23/2024 - 6:23:33 PM
   *
   * @param {*} value
   * @param {*} displayOffset
   */
  updatePoint (value, displayOffset) {
    const points = this.interpretPoint(value, displayOffset)
    this.graphic.updateValue(value, points)
  }

  /**
   * Awful method that tries to guess how to display point values and recalculate them with respect to how the trace currently is shown
   * @param {*} value This structure contains a target and might contain a upper and lower limit
   * @returns a structure with target, limits and name where the values have been recalculated to the selected mode of displaying the trace
   */
  interpretPoint (value, displayOffset) {
    let x; let y; let xHigh; let yHigh; let xLow; let yLow; let xTarget; let yTarget; let xOffset = 0
    switch (parseInt(value.PhysicalQuantity)) {
      case 1: // Time
        x = value.MeasuredValue
        xHigh = value.HighLimit
        xLow = value.LowLimit
        xTarget = value.TargetValue
        xOffset = this.startTimeOffset
        break
      case 2: // Torque
        y = value.MeasuredValue
        yHigh = value.HighLimit
        yLow = value.LowLimit
        yTarget = value.TargetValue
        break
      case 3: // Angle
        x = value.MeasuredValue
        xHigh = value.HighLimit
        xLow = value.LowLimit
        xTarget = value.TargetValue
        if (this.step.angle.length > 0) {
          xOffset = this.step.angle[0]
        }
        break
      default:
        throw new Error('Unknown physicalQuantity in trace [physicalQuantity=' + value.PhysicalQuantity + ']')
    }

    xHigh = value.HighLimit
    xLow = value.LowLimit
    xTarget = value.TargetValue

    // Guess where on the non described dimension it should be put
    if (y == null) {
      y = -1
      yHigh = null
      yLow = null
      yTarget = null
    }
    if (x == null) {
      x = this.step.last.x
      xHigh = null
      xLow = null
      xTarget = null
    }
    // Avoid drawing spans when high and low are not set
    if (yHigh === 0 && yLow === 0) {
      yHigh = null
      yLow = null
    }
    if (xHigh === 0 && xLow === 0) {
      xHigh = null
      xLow = null
    }

    const limits = []
    let target
    const limitYOffset = 5
    const stepOffset = displayOffset - xOffset

    if (xHigh != null) {
      limits.push({ x: xHigh - stepOffset, y: y + limitYOffset, name: '[maxlimit]', type: 'limit' })
    }
    if (yHigh != null) {
      limits.push({ x: x - stepOffset, y: yHigh + limitYOffset, name: '[maxlimit]', type: 'limit' })
    }
    const value2 = { x: x - stepOffset, y, type: '' }

    if (xLow != null) {
      limits.push({ x: xLow - stepOffset, y: y + limitYOffset, name: '[minlimit]', type: 'limit' })
    }
    if (yLow != null) {
      limits.push({ x: x - stepOffset, y: yLow + limitYOffset, name: '[minlimit]', type: 'limit' })
    }
    if (xTarget != null) {
      target = { x: xTarget - stepOffset, y: y + limitYOffset, name: '[target]', type: 'target' }
    }
    if (yTarget != null) {
      target = { x: x - stepOffset, y: yTarget + limitYOffset, name: '[target]', type: 'target' }
    }

    return {
      target,
      limits,
      value: value2,
      name: value.Name
    }
  }
}
