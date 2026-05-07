import BasicScreen from '../graphic-support/basic-screen.mjs'
import { lowerCaseJsonKeys } from '../graphic-support/json-key-normalization.mjs'
import EndpointGraphics from '../tab-setup/endpoint-graphics.mjs'

function normalizeConnectionPoint (point) {
  const loweredPoint = lowerCaseJsonKeys(point)
  if (!loweredPoint || typeof loweredPoint !== 'object') {
    return { name: '', address: '', autoconnect: false }
  }
  return {
    name: loweredPoint.name || '',
    address: loweredPoint.address || '',
    autoconnect: Boolean(loweredPoint.autoconnect)
  }
}

function valuesMatch (left, right, caseInsensitive = false) {
  if (left === undefined || left === null || right === undefined || right === null) return false
  const leftValue = String(left)
  const rightValue = String(right)
  return caseInsensitive
    ? leftValue.toLowerCase() === rightValue.toLowerCase()
    : leftValue === rightValue
}

/**
 * The purpose of this class is to generate a webpage that shows a list of OPC UA servers that the user is interested in
 * and that easily can be added or removed as tabs. The list can be edited and saved to allow fast prototyping
 */
export default class ServerGraphics extends BasicScreen {
  constructor (webSocketManager, endpointTabGenerator, settings) {
    super('Servers')
    this.tabHelpText = 'Manage OPC UA server endpoints. Add, edit, save, and connect to server profiles.'
    this.backGround.classList.add('serversScreen')
    this.webSocketManager = webSocketManager
    this.endpointTabGenerator = endpointTabGenerator

    const column = this.makeNamedArea('Servers', 'leftArea', this.backGround)

    // The title row
    column.appendChild(this.makeServerRow(
      this.createLabel('Name'),
      this.createLabel('EndpointUrl'),
      this.createLabel('Connect'),
      this.createLabel('Delete')
    ))

    this.rows = document.createElement('div')
    this.rows.classList.add('serversRows')
    column.appendChild(this.rows)

    const newRow = document.createElement('div')
    newRow.classList.add('serversActions')

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
      const loweredMsg = lowerCaseJsonKeys(msg) || {}
      this.connectionPoints(loweredMsg.connectionpoints, this.webSocketManager, this.endpointTabGenerator, settings)
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
  connectionPoints (msg, socket, endpointTabGenerator, settings) {
    this.webSocketManager = socket
    const connect = (point) => {
      // document.getElementById('displayedServerName').innerText = point.name
      socket.send('connect to', point.address)
    }
    this.rows.innerHTML = ''
    const points = Array.isArray(msg) ? msg : []
    for (const rawPoint of points) {
      const point = normalizeConnectionPoint(rawPoint)
      this.makeConnectionPointRow(point, socket, endpointTabGenerator, settings)
      if (point.autoconnect && this.lastConnection !== point.address) { // Only automatically connect first time
        this.lastConnection = point.address
        connect(point)
      }
    }
  }

  findExistingEndpointTab (point, endpointTabGenerator) {
    if (!endpointTabGenerator || !Array.isArray(endpointTabGenerator.containerList)) {
      return null
    }
    return endpointTabGenerator.containerList.find((tab) => {
      const content = tab?.content
      if (!content) return false
      if (valuesMatch(point.address, content.endpointUrl)) return true
      if (valuesMatch(point.name, content.title, true)) return true
      return false
    }) || null
  }

  /**
   * This function generates an input row where the name and endpointurl can be edited and connection
   * can be managed
   * @param {*} point the stored JSON content of a row that should be displayed
   * @param {*} socket the Websocket representation
   * @param {*} endpointTabGenerator The class that manages the graphical representation of the tabs, so that a tab can be removed when disconnected
   */
  makeConnectionPointRow (point, socket, endpointTabGenerator, settings) {
    const normalizedPoint = normalizeConnectionPoint(point)

    const connect = (point, endpointTabGenerator) => {
      const existingTab = this.findExistingEndpointTab(point, endpointTabGenerator)
      if (existingTab) {
        existingTab.select()
        return
      }
      const newConnection = new EndpointGraphics(point.name, settings)
      newConnection.instantiate(point.address, socket)
      const endpointTab = endpointTabGenerator.generateTab(newConnection, 1, true)
      newConnection.bindEndpointTab(endpointTab)
    }

    const disconnect = (point, endpointTabGenerator) => {
      if (!endpointTabGenerator || !Array.isArray(endpointTabGenerator.containerList)) {
        return
      }
      const tabsToClose = endpointTabGenerator.containerList.filter((tab) => {
        const content = tab?.content
        if (!content) return false
        if (valuesMatch(point.address, content.endpointUrl)) return true
        if (valuesMatch(point.name, content.title, true)) return true
        return false
      })
      for (const tab of tabsToClose) {
        tab.close()
      }
      endpointTabGenerator.containerList = endpointTabGenerator.containerList.filter((tab) => !tabsToClose.includes(tab))
    }

    const nameInput = this.createInput(normalizedPoint.name, null, () => {})

    const addrInput = this.createInput(normalizedPoint.address, null, (_x) => {})

    const autoConnect = Boolean(normalizedPoint.autoconnect)
    const checkBox = this.createCheckbox(autoConnect, (newValue) => {
      normalizedPoint.autoconnect = newValue
      if (newValue) {
        connect(normalizedPoint, endpointTabGenerator)
      } else {
        disconnect(normalizedPoint, endpointTabGenerator)
      }
    })

    if (autoConnect) {
      connect(normalizedPoint, endpointTabGenerator)
    }

    nameInput.oninput = (evt) => {
      normalizedPoint.name = evt.target.value
    }
    addrInput.oninput = (evt) => {
      normalizedPoint.address = evt.target.value
    }

    const deleteButton = this.createButton('Delete', null, () => {
      deleteButton.deleteReference.rows.removeChild(deleteButton.deleteReference.row)
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
