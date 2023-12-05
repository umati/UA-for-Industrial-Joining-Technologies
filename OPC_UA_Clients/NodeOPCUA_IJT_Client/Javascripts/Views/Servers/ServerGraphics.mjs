import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
import EndpointGraphics from './EndpointGraphics.mjs'

export default class ServerGraphics extends BasicScreen {
  constructor (socket, endpointTabGenerator) {
    super('+')
    this.socket = socket
    this.endpointTabGenerator = endpointTabGenerator

    const makeLabel = function (text) {
      const a = document.createElement('label')
      a.classList.add('labelStyle')
      a.innerHTML = text
      return a
    }
    const column = this.makeNamedArea('Servers', 'leftArea')
    this.backGround.appendChild(column)

    column.appendChild(this.makeServerRow(
      makeLabel('Name'),
      makeLabel('EndpointUrl'),
      makeLabel('Connect'),
      makeLabel('Delete')
    ))

    this.rows = document.createElement('div')
    column.appendChild(this.rows)

    const newRow = document.createElement('div')
    newRow.style.textAlign = 'right'

    this.createButton('Add new server', newRow, () => {
      this.makeConnectionPointRow({
        name: '<NEW NAME>',
        address: '<NEW ENDPOINTURL>'
      }, this.socket, this.endpointTabGenerator)
    })
    column.appendChild(newRow)

    this.createButton('Save', newRow, () => {
      const connectionpoints = []
      for (const row of this.rows.children) {
        const name = row.children[0].children[0].value
        const address = row.children[1].children[0].value
        const autoconnect = row.children[2].children[0].checked
        connectionpoints.push({ name, address, autoconnect })
      }
      const saveObject = { connectionpoints }
      this.socket.emit('set connectionpoints', JSON.stringify(saveObject))
    })

    // Listen to the tree of possible connection points (Available OPC UA servers)
    this.socket.on('connection points', (msg) => {
      this.connectionPoints(JSON.parse(msg).connectionpoints, this.socket, this.endpointTabGenerator)
    })

    // Ask for the currently stored connectionpoints (Answer in 'connection points')
    this.socket.emit('get connectionpoints')
  }

  makeServerRow (nameContent, endpointUrlContent, connectContent, deleteContent) {
    const row = document.createElement('div')
    row.classList.add('serverRow')

    const name = document.createElement('div')
    name.classList.add('serverName')
    name.appendChild(nameContent)
    row.appendChild(name)

    const endp = document.createElement('div')
    endp.classList.add('serverEndpoint')
    endp.appendChild(endpointUrlContent)
    row.appendChild(endp)

    const connect = document.createElement('div')
    connect.classList.add('serverConnect')
    connect.appendChild(connectContent)
    row.appendChild(connect)

    const deleteArea = document.createElement('div')
    deleteArea.classList.add('serverDelete')
    deleteArea.appendChild(deleteContent)
    row.appendChild(deleteArea)

    return row
  }

  initiate () {

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
  connectionPoints (msg, socket, endpointTabGenerator) {
    this.socket = socket
    function connect (point) {
      // document.getElementById('displayedServerName').innerText = point.name
      socket.emit('connect to', point.address)
    }
    this.rows.innerHTML = ''
    for (const point of msg) {
      this.makeConnectionPointRow(point, socket, endpointTabGenerator)
      if (point.autoConnect && this.lastConnection !== point.address) { // Only automatically connect first time
        this.lastConnection = point.address
        connect(point)
      }
    }
  }

  makeConnectionPointRow (point, socket, endpointTabGenerator) {
    function connect (point, endpointTabGenerator) {
      const newConnection = new EndpointGraphics(point.name)
      newConnection.instantiate(point.address, socket)
      endpointTabGenerator.generateTab(newConnection, true)
    }

    function disconnect (point, endpointTabGenerator) {
      endpointTabGenerator.close(point)
    }

    const nameInput = this.createInput(point.name, null, () => {})

    const addrInput = this.createInput(point.address, null, (x) => {
      console.log(x)
    })

    const x = document.createElement('INPUT')
    x.setAttribute('type', 'checkbox')
    if (point.autoconnect) {
      x.checked = true
      connect(point, endpointTabGenerator)
    }
    x.onclick = function () {
      if (this.checked) {
        connect(point, endpointTabGenerator)
      } else {
        disconnect(point, endpointTabGenerator)
      }
    }

    const deleteButton = this.createButton('Delete', null, function () {
      this.deleteReference.rows.removeChild(this.deleteReference.row)
    })
    const row = this.makeServerRow(nameInput, addrInput, x, deleteButton)
    deleteButton.deleteReference = { rows: this.rows, row }

    this.rows.appendChild(row)
  }
}
