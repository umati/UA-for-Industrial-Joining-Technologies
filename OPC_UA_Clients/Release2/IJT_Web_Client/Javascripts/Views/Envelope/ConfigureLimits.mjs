import { TraceInterface } from '../Trace/TraceInterface.mjs' // Buttons and other standard graphical elements
import ZoomHandler from '../Trace/ZoomHandler.mjs' // Handling different types of zoom
import TraceDisplay from '../Trace/TraceDisplay.mjs' // The trace area
import * as BasicScreenX from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality
import * as Triggers from './trigger.mjs'
/* import Polynomial from './polynomial.mjs'
import Limit from './limit.mjs' */
import * as Checks from './Check.mjs'
import SelectionView from './SelectionView.mjs'
import SelectionList from './SelectionList.mjs'
/* import * as Selection from './Selection.mjs' */

console.log('HERE')
/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC /* UA Industrial Joining Technologies communication
 */
export default class ConfigureLimits extends BasicScreenX.default {
  constructor (connectionManager, resultManager, settings) {
    super('Configure Limits', 'tighteningsystem') // Setting the name of the tab
    this.settings = settings

    // Create display areas
    const displayArea = document.createElement('div')
    // displayArea.style.border = '1px solid red'
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

    const ListAreas = document.createElement('div')
    ListAreas.style.width = '20%'
    ListAreas.classList.add('demoCol')
    ListAreas.classList.add('envelopeleft')
    ListAreas.style.justifyContent = 'center'
    this.container.appendChild(ListAreas)


    this.selection = this.makeNamedArea('Selection list', 'Selection list')
    this.selection.style.height = '180px'
    this.selection.style.width = '300px'
    ListAreas.appendChild(this.selection)

    this.fullSelectionList = new SelectionList(this.selection, this) 

    const selectionHolder = document.createElement('div')
    ListAreas.appendChild(selectionHolder)
    this.selection = new BasicScreenX.SelectionList('Selection management', selectionHolder, this)
    this.selection.addOption('NEW',
      (button) => {
        if (!button.selectionObject) {
          button.selectionObject = this.selectionView.getDefault()
          this.fullSelectionList.addSelection(button.selectionObject)
        }
        this.selectionView.draw(button.selectionObject)
      },
      () => { /* drag() */ })

    /*
    this.limits.style.height = '180px'
    ListAreas.appendChild(this.limits)
    this.limits.contentArea.innerText = 'LowerRampHard'
    */

    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '320px'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    const selectorConfig = this.makeNamedArea('Selector', 'selectionArea')
    selectorConfig.style.width = '200px'
    selectorConfig.style.height = '305px'
    resultTopArea.appendChild(selectorConfig)
    this.selectionArea = selectorConfig.contentArea

    const limitList = this.makeNamedArea('Limit', 'selectionArea')
    limitList.style.width = '200px'
    limitList.style.height = '305px'
    resultTopArea.appendChild(limitList)
    this.limitArea = limitList.contentArea

    const borderBox = this.makeNamedArea('Border', 'selectionArea')
    borderBox.style.height = '305px'
    borderBox.style.width = '200px'
    resultTopArea.appendChild(borderBox)

    const generalArea = this.createArea('Trigger')
    generalArea.classList.add('methodBorder')
    this.limitArea.appendChild(generalArea)

    this.createTitledInput(
      'Name',
      this.createInput('Limit_1', null, (value) => { this.limitName = value }),
      generalArea
    )

    this.createTitledInput(
      'Tag name',
      this.createInput('ViolationTag_1', null, (value) => { this.limitName = value }),
      generalArea
    )

    this.createTitledInput(
      'Severity',
      this.createInput('100', null, (value) => {
        this.limitName = value
      }),
      generalArea
    )

    this.selectionView = new SelectionView(this.selectionArea, this, null)

    /*
    const selectorDropDown = this.fillDropdownFromImport('Selector', Selection, 'Selection', (selector) => {
      this.selector = selector
      if (this.lastResult) {
        const value = this.selector.getResultValue(this.lastResult)
        this.resultLabel.innerText = value
      }
    })
    this.selector = selectorDropDown.dropdownObject
    this.selectionArea.appendChild(selectorDropDown)

    this.resultLabel = this.createLabel('Latest: ')
    this.selectionArea.appendChild(this.resultLabel)

    this.resultButton = this.createButton('Apply', this.selectionArea, (button) => {
      if (this.lastResult) {
        const value = this.selector.getResultValue(this.lastResult)
        this.selector.value = value
        selectorDropDown.redraw()
      }
    })

    this.selectionArea.appendChild(this.resultButton) */

    this.resultManager.subscribe((result) => {
      this.selectionView.setResult(result)
    })

    const triggerArea = this.createArea('Trigger')
    triggerArea.classList.add('methodBorder')
    const dropDown = this.createDropdownFromImport('TriggerType', Triggers, 'Triggers')
    triggerArea.appendChild(dropDown)
    this.limitArea.appendChild(triggerArea)

    const polyArea = document.createElement('div')

    this.createTitledInput(
      'Constant',
      this.createInput('0.0', null, (value) => {
        this.polynomial0 = value
      }),
      polyArea
    )

    this.createTitledInput(
      'x * ',
      this.createInput('0.0', null, (value) => {
        this.polynomial1 = value
      }),
      polyArea
    )

    this.createTitledInput(
      'x<sup>2</sup> * ',
      this.createInput('0.0', null, (value) => {
        this.polynomial2 = value
      }),
      polyArea
    )

    this.createTitledInput(
      'x<sup>3</sup> * ',
      this.createInput('0.0', null, (value) => {
        this.polynomial3 = value
      }),
      polyArea
    )

    this.createTitledInput(
      'x<sup>4</sup> * ',
      this.createInput('0.0', null, (value) => {
        this.polynomial4 = value
      }),
      polyArea
    )

    this.createTitledInput(
      'x<sup>5</sup> * ',
      this.createInput('0.0', null, (value) => {
        this.polynomial5 = value
      }),
      polyArea
    )

    borderBox.appendChild(this.addTitle('Polynomial', polyArea))

    const checkArea = this.createArea('Check')
    checkArea.classList.add('methodBorder')
    const checkDropDown = this.createDropdownFromImport('Check', Checks, 'Checks')
    checkArea.appendChild(checkDropDown)
    borderBox.appendChild(checkArea)

    const range = this.createArea('Range')
    range.classList.add('methodBorder')
    this.limitArea.appendChild(range)

    this.createTitledInput(
      'X-axis',
      this.createInput('ANGLE TRACE', null, (value) => {
        this.xAxis = value
      }),
      range
    )

    this.createTitledInput(
      'Start x value',
      this.createInput('0', null, (value) => {
        this.xAxisStart = value
      }),
      range
    )

    this.createTitledInput(
      'End x value',
      this.createInput('100', null, (value) => {
        this.xAxisEnd = value
      }),
      range
    )

    const resultBottomArea = document.createElement('div')
    resultBottomArea.style.height = '60%'
    resultBottomArea.style.margin = '5px'
    // resultBottomArea.style.border = '1px solid blue'
    resultArea.appendChild(resultBottomArea)

    const backGround = document.createElement('div')
    backGround.classList.add('myInfoArea')
    // backGround.style.border = '1px solid red'
    backGround.style.height = '100%'
    // backGround.style.maxHeight = '400px'
    resultBottomArea.appendChild(backGround)

    const title = document.createElement('div')
    title.classList.add('myHeader')
    title.innerText = 'Trace'
    backGround.appendChild(title)

    const field = document.createElement('div') // This is where the trace graphics will do
    // field.style.border = '1px solid red'
    field.style.height = '95%'
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
      new Checks.OverLimit('TORQUE TRACE'),
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
