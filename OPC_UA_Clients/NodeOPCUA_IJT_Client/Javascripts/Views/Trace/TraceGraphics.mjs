// The purpose of this class is to display traces on the screen and manage
// user interaction with them. It has little to do with the OPC UA communication as such
// and is consequently kept entierly in the View folder.

import ChartManager from './ChartHandler.mjs'
import TraceInterface from './TraceInterface.mjs'
import SingleTraceData from './SingleTraceData.mjs'
import Step from './Step.mjs'

/**
 * TraceGraphics displays result events in order to display the traces (graphs)
 * on the screen and management of the displayed traces such as selection and such.
 * Little to none OPC UA relevant logic happens here
 */
export default class TraceGraphics {
  constructor (container, dimensions, addressSpace) {
    this.traceInterface = new TraceInterface(container)
    this.xDimensionName = dimensions[0]
    this.yDimensionName = dimensions[1]
    this.addressSpace = addressSpace
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

    this.chartManager = new ChartManager(this.traceInterface.canvas, this)
    this.setupEventListeners()

    const serverDiv = document.getElementById('connectedServer')
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Trace') {
        if (this.allTraces.length === 0) {
          this.initiate()
        }
      }
    }, false)
  }

  /**
   * Setup-function the first time the view is opened to load a trace if none exists
   */
  initiate () {

  }

  // /////////////////////////////////////////////////////////////////////////
  createNewTrace (event) {
    const { result, trace } = event.detail
    this.result = result

    if (!trace) return

    const stepTraces = trace.stepTraces
    const newResultandTrace = new SingleTraceData(result, this)

    for (const step of stepTraces) {
      const newStep = new Step(step, newResultandTrace)
      for (const data of step.stepTraceContent) {
        switch (data.physicalQuantity) {
          case 1: // Time
            newStep.time = data.values
            break
          case 2: // Torque
            newStep.torque = data.values
            break
          case 3: // Angle
            newStep.angle = data.values
            break
          case 11: // Current
            break
          default:
            throw new Error('Unknown physicalQuantity in trace')
        }
      }
      newStep.color = this.traceInterface.getRandomColor()
      if (!newStep.time) {
        newStep.time = Array.from(Array(newStep.torque.length), (_, x) => step.samplingInterval * x / 1000)
      }
      newResultandTrace.addStep(newStep)
    }

    newResultandTrace.displayName += '(' + (this.identityCounter++) + ')'

    this.allTraces.push(newResultandTrace)
    newResultandTrace.generateTrace()
    this.traceInterface.updateTracesInGUI(this.allTraces)
    this.selectTrace(newResultandTrace)
  }

  // /////////////////////////////////////////////////////////////////////////
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
  align (trace, step) {
    this.applyToAll(trace, step, (a, b) => { this.alignByProgramStepId(a, b) })
  }

  zoom (trace, step) {
    this.applyToAll(trace, step, (a, b) => { this.zoomByProgramStepId(a, b) })
  }

  applyToAll (trace, step, operation) {
    if (trace.steps.length === 0) {
      throw new Error('No trace selected for applyToAll')
    }
    // let step = trace.findStepByStepId(stepId)
    let programStepId
    if (!step) {
      programStepId = 'all'
    } else {
      programStepId = step.stepId.link.programStepId
    }
    for (const trace of this.allTraces) {
      operation(trace, programStepId)
    }

    trace.highLight()
    this.refreshAllData()
    this.chartManager.update()
  }

  alignByProgramStepId (trace, programStepId) {
    const step = trace.findStepByProgramStepId(programStepId)
    if (step === 'all') {
      trace.displayOffset = 0
    } else {
      trace.displayOffset = this.findExtremes(step).min
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
      this.chartManager.update()
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
    return this.allTraces.find((element) => { return element.result.resultId === Id }
    )
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
      this.selectStep(stepId)
    }
  }

  // ////////////   Setup support functions ////////////////////////////
  setupEventListeners () {
    const serverDiv = document.getElementById('connectedServer')
    serverDiv.addEventListener('newResultReceived', (event) => {
      this.createNewTrace(event)
    }, false)

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
      this.zoom(this.selectedTrace, this.selectedStep)
    })

    this.traceInterface.clearSteps()

    this.traceInterface.alignButton.addEventListener('click', (event) => {
      this.align(this.selectedTrace, this.selectedStep)
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
}
