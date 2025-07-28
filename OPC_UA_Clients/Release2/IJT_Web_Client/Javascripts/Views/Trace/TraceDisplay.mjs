import SingleTraceData from './SingleTraceData.mjs'
import ChartManager from './ChartHandler.mjs'

/**
 * TraceGraphics displays result events in order to display the traces (graphs)
 * on the screen and management of the displayed traces such as selection and such.
 * Little to none OPC UA relevant logic happens here
 */
export default class TraceDisplay {
  constructor (dimensions, resultManager, traceManager, container) {
    this.traceInterface = traceManager.traceInterface
    this.traceManager = traceManager
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

    this.canvasCoverLayer = document.createElement('div')
    this.canvasCoverLayer.classList.add('traceArea')
    container.appendChild(this.canvasCoverLayer)

    this.canvas = document.createElement('canvas')
    this.canvas.setAttribute('id', 'myChart')
    this.canvasCoverLayer.appendChild(this.canvas)

    this.chartManager = new ChartManager(traceManager, this.canvas)

    this.canvasCoverLayer.addEventListener('mouseup', (evt) => {
      const points = this.chartManager.myChart.getElementsAtEventForMode(evt,
        'nearest', { intersect: true }, true)

      let resultId = null
      let stepId = null
      if (points.length) {
        const firstPoint = points[0]
        const dataset = this.chartManager.myChart.data.datasets[firstPoint.datasetIndex]
        resultId = dataset.resultId
        stepId = dataset.stepId
        // this.traceManager.clicked(dataset.resultId, dataset.stepId.value)
      }

      this.traceManager.onclick(
        evt,
        this.chartManager.pixelToValue(evt),
        resultId,
        stepId)
    })

    // this.setupEventListeners()
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

  update () {
    this.chartManager.update()
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

    this.handleOldTraces(this.traceInterface.refreshTraceCallback())

    // Create new trace and align it
    const newResultandTrace = new SingleTraceData(this.result, this, this.chartManager, this.identityCounter++, () => { return this.traceInterface.getRandomColor() })

    // Store it
    this.allTraces.push(newResultandTrace)

    this.align(newResultandTrace, this.alignStep)

    // Show buttons to select the trace and its substeps
    if (this.traceInterface) {
      this.traceInterface.updateTracesInGUI(this.allTraces)
    }
    // Select it
    this.selectTrace(newResultandTrace)
    this.update()
  }

  handleOldTraces (refreshCallback) {
    if (refreshCallback) {
      for (const oldTrace of this.allTraces) {
        refreshCallback(oldTrace, this)
      }
    }
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

    // trace.highLight()
    this.refreshAllData()
    // this.chartManager.update()
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

  deleteSelected (trace) {
    if (trace) {
      this.selectedTrace = trace
    }
    if (!this.selectedTrace) {
      throw new Error('No trace selected.')
    }
    this.selectedTrace.delete()
    this.allTraces = this.allTraces.filter((x) => { return x !== this.selectedTrace })

    if (this.traceInterface) {
      this.traceInterface.updateTracesInGUI(this.allTraces)
    }
    if (this.allTraces.length > 0) {
      this.selectTrace(this.allTraces[this.allTraces.length - 1])
    }
  }

  // //////////////////////////// Selection support ////////////////////////////////
  selectTrace (trace) {
    this.deselectTrace()

    if (this.traceInterface) {
      for (const step of trace.steps) {
        this.traceInterface.addStepInGUI(step, step.stepId.value)
      }
    }
    this.selectedTrace = trace
    trace.select()

    if (this.traceInterface) {
      this.traceInterface.selectTrace(trace.resultId)
    }
  }

  deselectTrace () {
    if (!this.selectedTrace) {
      return
    }

    if (this.traceInterface) {
      this.traceInterface.clearSteps()
    }
    this.selectedTrace.deselect()
    this.selectedTrace = null
  }

  selectStep (selectedStep) {
    // this.selectedTrace.deHighLight()
    if (this.traceInterface) {
      this.traceInterface.selectStep(selectedStep)
    }
    this.selectedStep = null
    for (const step of this.selectedTrace.steps) {
      if (selectedStep === step.stepId.value) {
        step.select()
        this.selectedStep = step
      } else {
        step.deselect()
      }
    }
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
    this.chartManager.update()
  }

  createGraphicalLimit (limit) {
    limit.limitGraphic = new GraphicalLimit(this.chartManager, limit)
    return limit.limitGraphic
  }
}

class GraphicalLimit {
  constructor (chartManager, limit) {
    this.chartManager = chartManager
    this.glimit = this.chartManager.newLimit('red', 'rgba(135, 135, 241, 0.5)', 'start')
    this.update(limit)
  }

  update (limit) {
    const dataList = []
    for (let x = limit.range.start;
      x <= limit.range.end;
      x += (limit.range.end - limit.range.start) / 100) {
      dataList.push({
        x,
        y: limit.polynomial.value(x - limit.range.offset)
      })
    }
    this.glimit.data = dataList

    if (limit.check.constructor.name === 'OverLimit') {
      this.glimit.fill = 'end'
    } else if (limit.check.constructor.name === 'UnderLimit') {
      this.glimit.fill = 'start'
    } else {
      this.glimit.fill = false
    }

    this.chartManager.update()
  }

  pixelToValue (pos) {
    return this.chartManager.pixelToValue(pos)
  }

  valueToPixel (pos) {
    /* console.log(this.chartManager.valueToPixel({ x: 150, y: 1}))
    // console.log(this.chartManager.pixelToValue({ x: 250, y: 500}))
    setTimeout(() => {
      console.log(this.chartManager.valueToPixel({ x: 150, y: 1}))
    }, 2000) */
    return this.chartManager.valueToPixel(pos)
  }
}