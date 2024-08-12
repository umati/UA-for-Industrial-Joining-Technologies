import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class Settings extends BasicScreen {
  constructor (webSocketManager) {
    super('Settings', 'tighteningsystem')
    this.loaded = false
    this.resolvers = []

    this.webSocketManager = webSocketManager
    this.productId = '-'
    this.JoiningProcess1 = '-'
    this.JoiningProcess2 = '-'

    this.settings = { // default values
      productid: 'www.company.com/ProductABC123',
      button1selection: 'ProgramIndex_1',
      button2selection: 'ProgramIndex_2',
      initialviewlevel: 3,
      command: 'set settings',
      endpoint: 'common'
    }

    // Listen to the tree of possible connection points (Available OPC UA servers)
    this.webSocketManager.subscribe(null, 'get settings', (msg) => {
      this.setupPage(msg)
    })

    this.webSocketManager.send('get settings')

    this.fadeList = {}
    this.fadeTime = 10000
    this.fadeSteps = 5

    this.refreshTraceCallbackFade = (trace, traceOwner) => {
      const fadeFunc = () => {
        if (trace.fadeCounter < 1) {
          traceOwner.deleteSelected(trace)
          this.fadeList[trace.resultId] = false
        } else {
          trace.fadeCounter--
          trace.fade(1 / (this.fadeSteps + 1))
          setTimeout(fadeFunc, this.fadeTime / this.fadeSteps)
        }
      }
      const currentCounter = this.fadeList[trace.resultId]
      if (!currentCounter) {
        this.fadeList[trace.resultId] = true
        trace.fadeCounter = this.fadeSteps
        setTimeout(fadeFunc, this.fadeTime / this.fadeSteps)
      }
    }

    this.refreshTraceCallback = (trace, traceOwner) => {
      traceOwner.deleteSelected(trace)
    }

    const editArea = document.createElement('div')
    editArea.classList.add('demosettingArea')
    this.backGround.appendChild(editArea)

    this.displayArea = document.createElement('div')
    this.backGround.appendChild(this.displayArea)

    this.container = editArea

    this.createButton('Save', this.displayArea, () => {
      this.settings.productid = this.productId
      this.settings.button1selection = this.JoiningProcess1
      this.settings.button2selection = this.JoiningProcess2
      this.settings.initialviewlevel = this.initialViewLevel

      this.webSocketManager.send('set settings', null, null, this.settings)
    })

    this.setupPage(this.settings, true)

    // this.container.innerHTML += '<p>ProductId'
  }

  setupPage (msg, initial) {
    if (msg.productid || msg.initialviewlevel
    ) {
      this.settings = msg
      this.productId = msg.productid
      this.JoiningProcess1 = msg.button1selection
      this.JoiningProcess2 = msg.button2selection
      this.methodDefaults = msg.methoddefaults
      this.initialViewLevel = msg.initialviewlevel
    }

    try {
      this.container.innerHTML = ''

      const labelElement = document.createElement('label')
      labelElement.innerHTML = 'ProductId   '
      this.container.appendChild(labelElement)

      this.createInput(this.productId, this.container, (evt) => {
        this.productId = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement2 = document.createElement('label')
      labelElement2.innerHTML = 'Button 1 selection   '
      this.container.appendChild(labelElement2)

      this.createInput(this.JoiningProcess1, this.container, (evt) => {
        this.JoiningProcess1 = evt
        console.log(evt.srcElement.value)
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement3 = document.createElement('label')
      labelElement3.innerHTML = 'Button 2 selection   '
      this.container.appendChild(labelElement3)

      this.createInput(this.JoiningProcess2, this.container, (evt) => {
        this.JoiningProcess2 = evt
      }, '40')
      this.container.appendChild(document.createElement('br'))

      const labelElement4 = document.createElement('label')
      labelElement4.innerHTML = 'Default view level   '
      this.container.appendChild(labelElement4)

      this.container.select = document.createElement('select')
      this.container.appendChild(this.container.select)

      const viewLevels = [['Basic', 1], ['Simple', 2], ['Detailed', 3], ['Specialized', 4], ['Settings', 5]]

      for (const optionData of viewLevels) {
        const option = document.createElement('option')
        option.value = optionData[1]
        option.innerHTML = optionData[0]
        this.container.select.appendChild(option)
      }

      this.container.select.value = this.initialViewLevel

      this.container.select.onchange = (evt) => {
        this.initialViewLevel = evt.target.value
      }

      this.container.appendChild(document.createElement('br'))
    } finally {
      if (!initial) {
        this.loaded = true
        for (const resolve of this.resolvers) {
          resolve(this)
        }
      }
    }
  }

  settingPromise () {
    // console.log('LOOKING FOR: '+nodeId+path)
    return new Promise((resolve, reject) => {
      if (this.loaded) {
        resolve(this)
      } else {
        this.resolvers.push(resolve)
      }
    })
  }
}
