// import ChartManager from './ChartHandler.mjs'
import Step from './Step.mjs'

export default class SingleTraceData {
  constructor (result, owner, chartManager, identityCounter, colorFunction, displayOffset = 0) {
    this.chartManager = chartManager
    this.steps = []
    this.result = result
    this.resultId = result.ResultMetaData.ResultId
    // this.colorFunction = colorFunction
    this.trace = result?.ResultContent[0].Trace
    this.displayOffset = displayOffset
    this.owner = owner
    this.selected = false
    this.highLights = []
    this.displayName = result.ResultMetaData.CreationTime.substr(11, 5) + '(' + (identityCounter++) + ')'

    for (const resultStep of this.trace.StepTraces) {
      const nr = this.steps.length
      const newStep = new Step(resultStep, this, nr, this.chartManager, this.resultId, colorFunction(), displayOffset)
      this.steps.push(newStep)
    }
  }

  /**
   * Is the value showing turned on in the GUI
   * @date 2/23/2024 - 5:40:20 PM
   *
   * @readonly
   * @type {*}
   */
  get showValuesSelected () {
    return this.owner.showValuesSelected
  }

  /**
   * Is the limit showing turned on in the GUI
   * @date 2/23/2024 - 5:41:02 PM
   *
   * @readonly
   * @type {*}
   */
  get showLimitSelected () {
    return this.owner.showLimitSelected
  }

  /*
  highLight () {
    this.deHighLight()
    for (const traceStep of this.steps) {
      traceStep.highLight()
    }
  }

  deHighLight () {
    for (const traceStep of this.steps) {
      traceStep.deHighLight()
    }
  } */

  select () {
    this.selected = true
    // this.highLight()
  }

  deselect () {
    this.selected = false
    // this.deHighLight()
    for (const traceStep of this.steps) {
      traceStep.deselect()
    }
  }

  delete () {
    this.deselect()
    for (const traceStep of this.steps) {
      traceStep.delete()
    }
  }

  fade (factionFade) {
    for (const traceStep of this.steps) {
      traceStep.fade(factionFade)
    }
    this.owner.update()
  }

  refreshTraceData () {
    for (const traceStep of this.steps) {
      traceStep.refresh(this.displayOffset)
    }
  }

  findStepByStepId (id) {
    if (id === 'all') {
      return 'all'
    }
    return this.steps.find((element) => {
      return element.stepId.value === id
    }
    )
  }

  findStepByProgramStepId (id) {
    if (id === 'all') {
      return 'all'
    }
    return this.steps.find((element) => {
      return element.stepId.link.ProgramStepId === id
    }
    )
  }
}
