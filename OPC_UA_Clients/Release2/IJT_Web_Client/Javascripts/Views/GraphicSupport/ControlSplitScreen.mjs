import BasicScreen from './BasicScreen.mjs'
/**
 * Support class that creates the split screen
 * Use this.controlArea to add things to interact with
 * Use this.messageDisplay(msg) to desplay user feedback
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class ControlSplitScreen extends BasicScreen {
  constructor (title, leftText, rightText, activationPhase) {
    super(title, activationPhase)

    const columnSetter = document.createElement('div')
    columnSetter.classList.add('columns')
    this.backGround.appendChild(columnSetter)

    this.controlArea = this.makeNamedArea(leftText, 'lefthalf')
    columnSetter.appendChild(this.controlArea)

    this.controls = document.createElement('div')
    this.controls.classList.add('doublecolumnleft')
    this.controlArea.appendChild(this.controls)

    this.viewArea = this.makeNamedArea(rightText, 'righthalf')
    columnSetter.appendChild(this.viewArea)

    this.views = document.createElement('div')
    this.views.classList.add('doublecolumnright')
    this.viewArea.appendChild(this.views)
  }

  createArea (name) {
    const newDiv = document.createElement('div')
    newDiv.classList.add('methodDiv')
    this.controlArea.appendChild(newDiv)
    return newDiv
  }
}
