// import ChartManager from './ChartHandler.mjs'
// import Dataset from './Dataset.mjs'

export default class SingleTraceData {
  constructor (result, owner) {
    this.steps = []
    this.result = result
    this.resultId = result.ResultMetaData.ResultId
    this.displayOffset = 0
    this.owner = owner
    this.selected = false
    this.highLights = []
    this.displayName = result.ResultMetaData.CreationTime.substr(11, 5)
  }

  get chartManager () {
    return this.owner.chartManager
  }

  get showValuesSelected () {
    return this.owner.showValuesSelected
  }

  get showLimitSelected () {
    return this.owner.showLimitSelected
  }

  addStep (step) {
    this.steps.push(step)
  }

  generateTrace () {
    for (const traceStep of this.steps) {
      const color = traceStep.color
      const cm = this.chartManager

      const dataset = cm.createDataset(traceStep.name)

      dataset.show()
      dataset.setResultId(this.result.resultId)
      dataset.setStepId(traceStep.stepId)
      dataset.setBackgroundColor(color)
      dataset.setBorderColor(color)
      dataset.setBorderWidth(1)

      traceStep.dataset = dataset
      traceStep.calculateData()
      traceStep.createPoints(color)
      traceStep.calculatePoints()
    }
  }

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
  }

  select () {
    this.selected = true
    this.highLight()
  }

  deselect () {
    this.selected = false
    this.deHighLight()
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

  refreshTraceData () {
    for (const traceStep of this.steps) {
      traceStep.calculateData()
      traceStep.calculatePoints()
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
      return element.stepId.link.programStepId === id
    }
    )
  }
}
