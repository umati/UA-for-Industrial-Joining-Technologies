/**
 * Basclass for a HTML screen that interact with the tabGenerator to create the backGround and call initiate() everytime the tab is opened
 */
export default class BasicScreen {
  constructor (title) {
    this.title = title
    this.backGround = document.createElement('div')
    this.backGround.classList.add('basescreen')
  }

  initiate () {}

  activate () {}

  /**
   * Create a button containing named title, in area and call callback when pressed
   * @param {*} title the name on the btton
   * @param {*} area the area where to put it
   * @param {*} callback call this when pressed
   * @returns the button
   */
  createButton (title, area, callback) {
    const newButton = document.createElement('button')
    newButton.callback = callback
    newButton.classList.add('myButton')

    newButton.innerHTML = title

    newButton.onclick = () => {
      newButton.callback(newButton)
    }
    if (area) {
      area.appendChild(newButton)
    }
    return newButton
  }

  // Support to generate the labels in the title row
  createLabel (text) {
    const a = document.createElement('label')
    a.classList.add('labelStyle')
    a.innerHTML = text
    delete a.textprediction
    return a
  }

  /**
   * create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} onchange this function is called when the value changed
   * @returns a function that tells the value of the input field
   */
  createInput (title, area, changeFunction, width = 90) {
    const newInput = document.createElement('input')
    newInput.classList.add('inputStyle')
    newInput.style.width = width + '%'
    newInput.value = title
    newInput.spellcheck = false
    newInput.onchange = (x) => {
      if (changeFunction) {
        changeFunction(x.currentTarget.value)
      }
    }
    newInput.onkeyup = (x) => {
      if (changeFunction) {
        if (x.key === 'Enter' || x.keyCode === 13) {
          changeFunction(x.currentTarget.value)
        }
      }
    }
    if (area) {
      area.appendChild(newInput)
    }
    return newInput
  }

  createCheckbox (initialValue, onchange, name) {
    const x = document.createElement('INPUT')
    x.setAttribute('type', 'checkbox')
    x.checked = initialValue
    x.onclick = function () {
      onchange(this.checked)
    }
    return x
  }

  createDropdown (name, onchange) {
    const container = document.createElement('div')
    const label = document.createElement('label')
    label.innerHTML = name + '  '
    container.select = document.createElement('select')
    container.appendChild(label)
    container.appendChild(container.select)

    container.addOption = function (opt, key) {
      const option = document.createElement('option')
      option.value = key
      option.innerHTML = opt
      this.select.appendChild(option)
    }

    container.clearOptions = function () {
      const L = this.select.options.length - 1
      for (let i = L; i >= 0; i--) {
        this.select.remove(i)
      }
    }

    container.select.onchange = function () {
      onchange(this.value)
    }
    return container
  }

  /**
   * Create a screen area with a title
   * @param {*} text the title
   * @param {*} style the css style
   * @returns the new area where to put things
   */
  makeNamedArea (text, style) {
    const namedArea = document.createElement('div')
    namedArea.classList.add(style)
    namedArea.classList.add('scrollableInfoArea')

    const header = document.createElement('div')
    header.classList.add('myHeader')
    header.innerText = text
    namedArea.appendChild(header)

    const contentArea = document.createElement('div')
    contentArea.classList.add('tightUL')
    namedArea.appendChild(contentArea)
    namedArea.contentArea = contentArea

    return namedArea
  }

  /**
   * Create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @returns a function that tells the value of the input field
   */
  createMethodInput (arg, area, defaultValue = '', callback) {
    const titleLabel = this.createLabel(arg.Name + '  ')
    area.appendChild(titleLabel)

    switch (arg.DataType.Identifier) {
      case 'DropDown': { // DropDown
        const drop = this.createDropdown('', (x) => {
          if (callback) {
            callback(x)
          }
        })

        drop.classList.add('methodJoiningProcess')
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

        const sel = this.createInput('', area, callback, 30)
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

        this.createButton('Add identifier', selectionArea, () => {
          const selectionDiv = this.entityManager?.makeSelectableEntityView((x, entity) => {
            selectionArea.removeChild(selectionDiv)
            selectionArea.removeChild(selectionAreaBackground)
            entityList.push(entity)
            entityListDiv.innerHTML = ''
            for (const entity of entityList) {
              const entityArea = this.createLabel(entity.name + '(' + entity.entityId + ')')
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
        const input = this.createInput('', area, callback, 30)
        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = 0
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '6': // Int32
      case '7': { // UInt32
        const input = this.createInput('', area, callback, 30)

        input.dataType = arg.DataType
        input.title = 'Datatype: Number\n' + (arg?.Description?.Text ? arg.Description.Text : '')
        input.value = defaultValue
        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
      case '12': { // String
        const input = this.createInput('', area, callback, 30)

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
        const input = this.createCheckbox(returnValue, (newValue) => {
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
        const input = this.createInput('', area, callback, 30)

        input.dataType = arg.DataType
        input.title = 'Datatype: ' + arg.DataType.Identifier + '\n' + (arg?.Description?._text ? arg.Description._text : '')

        return function () {
          return { value: input.value, type: input.dataType }
        }
      }
    }
  }
}
