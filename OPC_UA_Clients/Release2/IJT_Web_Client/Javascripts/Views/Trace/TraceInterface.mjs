export class TraceInterface {
  constructor (container, settings) {
    this.resetColor()
    this.settings = settings
  }

  getRandomColor () {
    if (this.hue > 100000) {
      this.resetColor()
    }
    const lightness = Math.floor(15 + 35 * Math.random())
    return 'hsla(' + (this.hue += 78) + ', 100%, ' + lightness + '%, 1.0)'
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
      tracebutton.classList.add('myButton')
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
    stepButton.classList.add('myButton')
    stepButton.innerText = step.name
    this.traceDiv.appendChild(stepButton)
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
    function createHeader (container, name) {
      const header = document.createElement('div')
      header.innerText = name
      header.classList.add('myHeader')
      container.appendChild(header)
    }
    function createTuple (name, right) {
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

    function createSelector (container, name, values, standalone = false) {
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

    this.traceArea = document.createElement('div') // This is where the trace graphics will do
    backGround.appendChild(this.traceArea)

    const interfaceArea = document.createElement('div')
    interfaceArea.classList.add('traceButtonArea')
    container.appendChild(interfaceArea)

    const trace = document.createElement('div')
    trace.classList.add('myInfoArea')
    trace.classList.add('fillWidth')
    interfaceArea.appendChild(trace)

    createHeader(trace, 'Traces')

    this.traceDiv = document.createElement('div')
    trace.appendChild(this.traceDiv)

    // this.traceDiv.classList.add('traceList')

    createHeader(trace, 'Steps')

    this.stepDiv = document.createElement('div')
    trace.appendChild(this.stepDiv)

    const view = document.createElement('div')
    view.classList.add('myInfoArea')
    view.classList.add('thinView')
    // view.classList.add('smallSettingArea')
    interfaceArea.appendChild(view)

    createHeader(view, 'View')

    this.traceTypeSelect = createSelector(view, 'View type', [['toa', 'Torque over angle'], ['tot', 'Torque over time']], true)
    this.absoluteSelect = createSelector(view, 'Torque values', [['normal', 'Normal'], ['absolute', 'Absolute']], true)
    // this.xyz = createSelector(interfaceArea, 'Fade old', [['toa','Torque over angle'],['tot','Torque over time']])

    this.valueShower = createSelector(view, 'Show values', [['no', 'Hide values'], ['yes', 'Show values']], true)
    this.limitShower = createSelector(view, 'Show limits', [['no', 'Hide limits'], ['yes', 'Show limits']], true)

    this.deleteButton = document.createElement('button')
    this.deleteButton.classList.add('myButton')
    this.deleteButton.innerText = 'Delete'
    view.appendChild(this.deleteButton)

    this.alignButton = document.createElement('button')
    this.alignButton.classList.add('myButton')
    this.alignButton.innerText = 'Align'
    view.appendChild(this.alignButton)
  }
}
