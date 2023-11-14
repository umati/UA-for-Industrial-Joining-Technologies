import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class ServerGraphics extends ControlMessageSplitScreen {
  constructor () {
    super('Servers', 'Servers', 'Server status')
    this.lastConnection = ''

    this.createButton('Add', this.controlArea, () => {
      if (this.socket) {
        this.socket.emit('set connectionpoints', 'Hallo')
      }
    })

    this.createButton('Select', this.controlArea, () => {
      if (this.socket) {
        this.socket.emit('set connectionpoints', 'Hallo')
      }
    })
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
    /*
    this.socket = socket
    function connect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    this.controlArea.innerHTML = ''
    for (const point of msg) {
      this.makeConnectionPointRow(point, socket)
      if (point.autoConnect && this.lastConnection !== point.address) { // Only automatically connect first time
        this.lastConnection = point.address
        connect(point)
      }
    } */
  }

  // Connect, disconnect, delete, add, highlight default

  makeConnectionPointRow (point, socket) {
    function connect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    function disconnect (point) {
      document.getElementById('displayedServerName').innerText = point.name
      socket.emit('disconnect from', point.address)
    }
    const row = document.createElement('div')
    row.classList.add('row')
    this.controlArea.appendChild(row)

    this.createButton(point.name, row, () => {
      connect(point)
    })

    const x = document.createElement('INPUT')
    x.setAttribute('type', 'checkbox')
    x.onclick = function () {
      if (this.checked) {
        connect(point)
      } else {
        disconnect(point)
      }
    }
    row.appendChild(x)

    this.createButton('Save', row, () => {
      connect(point)
    })

    this.createButton('Delete', row, () => {
      connect(point)
    })
  }
}
