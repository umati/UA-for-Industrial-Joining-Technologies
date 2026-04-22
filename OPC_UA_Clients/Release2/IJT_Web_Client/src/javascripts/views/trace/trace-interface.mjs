export class TraceInterface {
  constructor (container, settings) {
    this.resetColor()
    this.settings = settings
  }

  getRandomColor () {
    if (this.hue > 100000) {
      this.resetColor()
    }
    const saturation = 92 + Math.floor(8 * Math.random())
    const lightness = 56 + Math.floor(14 * Math.random())
    return `hsla(${(this.hue += 78)}, ${saturation}%, ${lightness}%, 1.0)`
  }

  refreshTraceCallback () {
    if (this.settings) {
      if (this.settings.refreshTraceCallback) {
        return this.settings.refreshTraceCallback
      }
    }
    return false
  }

  resetColor () {
    this.hue = 20
    this.saturation = 100
    this.lightness = 40
  }

  zoomBoxDraw (evt, pressed, divOffset) {

  }

  selectStep (selectedStep) {

  }

  clearSteps () {

  }

  selectTrace (resultId) {

  }

  addStepInGUI (step, stepIdValue) {

  }

  updateTracesInGUI (allTraces) {

  }

  setTraceMode (_mode) {}

  setAxisInfo (_xAxis, _yAxis) {}

  pulseTraceViewport () {}
}
export class ButtonTraceInterface extends TraceInterface {
  constructor (container) {
    super()
    this.generateHTML(container)
    this.resetColor()
    this.zoomBox = null
  }

  setTraceSelectEventListener (evtHandler) {
    this.selectTraceEventHandler = evtHandler
  }

  updateTracesInGUI (allTraces) {
    this.traceDiv.innerHTML = ''
    for (const trace of allTraces) {
      const tracebutton = document.createElement('button')
      tracebutton.classList.add('myButton', 'traceItemButton')
      tracebutton.innerText = trace.displayName
      this.traceDiv.appendChild(tracebutton)
      tracebutton.resultId = trace.result.id

      tracebutton.addEventListener('click', this.selectTraceEventHandler)
    }
  }

  selectTrace (id) {
    for (const button of this.traceDiv.children) {
      if (button.resultId === id) {
        button.classList.add('myButtonSelected')
      } else {
        button.classList.remove('myButtonSelected')
      }
    }
  }

  setStepSelectEventListener (evtHandler) {
    this.selectStepEventHandler = evtHandler
  }

  clearSteps () {
    this.stepDiv.innerHTML = ''
    this.addStepInGUI({ name: 'All', stepId: { value: 'all' } })
  }

  addStepInGUI (step) {
    const stepButton = document.createElement('button')
    stepButton.classList.add('myButton', 'stepItemButton')
    stepButton.innerText = step.name
    stepButton.stepId = step.stepId.value

    stepButton.addEventListener('click', this.selectStepEventHandler)
    this.stepDiv.appendChild(stepButton)
  }

  selectStep (id) {
    for (const button of this.stepDiv.children) {
      if (button.stepId === id) {
        button.classList.add('myButtonSelected')
      } else {
        button.classList.remove('myButtonSelected')
      }
    }
  }

  generateHTML (container) {
    const createHeader = (container, name) => {
      const header = document.createElement('div')
      header.innerText = name
      header.classList.add('myHeader')
      container.appendChild(header)
    }
    const createTuple = (name, right) => {
      const outer = document.createElement('div')
      outer.classList.add('kvPair')
      const title = document.createElement('div')
      title.classList.add('kvKey')
      title.innerText = name
      outer.appendChild(title)
      const content = document.createElement('div')
      content.classList.add('kvValue')
      content.appendChild(right)
      outer.appendChild(content)

      return outer
    }

    const createSelector = (container, name, values, standalone = false) => {
      const selector = document.createElement('select')
      selector.classList.add('kvSelect')
      for (const v of values) {
        const option = document.createElement('option')
        option.setAttribute('value', v[0])
        option.innerText = v[1]
        selector.appendChild(option)
      }
      if (standalone) {
        container.appendChild(selector)
      } else {
        container.appendChild(createTuple(name, selector))
      }
      return selector
    }

    const backGround = document.createElement('div')
    backGround.classList.add('mainDropDown')
    backGround.classList.add('bigTraceMargin')
    container.appendChild(backGround)

    const title = document.createElement('div')
    title.classList.add('myHeader')
    title.innerText = 'Trace'
    backGround.appendChild(title)

    this.traceMetaBar = document.createElement('div')
    this.traceMetaBar.classList.add('traceMetaBar')
    backGround.appendChild(this.traceMetaBar)

    this.traceModeBadge = document.createElement('div')
    this.traceModeBadge.classList.add('traceMetaBadge')
    this.traceMetaBar.appendChild(this.traceModeBadge)

    this.traceAxisBadge = document.createElement('div')
    this.traceAxisBadge.classList.add('traceMetaBadge', 'traceMetaBadgeAxis')
    this.traceMetaBar.appendChild(this.traceAxisBadge)

    this.traceArea = document.createElement('div') // This is where the trace graphics will do
    this.traceArea.classList.add('traceChartHost')
    backGround.appendChild(this.traceArea)

    const interfaceArea = document.createElement('div')
    interfaceArea.classList.add('traceButtonArea', 'traceControlDock')
    container.appendChild(interfaceArea)

    const trace = document.createElement('div')
    trace.classList.add('myInfoArea')
    trace.classList.add('fillWidth')
    interfaceArea.appendChild(trace)

    createHeader(trace, 'Trace list')

    this.traceDiv = document.createElement('div')
    this.traceDiv.classList.add('traceListPanel')
    trace.appendChild(this.traceDiv)

    // this.traceDiv.classList.add('traceList')

    createHeader(trace, 'Steps')

    this.stepDiv = document.createElement('div')
    this.stepDiv.classList.add('stepListPanel')
    trace.appendChild(this.stepDiv)

    const view = document.createElement('div')
    view.classList.add('myInfoArea')
    view.classList.add('thinView')
    // view.classList.add('smallSettingArea')
    interfaceArea.appendChild(view)

    createHeader(view, 'Display')

    this.traceTypeSelect = createSelector(view, 'Type', [['toa', 'Torque over angle'], ['tot', 'Torque over time']], true)
    this.absoluteSelect = createSelector(view, 'Torque', [['normal', 'Normal'], ['absolute', 'Absolute']], true)
    // this.xyz = createSelector(interfaceArea, 'Fade old', [['toa','Torque over angle'],['tot','Torque over time']])

    this.valueShower = createSelector(view, 'Values', [['no', 'Hide'], ['yes', 'Show']], true)
    this.limitShower = createSelector(view, 'Limits', [['no', 'Hide'], ['yes', 'Show']], true)

    this.deleteButton = document.createElement('button')
    this.deleteButton.classList.add('myButton')
    this.deleteButton.innerText = 'Delete'
    view.appendChild(this.deleteButton)

    this.alignButton = document.createElement('button')
    this.alignButton.classList.add('myButton')
    this.alignButton.innerText = 'Align'
    view.appendChild(this.alignButton)

    this.setTraceMode('toa')
    this.setAxisInfo('angle', 'torque')
  }

  setTraceMode (mode) {
    if (!this.traceModeBadge) {
      return
    }
    const modeLabel = mode === 'tot' ? 'Mode: Torque over Time' : 'Mode: Torque over Angle'
    this.traceModeBadge.innerText = modeLabel
  }

  setAxisInfo (xAxis, yAxis) {
    if (!this.traceAxisBadge) {
      return
    }
    const normalizedX = String(xAxis || '').toUpperCase() || 'ANGLE'
    const normalizedY = String(yAxis || '').toUpperCase() || 'TORQUE'
    this.traceAxisBadge.innerText = `X: ${normalizedX} | Y: ${normalizedY}`
  }

  pulseTraceViewport () {
    if (!this.traceArea) {
      return
    }
    this.traceArea.classList.remove('is-trace-fresh')
    // Force reflow so repeated trace updates can replay the animation.
    // eslint-disable-next-line no-unused-expressions
    this.traceArea.offsetWidth
    this.traceArea.classList.add('is-trace-fresh')
    window.setTimeout(() => {
      this.traceArea?.classList?.remove('is-trace-fresh')
    }, 260)
  }
}
