/**
 * Supportclass to help encapsulate the chart package
 */
const DEFAULT_RADIUS = 0
const DEFAULT_BORDER_WIDTH = 1
const SELECTED_BORDER_WIDTH = 2

export default class Dataset {
  constructor (name) {
    this.label = name
    this.radius = DEFAULT_RADIUS
    this.borderWidth = DEFAULT_BORDER_WIDTH
  }

  show () {
    this.hidden = false
  }

  hide () {
    this.hidden = true
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

  setPoints (points) {
    this.data = points
  }

  setResultId (id) {
    this.resultId = id
  }

  setStepId (id) {
    this.stepId = id
  }

  select () {
    this.borderWidth = SELECTED_BORDER_WIDTH
  }

  deselect () {
    this.borderWidth = DEFAULT_BORDER_WIDTH
  }
}
