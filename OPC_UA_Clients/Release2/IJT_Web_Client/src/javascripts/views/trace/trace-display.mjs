import SingleTraceData from './single-trace-data.mjs'
import ChartManager from './chart-handler.mjs'
import { createOptionalTraceExtensionLoader } from './optional-trace-extension-loader.mjs'
import { detectRundownEndX, detectRundownZoomRange, isRundownStep } from './rundown-detector.mjs'

const limitGeometryExtension = createOptionalTraceExtensionLoader('../envelope/core/limit-curve-geometry.mjs')

/**
 * TraceGraphics displays result events in order to display the traces (graphs)
 * on the screen and management of the displayed traces such as selection and such.
 * Little to none OPC UA relevant logic happens here
 */
export default class TraceDisplay {
  constructor (dimensions, resultManager, traceManager, container, debugSourceText, options = {}) {
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
    this.alignOnRundownEnd = options.alignOnRundownEnd === true
    this.absoluteFunction = (x) => { return x }
    this.plugins = {
      autocolors: false,
      annotation: {
        annotations: {},
      },
    }
    this.evictedSubscriptionAttached = false
    this.pendingChartUpdate = false

    this.canvasCoverLayer = document.createElement('div')
    this.canvasCoverLayer.classList.add('traceArea')
    container.appendChild(this.canvasCoverLayer)
    this.mouseDownInTraceArea = false
    this.fullscreenResizeTimer = null
    this.setupFullscreenToggle()

    this.canvas = document.createElement('canvas')
    this.canvas.setAttribute('id', 'myChart')
    this.canvasCoverLayer.appendChild(this.canvas)

    this.chartManager = new ChartManager(traceManager, this.canvas, debugSourceText, {
      chartPlugins: Array.isArray(options.chartPlugins) ? options.chartPlugins : []
    })

    this.canvasCoverLayer.addEventListener('mousedown', () => {
      this.mouseDownInTraceArea = true
    })

    this.canvasCoverLayer.addEventListener('mouseup', (evt) => {
      this.mouseDownInTraceArea = false
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

    window.addEventListener('mouseup', (evt) => {
      if (!this.mouseDownInTraceArea) {
        return
      }
      this.mouseDownInTraceArea = false
      this.traceManager.onclick(
        evt,
        this.chartManager.pixelToValue(evt),
        null,
        null)
    })

    // this.setupEventListeners()
  }

  setupFullscreenToggle () {
    this.fullscreenButton = document.createElement('button')
    this.fullscreenButton.type = 'button'
    this.fullscreenButton.classList.add('traceFullscreenToggle')
    this.fullscreenButton.setAttribute('aria-label', 'Expand trace')
    this.fullscreenButton.setAttribute('aria-pressed', 'false')
    this.fullscreenButton.title = 'Expand trace'

    const stopTracePointerHandling = (evt) => {
      evt.stopPropagation()
    }
    for (const eventName of ['mousedown', 'mouseup', 'touchstart', 'touchend', 'pointerdown', 'pointerup']) {
      this.fullscreenButton.addEventListener(eventName, stopTracePointerHandling)
    }
    this.canvasCoverLayer.addEventListener('tracefullscreenchange', (evt) => {
      this.traceManager?.onTraceFullscreenChanged?.(evt.detail?.expanded === true)
    })
    this.fullscreenButton.addEventListener('click', (evt) => {
      evt.preventDefault()
      evt.stopPropagation()
      this.toggleFullscreen()
    })
    this.canvasCoverLayer.appendChild(this.fullscreenButton)
  }

  toggleFullscreen () {
    if (this.canvasCoverLayer.classList.contains('is-trace-fullscreen')) {
      this.exitFullscreen()
    } else {
      this.enterFullscreen()
    }
  }

  enterFullscreen () {
    for (const expandedTrace of document.querySelectorAll('.traceArea.is-trace-fullscreen')) {
      if (expandedTrace !== this.canvasCoverLayer) {
        expandedTrace.classList.remove('is-trace-fullscreen')
        expandedTrace.querySelector('.traceFullscreenToggle')?.setAttribute('aria-pressed', 'false')
        expandedTrace.querySelector('.traceFullscreenToggle')?.setAttribute('aria-label', 'Expand trace')
        expandedTrace.querySelector('.traceFullscreenToggle')?.setAttribute('title', 'Expand trace')
        expandedTrace.dispatchEvent(new CustomEvent('tracefullscreenchange', { detail: { expanded: false } }))
      }
    }
    this.canvasCoverLayer.classList.add('is-trace-fullscreen')
    document.body.classList.add('trace-fullscreen-open')
    this.updateFullscreenButtonState()
    this.canvasCoverLayer.dispatchEvent(new CustomEvent('tracefullscreenchange', { detail: { expanded: true } }))
    this.zoomToLatestTraceXRange()
    this.scheduleChartResize()
  }

  exitFullscreen () {
    this.canvasCoverLayer.classList.remove('is-trace-fullscreen')
    if (!document.querySelector('.traceArea.is-trace-fullscreen')) {
      document.body.classList.remove('trace-fullscreen-open')
    }
    this.updateFullscreenButtonState()
    this.canvasCoverLayer.dispatchEvent(new CustomEvent('tracefullscreenchange', { detail: { expanded: false } }))
    this.scheduleChartResize()
  }

  updateFullscreenButtonState () {
    if (!this.fullscreenButton) {
      return
    }
    const expanded = this.canvasCoverLayer.classList.contains('is-trace-fullscreen')
    const label = expanded ? 'Shrink trace' : 'Expand trace'
    this.fullscreenButton.setAttribute('aria-pressed', expanded ? 'true' : 'false')
    this.fullscreenButton.setAttribute('aria-label', label)
    this.fullscreenButton.title = label
  }

  scheduleChartResize () {
    if (this.fullscreenResizeTimer) {
      window.clearTimeout(this.fullscreenResizeTimer)
    }
    window.requestAnimationFrame(() => {
      this.chartManager?.myChart?.resize?.()
      this.update()
      this.fullscreenResizeTimer = window.setTimeout(() => {
        this.chartManager?.myChart?.resize?.()
        this.update()
        this.fullscreenResizeTimer = null
      }, 220)
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
    this.attachEvictedResultsSubscription()
  }

  attachEvictedResultsSubscription () {
    if (this.evictedSubscriptionAttached) {
      return
    }
    const subscribeEvicted = this.resultManager?.subscribeEvicted
    const subscribeRemoved = this.resultManager?.subscribeRemoved
    const subscribeFn = typeof subscribeEvicted === 'function'
      ? subscribeEvicted.bind(this.resultManager)
      : (typeof subscribeRemoved === 'function' ? subscribeRemoved.bind(this.resultManager) : null)
    if (!subscribeFn) {
      return
    }
    subscribeFn((evt) => {
      this.handleEvictedResult(evt)
    })
    this.evictedSubscriptionAttached = true
  }

  resolveResultIdFromEvent (evt) {
    const fromPayload = evt?.resultId
    if (typeof fromPayload === 'string' || typeof fromPayload === 'number') {
      return String(fromPayload)
    }
    const fromResult = evt?.result?.id ?? evt?.result?.ResultMetaData?.ResultId
    if (typeof fromResult === 'string' || typeof fromResult === 'number') {
      return String(fromResult)
    }
    if (typeof evt === 'string' || typeof evt === 'number') {
      return String(evt)
    }
    return null
  }

  handleEvictedResult (evt) {
    const resultId = this.resolveResultIdFromEvent(evt)
    if (!resultId) {
      return
    }
    this.removeTracesByResultId(resultId)
  }

  removeTracesByResultId (resultId) {
    const keep = []
    let removed = 0
    for (const trace of this.allTraces) {
      if (String(trace?.resultId) === String(resultId)) {
        trace?.delete?.()
        removed++
        continue
      }
      keep.push(trace)
    }
    if (removed === 0) {
      return
    }
    this.allTraces = keep
    if (this.selectedTrace && String(this.selectedTrace?.resultId) === String(resultId)) {
      this.selectedTrace = null
      this.selectedStep = null
      this.traceInterface?.clearSteps?.()
    }
    if (this.traceInterface) {
      this.traceInterface.updateTracesInGUI(this.allTraces)
    }
    if (!this.selectedTrace && this.allTraces.length > 0) {
      this.selectTrace(this.allTraces[this.allTraces.length - 1])
    }
    this.update()
  }

  clearAllTraces () {
    for (const trace of this.allTraces) {
      trace?.delete?.()
    }
    this.allTraces = []
    this.chartManager?.clearTraceDatasets?.()
    this.selectedTrace = null
    this.selectedStep = null
    this.result = null
    this.traceInterface?.updateTracesInGUI?.(this.allTraces)
    this.traceInterface?.clearSteps?.()
    this.update()
  }

  update () {
    this.scheduleChartUpdate()
  }

  scheduleChartUpdate () {
    if (this.pendingChartUpdate) {
      return
    }
    this.pendingChartUpdate = true
    const scheduler = (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function')
      ? window.requestAnimationFrame.bind(window)
      : (callback) => setTimeout(callback, 0)
    scheduler(() => {
      this.pendingChartUpdate = false
      this.chartManager.update()
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
    if (typeof this.traceManager?.shouldDisplayResult === 'function') {
      const shouldDisplay = this.traceManager.shouldDisplayResult(model)
      if (!shouldDisplay) {
        return 'Filtered out by active envelope filters'
      }
    }

    if (parseInt(model?.ResultMetaData.Classification) !== 1) { // Only for single traces
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

    if (this.alignOnRundownEnd && this.alignTracesOnRundownEnd()) {
      this.update()
    } else {
      this.align(newResultandTrace, this.alignStep)
    }

    // Show buttons to select the trace and its substeps
    if (this.traceInterface) {
      this.traceInterface.updateTracesInGUI(this.allTraces)
    }
    // Select it
    this.selectTrace(newResultandTrace)

    this.zoomToExcludeRundown(newResultandTrace)
    this.traceInterface?.pulseTraceViewport?.()
    this.update()
  }

  zoomToExcludeRundown (trace) {
    const range = detectRundownZoomRange(trace, this.xDimensionName)
    if (!range) {
      return
    }
    const remainingInterval = range.maxX - range.snugX
    const paddedLeft = range.snugX - (remainingInterval * 0.2)
    const zoomLeft = Math.max(range.minX, paddedLeft)
    const displayOffset = Number(trace?.displayOffset)
    const offset = Number.isFinite(displayOffset) ? displayOffset : 0
    this.chartManager.setXZoom(zoomLeft - offset, range.maxX - offset)
  }

  alignTracesOnRundownEnd () {
    let aligned = false
    const diagnostics = []
    for (const trace of this.allTraces) {
      const rundownEndX = detectRundownEndX(trace, this.xDimensionName)
      if (rundownEndX === null) {
        trace.displayOffset = 0
        diagnostics.push({
          resultId: trace?.resultId,
          rundownEndX: null,
          displayOffset: trace.displayOffset,
          renderedRundownEndX: null
        })
        continue
      }
      trace.displayOffset = rundownEndX
      aligned = true
      diagnostics.push({
        resultId: trace?.resultId,
        rundownEndX,
        displayOffset: trace.displayOffset,
        renderedRundownEndX: null
      })
    }
    if (aligned) {
      this.refreshAllData()
    }
    for (const diagnostic of diagnostics) {
      const trace = this.allTraces.find((item) => item?.resultId === diagnostic.resultId)
      const rundownStep = (trace?.steps ?? []).find(isRundownStep)
      const renderedPoints = rundownStep?.graphic?.mainDataset?.data
      const renderedEndPoint = Array.isArray(renderedPoints) ? renderedPoints[renderedPoints.length - 1] : null
      diagnostic.renderedRundownEndX = Number.isFinite(Number(renderedEndPoint?.x)) ? Number(renderedEndPoint.x) : null
    }
    this.traceManager?.onRundownAlignmentUpdated?.(diagnostics)
    return aligned
  }

  zoomToLatestTraceXRange () {
    const latestTrace = this.allTraces[this.allTraces.length - 1]
    const range = this.getTraceXAxisRange(latestTrace)
    if (!range) {
      return
    }
    this.chartManager.setXZoom(range.minX, range.maxX)
  }

  getTraceXAxisRange (trace) {
    let minX = Infinity
    let maxX = -Infinity
    const displayOffset = Number(trace?.displayOffset) || 0

    for (const step of trace?.steps ?? []) {
      const values = this.getStepXAxisValues(step)
      const startTimeOffset = this.xDimensionName === 'time' ? Number(step?.startTimeOffset) || 0 : 0
      for (const value of values) {
        const xValue = Number(value)
        if (!Number.isFinite(xValue)) {
          continue
        }
        const displayedX = xValue + startTimeOffset - displayOffset
        if (displayedX < minX) {
          minX = displayedX
        }
        if (displayedX > maxX) {
          maxX = displayedX
        }
      }
    }

    if (!Number.isFinite(minX) || !Number.isFinite(maxX)) {
      return null
    }
    if (minX === maxX) {
      return { minX: minX - 1, maxX: maxX + 1 }
    }
    return { minX, maxX }
  }

  getStepXAxisValues (step) {
    if (this.xDimensionName === 'time') {
      return Array.isArray(step?.time) ? step.time : []
    }
    return Array.isArray(step?.angle) ? step.angle : []
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
        this.traceInterface?.setTraceMode?.('toa')
        break
      case 'tot': // Torque over time
        this.xDimensionName = 'time'
        this.traceInterface?.setTraceMode?.('tot')
        break
      // case 'sot': // Speed over time
      //    this.xDimensionName
      //    break
      default:
        throw new Error(`No matching type of trace: ${yName}`)
    }
    this.traceInterface?.setAxisInfo?.(this.xDimensionName, this.yDimensionName)
    this.refreshAllData()
    this.update()
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

  findStepByProgramStepIdOrStepNumber (trace, programStepIdOrStepNumber) {
    if (!trace || !Array.isArray(trace.steps)) {
      return null
    }
    if (programStepIdOrStepNumber === 'all') {
      return 'all'
    }
    if (Number.isInteger(programStepIdOrStepNumber)) {
      return trace.steps[programStepIdOrStepNumber - 1] || null
    }
    return trace.findStepByProgramStepId(programStepIdOrStepNumber)
  }

  getStepXAxisRangeByProgramStepIdOrStepNumber (trace, programStepIdOrStepNumber) {
    const step = this.findStepByProgramStepIdOrStepNumber(trace, programStepIdOrStepNumber)
    if (!step || step === 'all') {
      return null
    }
    const range = this.findExtremes(step)
    if (!Number.isFinite(range.min) || !Number.isFinite(range.max)) {
      return null
    }
    return range
  }

  alignByProgramStepIdOrStepNumber (trace, programStepIdOrStepNumber, referenceX = 0) {
    const step = this.findStepByProgramStepIdOrStepNumber(trace, programStepIdOrStepNumber)
    if (!step) {
      return false
    }
    if (step === 'all') {
      trace.displayOffset = 0
      return true
    }
    const range = this.findExtremes(step)
    const normalizedReferenceX = Number.isFinite(referenceX) ? referenceX : 0
    const displayOffset = range.min - normalizedReferenceX
    if (!Number.isFinite(displayOffset)) {
      return false
    }
    trace.displayOffset = displayOffset
    return true
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
    this.update()
  }

  showLimits (value) {
    if (value === 'yes') {
      this.showLimitSelected = true
    } else {
      this.showLimitSelected = false
    }
    this.refreshAllData()
    this.update()
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
    this.update()
  }

  createGraphicalLimit (limit, callback) {
    limit.limitGraphic = new GraphicalLimit(this, limit, callback)
    return limit.limitGraphic
  }
}

class GraphicalLimit {
  constructor (traceDisplay, limit, afterUpdateCallback) {
    this.traceDisplay = traceDisplay
    this.chartManager = traceDisplay.chartManager
    this.glimit = this.chartManager.newLimit('hsl(48 92% 58%)', 'hsl(48 92% 58% / 0.20)', 'start')
    this.chartManager.afterUpdateSubscribe(afterUpdateCallback)
    this.latestLimit = limit
    limitGeometryExtension.onLoad(() => {
      if (this.latestLimit) {
        this.update(this.latestLimit)
      }
    })
    this.update(limit)
  }

  update (limit) {
    this.latestLimit = limit
    const extension = limitGeometryExtension.get()
    const determineLimitDirection = extension.determineLimitDirection ||
      (() => 1)
    const buildLimitCurvePoints = extension.buildLimitCurvePoints ||
      (() => [])
    this.glimit.envelopeMetaData.direction = determineLimitDirection(limit.range.start, limit.range.end)
    this.glimit.data = buildLimitCurvePoints(limit)

    if (limit.check.constructor.name === 'OverLimit') {
      this.glimit.fill = 'end'
    } else if (limit.check.constructor.name === 'UnderLimit') {
      this.glimit.fill = 'start'
    } else {
      this.glimit.fill = false
    }

    this.traceDisplay.update()
  }

  pixelToValue (pos) {
    return this.chartManager.pixelToValue(pos)
  }

  valueToPixel (pos) {
    return this.chartManager.valueToPixel(pos)
  }
}
