import BasicScreen from './BasicScreen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to desplay user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class ControlMessageSplitScreen extends BasicScreen {
  constructor (title, leftText, rightText, activationPhase) {
    super(title, activationPhase)

    const columnSetter = document.createElement('div')
    columnSetter.classList.add('columns')
    this.backGround.appendChild(columnSetter)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    leftHalf.classList.add('scrollableInfoArea')
    columnSetter.appendChild(leftHalf)

    const nodeDiv = document.createElement('div')
    nodeDiv.classList.add('myHeader')
    nodeDiv.innerText = leftText
    leftHalf.appendChild(nodeDiv)

    const leftArea = document.createElement('div')
    leftArea.classList.add('tightUL')
    leftHalf.appendChild(leftArea)
    this.controlArea = leftArea

    const rightHalf = document.createElement('div')
    rightHalf.classList.add('righthalf')
    rightHalf.classList.add('scrollableInfoArea')
    columnSetter.appendChild(rightHalf)

    const comDiv = document.createElement('div')
    comDiv.classList.add('myHeader')
    comDiv.innerText = rightText
    rightHalf.appendChild(comDiv)

    const messageArea = document.createElement('div')
    messageArea.setAttribute('id', 'messageArea')
    rightHalf.appendChild(messageArea)

    this.messages = document.createElement('div')
    this.messages.setAttribute('id', 'messages')
    messageArea.appendChild(this.messages)
  }

  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  }

  createArea (name) {
    const simulateResultDiv = document.createElement('div')
    simulateResultDiv.classList.add('methodDiv')
    this.controlArea.appendChild(simulateResultDiv)
    return simulateResultDiv
  }

  createButton (title, area, callback) {
    const newButton = document.createElement('button')
    newButton.callback = callback
    newButton.classList.add('myButton')

    newButton.innerHTML = title

    newButton.onclick = () => {
      newButton.callback(newButton)
    }
    area.appendChild(newButton)
    return newButton
  }

  createInput (title, area) {
    const newInput = document.createElement('input')
    newInput.classList.add('methodInputStyle')

    area.appendChild(newInput)
    return newInput
  }
}
