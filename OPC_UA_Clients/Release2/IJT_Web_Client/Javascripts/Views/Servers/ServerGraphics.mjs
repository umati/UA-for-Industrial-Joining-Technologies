import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
import EndpointGraphics from './EndpointGraphics.mjs'

/**
 * The purpose of this class is to generate a webpage that shows a list of OPC UA servers that the user is interested in
 * and that easily can be added or removed as tabs. The list can be edited and saved to allow fast prototyping
 */
export default class ServerGraphics extends BasicScreen {
  constructor (webSocketManager, endpointTabGenerator) {
    super('+')
    this.webSocketManager = webSocketManager
    this.endpointTabGenerator = endpointTabGenerator

    const column = this.makeNamedArea('Servers', 'leftArea')
    this.backGround.appendChild(column)

    // The title row
    column.appendChild(this.makeServerRow(
      this.createLabel('Name'),
      this.createLabel('EndpointUrl'),
      this.createLabel('Connect'),
      this.createLabel('Delete')
    ))

    this.rows = document.createElement('div')
    column.appendChild(this.rows)

    const newRow = document.createElement('div')
    newRow.style.textAlign = 'right'

    // The 'Add server' button
    this.createButton('Add new server', newRow, () => {
      this.makeConnectionPointRow({
        name: '<NEW NAME>',
        address: '<NEW ENDPOINTURL>'
      }, this.webSocketManager, this.endpointTabGenerator)
    })
    column.appendChild(newRow)

    // The save button
    this.createButton('Save', newRow, () => {
      const connectionpoints = []
      for (const row of this.rows.children) {
        const name = row.children[0].children[0].value
        const address = row.children[1].children[0].value
        const autoconnect = row.children[2].children[0].checked
        connectionpoints.push({ name, address, autoconnect })
      }
      const saveObject = { connectionpoints }
      this.webSocketManager.send('set connectionpoints', null, null, saveObject)
    })

    // Listen to the tree of possible connection points (Available OPC UA servers)
    this.webSocketManager.subscribe(null, 'get connectionpoints', (msg) => {
      this.connectionPoints(msg.connectionpoints, this.webSocketManager, this.endpointTabGenerator)
    })

    // Ask for the currently stored connectionpoints (Answer in 'connection points')
    this.webSocketManager.send('get connectionpoints')
  }

  /**
   * Clears the message area
   */
  clearDisplay () {
    this.messages.innerHTML = ''
  }

  /**
   * Display the different OPC UA servers that the saved list of endpoints contain
   * @param {*} msg the message received
   * @param {*} socket the socket to use to call the 'connect to'
   * @param {*} endpointTabGenerator The class that manages the graphical representation of the tabs
   */
  connectionPoints (msg, socket, endpointTabGenerator) {
    this.webSocketManager = socket
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

  /**
   * This function generates an input row where the name and endpointurl can be edited and connection
   * can be managed
   * @param {*} point the stored JSON content of a row that should be displayed
   * @param {*} socket the Websocket representation
   * @param {*} endpointTabGenerator The class that manages the graphical representation of the tabs, so that a tab can be removed when disconnected
   */
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

    const checkBox = this.createCheckbox(point.autoconnect, (newValue) => {
      if (newValue) {
        connect(point, endpointTabGenerator)
      } else {
        disconnect(point, endpointTabGenerator)
      }
    })

    if (point.autoconnect) {
      connect(point, endpointTabGenerator)
    }

    const deleteButton = this.createButton('Delete', null, function () {
      this.deleteReference.rows.removeChild(this.deleteReference.row)
    })
    const row = this.makeServerRow(nameInput, addrInput, checkBox, deleteButton)
    deleteButton.deleteReference = { rows: this.rows, row }

    this.rows.appendChild(row)
  }

  /**
   * Basic support function to generate a row in the table
   * @param {*} nameContent The HTML repressentation of name of the server
   * @param {*} endpointUrlContent The HTML repressentation of address of the server
   * @param {*} connectContent The HTML repressentation of 'wanted' connection status
   * @param {*} deleteContent Th eHTML repressentation of button to delete the row
   * @returns A HTML representation of the row
   */
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
}
