import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class ServerGraphics extends ControlMessageSplitScreen {
  constructor () {
    super('Servers', 'Servers', 'Server status')
    this.lastConnection = ''
  }

  /**
   * Clears the message area
   */
  clearDisplay () {
    this.messages.innerHTML = ''
  }

  /**
   * Display the different OPC UA servers that the web server suggests
   * @param {*} msg the message received
   * @param {*} socket the socket to use to call the 'connect to'
   */
  connectionPoints (msg, socket) {
    function connect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    this.controlArea.innerHTML = ''
    for (const point of msg) {
      this.createButton(point.name, this.controlArea, () => {
        connect(point)
      })

      if (point.autoConnect && this.lastConnection !== point.address) { // Only automatically connect first time
        this.lastConnection = point.address
        connect(point)
      }
    }
  }
}
