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

    this.controlArea = this.makeNamedArea(leftText, 'lefthalf')
    columnSetter.appendChild(this.controlArea)

    this.messageArea = this.makeNamedArea(rightText, 'righthalf')
    columnSetter.appendChild(this.messageArea)

    this.messages = document.createElement('div')
    this.messages.setAttribute('id', 'messages')
    this.messageArea.appendChild(this.messages)
  }

  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  }

  createArea (name) {
    const newDiv = document.createElement('div')
    newDiv.classList.add('methodDiv')
    this.controlArea.appendChild(newDiv)
    return newDiv
  }
}
