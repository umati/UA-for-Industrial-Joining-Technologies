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

  /*
  createLabel (title, area) {
    const newContainer = document.createElement('div')
    newContainer.classList.add('myLabelWidth')
    const newLabel = document.createElement('label')
    newLabel.classList.add('myLabel')

    newLabel.innerHTML = title

    if (area) {
      area.appendChild(newContainer)
    }
    newContainer.appendChild(newLabel)
    return newContainer
  } */

  // Support to generate the labels in the title row
  createLabel (text) {
    const a = document.createElement('label')
    a.classList.add('labelStyle')
    a.innerHTML = text
    return a
  }

  /*
  createInput2 (title, area) {
    const newInput = document.createElement('input')
    newInput.classList.add('methodInputStyle')

    area.appendChild(newInput)
    return newInput
  }
  */

  /**
   * create an input field that helps in the invokation of a method
   * @param {*} arg the argument that you want the data for
   * @param {*} area the area where the input field should go
   * @param {*} onchange this function is called when the value changed
   * @returns a function that tells the value of the input field
   */
  createInput (title, area, onchange) {
    const newInput = document.createElement('input')
    newInput.classList.add('inputStyle')
    newInput.value = title
    newInput.spellcheck = false
    newInput.onchange = onchange

    if (area) {
      area.appendChild(newInput)
    }

    return newInput

  /*
    return function () {
      return newInput.value
    }
    */
  }

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

    return namedArea
  }
}
