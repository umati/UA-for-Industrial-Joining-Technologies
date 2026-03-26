import BasicScreen from './basic-screen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to display user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class ControlMessageSplitScreen extends BasicScreen {
  constructor (title, leftText, rightText) {
    super(title)

    const columnSetter = document.createElement('div')
    columnSetter.classList.add('columns')
    this.backGround.appendChild(columnSetter)

    this.controlArea = this.makeNamedArea(leftText, 'left-half')
    columnSetter.appendChild(this.controlArea)

    this.messageArea = this.makeNamedArea(rightText, 'right-half')
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
    const simulateResultDiv = document.createElement('div')
    simulateResultDiv.classList.add('method-div')
    this.controlArea.appendChild(simulateResultDiv)
    return simulateResultDiv
  }
}
