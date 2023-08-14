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

  setTighteningSystem (tighteningSystemNode) {
    this.tighteningSystemNode = tighteningSystemNode
    this.setupComplete()
  }

  setDataTypes (dataTypeEnumeration) {
    this.dataTypeEnumeration = dataTypeEnumeration
    this.setupComplete()
  }

  setupComplete () {
    if (this.tighteningSystemNode && this.dataTypeEnumeration) {
      this.simulateResultDiv.style.borderColor = 'yellow'
    }
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
