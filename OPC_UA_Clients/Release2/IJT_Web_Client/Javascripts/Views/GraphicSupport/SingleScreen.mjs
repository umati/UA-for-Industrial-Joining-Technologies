import BasicScreen from './BasicScreen.mjs'
/**
 * Support class that creates a single column screen screen
 * Use this.singleArea to add things to interact with
 * Implement your own initiate() function to run code every time the tab is opened
 */
export default class SingleScreen extends BasicScreen {
  constructor (title, text, activationPhase) {
    super(title, activationPhase)

    this.singleArea = document.createElement('div')
    this.backGround.appendChild(this.singleArea)
  }
}
