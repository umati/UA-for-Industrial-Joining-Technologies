import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this class is to generate an HTML representation of method
 * invocations for OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (methodManager, addressSpace) {
    super('Methods', 'Methods', 'Call results')
    this.methodManager = methodManager
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
  * Run activate when normal setup is done. This queries the method manager for the available methods in the given folders, and set up invokation buttons for all found methods
  * @param {*} state the name of the state when this is run
  */
  activate (state) {
    const methodFolders = [ // These folders should be searched for methods
    `/${this.addressSpace.nsTighteningServer}:Simulations/${this.addressSpace.nsTighteningServer}:SimulateResults`, // The simulateResult folder
    `/${this.addressSpace.nsTighteningServer}:Simulations/${this.addressSpace.nsTighteningServer}:SimulateEventsAndConditions`, // The simulateResult folder
    `/${this.addressSpace.nsMachineryResult}:ResultManagement`, // The result folder
    `/${this.addressSpace.nsIJT}:JointManagement`, // The joint folder
    `/${this.addressSpace.nsIJT}:JoiningProcessManagement`, // The job folder
    `/${this.addressSpace.nsIJT}:AssetManagement/${this.addressSpace.nsIJT}:MethodSet`, // The job folder
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
    area.classList.add('methodBorder')
    const titleLabel = this.createLabel(methodNode.displayName)
    area.appendChild(titleLabel)

    const listOfValuegrabbers = []
    for (const arg of methodData.arguments) {
      const lineArea = this.createArea()
      lineArea.classList.add('methodRowDistance')
      area.appendChild(lineArea)
      listOfValuegrabbers.push(this.createMethodInput(arg, lineArea))
    }

    const button = this.createButton('Call', area, (button) => {
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      this.methodManager.call(methodData, values)
    })

    button.listOfValuegrabbers = listOfValuegrabbers
  }

  /**
   * Create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @returns a function that tells the value of the input field
   */
  createMethodInput (arg, area) {
    const titleLabel = this.createLabel(arg.name + '  ')
    area.appendChild(titleLabel)

    switch (arg.typeName) {
      case 'Byte':
      case 'Int32':
      case 'UInt32': {
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.dataType
        input.title = 'Datatype: ' + arg.typeName + '\n' + (arg?.description?.text ? arg.description.text : '')
        input.value = 0
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case 'String': {
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.dataType
        input.title = 'Datatype: ' + arg.typeName + '\n' + (arg?.description?.text ? arg.description.text : '')
        input.value = 0
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case 'Boolean': {
        let returnValue = false
        const input = this.createCheckbox(returnValue, (newValue) => {
          returnValue = newValue
        })

        input.dataType = arg.dataType
        input.title = 'Datatype: ' + arg.typeName + '\n' + (arg?.description?.text ? arg.description.text : '')

        area.appendChild(input)

        return function () {
          if (returnValue) {
            return { value: true, type: input.dataType }
          } else {
            return { value: false, type: input.dataType }
          }
        }
      }
      default: {
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.dataType
        if (arg.typeName) {
          input.title = 'Datatype: ' + arg.typeName + '\n' + (arg?.description?.text ? arg.description.text : '')
        } else {
          input.title = 'Datatype: IDENTIFIER \n' + (arg?.description?.text ? arg.description.text : '')
        }
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
    }
  }
}
