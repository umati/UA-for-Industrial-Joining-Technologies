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
    const handleGroup = (list, tag) => {
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

  fade (fractionFade) {
    // for (const ds of Object.values(this.datasetMapping)) {
    this.mainDataset.fade(fractionFade)
    // }
  }

  setTransparency (fractionTransparency) {
    this.mainDataset.setTransparency(fractionTransparency)
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
    this._baseBackgroundColor = null
    this._baseBorderColor = null
  }

  display (value) {
    this.hidden = !value
  }

  setBackgroundColor (color) {
    this.backgroundColor = color
    this._baseBackgroundColor = color
  }

  setRadius (radius) {
    this.radius = radius
  }

  setBorderColor (color) {
    this.borderColor = color
    this._baseBorderColor = color
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

  fade (fractionFade) {
    this.backgroundColor = this.fadeSupport(fractionFade, this.backgroundColor)
    this.borderColor = this.fadeSupport(fractionFade, this.borderColor)
  }

  setTransparency (fractionTransparency) {
    const transparency = Number.isFinite(fractionTransparency) ? Math.max(0, Math.min(1, fractionTransparency)) : 0
    const alphaMultiplier = 1 - transparency
    if (typeof this._baseBackgroundColor === 'string') {
      this.backgroundColor = this.applyAlphaMultiplier(this._baseBackgroundColor, alphaMultiplier)
    }
    if (typeof this._baseBorderColor === 'string') {
      this.borderColor = this.applyAlphaMultiplier(this._baseBorderColor, alphaMultiplier)
    }
  }

  fadeSupport (fractionFade, color) {
    const colorList = color.split(',')
    const a = colorList.pop()
    const l = colorList.pop()
    const s = colorList.pop()
    const h = colorList.pop()
    const b = a.slice(0, -1)
    let c = parseFloat(b)
    c = 100 * (c - fractionFade) / 100

    return `${h},${s},${l},${c})`
  }

  applyAlphaMultiplier (color, multiplier) {
    const colorText = String(color || '')
    const hslaMatch = colorText.match(/^hsla\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)$/i)
    if (hslaMatch) {
      const alpha = Number.parseFloat(hslaMatch[4])
      const safeAlpha = Number.isFinite(alpha) ? alpha : 1
      const nextAlpha = Math.max(0, Math.min(1, safeAlpha * multiplier))
      return `hsla(${hslaMatch[1]}, ${hslaMatch[2]}, ${hslaMatch[3]}, ${nextAlpha})`
    }
    const rgbaMatch = colorText.match(/^rgba\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)$/i)
    if (rgbaMatch) {
      const alpha = Number.parseFloat(rgbaMatch[4])
      const safeAlpha = Number.isFinite(alpha) ? alpha : 1
      const nextAlpha = Math.max(0, Math.min(1, safeAlpha * multiplier))
      return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${nextAlpha})`
    }
    return colorText
  }
}
