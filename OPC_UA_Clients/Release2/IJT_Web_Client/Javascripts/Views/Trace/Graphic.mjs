/**
 * This represents the graphical element for a trace, its highlight, and
 * the step values
 * @date 3/4/2024 - 9:03:35 AM
 *
 * @export
 * @class Graphic
 * @typedef {Graphic}
 */
export default class Graphic {
  constructor (name, resultId, stepId, color) {
    this.name = name
    this.mainDataset = new Dataset(name)

    // The look of the trace
    this.mainDataset.setResultId(resultId)
    this.mainDataset.setStepId(stepId)
    this.mainDataset.setBackgroundColor(color)
    this.mainDataset.setBorderColor(color)
    this.mainDataset.setBorderWidth(1)

    // The look of highlighting of trace
    /*
    this.highlightDataset = new Dataset(name + '_highlight')
    const highlightColor = 'rgba( 255, 255, 180, 0.4 )'
    this.highlightDataset.setBackgroundColor(highlightColor)
    this.highlightDataset.setBorderColor(highlightColor)
    this.highlightDataset.setBorderWidth(5) */

    this.datasetMapping = {}
  }

  createStepValue (value, points, color) {
    function handleGroup (list, tag) {
      const dataset = new Dataset(value.Name + tag)
      // The look of a step value
      dataset.display(true)
      dataset.setBackgroundColor(color)
      dataset.setBorderColor('gray')
      dataset.setBorderWidth(1)
      dataset.setRadius(3)
      dataset.setPoints(list)
      return dataset
    }

    const res = {
      valueDataset: handleGroup([points.value], ''),
      limitsDataset: handleGroup(points.limits, '[limit]'),
      targetDataset: handleGroup([points.target], '[target]')
    }

    this.setDataSet(value.ValueId, res)
    return res
  }

  getDataSet (valueId) {
    return this.datasetMapping[valueId]
  }

  setDataSet (valueId, content) {
    this.datasetMapping[valueId] = content
  }

  clearPoints () {
    this.mainDataset.clearPoints()
    // this.highlightDataset.clearPoints()
  }

  setPoints (points) {
    this.mainDataset.setPoints(points)
    // this.highlightDataset.setPoints(points)
  }

  addPoint (point) {
    this.mainDataset.addPoint(point)
    // this.highlightDataset.addPoint(point)
  }

  updateValue (value, point) {
    const v = this.getDataSet(value.ValueId)
    v.valueDataset.data = [point.value]
    v.limitsDataset.data = point.limits
    v.targetDataset.data = [point.target]
  }

  /**
   * ecide if the trace and the step values should be displayed or hiden
   * @date 3/6/2024 - 9:13:34 AM
   *
   * @param {boolean} [showTrace=true]
   * @param {boolean} [showValue=false]
   * @param {boolean} [showLimits=false]
   */
  display (showTrace = true, showValue = false, showLimits = false) {
    this.mainDataset.display(showTrace)
    // this.highlightDataset.display(showTrace)
    for (const value of Object.values(this.datasetMapping)) {
      value.valueDataset.display(showValue)
      value.targetDataset.display(showLimits)
      value.limitsDataset.display(showLimits)
    }
  }

  /**
   * Force a step value to be totally hidden
   * @param {*} value tha step value that should be hidden
   */
  hideValue (value) {
    const dataset = this.getDataSet(value.ValueId)
    dataset.valueDataset.display(false)
    dataset.limitsDataset.display(false)
    dataset.targetDataset.display(false)
  }

  select () {
    this.mainDataset.borderWidth = 2
  }

  deselect () {
    this.mainDataset.borderWidth = 1
  }
}

/**
 * Supportclass to represent a single graphical part of a step
 * For example the trace, the highlight of the trace, or step values
 */
export class Dataset {
  constructor (name) {
    this.label = name
    this.radius = 0
    this.borderWidth = 1
  }

  display (value) {
    this.hidden = !value
  }

  setBackgroundColor (color) {
    this.backgroundColor = color
  }

  setRadius (radius) {
    this.radius = radius
  }

  setBorderColor (color) {
    this.borderColor = color
  }

  setBorderWidth (width) {
    this.borderWidth = width
  }

  clearPoints () {
    this.data = []
  }

  setPoints (points) {
    this.data = points
  }

  addPoint (point) {
    this.data.push(point)
  }

  setResultId (id) {
    this.resultId = id
  }

  setStepId (id) {
    this.stepId = id
  }
}
