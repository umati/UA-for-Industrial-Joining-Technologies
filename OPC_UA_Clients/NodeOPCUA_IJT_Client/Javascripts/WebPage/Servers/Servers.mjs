import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class Serverhandler extends ControlMessageSplitScreen {
  constructor (container, socket) {
    super(container, 'Servers', 'Server status')
  }

  clearDisplay () {
    this.messages.innerHTML = ''
  }

  // Display the different OPC UA servers that the web server suggests
  connectionPoints (msg, socket) {
    function connect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    this.controlArea.innerHTML = ''
    for (const point of msg) {
      const item = document.createElement('button')
      item.classList.add('myButton')
      item.style.display = 'block'
      item.innerHTML = point.name
      item.onclick = () => {
        connect(point)
      }
      if (point.autoConnect) {
        connect(point)
      }
      this.controlArea.appendChild(item)
      window.scrollTo(0, document.body.scrollHeight)
    }
  }
}
