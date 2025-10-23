/**
 * The purpose of this class is to display a GUI for filling in arguments and calling a method
 */
export default class MethodGUICreator {
  constructor (screen, methodManager, entityManager, settings) {
    this.methodManager = methodManager
    this.entityManager = entityManager
    this.settings = settings
    this.screen = screen
  }

  /**
   * Given method data, create a button and input fields in an area
   * @param {*} methodData data about the method from the method manager
   */
  createMethodArea (pathName) {
    const methodData = this.methodManager.getMethod(pathName)

    const buttonPress = (button) => {
      // Load argument values
      const values = []
      for (const argValue of button.listOfValuegrabbers) {
        values.push(argValue())
      }
      // This is when the actual call is made
      this.methodManager.call(methodData, values).then(
        (success) => {
          this.screen.messageDisplay(JSON.stringify(success))
        },
        (fail) => {
          this.screen.messageDisplay(JSON.stringify(fail))
        }
      )
    }

    // Setting up method area
    const methodNode = methodData.methodNode
    const area = this.screen.createArea(methodNode.displayName)
    area.classList.add('methodBorder')
    const titleLabel = this.screen.createLabel(methodNode.displayName)
    area.appendChild(titleLabel)

    try {
      let defaults
      if (this.settings?.methodDefaults) {
        defaults = this.settings.methodDefaults[methodData.methodNode.nodeIdString]
      }

      // Setting up argument windows
      const listOfValuegrabbers = []
      for (let index = 0; index < methodData.arguments.length; index++) {
        const arg = methodData.arguments[index]
        const lineArea = this.screen.createArea()
        lineArea.classList.add('methodRowDistance')
        area.appendChild(lineArea)
        listOfValuegrabbers.push(this.createMethodInput(arg, lineArea, defaults?.arguments[index]))
      }

      // Create the actual button for the call
      const button = this.screen.createButton('Call', area, buttonPress)

      button.listOfValuegrabbers = listOfValuegrabbers

      if (defaults?.autocall) {
        buttonPress(button)
      }
    } catch (error) {
      area.classList.add('errorBackground')
      const errorArea = this.screen.createArea()
      errorArea.innerText = error.name + ' : ' + error.message
      console.log(error.name + ' : ' + error.message)
      area.appendChild(errorArea)
    }
    return area
  }

  /**
   * Create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @returns a function that tells the value of the input field
   */
  createMethodInput (arg, area, defaultValue = '', callback) {
    if (arg.Name && arg.Name.length > 0) {
      const titleLabel = this.screen.createLabel(arg.Name + '  ')
      titleLabel.classList.add('methodLabel')
      area.appendChild(titleLabel)
    }

    switch (arg.DataType.Identifier) {
      case 'DropDown': { // DropDown
        const drop = this.screen.createDropdown('', (x) => {
          if (callback) {
            callback(x)
          }
        })

        drop.classList.add('inputStyle')
        drop.classList.add('methodInput')
        for (let i = 0; i < Object.values(arg.Options).length; i++) {
          const key = Object.keys(arg.Options)[i]
          const value = Object.values(arg.Options)[i]
          drop.addOption(value, key)
        }

        drop.select.selectedIndex = defaultValue

        area.appendChild(drop)
        return function () {
          return { value: drop.value }
        }
      }
      case '3029': { // JoiningProcessIdentification
        const selectionArea = document.createElement('div')
        selectionArea.classList.add('methodInputRight')
        area.appendChild(selectionArea)

        const drop = this.screen.createDropdown('Type', (x) => {

        }, 'dropJoiningProcess')

        // drop.classList.add('dropJoiningProcess')
        drop.addOption('OriginId', 1)
        drop.addOption('Specific Id', 0)
        drop.addOption('Selection name', 2)

        selectionArea.appendChild(drop)
        const label = this.screen.createLabel('Value')
        // label.classList.add('methodJoiningProcess')
        selectionArea.appendChild(label)

        const sel = this.screen.createInput('', selectionArea, callback, 55)
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
      }
      case '3010': { // EntityDataType ***************************************************************
        const selectionArea = document.createElement('div')
        area.appendChild(selectionArea)

        let entityList = []

        const entityListDiv = document.createElement('div')
        selectionArea.appendChild(entityListDiv)

        this.screen.createButton('Add identifier', selectionArea, () => {
          const selectionDiv = this.entityManager?.makeSelectableEntityView((x, entity) => {
            selectionArea.removeChild(selectionDiv)
            selectionArea.removeChild(selectionAreaBackground)
            entityListDiv.classList.add('rows')
            entityList.push(entity)
            entityListDiv.innerHTML = ''
            for (const entity of entityList) {
              const entityArea = this.screen.createLabel(entity.Name + '(' + entity.EntityId + ')')
              entityArea.classList.add('indent')
              entityListDiv.appendChild(entityArea)
            }
          }, 'Select an identifier entity')
          const selectionAreaBackground = document.createElement('div')
          selectionAreaBackground.classList.add('idSelectDialogGrayBackground')
          selectionArea.appendChild(selectionAreaBackground)
          selectionDiv.classList.add('idSelectDialog')
          selectionArea.appendChild(selectionDiv)
        })

        return function () {
          const value = []
          for (const entity of entityList) {
            value.push({
              value: {
                Name: entity.name,
                Description: entity.description,
                EntityId: entity.entityId,
                EntityOriginId: entity.entityOriginId,
                IsExternal: entity.isExternal,
                EntityType: entity.entityType
              }
            })
          }
          entityList = []
          entityListDiv.innerText = ''
          return {
            type: {
              Identifier: '3010',
              NamespaceIndex: '3'
            },
            structure: 'EntityDataType',
            value
          }
        }
      }
      case '3': { // Also byte. For the time being, treat it as an int
        const input = this.screen.createInput('', area, callback, 45)
        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = defaultValue
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '6': // Int32
      case '7': { // UInt32
        const input = this.screen.createInput('', area, callback, 45)

        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = defaultValue
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '12': { // String
        const input = this.screen.createInput('', area, callback, 45)

        input.dataType = arg.DataType
        input.value = defaultValue
        input.title = 'Datatype: String\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '1': { // Boolean
        let returnValue = false
        if (defaultValue) {
          returnValue = defaultValue
        }
        const input = this.screen.createCheckbox(returnValue, (newValue) => {
          returnValue = newValue
          if (callback) {
            callback(newValue)
          }
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
      default: {
        const input = this.screen.createInput('', area, callback, 45)

        input.dataType = arg.DataType
        input.title = 'Datatype: ' + arg.DataType.Identifier + '\n' + (arg?.Description?._text ? arg.Description._text : '')

        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
    }
  }
}
