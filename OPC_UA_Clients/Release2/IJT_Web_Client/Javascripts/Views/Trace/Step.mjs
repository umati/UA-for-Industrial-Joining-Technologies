// import ChartManager from './ChartHandler.mjs'
import ResultValueHandler from './ResultValueHandler.mjs'

export default class Step {
  constructor (step, owner, nr, chartManager, resultId, color) {
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
    this.datasetMapping = {}
    this.startTimeOffset = step.StartTimeOffset
    this.dataset = []
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

    const dataset = chartManager.createDataset(this.name)

    dataset.show()
    dataset.setResultId(this.resultId)
    dataset.setStepId(this.stepId)
    dataset.setBackgroundColor(this.color)
    dataset.setBorderColor(this.color)
    dataset.setBorderWidth(1)

    this.dataset = dataset
    this.calculateData(0)
    this.resultValueHandler.createPoints(this.color, 0)
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
    this.dataset.data = []
    if (xValues.length !== yValues.length) {
      if (!this.name) {
        this.name = 'number ' + this.nr
      }
      throw new Error('In step ' + this.name +
      ' there are not the same number of trace sample points in the ' + this.xDimensionName +
      ' and ' + this.yDimensionName + ' lists')
    }
    for (let i = 0; i < xValues.length; i++) {
      this.dataset.data.push({
        x: xValues[i] - displayOffset,
        y: parseFloat(yValues[i])
      })
    }

    this.last.x = xValues[xValues.length - 1]
    this.last.y = yValues[yValues.length - 1]
    if (this.highLightDataset) {
      this.highLightDataset.data = this.dataset.data
    }
  }

  /**
   * Refresh all the data by recalculating based on new offset
   * @param {*} offset
   */
  refresh (offset) {
    this.calculateData(offset)
    this.resultValueHandler.calculatePoints(offset, this.showLimitSelected)
  }

  /// ////////////////////////////////////////////////////
  //                                                   //
  //    Support functions                              //
  //                                                   //
  /// ////////////////////////////////////////////////////

  delete () {
    for (const value of Object.values(this.datasetMapping)) {
      this.chartManager.filterOut([value.valueDataset, value.targetDataset, value.limitsDataset])
    }
    this.chartManager.filterOut([this.highLightDataset, this.dataset])
  }

  select () {
    this.dataset.select()
  }

  deselect () {
    this.dataset.deselect()
  }

  highLight () {
    if (!this.highLightDataset) {
      this.highLightDataset = this.chartManager.createDataset('highlight')
      const color = 'rgba( 255, 255, 180, 0.4 )'
      this.highLightDataset.setBackgroundColor(color)
      this.highLightDataset.setBorderColor(color)
      this.highLightDataset.setBorderWidth(5)
    }
    this.highLightDataset.setPoints(this.dataset.data)
    if (this.hidden) {
      this.highLightDataset.hide()
    } else {
      this.highLightDataset.show()
    }
  }

  deHighLight () {
    if (this.highLightDataset) {
      this.highLightDataset.hide()
    }
  }

  createHighlightDataset () {
    if (this.hidden) {
      return
    }
    const dataset = this.chartManager.createDataset('highlight')
    dataset.show()
    const color = 'rgba( 255, 255, 180, 0.4 )'
    dataset.setBackgroundColor(color)
    dataset.setBorderColor(color)
    dataset.setBorderWidth(5)
    dataset.setPoints(this.dataset.data)
    return dataset
  }

  /// //////////////////////////////////////////////////////////////////////
  //                                                                     //
  //    These methods help with hiding or showing traces and values      //
  //                                                                     //
  /// //////////////////////////////////////////////////////////////////////

  hideStepTrace () {
    this.dataset.hide() // Hide the trace curve
    this.hidden = true
    this.resultValueHandler.hideValues() // Hide the reported step values
  }

  showStepTrace () {
    this.dataset.show() // Show the trace curve
    this.hidden = false
    this.resultValueHandler.showValues(this.showValuesSelected, this.showLimitSelected) // Show the reported step values
  }

  getDataSet (valueId) {
    return this.datasetMapping[valueId]
  }

  setDataSet (valueId, content) {
    this.datasetMapping[valueId] = content
  }
}
