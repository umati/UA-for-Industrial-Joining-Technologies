/**
 * Baseclass for a HTML screen that interact with the tabGenerator to create the backGround and call initiate() everytime the tab is opened
 */
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'

const BUTTON_DEBOUNCE_MS = 150
const DEFAULT_INPUT_WIDTH_PCT = 45

export default class BasicScreen {
  constructor (title) {
    this.title = title
    this.backGround = document.createElement('div')
    this.backGround.classList.add('basescreen')
  }

  initiate () {}

  activate () {}

  changeViewLevel (_newLevel) {}

  createArea (name) {
    const newDiv = document.createElement('div')
    newDiv.classList.add('methodDiv')
    return newDiv
  }

  addTitle (title, component) {
    const area = document.createElement('div')
    area.appendChild(this.createLabel(title))
    area.appendChild(component)
    return area
  }

  createTitledInput (title, input, component) {
    const lineArea = this.createArea()
    input.classList.add('methodInputRight')
    const label = this.createLabel(title)
    label.classList.add('methodLabel')
    lineArea.appendChild(label)
    lineArea.appendChild(input)
    component.appendChild(lineArea)
    return lineArea
  }

  /**
   * Create a button containing named title, in area and call callback when pressed
   * @param {*} title the name on the button
   * @param {*} area the area where to put it
   * @param {*} callback call this when pressed
   * @returns the button
   */
  createButton (title, area, callback) {
    const newButton = document.createElement('button')
    newButton.callback = callback
    newButton.classList.add('myButton')

    newButton.textContent = title || 'Action'

    newButton.onclick = async () => {
      if (newButton.disabled) {
        return
      }
      newButton.disabled = true
      try {
        if (typeof newButton.callback === 'function') {
          await newButton.callback(newButton, this)
        }
      } catch (error) {
        ijtLog.error('Button callback failed:', error)
      } finally {
        // Small debounce to avoid accidental double-activations.
        window.setTimeout(() => { newButton.disabled = false }, BUTTON_DEBOUNCE_MS)
      }
    }
    newButton.moveTo = (location) => {
      if (location && location.appendChild) {
        location.appendChild(newButton)
      }
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
    // Always use textContent — OPC UA node names/descriptions are plain text,
    // not HTML. Using innerHTML with server-supplied strings is an XSS risk.
    a.textContent = text || ''
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
  createInput (title, area, changeFunction, width = DEFAULT_INPUT_WIDTH_PCT) {
    const newInput = document.createElement('input')
    newInput.classList.add('inputStyle')
    newInput.classList.add('methodInput')
    const parsedWidth = Number(width)
    newInput.style.width = (Number.isFinite(parsedWidth) ? parsedWidth : DEFAULT_INPUT_WIDTH_PCT) + '%'
    newInput.value = title || ''
    newInput.spellcheck = false
    newInput.onchange = (x) => {
      if (changeFunction) {
        try {
          changeFunction(x.currentTarget.value)
        } catch (error) {
          ijtLog.error('Input onchange failed:', error)
        }
      }
    }
    newInput.onkeyup = (x) => {
      if (changeFunction) {
        try {
          changeFunction(x.currentTarget.value)
        } catch (error) {
          ijtLog.error('Input onkeyup failed:', error)
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
    x.classList.add('myCheckBox')
    x.checked = initialValue
    x.onclick = () => {
      if (typeof onchange === 'function') {
        onchange(x.checked)
      }
    }
    return x
  }

  createDropdown (name, onchange, style) {
    const container = document.createElement('div')
    if (name && name.length > 0) {
      const label = document.createElement('label')
      label.textContent = `${name}  `
      container.appendChild(label)
    }
    container.select = document.createElement('select')
    if (style) {
      container.select.classList.add(style)
    } else {
      container.select.classList.add('envSelect')
    }
    container.appendChild(container.select)

    container.addOption = function (opt, key) {
      const option = document.createElement('option')
      option.value = key
      option.textContent = opt === null || opt === undefined ? '' : String(opt)
      this.select.appendChild(option)
    }

    container.clearOptions = function () {
      const L = this.select.options.length - 1
      for (let i = L; i >= 0; i--) {
        this.select.remove(i)
      }
    }

    container.select.onchange = () => {
      if (typeof onchange === 'function') {
        onchange(container.select.value)
      }
    }
    return container
  }

  createDropdownFromImport (importList, onchange) {
    const dropDown = this.createDropdown(null, (cname) => {
      const newSelection = new importList[cname]()

      if (onchange) {
        onchange(newSelection)
      }
    })

    for (const subclass of Object.values(importList)) {
      dropDown.addOption(subclass.displayText, subclass.name)
    }
    return dropDown
  }

  /**
   * Create a screen area with a title
   * @param {*} text the title
   * @param {*} style the css style
   * @returns the new area where to put things
   */
  makeNamedArea (text, style, area) {
    const namedArea = document.createElement('div')
    namedArea.classList.add('scrollableInfoArea')
    if (style) {
      namedArea.classList.add(style)
    }

    const header = document.createElement('div')
    header.classList.add('myHeader')
    header.innerText = text || ''
    namedArea.appendChild(header)

    const contentArea = document.createElement('div')
    contentArea.classList.add('tightUL')
    contentArea.classList.add('standardCol')
    contentArea.parentArea = namedArea
    namedArea.appendChild(contentArea)
    namedArea.contentArea = contentArea

    if (area) {
      area.appendChild(namedArea)
      return contentArea
    }
    return namedArea
  }

  makeSelectionList (title, context) {
    const area = this.makeNamedArea(title, 'selectionArea', context)
    return new SelectionList(title, area, this)
  }
}

export class SelectionList {
  constructor (title, area, screen) {
    this.title = title
    this.area = area
    this.screen = screen
    this.options = []
  }

  redraw () {
    if (!this.area) {
      return
    }
    this.area.innerHTML = ''
    for (const option of this.options) {
      this.screen.createButton(option.name, this.area, option.onclick)
    }
  }

  addOption (name, onclick, drag) { // option.name, option.onclick, option.drag
    const option = {
      name: name || 'Option',
      onclick,
      drag
    }
    this.options.push(option)
    this.redraw()
  }
}
