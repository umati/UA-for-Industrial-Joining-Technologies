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
  constructor (methodManager, resultManager, connectionManager) {
    super('Demo', 'tighteningsystem')
    this.methodManager = methodManager
    this.resultManager = resultManager
    this.productId = 'testProduct'
    this.JoiningProcess1 = 'ProgramIndex_1'
    this.JoiningProcess2 = 'ProgramIndex_2'
    this.JoiningProcess3 = 'ProgramIndex_3'

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
    const selectJoiningProcess1 = this.methodManager.getMethod('SelectJoiningProcess')
    this.container.classList.add('demoRow')

    const buttonArea = document.createElement('div')
    buttonArea.style.width = '20%'
    buttonArea.classList.add('demoCol')
    buttonArea.style.justifyContent = 'center'
    this.container.appendChild(buttonArea)

    const button1 = document.createElement('button')
    button1.innerText = 'Tigtening program 1'
    button1.classList.add('demoButton')
    buttonArea.appendChild(button1)

    /*
    button1.addEventListener('click', (edu) => {
      if (!selectJoiningProcess1) {
        return
      }

      const values = [
        {
          value: this.productId,
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
              value: this.JoiningProcess1,
              type: '31918'
            }]
        }
      ]

      this.methodManager.call(selectJoiningProcess1, values).then(
        (success) => {
          console.log(JSON.stringify(success))
        },
        (fail) => {
          console.log(JSON.stringify(fail))
        }
      )
    }) */

    const simulateSingleResult = this.methodManager.getMethod('SimulateSingleResult')

    button1.innerText = 'SimulateSingleresult'
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

      this.methodManager.call(simulateSingleResult, values).then(
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

    button2.addEventListener('click', (edu) => {
      if (!selectJoiningProcess1) {
        return
      }

      const values = [
        {
          value: this.productId,
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
              value: this.JoiningProcess2,
              type: '31918'
            }]
        }
      ]

      this.methodManager.call(selectJoiningProcess1, values).then(
        (success) => {
          console.log(JSON.stringify(success))
        },
        (fail) => {
          console.log(JSON.stringify(fail))
        }
      )
    })

    const button3 = document.createElement('button')
    button3.innerText = 'Tightening program 3'
    button3.classList.add('demoButton')
    buttonArea.appendChild(button3)

    button3.addEventListener('click', (edu) => {
      if (!selectJoiningProcess1) {
        return
      }

      const values = [
        {
          value: this.productId,
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
              value: this.JoiningProcess3,
              type: '31918'
            }]
        }
      ]

      this.methodManager.call(selectJoiningProcess1, values).then(
        (success) => {
          console.log(JSON.stringify(success))
        },
        (fail) => {
          console.log(JSON.stringify(fail))
        }
      )
    })
    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '220px'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    const infoArea = this.makeNamedArea('Common Result Data', 'demoMachine')
    infoArea.style.border = '2px solid white'
    infoArea.style.height = '200px'
    infoArea.style.width = '500px'
    resultTopArea.appendChild(infoArea)
    this.propertyView = new CommonPropertyView(
      ['result.ResultMetaData.Name',
        'result.ResultMetaData.ResultEvaluationCode',
        'result.ResultMetaData.CreationTime',
        'result.ResultMetaData.SequenceNumber',
        'result.ResultMetaData.ResultId'],
      infoArea.contentArea,
      this.resultManager)

    const tqAngleBoax = this.makeNamedArea('Tightening Result Data', 'demoMachine')
    tqAngleBoax.style.border = '2px solid black'
    tqAngleBoax.style.height = '200px'
    tqAngleBoax.style.width = '300px'
    // tqAngleBoax.contentArea.innerText = 'FinalTorque: FinalAngle'
    resultTopArea.appendChild(tqAngleBoax)
    this.IJTpropertyView = new IJTPropertyView(tqAngleBoax.contentArea, this.resultManager)

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
