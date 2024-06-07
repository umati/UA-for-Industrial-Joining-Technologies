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
    // Setting up method area
    const methodNode = methodData.methodNode
    const area = this.createArea(methodNode.displayName)
    area.classList.add('methodBorder')
    const titleLabel = this.createLabel(methodNode.displayName)
    area.appendChild(titleLabel)

    // Setting up argument windows
    const listOfValuegrabbers = []
    for (const arg of methodData.arguments) {
      const lineArea = this.createArea()
      lineArea.classList.add('methodRowDistance')
      area.appendChild(lineArea)
      listOfValuegrabbers.push(this.createMethodInput(arg, lineArea))
    }

    // Create the actual button for the call
    const button = this.createButton('Call', area, (button) => {
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
    const titleLabel = this.createLabel(arg.Name + '  ')
    area.appendChild(titleLabel)

    switch (arg.DataType.Identifier) {
      case 'Byte': // Change this to a number
        throw new Error('Byte is not implemented in MethodGraphics.mjs')
      case '3029':{ // JoiningProcessIdentification
        const selectionArea = document.createElement('div')
        area.appendChild(selectionArea)

        const drop = this.createDropdown('Type', (x) => {

        })

        drop.classList.add('methodJoiningProcess')
        drop.addOption('OriginId', 1)
        drop.addOption('Specific Id', 0)
        drop.addOption('Selection name', 2)

        area.appendChild(drop)
        const label = this.createLabel('Value')
        label.classList.add('methodJoiningProcess')
        area.appendChild(label)

        const sel = this.createInput('', area, null, 30)
        sel.dataType = arg.DataType
        sel.title = 'Datatype: Id\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        sel.value = 0

        return function () {
          const value = []
          for (let i = 0; i < 3; i++) {
            if (parseInt(drop.select.value) === i) {
              value.push({
                value: sel.value,
                type: '31918'
              })
            } else {
              value.push({
                value: '',
                type: '31918'
              })
            }
          }
          return {
            type: {
              Identifier: '3029',
              NamespaceIndex: '3'
            },
            structure: 'JoiningProcessIdentification',
            value
          }
        }

        /* const input1 = this.createInput('', area, null, 30)
        input1.dataType = arg.DataType
        input1.title = 'Datatype: Id\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input1.value = 0

        const input2 = this.createInput('', area, null, 30)
        input2.dataType = arg.DataType
        input2.title = 'Datatype: Id\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input2.value = 0

        const input3 = this.createInput('', area, null, 30)
        input3.dataType = arg.DataType
        input3.title = 'Datatype: Id\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input3.value = 0
        return function () {
          return {
            type: {
              Identifier: '3029',
              NamespaceIndex: '3'
            },
            structure: 'JoiningProcessIdentification',
            value: [
              {
                value: input1.value,
                type: '31918'
              }, {
                value: input2.value,
                type: '31918'
              }, {
                value: input3.value,
                type: '31918'
              }]
          }
        } */
      }
      case '3': { // Also byte. For the time being, treat it as an int
        const input = this.createInput('', area, null, 30)
        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = 0
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '6': // Int32
      case '7': { // UInt32
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = 0
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '12': { // String
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.DataType
        input.title = 'Datatype: String\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '1': { // Boolean
        let returnValue = false
        const input = this.createCheckbox(returnValue, (newValue) => {
          returnValue = newValue
        })

        input.dataType = arg.DataType
        input.title = 'Datatype: Boolean\n' + (arg?.Description?.Text ? arg.Description.Text : '')

        area.appendChild(input)

        return function () {
          if (returnValue) {
            return { value: true, type: input.dataType }
          } else {
            return { value: false, type: input.dataType }
          }
        }
      }
      /* case '3029': {
        console.log('JoiningProcessidentificationId') // TODO implement this another way
        const input = this.createInput('', area, null, 30)
        input.dataType = arg.dataType

        input.title = 'Datatype: ' + arg.DataType.Identifier + '\n' + (arg?.description?.text ? arg.description.text : '')
        return function () {
          return { value: input.value, type: input.dataType }
        }
      } */
      default: {
        const input = this.createInput('', area, null, 30)

        input.dataType = arg.DataType
        input.title = 'Datatype: ' + arg.DataType.Identifier + '\n' + (arg?.Description?._text ? arg.Description._text : '')

        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
    }
  }
}
