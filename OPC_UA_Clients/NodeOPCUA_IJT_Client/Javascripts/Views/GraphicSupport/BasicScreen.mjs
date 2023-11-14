/**
 * Basclass for a HTML screen that interact with the tabGenerator to create the backGround and call initiate() everytime the tab is opened
 */
export default class BasicScreen {
  constructor (title, activationPhase, container) {
    this.title = title
    this.activationPhase = activationPhase || 'oncreate'
    this.backGround = document.createElement('div')
    this.backGround.classList.add('basescreen')
    // container.appendChild(this.backGround)

    // const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    /* container.addEventListener('tabOpened', (event) => {
      if (event.detail.title === title) {
        if (this.initiate) {
          this.initiate()
        }
      }
    }, false) */
  }

  initiate () {}

  activate () {}
}
