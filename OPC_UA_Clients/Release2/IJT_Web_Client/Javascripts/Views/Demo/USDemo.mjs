import { TraceInterface } from '../Trace/TraceInterface.mjs' // Buttons and other standard graphical elements
import ZoomHandler from '../Trace/ZoomHandler.mjs' // Handling different types of zoom
import TraceDisplay from '../Trace/TraceDisplay.mjs' // The trace area
import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
import PropertyView from './PropertyView.mjs' // The trace area

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class USDemo extends BasicScreen {
  constructor (methodManager, resultManager, connectionManager) {
    super('Demo', 'tighteningsystem')
    this.methodManager = methodManager
    this.resultManager = resultManager

    const displayArea = document.createElement('div')
    // displayArea.classList.add('drawAssetBox')
    this.backGround.appendChild(displayArea)

    this.container = displayArea

    connectionManager.subscribe('methods', (setToTrue) => {
      if (setToTrue) {
        this.activate()
      }
    })
  }

  /**
   * Run everytime the tab is opened
   */
  initiate () {

  }

  /**
  * Run activate when normal setup is done.
  * This queries the methodmanager for the available methods in the
  * given folders, and set up invokation buttons for all found methods
  */
  activate () {
    this.container.classList.add('demoRow')

    const buttonArea = document.createElement('div')
    buttonArea.style.width = '20%'
    buttonArea.classList.add('demoCol')
    buttonArea.style.justifyContent = 'center'
    this.container.appendChild(buttonArea)

    const button1 = document.createElement('button')
    button1.innerText = 'Tightening program 1'
    button1.classList.add('demoButton')
    buttonArea.appendChild(button1)

    const mth = this.methodManager.getMethod('SimulateSingleResult')

    button1.addEventListener('click', (edu) => {
      const values = [
        {
          value: '2',
          type: {
            pythonclass: 'NodeId',
            Identifier: '7',
            NamespaceIndex: '0',
            NodeIdType: 'NodeIdType.TwoByte'
          }
        },
        {
          value: true,
          type: {
            pythonclass: 'NodeId',
            Identifier: '1',
            NamespaceIndex: '0',
            NodeIdType: 'NodeIdType.TwoByte'
          }
        }
      ]

      this.methodManager.call(mth, values).then(
        (success) => {
          console.log(JSON.stringify(success))
        },
        (fail) => {
          console.log(JSON.stringify(fail))
        }
      )
    })

    const button2 = document.createElement('button')
    button2.innerText = 'Tightening program 2'
    button2.classList.add('demoButton')
    buttonArea.appendChild(button2)

    const button3 = document.createElement('button')
    button3.innerText = 'Tightening program 3'
    button3.classList.add('demoButton')
    buttonArea.appendChild(button3)

    const resultArea = document.createElement('div')
    // displayArea.classList.add('drawAssetBox')
    // resultArea.style.border = '2px solid blue'
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    // displayArea.classList.add('drawAssetBox')
    resultTopArea.style.height = '200px'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    const infoArea = document.createElement('div')
    infoArea.style.border = '2px solid white'
    infoArea.style.height = '200px'
    infoArea.style.width = '600px'
    // infoArea.innerText = 'Name: CreationTime: ResultId: ResultEvaluation:'
    resultTopArea.appendChild(infoArea)
    this.propertyView = new PropertyView(
      ['result.ResultMetaData.Name',
        'result.ResultMetaData.ResultEvaluationCode',
        'result.ResultMetaData.CreationTime',
        'result.ResultMetaData.SequenceNumber',
        'result.ResultMetaData.ResultId'],
      infoArea,
      this.resultManager)

    const tqAngleBoax = document.createElement('div')
    tqAngleBoax.style.border = '2px solid black'
    tqAngleBoax.style.height = '200px'
    tqAngleBoax.style.width = '300px'
    tqAngleBoax.innerText = 'FinalTorque: FinalAngle'
    resultTopArea.appendChild(tqAngleBoax)

    const resultBottomArea = document.createElement('div')
    resultBottomArea.style.height = '50%'
    resultArea.appendChild(resultBottomArea)

    const backGround = document.createElement('div')
    backGround.classList.add('myInfoArea')
    resultBottomArea.appendChild(backGround)

    const title = document.createElement('div')
    title.classList.add('myHeader')
    title.innerText = 'Trace'
    backGround.appendChild(title)

    const field = document.createElement('div') // This is where the trace graphics will do
    backGround.appendChild(field)
    //

    this.traceInterface = new TraceInterface(resultBottomArea)
    this.traceDisplay = new TraceDisplay(['angle', 'torque'], this.resultManager, this, field)

    this.zoomHandler = new ZoomHandler(this.traceDisplay)
    this.traceDisplay.activate()
  }

  /**
   * Mouse button up - switch of behaviour (select trace or start zoom)
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} resultId the actual result if the click was on a given trace
   * @param {*} stepId the step if the click was on a given trace
   */
  onclick = (evt, coord, resultId, stepId) => {
    if (resultId) {
      this.traceDisplay.clicked(resultId, stepId)
    } else {
      this.zoomHandler.onclick(evt, coord, resultId, stepId)
    }
  }

  /**
   * Draw a box when mouse selecting a zoom area
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousemove = (evt, coord) => {
    this.zoomHandler.onmousemove(evt, coord)
  }

  /**
   * Mouse button down - zoom area start of selection
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   */
  onmousedown = (evt, coord) => {
    this.zoomHandler.onmousedown(evt, coord)
  }

  /**
   * handle mouse wheel, or touchpad zoom
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @returns Nothing
   */
  onmousewheel = (evt, coord) => {
    this.zoomHandler.onmousewheel(evt, coord)
  }

  /**
   * Touchscreen start touch
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffsetoffset to correctly location
   */
  touchstart (evt, coord, touchOffset) {
    this.zoomHandler.touchstart(evt, coord, touchOffset)
  }

  /**
   * Moving a screentouch
   * @param {*} evt mouse event
   * @param {*} coord graph coordinates of the event
   * @param {*} touchOffset to correctly calculate location
   */
  touchmove (evt, coord, touchOffset) {
    this.zoomHandler.touchmove(evt, coord, touchOffset)
  }

  touchend (evt, coord, touchOffset) {
    this.zoomHandler.touchend(evt, coord, touchOffset)
  }

  touchcancel (evt, coord, touchOffset) {
    this.zoomHandler.touchcancel(evt, coord, touchOffset)
  }
}
