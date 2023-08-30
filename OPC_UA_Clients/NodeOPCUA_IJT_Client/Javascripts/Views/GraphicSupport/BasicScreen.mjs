export default class ControlMessageSplitScreen {
  constructor (container) {
    this.backGround = document.createElement('div')
    this.backGround.classList.add('basescreen')
    container.appendChild(this.backGround)

    const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === container.tabTitle) {
        if (this.initiate) {
          this.initiate()
        }
      }
    }, false)
  }
}
