import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class USDemo extends BasicScreen {
  constructor () {
    super('DemoSettings', 'tighteningsystem')

    this.productId = 'www.atlascopco.com/CABLE-B0000000-'
    this.JoiningProcess1 = 'ProgramIndex_1'
    this.JoiningProcess2 = 'ProgramIndex_2'
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

    const displayArea = document.createElement('div')
    this.backGround.appendChild(displayArea)

    this.container = displayArea

    // this.container.innerHTML += '<p>ProductId'
    const labelElement = document.createElement('label')
    labelElement.innerHTML = 'ProductId   '
    this.container.appendChild(labelElement)

    this.createInput(this.productId, this.container, (evt) => {
      this.productId = evt.srcElement.value
    }, '40')
    this.container.appendChild(document.createElement('br'))

    const labelElement2 = document.createElement('label')
    labelElement2.innerHTML = 'Button 1 selection   '
    this.container.appendChild(labelElement2)

    this.createInput(this.JoiningProcess1, this.container, (evt) => {
      this.JoiningProcess1 = evt.srcElement.value
      console.log(evt.srcElement.value)
    }, '40')
    this.container.appendChild(document.createElement('br'))

    const labelElement3 = document.createElement('label')
    labelElement3.innerHTML = 'Button 2 selection   '
    this.container.appendChild(labelElement3)

    this.createInput(this.JoiningProcess2, this.container, (evt) => {
      this.JoiningProcess2 = evt.srcElement.value
    }, '40')
  }
}
