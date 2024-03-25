// The purpose of this class is to display traces on the screen and manage
// user interaction with them. It has little to do with the OPC UA communication as such
// and is consequently kept entierly in the View folder.
// import ModelManager from '../../Models/ModelManager.mjs'
import ChartManager from './ChartHandler.mjs'
import TraceInterface from './TraceInterface.mjs'
import SingleTraceData from './SingleTraceData.mjs'
import BasicScreen from '../GraphicSupport/BasicScreen.mjs'

/**
 * TraceGraphics displays result events in order to display the traces (graphs)
 * on the screen and management of the displayed traces such as selection and such.
 * Little to none OPC UA relevant logic happens here
 */
export default class TraceGraphics extends BasicScreen {
  constructor (dimensions, addressSpace, resultManager) {
    super('Traces')
    this.traceInterface = new TraceInterface(this.backGround)
    this.xDimensionName = dimensions[0]
    this.yDimensionName = dimensions[1]
    this.resultManager = resultManager
    this.result = null
    this.showValuesSelected = false
    this.showLimitsSelected = false
    this.labelId = 3
    this.identityCounter = 0
    this.allTraces = []
    this.selectedTrace = null
    this.selectedStep = null
    this.absoluteFunction = (x) => { return x }
    this.plugins = {
      autocolors: false,
      annotation: {
        annotations: {}
      }
    }

    this.chartManager = new ChartManager(this)
    this.setupEventListeners()
    addressSpace.connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        this.activate()
      }
    })
  }

  /**
   * Setup-function the first time the view is opened to load a trace if none exists
   */
  initiate () {

  }

  /**
   * This should be run when this view is set up, which should be after
   * subscription to events have been done. Then subscribe to results
   */
  activate () {
    this.resultManager.subscribe((result) => {
      this.createNewTrace(result)
    })
  }

  /**
   * Main function for generating a new graphical representation of a trace
   * @date 2/23/2024 - 6:19:47 PM
   *
   * @param {*} model the OPC UA IJT model of a result
   * @returns {string} possible error message
   */
  createNewTrace (model) {
    if (model?.ResultMetaData.Classification !== '1') { // Only for single traces
      return 'Only traces for single results'
    }

    if (!model?.ResultContent[0].Trace) { // A trace must be included in the result
      return
    }
    this.result = model

    // Create new trace and align it
    const newResultandTrace = new SingleTraceData(this.result, this, this.chartManager, this.identityCounter++, () => { return this.traceInterface.getRandomColor() })
    this.align(newResultandTrace, this.alignStep)

    // Store it
    this.allTraces.push(newResultandTrace)

    // Show buttons to select the trace and its substeps
    this.traceInterface.updateTracesInGUI(this.allTraces)

    // Select it
    this.selectTrace(newResultandTrace)
  }

  /**
   * Set if you want a curve over time or over angle
   * @date 2/23/2024 - 6:20:50 PM
   *
   * @param {*} yName
   */
  decideTraceType (yName) {
    switch (yName) {
      case 'toa': // Torque over Angle
        this.xDimensionName = 'angle'
        break
      case 'tot': // Torque over time
        this.xDimensionName = 'time'
        break
      // case 'sot': // Speed over time
      //    this.xDimensionName
      //    break
      default:
        throw new Error('No matching type of trace: ' + yName)
    }
    this.refreshAllData()
    this.chartManager.update()
  }

  // Step handling ////////////////////////////////////////////////////////////////////////////////////////////////////////////
  alignCORRECT (trace, step) {
    this.applyToAll(trace, step, (a, b) => { this.alignByProgramStepId(a, b) })
  }

  zoomCORRECT (trace, step) {
    this.applyToAll(trace, step, (a, b) => { this.zoomByProgramStepId(a, b) })
  }

  align (trace, step) { // Temp solution until programStepId is correct in simulator
    const index = trace.steps.indexOf(step)
    this.applyToAll(trace, step, (a, b) => { this.alignByIndex(a, index) })
  }

  zoom (trace, step) {
    const index = trace.steps.indexOf(step)
    this.applyToAll(trace, step, (a, b) => { this.zoomByIndex(a, index) })
  }

  applyToAll (trace, step, operation) {
    if (trace.steps.length === 0) {
      throw new Error('No trace selected for applyToAll')
    }

    let programStepId
    if (!step) {
      programStepId = 'all'
    } else {
      programStepId = step.stepId.link.ProgramStepId
    }
    for (const trace of this.allTraces) {
      operation(trace, programStepId)
    }

    trace.highLight()
    this.refreshAllData()
    this.chartManager.update()
  }

  alignByIndex (trace, index) { // Temp solution until programStepId is correct in simulator
    const step = trace.steps[index]
    if (index === -1) {
      trace.displayOffset = 0
    } else {
      trace.displayOffset = this.findExtremes(step).min
    }
  }

  alignByProgramStepId (trace, programStepId) {
    const step = trace.findStepByProgramStepId(programStepId)
    if (step) {
      if (step === 'all') {
        trace.displayOffset = 0
      } else {
        trace.displayOffset = this.findExtremes(step).min
      }
    }
  }

  zoomByIndex (trace, index) {
    const zoomedStep = trace.steps[index]
    for (const step of trace.steps) {
      if (index === -1 || step === zoomedStep) {
        step.showStepTrace()
      } else {
        step.hideStepTrace()
      }
    }
  }

  zoomByProgramStepId (trace, programStepId) {
    const zoomedStep = trace.findStepByProgramStepId(programStepId)
    for (const step of trace.steps) {
      if (zoomedStep === 'all' || step === zoomedStep) {
        step.showStepTrace()
      } else {
        step.hideStepTrace()
      }
    }
  }

  deleteSelected () {
    if (!this.selectedTrace) {
      throw new Error('No trace selected.')
    }
    this.selectedTrace.delete()
    this.allTraces = this.allTraces.filter((x) => { return x !== this.selectedTrace })

    this.traceInterface.updateTracesInGUI(this.allTraces)
    if (this.allTraces.length > 0) {
      this.selectTrace(this.allTraces[this.allTraces.length - 1])
    } else {
      this.chartManager.update()
    }
  }

  // //////////////////////////// Selection support ////////////////////////////////
  selectTrace (trace) {
    this.deselectTrace()

    for (const step of trace.steps) {
      this.traceInterface.addStepInGUI(step, step.stepId.value)
    }
    this.selectedTrace = trace
    trace.select()
    this.traceInterface.selectTrace(trace.resultId)
    this.chartManager.update()
  }

  deselectTrace () {
    if (!this.selectedTrace) {
      return
    }
    this.traceInterface.clearSteps()
    this.selectedTrace.deselect()
    this.selectedTrace = null
    this.chartManager.update()
  }

  selectStep (selectedStep) {
    this.selectedTrace.deHighLight()
    this.traceInterface.selectStep(selectedStep)
    this.selectedStep = null
    for (const step of this.selectedTrace.steps) {
      if (selectedStep === step.stepId.value) {
        step.select()
        this.selectedStep = step
      } else {
        step.deselect()
      }
    }
    this.chartManager.update()
  }

  showPoints (value) {
    if (value === 'yes') {
      this.showValuesSelected = true
    } else {
      this.showValuesSelected = false
    }
    this.refreshAllData()
    this.chartManager.update()
  }

  showLimits (value) {
    if (value === 'yes') {
      this.showLimitSelected = true
    } else {
      this.showLimitSelected = false
    }
    this.refreshAllData()
    this.chartManager.update()
  }

  //  Point handling //////////////////////////////////////////////////////////////
  findExtremes (step) {
    let valueList = step.angle
    if (this.xDimensionName !== 'angle') {
      valueList = step.time
    }
    return { min: Math.min(...valueList), max: Math.max(...valueList) }
  }

  findTrace (Id) {
    return this.allTraces.find((element) => {
      return element.result.id === Id
    })
  }

  setAbsolutes () {
    this.absoluteFunction = (x) => { return Math.abs(x) }
  }

  removeAbsolutes () {
    this.absoluteFunction = (x) => { return x }
  }

  convertDimension (dimension) {
    if (dimension === this.xDimensionName) {
      return 'x'
    }

    if (dimension === this.yDimensionName) {
      return 'y'
    }
    throw new Error('Dimension does not match trace axis')
  }

  refreshAllData () {
    for (const trace of this.allTraces) {
      trace.refreshTraceData()
    }
  }

  clicked (resultId, stepId) {
    if (resultId !== this.selectedTrace.resultId) {
      this.selectTrace(this.findTrace(resultId))
    } else {
      this.selectStep(stepId.value)
    }
  }

  // ////////////   Setup GUI related functionality ////////////////////////////
  setupEventListeners () {
    this.traceInterface.traceTypeSelect.addEventListener('click', (event) => {
      this.decideTraceType(this.traceInterface.traceTypeSelect.options[this.traceInterface.traceTypeSelect.selectedIndex].value)
    }, false)

    this.traceInterface.absoluteSelect.addEventListener('click', (event) => {
      if (this.traceInterface.absoluteSelect.options[this.traceInterface.absoluteSelect.selectedIndex].value === 'absolute') {
        this.setAbsolutes()
      } else {
        this.removeAbsolutes()
      }
      this.refreshAllData()
      this.chartManager.update()
    }, false)

    this.traceInterface.setTraceSelectEventListener((event) => {
      this.selectTrace(this.findTrace(event.currentTarget.resultId))
      this.selectedStep = null
    })

    this.traceInterface.setStepSelectEventListener((event) => {
      this.selectStep(event.currentTarget.stepId)
      this.chartManager.resetZoom()
      this.zoom(this.selectedTrace, this.selectedStep)
    })

    this.traceInterface.clearSteps()

    this.traceInterface.alignButton.addEventListener('click', (event) => {
      this.align(this.selectedTrace, this.selectedStep)
      this.alignStep = this.selectStep
    }, false)

    this.traceInterface.valueShower.addEventListener('click', (event) => {
      this.showPoints(this.traceInterface.valueShower.options[this.traceInterface.valueShower.selectedIndex].value)
    }, false)

    this.traceInterface.limitShower.addEventListener('click', (event) => {
      this.showLimits(this.traceInterface.limitShower.options[this.traceInterface.limitShower.selectedIndex].value)
    }, false)

    this.traceInterface.deleteButton.addEventListener('click', (event) => {
      this.deleteSelected()
    }, false)
  }

  onclick = (evt, coord, resultId, stepId) => {
    if (resultId) {
      this.clicked(resultId, stepId)
    } else if (this.pressed) {
      const originalZoom = this.chartManager.getZoom()
      const originaXLength = originalZoom.right - originalZoom.left
      const originaYLength = originalZoom.bottom - originalZoom.top

      const amountOfXChange = Math.abs(this.startZoomCoord.x - coord.x) / originaXLength
      const amountOfYChange = Math.abs(this.startZoomCoord.y - coord.y) / originaYLength

      if (amountOfXChange > 0.005 && amountOfYChange > 0.005) { // prevent single click zoom
        this.chartManager.zoom(this.startZoomCoord, coord)
      }
    }
    this.traceInterface.zoomBoxDraw(null, null)
    this.pressed = null
    this.startZoomCoord = null
  }

  onmousedown = (evt, coord) => {
    switch (evt.button) {
      case 0:
        this.divOffset = {
          x: evt.x - evt.offsetX,
          y: evt.y - evt.offsetY
        }
        this.startZoomCoord = coord
        this.pressed = evt
        break
      default:
        this.chartManager.resetZoom()
    }
  }

  onmousewheel = (evt, coord) => {
    const sensitivityWheel = 500
    const sensitivityPad = 100

    let deltaY = (evt.deltaY / sensitivityWheel) + 1

    if (evt.ctrlKey) { // Only way to differentiate between touchpad and mousewheel???
      deltaY = (evt.deltaY / sensitivityPad) + 1
    }

    const deltaX = deltaY

    if ((deltaX < 0.5) || (deltaX > 2) || (deltaY < 0.5) || (deltaY > 2)) {
      return // Ignore random very large zooms
    }

    const currentZoom = this.chartManager.getZoom()

    const new1 = {
      x: coord.x - (coord.x - currentZoom.left) * deltaX,
      y: coord.y - (coord.y - currentZoom.top) * deltaY
    }

    const new2 = {
      x: coord.x + (currentZoom.right - coord.x) * deltaX,
      y: coord.y + (currentZoom.bottom - coord.y) * deltaY
    }
    this.chartManager.zoom(new1, new2)
  }

  onmousemove = (evt, coord) => {
    if (this.pressed) {
      this.traceInterface.zoomBoxDraw(evt, this.pressed, this.divOffset)
    }
  }

  touchstart (evt, coord) {
    this.touchStarts = evt.touches
    this.touchStartZoom = this.chartManager.getZoom()
    this.touchStartWindow = this.chartManager.getWindowDimensions()
  }

  normalizeTouches (first, second) {
    const minX = Math.min(first.clientX, second.clientX)
    const minY = Math.min(first.clientY, second.clientY)
    const maxX = Math.max(first.clientX, second.clientX)
    const maxY = Math.max(first.clientY, second.clientY)
    return {
      lower: { x: minX, y: minY },
      upper: { x: maxX, y: maxY }
    }
  }

  touchmove (evt, coord) {
    const xMultiplier = 1
    const yMultiplier = 1

    if (evt.touches.length === 2) {
      const startPoints = this.normalizeTouches(this.touchStarts[0], this.touchStarts[1])
      const currentPoints = this.normalizeTouches(evt.touches[0], evt.touches[1])

      const xLength = this.touchStartWindow.right - this.touchStartWindow.left
      const yLength = this.touchStartWindow.bottom - this.touchStartWindow.top

      const deltaXlower = (startPoints.lower.x - currentPoints.lower.x) / xLength
      const deltaYlower = (startPoints.lower.y - currentPoints.lower.y) / yLength
      const deltaXupper = (startPoints.upper.x - currentPoints.upper.x) / xLength
      const deltaYupper = (startPoints.upper.y - currentPoints.upper.y) / yLength

      const originalZoom = this.touchStartZoom
      const originaXLength = originalZoom.right - originalZoom.left
      const originaYLength = originalZoom.bottom - originalZoom.top

      const newLower = {
        x: originalZoom.left + originaXLength * deltaXlower * xMultiplier,
        y: originalZoom.bottom - originaYLength * deltaYlower * yMultiplier
      }
      const newUpper = {
        x: originalZoom.right + originaXLength * deltaXupper * xMultiplier,
        y: originalZoom.top - originaYLength * deltaYupper * yMultiplier
      }

      this.chartManager.zoom(newLower, newUpper)
    }
  }

  touchend (evt, coord) {
    // console.log(coord)
  }

  touchcancel (evt, coord) {
    // console.log(coord)
  }
}
