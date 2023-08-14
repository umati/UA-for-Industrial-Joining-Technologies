export default class MethodCallBase {
  constructor (container, socketHandler, messageReceiver) {
    this.container = container
    this.socketHandler = socketHandler
    this.messageReceiver = messageReceiver
    this.callback = null // Placeholder for button callback

    this.simulateResultDiv = document.createElement('div')
    this.simulateResultDiv.classList.add('methodDiv')
    container.appendChild(this.simulateResultDiv)
  }

  initiate (dataTypeEnumeration, tighteningSystemName) {
    this.dataTypeEnumeration = dataTypeEnumeration
    this.tighteningSystemName = tighteningSystemName
    this.simulateResultDiv.style.borderColor = 'yellow'
  }

  createButton (name, callback) {
    this.callback = callback
    const newButton = document.createElement('button')
    newButton.classList.add('myButton')

    newButton.innerHTML = name

    newButton.onclick = () => {
      this.callback()
    }
    this.simulateResultDiv.appendChild(newButton)
  }

  createInput (initialValue) {
    const newInput = document.createElement('input')
    newInput.classList.add('methodInputStyle')
    newInput.value = initialValue

    this.simulateResultDiv.appendChild(newInput)
    return function () {
      return newInput.value
    }
  }
}
