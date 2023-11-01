import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this class is to generate an HTML representation of method
 * invocations for OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (methodManager, addressSpace) {
    super('Methods', 'Methods', 'Call results', 'tighteningsystem')
    this.methodManager = methodManager
    this.addressSpace = addressSpace // This is just used to get the namespace number. Can this be done in a better way?
  }

  /**
   * Run everytime the tab is opened
   */
  initiate () {
  }

  /**
  * Run activate when normal setup is done. This queries the method manager for the available methods in the given folders, and set up invokation buttons for all found methods
  * @param {*} state the name of the state when this is run
  */
  activate (state) {
    const methodFolders = [ // These folders should be searched for methods
      `/${this.addressSpace.nsIJT}:ResultManagement`, // The result folder
      '' // The top folder in the tightening system
    ]

    this.methodManager.setupMethodsInFolders(methodFolders).then(() => {
      this.createMethodAreas(this.methodManager.getMethodNames())
    })
  }

  /**
   * Given a list of method names, create invokation areas for them
   * @param {*} methodNames a list of method names
   */
  createMethodAreas (methodNames) {
    for (const name of methodNames) {
      this.createMethodArea(this.methodManager.getMethod(name))
    }
  }

  /**
   * Given method data, create a button and input fields in an area
   * @param {*} methodData data about the method from the method manager
   */
  createMethodArea (methodData) {
    const methodNode = methodData.methodNode
    const area = this.createArea(methodNode.displayName)
    const button = this.createButton(methodNode.displayName, area, (button) => {
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      this.methodManager.call(methodData.methodNode, values)
    })

    button.listOfValuegrabbers = []
    for (const arg of methodData.arguments) {
      button.listOfValuegrabbers.push(this.createMethodInput(arg, area))
    }
  }

  /**
   * create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @returns a function that tells the value of the input field
   */
  createMethodInput (arg, area) {
    const input = this.createInput(arg.name, area)

    input.dataType = arg.dataType
    input.title = 'Datatype: ' + arg.typeName + '\n' + (arg?.description?.text ? arg.description.text : '')

    return function () {
      return { value: input.value, type: input.dataType }
    }
  }
}
