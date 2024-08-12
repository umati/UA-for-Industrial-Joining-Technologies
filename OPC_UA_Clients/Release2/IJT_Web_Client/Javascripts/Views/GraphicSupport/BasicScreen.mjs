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

  changeViewLevel (newLevel) {}

  createArea (name) {
    const newDiv = document.createElement('div')
    newDiv.classList.add('methodDiv')
    return newDiv
  }

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
    newInput.classList.add('methodInput')
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
    x.classList.add('myCheckBox')
    x.checked = initialValue
    x.onclick = function () {
      onchange(this.checked)
    }
    return x
  }

  createDropdown (name, onchange) {
    const container = document.createElement('div')
    if (name && name.length > 0) {
      const label = document.createElement('label')
      label.innerHTML = name + '  '
      container.appendChild(label)
    }
    container.select = document.createElement('select')
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
}
