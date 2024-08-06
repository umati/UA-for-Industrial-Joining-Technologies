import BasicScreen from './BasicScreen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to desplay user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class SingleScreen extends BasicScreen {
  constructor (title, leftText, rightText, activationPhase) {
    super(title, activationPhase)

    const columnSetter = document.createElement('div')
    columnSetter.classList.add('columns')
    this.backGround.appendChild(columnSetter)

    this.controlArea = this.makeNamedArea(leftText, 'lefthalf')
    columnSetter.appendChild(this.controlArea)

    this.singleArea = document.createElement('div')
    this.singleArea.classList.add('doublecolumnleft')
    this.controlArea.appendChild(this.singleArea)
  }

  createArea (name) {
    const newDiv = document.createElement('div')
    newDiv.classList.add('methodDiv')
    this.singleArea.appendChild(newDiv)
    return newDiv
  }
}
