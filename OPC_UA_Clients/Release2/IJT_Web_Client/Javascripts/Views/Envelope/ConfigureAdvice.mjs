import BasicScreen from '../GraphicSupport/BasicScreen.mjs' // Basic functionality application code for the screen functionality

/**
 * The purpose of this class is to generate an HTML representation of tightening selection and basic
 * display of a result for OPC UA Industrial Joining Technologies communication
 */
export default class Envelope extends BasicScreen {
  constructor (connectionManager, resultManager, settings) {
    super('Configure Advice', 'tighteningsystem') // Setting the name of the tab
    this.settings = settings

    // Create display areas
    const displayArea = document.createElement('div')
    displayArea.style.border = '1px solid pink'
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
    this.setupScreen()
  }

  setupScreen () {
    this.container.classList.add('demoRow')

    const ListAreas = document.createElement('div')
    ListAreas.style.width = '20%'
    ListAreas.classList.add('demoCol')
    ListAreas.classList.add('envelopeleft')
    ListAreas.style.justifyContent = 'center'
    this.container.appendChild(ListAreas)

    this.selection = this.makeNamedArea('Selection management', 'demoMachine')
    this.selection.style.height = '180px'
    this.selection.style.width = '300px'
    ListAreas.appendChild(this.selection)
    this.selection.innerText = 'All'

    this.limits = this.makeNamedArea('Limit management', 'demoMachine')
    this.limits.style.height = '180px'
    // this.limits.style.width = '300px'
    ListAreas.appendChild(this.limits)
    this.selection.innerText = 'All'

    this.advice = this.makeNamedArea('Advice management', 'demoMachine')
    this.advice.style.height = '180px'
    // this.limits.style.width = '300px'
    ListAreas.appendChild(this.advice)

    const resultArea = document.createElement('div')
    resultArea.style.width = '80%'
    resultArea.classList.add('demoCol')
    this.container.appendChild(resultArea)

    const resultTopArea = document.createElement('div')
    resultTopArea.style.height = '200px'
    resultTopArea.style.color = 'red'
    resultTopArea.classList.add('demoRow')
    resultArea.appendChild(resultTopArea)

    this.tagArea = this.makeNamedArea('Parameters', 'demoMachine')
    // infoArea.style.border = '2px solid white'
    this.tagArea.style.height = '180px'
    this.tagArea.style.width = '500px'
    resultTopArea.appendChild(this.tagArea)

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
}
