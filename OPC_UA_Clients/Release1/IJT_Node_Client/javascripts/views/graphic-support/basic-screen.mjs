/**
 * Basclass for a HTML screen that interact with the tabGenerator to create the backGround and call initiate() everytime the tab is opened
 */
const DEFAULT_INPUT_WIDTH_PERCENT = 90

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
    newButton.classList.add('my-button')

    newButton.textContent = title

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
    a.classList.add('label-style')
    a.textContent = text
    return a
  }

  /**
   * create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} onchange this function is called when the value changed
   * @returns a function that tells the value of the input field
   */
  createInput (title, area, onchange, width = DEFAULT_INPUT_WIDTH_PERCENT) {
    const newInput = document.createElement('input')
    newInput.classList.add('input-style')
    newInput.style.width = width + '%'
    newInput.value = title
    newInput.spellcheck = false
    newInput.onchange = onchange
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

  /**
   * Create a screena area with a title
   * @param {*} text the title
   * @param {*} style the css style
   * @returns the new area where to put things
   */
  makeNamedArea (text, style) {
    const namedArea = document.createElement('div')
    namedArea.classList.add(style)
    namedArea.classList.add('scrollable-info-area')

    const header = document.createElement('div')
    header.classList.add('my-header')
    header.innerText = text
    namedArea.appendChild(header)

    const contentArea = document.createElement('div')
    contentArea.classList.add('tight-ul')
    namedArea.appendChild(contentArea)

    return namedArea
  }
}
