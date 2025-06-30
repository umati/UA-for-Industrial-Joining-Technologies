import { TraceInterface } from '../Trace/TraceInterface.mjs' // Buttons and other standard graphical elements
import ZoomHandler from '../Trace/ZoomHandler.mjs' // Handling different types of zoom
import TraceDisplay from '../Trace/TraceDisplay.mjs' // The trace area
import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
/* import * as Triggers from './trigger.mjs'
import Polynomial from './polynomial.mjs'
import Limit from './limit.mjs'
import * as Check from './Check.mjs'
import * as Selection from './Selection.mjs' */

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class Envelope extends BasicScreen {
  constructor (connectionManager, resultManager, settings) {
    super('Track', 'tighteningsystem') // Setting the name of the tab
    this.settings = settings

    // Create display areas
    const displayArea = document.createElement('div')
    displayArea.style.border = '1px solid green'
    this.backGround.appendChild(displayArea)
    this.resultManager = resultManager
    this.container = displayArea
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
    const { resultBottomArea, field } = this.setupScreen()

    this.traceInterface = new TraceInterface(resultBottomArea, this.settings)
    this.traceDisplay = new TraceDisplay(['angle', 'torque'], this.resultManager, this, field)

    this.zoomHandler = new ZoomHandler(this.traceDisplay)
    this.traceDisplay.activate()

    // this.limitTest()
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

  setupScreen () {
    this.container.classList.add('demoRow')

    const buttonArea = document.createElement('div')
    buttonArea.style.width = '20%'
    buttonArea.classList.add('demoCol')
    buttonArea.classList.add('envelopeleft')
    buttonArea.style.justifyContent = 'center'
    this.container.appendChild(buttonArea)

    /* this.selection = this.makeNamedArea('Selections', 'demoMachine')
    this.selection.style.height = '180px'
    this.selection.style.width = '300px'
    buttonArea.appendChild(this.selection) */

    this.selection = this.makeSelectionList('Selections', buttonArea)
    this.selection.addOption('OneSelection', () => alert('TEST'), () => { alert('TEST') })

    this.limits = this.makeSelectionList('Limits', buttonArea)

    this.selection.addOption('OneLimit', () => alert('TEST'), () => { alert('TEST') })

    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '200px'
    resultTopArea.style.color = 'red'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    this.tagArea = this.makeNamedArea('Tags', 'demoMachine')
    // infoArea.style.border = '2px solid white'
    this.tagArea.style.height = '180px'
    this.tagArea.style.width = '500px'
    resultTopArea.appendChild(this.tagArea)

    this.adviceArea = this.makeNamedArea('Advice', 'demoMachine')
    this.adviceArea.style.height = '180px'
    this.adviceArea.style.width = '300px'
    resultTopArea.appendChild(this.adviceArea)

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
    return { resultBottomArea, field }
  }

  /*
  limitTest () {
    // const trigger = new Triggers.MoreThanEqualTrigger('TORQUE TRACE', 5)
    // const trigger = new Triggers.StepTransition(null, null, 'TightenToTorque_4')
    // const violationTester = new Check.Crossings('TORQUE TRACE', 3) // Crossing the limit 3 times

    const limit = new Limit(
      'testLimit',
      new Triggers.StepResultValues(null, null, 'TightenToTorque_4', 'Final Angle'),
      new Polynomial([6]),
      new Check.OverLimit('TORQUE TRACE'),
      'ANGLE TRACE',
      [-10, 100],
      50,
      'TagLevel6')

    const tpSelection = new Selection.SelectTighteningProgramOrigin('ABCD')
    tpSelection.addLimit(limit)

    const selections = new Selection.SelectionList()
    selections.push(tpSelection)

    this.resultManager.subscribe((result) => {
      const violations = selections.checkAll(result)
      if (violations.length > 0) {
        this.printViolations(violations)
      }
    })
  }

  printViolations (violations) {

  } */
}
