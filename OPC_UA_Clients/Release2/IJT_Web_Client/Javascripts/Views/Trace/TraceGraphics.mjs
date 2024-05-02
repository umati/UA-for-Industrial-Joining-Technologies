// The purpose of this class is to display traces on the screen and manage
// user interaction with them. It has little to do with the OPC UA communication as such
// and is consequently kept entierly in the View folder.
// import ModelManager from '../../Models/ModelManager.mjs'
import { ButtonTraceInterface } from './TraceInterface.mjs' // Buttons and other standard graphical elements
import ZoomHandler from './ZoomHandler.mjs' // Handling different types of zoom
import TraceDisplay from './TraceDisplay.mjs' // The trace area
import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality

export default class TraceGraphics extends BasicScreen {
  constructor (dimensions, addressSpace, resultManager) {
    super('Traces')
    this.traceInterface = new ButtonTraceInterface(this.backGround)
    this.traceDisplay = new TraceDisplay(dimensions, resultManager, this, this.traceInterface.traceArea)

    this.zoomHandler = new ZoomHandler(this.traceDisplay)

    this.setupEventListeners()
    addressSpace.connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        this.traceDisplay.activate()
      }
    })
  }

  /**
   * Mouse button up - switch of behaviour (select trace or start zoom)
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} resultId the actual result if the click was on a given trace
   * @param {*} stepId the step if the click was on a given trace
   */
  onclick = (evt, coord, resultId, stepId) => {
    if (resultId) {
      this.traceDisplay.clicked(resultId, stepId)
    } else {
      this.zoomHandler.onclick(evt, coord, resultId, stepId)
    }
  }

  /**
   * Draw a box when mouse selecting a zoom area
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousemove = (evt, coord) => {
    this.zoomHandler.onmousemove(evt, coord)
  }

  /**
   * Mouse button down - zoom area start of selection
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousedown = (evt, coord) => {
    this.zoomHandler.onmousedown(evt, coord)
  }

  /**
   * handle mouse wheel, or touchpad zoom
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @returns Nothing
   */
  onmousewheel = (evt, coord) => {
    this.zoomHandler.onmousewheel(evt, coord)
  }

  /**
   * Touchscreen start touch
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffsetoffset to correctly location
   */
  touchstart (evt, coord, touchOffset) {
    this.zoomHandler.touchstart(evt, coord, touchOffset)
  }

  /**
   * Moving a screentouch
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffset to correctly calculate location
   */
  touchmove (evt, coord, touchOffset) {
    this.zoomHandler.touchmove(evt, coord, touchOffset)
  }

  touchend (evt, coord, touchOffset) {
    this.zoomHandler.touchend(evt, coord, touchOffset)
  }

  touchcancel (evt, coord, touchOffset) {
    this.zoomHandler.touchcancel(evt, coord, touchOffset)
  }

  // ////////////   Setup GUI related functionality ////////////////////////////
  setupEventListeners () {
    this.traceInterface.traceTypeSelect.addEventListener('click', (event) => {
      this.traceDisplay.decideTraceType(this.traceInterface.traceTypeSelect.options[this.traceInterface.traceTypeSelect.selectedIndex].value)
    }, false)

    this.traceInterface.absoluteSelect.addEventListener('click', (event) => {
      if (this.traceInterface.absoluteSelect.options[this.traceInterface.absoluteSelect.selectedIndex].value === 'absolute') {
        this.traceDisplay.setAbsolutes()
      } else {
        this.traceDisplay.removeAbsolutes()
      }
      this.traceDisplay.refreshAllData()
      this.traceDisplay.update()
    }, false)

    this.traceInterface.setTraceSelectEventListener((event) => {
      this.traceDisplay.selectTrace(this.traceDisplay.findTrace(event.currentTarget.resultId))
      this.selectedStep = null
    })

    this.traceInterface.setStepSelectEventListener((event) => {
      this.traceInterface.selectStep(event.currentTarget.stepId)
      this.traceDisplay.selectStep(event.currentTarget.stepId)
      // this.traceDisplay.resetZoom()
      this.traceDisplay.zoom(this.traceDisplay.selectedTrace, this.traceDisplay.selectedStep)
    })

    this.traceInterface.clearSteps()

    this.traceInterface.alignButton.addEventListener('click', (event) => {
      this.align(this.traceDisplay.selectedTrace, this.traceDisplay.selectedStep)
      this.alignStep = this.selectStep
    }, false)

    this.traceInterface.valueShower.addEventListener('click', (event) => {
      this.traceDisplay.showPoints(this.traceInterface.valueShower.options[this.traceInterface.valueShower.selectedIndex].value)
    }, false)

    this.traceInterface.limitShower.addEventListener('click', (event) => {
      this.traceDisplay.showLimits(this.traceInterface.limitShower.options[this.traceInterface.limitShower.selectedIndex].value)
    }, false)

    this.traceInterface.deleteButton.addEventListener('click', (event) => {
      this.deleteSelected()
    }, false)
  }
}
