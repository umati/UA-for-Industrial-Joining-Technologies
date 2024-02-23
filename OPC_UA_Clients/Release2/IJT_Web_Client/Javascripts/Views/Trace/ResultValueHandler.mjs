/**
 * The ResultValueHandler is a class that tries to display step related
 * values and their limits in the graph. FinalTorque and FinalAngle are for
 * example useful to see in a graph
 * All the decisions of how to display these values relies quite a bit from
 * guesswork and might be vendor specific
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
  createPoints (color, displayOffset) {
    if (this.values) {
      for (const value of this.values) {
        const point = this.interpretPoint(value, displayOffset)
        const datasets = this.createDatasets(value.Name, point, color)

        this.step.setDataSet(value.ValueId, {
          valueDataset: datasets.value,
          limitsDataset: datasets.limits,
          targetDataset: datasets.target
        })
      }
    }
  }

  /**
   * Main entry for displaying a step value inside the graph.
   * Responsible for deciding if the value should be displayed or hidden
   * @date 2/23/2024 - 6:22:16 PM
   *
   * @param {*} displayOffset
   * @param {*} limits
   */
  calculatePoints (displayOffset, limits) {
    for (const value of this.values) {
      let show = !this.step.hidden
      if ((this.step.xDimensionName === 'angle' && parseInt(value.PhysicalQuantity) === 1) ||
        (this.step.xDimensionName === 'time' && parseInt(value.PhysicalQuantity) === 3) ||
        (!this.step.showValuesSelected)) {
        show = false
      }

      this.updatePoint(value, displayOffset, show, limits)
    }
  }

  /**
   * Dcide if the value should be displayed, then recalculate based on offset
   * @date 2/23/2024 - 6:23:33 PM
   *
   * @param {*} value
   * @param {*} displayOffset
   * @param {*} show
   * @param {*} limits
   */
  updatePoint (value, displayOffset, show, limits) {
    this.displayValuesAccordingToSettings(value, show, limits)

    if (show) {
      const points = this.interpretPoint(value, displayOffset)
      const dataset = this.step.getDataSet(value.ValueId)
      dataset.valueDataset.data = [points.value]
      dataset.limitsDataset.data = points.limits
      dataset.targetDataset.data = [points.target]
    }
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

  createDatasets (name, points, color) {
    const res = {}
    function handleGroup (list, tag, chartManager) {
      const dataset = chartManager.createDataset(name + tag)
      dataset.show()
      dataset.setBackgroundColor(color)
      dataset.setBorderColor('gray')
      dataset.setBorderWidth(1)
      dataset.setRadius(3)
      dataset.setPoints(list)
      return dataset
    }

    res.value = handleGroup([points.value], '', this.chartManager)
    res.limits = handleGroup(points.limits, '[limit]', this.chartManager)
    res.target = handleGroup([points.target], '[target]', this.chartManager)

    return res
  }

  hideValues () {
    for (const value of this.values) {
      this.hideValue(value)
    }
  }

  hideValue (value) {
    const dataset = this.step.getDataSet(value.ValueId)
    dataset.valueDataset.hide()
    dataset.limitsDataset.hide()
    dataset.targetDataset.hide()
  }

  showValues (showValuesSelected, showLimitSelected) {
    for (const value of this.values) {
      this.displayValuesAccordingToSettings(value, showValuesSelected, showLimitSelected)
    }
  }

  displayValuesAccordingToSettings (value, showValue, showLimits) {
    this.hideValue(value)
    if (showValue) {
      const dataset = this.step.getDataSet(value.ValueId)
      dataset.valueDataset.show()
      if (showLimits) {
        dataset.limitsDataset.show()
        dataset.targetDataset.show()
      }
    }
  }
}
