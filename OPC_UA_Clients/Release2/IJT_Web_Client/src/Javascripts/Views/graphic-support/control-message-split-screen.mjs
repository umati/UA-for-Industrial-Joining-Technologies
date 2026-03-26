import ControlSplitScreen from './control-split-screen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to desplay user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class ControlMessageSplitScreen extends ControlSplitScreen {
  constructor (title, leftText, rightText) {
    super(title, leftText, rightText)

    this.messages = document.createElement('div')
    this.messages.classList.add('messages')
    this.views.appendChild(this.messages)
  }

  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  }
}
