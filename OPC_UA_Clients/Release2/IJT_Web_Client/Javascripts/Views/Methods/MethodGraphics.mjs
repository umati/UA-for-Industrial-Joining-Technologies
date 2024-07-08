import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this class is to generate an HTML representation of method
 * invocations for OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (methodManager, addressSpace, settings, entityManager) {
    super('Methods', 'Methods', 'Call results')
    this.methodManager = methodManager
    this.settings = settings
    this.entityManager = entityManager

    this.addressSpace = addressSpace // This is just used to get the namespace number. Can this be done in a better way?
    addressSpace.connectionManager.subscribe('tighteningsystem', (setToTrue) => {
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
    const methodFolders = [ // These folders should be searched for methods
      [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
        { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateResults' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'AssetManagement' },
        { namespaceindex: this.addressSpace.nsIJT, identifier: 'MethodSet' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'JoiningProcessManagement' }],
      [{ namespaceindex: this.addressSpace.nsIJT, identifier: 'JointManagement' }],
      [{ namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'Simulations' },
        { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateEventsAndConditions' }]
    ]

    this.methodManager.setupMethodsInFolders(methodFolders).then(() => {
      this.settings.settingPromise().then((s) => {
        this.createMethodAreas(this.methodManager.getMethodNames(), s)
      })
    })
  }

  /**
   * Given a list of method names, create invokation areas for them
   * @param {*} methodNames a list of method names
   */
  createMethodAreas (methodNames, settings) {
    for (const name of methodNames) {
      this.createMethodArea(this.methodManager.getMethod(name), settings)
    }
  }

  /**
   * Given method data, create a button and input fields in an area
   * @param {*} methodData data about the method from the method manager
   */
  createMethodArea (methodData, settings) {
    const buttonPress = (button) => {
      // Load argument values
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      // This is when the actual call is made
      this.methodManager.call(methodData, values).then(
        (success) => {
          this.messageDisplay(JSON.stringify(success))
        },
        (fail) => {
          this.messageDisplay(JSON.stringify(fail))
        }
      )
    }

    // Setting up method area
    const methodNode = methodData.methodNode
    const area = this.createArea(methodNode.displayName)
    area.classList.add('methodBorder')
    const titleLabel = this.createLabel(methodNode.displayName)
    area.appendChild(titleLabel)

    const defaults = settings.methodDefaults[methodData.methodNode.nodeIdString]

    // Setting up argument windows
    const listOfValuegrabbers = []
    for (let index = 0; index < methodData.arguments.length; index++) {
      const arg = methodData.arguments[index]
      const lineArea = this.createArea()
      lineArea.classList.add('methodRowDistance')
      area.appendChild(lineArea)
      listOfValuegrabbers.push(this.createMethodInput(arg, lineArea, defaults?.arguments[index]))
    }

    // Create the actual button for the call
    const button = this.createButton('Call', area, buttonPress)

    button.listOfValuegrabbers = listOfValuegrabbers

    if (defaults?.autocall) {
      buttonPress(button)
    }
  }
}
