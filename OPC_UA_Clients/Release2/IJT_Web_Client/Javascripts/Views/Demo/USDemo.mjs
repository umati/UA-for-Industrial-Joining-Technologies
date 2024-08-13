import { TraceInterface } from '../Trace/TraceInterface.mjs' // Buttons and other standard graphical elements
import ZoomHandler from '../Trace/ZoomHandler.mjs' // Handling different types of zoom
import TraceDisplay from '../Trace/TraceDisplay.mjs' // The trace area
import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
import CommonPropertyView from './CommonPropertyView.mjs' // The machine properties view
import IJTPropertyView from './IJTPropertyView.mjs' // The machine properties view

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class USDemo extends BasicScreen {
  constructor (methodManager, resultManager, connectionManager, settings) {
    super('Demo', 'tighteningsystem') // Setting the name of the tab
    this.methodManager = methodManager
    this.resultManager = resultManager
    this.settings = settings

    // Create display areas
    const displayArea = document.createElement('div')
    this.backGround.appendChild(displayArea)
    this.container = displayArea

    // Wait until the methods have loaded
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
  * given folders, and set up invokation buttons
  */
  activate () {
    this.container.classList.add('demoRow')

    const buttonArea = document.createElement('div')
    buttonArea.style.width = '20%'
    buttonArea.classList.add('demoCol')
    buttonArea.style.justifyContent = 'center'
    this.container.appendChild(buttonArea)

    // Handling of button 1 (calling select process)
    const button1 = document.createElement('button')
    button1.innerText = 'Select program 1'
    button1.classList.add('demoButton')
    buttonArea.appendChild(button1)
    button1.addEventListener('click', this.selectJoiningProcess(this.settings.JoiningProcess1))

    // Handling of button 2 (calling select process)
    const button2 = document.createElement('button')
    button2.innerText = 'Select program 2'
    button2.classList.add('demoButton')
    buttonArea.appendChild(button2)
    button2.addEventListener('click', this.selectJoiningProcess(this.settings.JoiningProcess2))

    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '200px'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    // Set up the common parts of the result
    const infoArea = this.makeNamedArea('Common Result Data', 'demoMachine')
    // infoArea.style.border = '2px solid white'
    infoArea.style.height = '180px'
    infoArea.style.width = '500px'
    resultTopArea.appendChild(infoArea)
    this.propertyView = new CommonPropertyView(
      ['result.ResultMetaData.Name',
        'result.ResultMetaData.ResultEvaluation',
        'result.ResultMetaData.CreationTime',
        'result.ResultMetaData.SequenceNumber',
        'result.ResultMetaData.ResultId'],
      infoArea.contentArea,
      this.resultManager)

    // Set up the specific tightening related parameters of the reult
    const tqAngleBox = this.makeNamedArea('Tightening Result Data', 'demoMachine')
    tqAngleBox.style.height = '180px'
    tqAngleBox.style.width = '300px'
    resultTopArea.appendChild(tqAngleBox)
    this.IJTpropertyView = new IJTPropertyView(tqAngleBox.contentArea, this.resultManager)

    const resultBottomArea = document.createElement('div')
    resultBottomArea.style.height = '50%'
    resultBottomArea.style.margin = '5px'
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

    this.traceInterface = new TraceInterface(resultBottomArea, this.settings)
    this.traceDisplay = new TraceDisplay(['angle', 'torque'], this.resultManager, this, field)

    this.zoomHandler = new ZoomHandler(this.traceDisplay)
    this.traceDisplay.activate()
  }

  /**
   * This function selects a tightening process on the tool
   * @param {*} process The identity of the tightening program
   * @returns Nothing
   */
  selectJoiningProcess (process) {
    const selectJoiningProcessMethod = this.methodManager.getMethod('SelectJoiningProcess')
    if (!selectJoiningProcessMethod) {
      return
    }

    const values = [
      {
        value: this.settings.productId,
        type: {
          pythonclass: 'NodeId',
          Identifier: '12',
          NamespaceIndex: '0',
          NodeIdType: 'NodeIdType.TwoByte'
        }
      },
      {
        type: {
          Identifier: 3029,
          NamespaceIndex: 3
        },
        value: [
          {
            value: '',
            type: '31918'
          }, {
            value: '',
            type: '31918'
          }, {
            value: process, // This should be the selection name of the process
            type: '31918'
          }]
      }
    ]

    this.methodManager.call(selectJoiningProcessMethod, values).then(
      (success) => {
        // console.log(JSON.stringify(success))
      },
      (fail) => {
        console.log(JSON.stringify(fail))
      }
    )
  }

  // THE METHODS BELOW THIS IS JUST TO SET UP ZOOMING, SCROLLING, ETC OF THE TRACE WINDOW

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
