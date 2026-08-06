import BasicScreen from '../graphic-support/basic-screen.mjs'
import { lowerCaseJsonKeys } from '../graphic-support/json-key-normalization.mjs'
import EndpointGraphics from '../tab-setup/endpoint-graphics.mjs'

const SAVE_RESPONSE_TIMEOUT_MS = 10_000
const CONNECTION_TEST_TIMEOUT_MS = 150_000
const NEW_SERVER_NAME = 'New server'
const NEW_SERVER_ENDPOINT = 'opc.tcp://host:4840'

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

function isValidEndpointAddress (value) {
  if (typeof value !== 'string') return false
  const trimmed = value.trim()
  if (!trimmed) return false
  return /^opc\.tcp:\/\/[^\s]+$/i.test(trimmed)
}

function simplifyConnectionError (value) {
  const text = String(value || '').trim()
  if (!text) return ''
  const lowerText = text.toLowerCase()
  if (lowerText.includes('timed out') || lowerText.includes('timeout')) return 'Connection timed out'
  if (lowerText.includes('network location cannot be reached') || lowerText.includes('unreachable')) return 'Network unreachable'
  if (lowerText.includes('connection refused')) return 'Connection refused'
  if (lowerText.includes('failed to connect')) return 'Connection failed'
  return text.length > 100 ? `${text.slice(0, 97)}...` : text
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
    this._saveInFlight = false
    this._saveDebounceTimer = null
    this._connectionStates = new Map()

    const column = this.makeNamedArea('Servers', 'leftArea', this.backGround)

    // The title row
    column.appendChild(this.makeServerRow(
      this.createLabel('Name'),
      this.createLabel('EndpointUrl'),
      this.createLabel('Connect'),
      this.createLabel('Test'),
      this.createLabel('Status'),
      this.createLabel('Delete')
    ))

    this.rows = document.createElement('div')
    this.rows.classList.add('serversRows')
    column.appendChild(this.rows)
    this.messages = document.createElement('div')
    this.messages.classList.add('serversMessage')
    column.appendChild(this.messages)

    const newRow = document.createElement('div')
    newRow.classList.add('serversActions')

    // The 'Add server' button
    this.createButton('Add new server', newRow, () => {
      this.makeConnectionPointRow({
        name: NEW_SERVER_NAME,
        address: NEW_SERVER_ENDPOINT
      }, this.webSocketManager, this.endpointTabGenerator)
    })
    column.appendChild(newRow)

    this.createButton('Export', newRow, () => {
      this.exportConnectionPoints()
    })

    this.importFileInput = document.createElement('input')
    this.importFileInput.setAttribute('type', 'file')
    this.importFileInput.setAttribute('accept', 'application/json,.json')
    this.importFileInput.classList.add('serversImportInput')
    this.importFileInput.onchange = async () => {
      const file = this.importFileInput.files?.[0]
      if (file) {
        await this.importConnectionPoints(file)
      }
      this.importFileInput.value = ''
    }
    column.appendChild(this.importFileInput)

    this.createButton('Import', newRow, () => {
      this.importFileInput.click()
    })

    this.createButton('Reset to defaults', newRow, () => {
      this.resetConnectionPoints()
    })

    // The save button
    this.createButton('Save', newRow, () => {
      this.saveConnectionPoints()
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

  showMessage (text) {
    if (!this.messages) {
      this.messages = document.createElement('div')
      this.messages.classList.add('serversMessage')
      this.backGround.appendChild(this.messages)
    }
    this.messages.innerText = text
  }

  _setConnectionState (endpoint, status, errorText = '') {
    if (!endpoint) return
    this._connectionStates.set(endpoint, { status, errorText })
    for (const row of this.rows.children) {
      const addressInput = row.children[1]?.children?.[0]
      const statusNode = row.children[4]
      if (!addressInput || !statusNode) continue
      if (String(addressInput.value).trim() === String(endpoint).trim()) {
        statusNode.innerText = errorText ? `${status}: ${errorText}` : status
      }
    }
  }

  _setRowStatus (row, text) {
    const statusNode = row.children[4]
    if (statusNode) {
      statusNode.innerText = text
    }
  }

  validateRowsAndBuildPayload () {
    const connectionpoints = []
    const errors = []
    const seenAddresses = new Set()
    for (const row of this.rows.children) {
      const nameInput = row.children[0].children[0]
      const addressInput = row.children[1].children[0]
      const autoconnect = row.children[2].children[0].checked
      const name = String(nameInput.value || '').trim()
      const address = String(addressInput.value || '').trim()
      nameInput.classList.remove('inputError')
      addressInput.classList.remove('inputError')
      if (!name) {
        nameInput.classList.add('inputError')
        this._setRowStatus(row, 'Invalid: empty name')
        errors.push(`Row with endpoint '${address || '<empty>'}' has empty name`)
        continue
      }
      if (!isValidEndpointAddress(address)) {
        addressInput.classList.add('inputError')
        this._setRowStatus(row, 'Invalid: endpoint')
        errors.push(`Endpoint '${address || '<empty>'}' is invalid`)
        continue
      }
      const addressKey = address.toLowerCase()
      if (seenAddresses.has(addressKey)) {
        addressInput.classList.add('inputError')
        this._setRowStatus(row, 'Invalid: duplicate endpoint')
        errors.push(`Endpoint '${address}' is duplicated`)
        continue
      }
      seenAddresses.add(addressKey)
      const connectionState = this._connectionStates.get(address)?.status || 'Disconnected'
      this._setRowStatus(row, connectionState)
      connectionpoints.push({ name, address, autoconnect })
    }
    return { connectionpoints, errors }
  }

  saveConnectionPoints () {
    if (this._saveInFlight) {
      this.showMessage('Save already in progress...')
      return
    }

    if (this._saveDebounceTimer) {
      clearTimeout(this._saveDebounceTimer)
    }
    this._saveDebounceTimer = setTimeout(() => {
      const { connectionpoints, errors } = this.validateRowsAndBuildPayload()
      if (connectionpoints.length === 0) {
        this.showMessage(errors.length ? `Nothing saved. ${errors[0]}` : 'Nothing to save.')
        return
      }
      const saveObject = {
        schema_version: 1,
        connectionpoints
      }
      const saveUniqueId = globalThis.crypto?.randomUUID?.() || `save-${Date.now()}`
      this._saveInFlight = true
      let saveTimeout = null
      const onSaveResponse = (msg, uniqueid) => {
        if (uniqueid !== saveUniqueId) return
        if (saveTimeout !== null) {
          clearTimeout(saveTimeout)
          saveTimeout = null
        }
        this.webSocketManager.unsubscribe('common', 'set connectionpoints', onSaveResponse)
        this._saveInFlight = false
        if (msg?.exception) {
          this.showMessage(`Could not save server list: ${msg.exception}`)
          return
        }
        const baseMessage = errors.length
          ? `Saved ${connectionpoints.length} server${connectionpoints.length === 1 ? '' : 's'}. ${errors.length} row${errors.length === 1 ? '' : 's'} need attention.`
          : 'Server list saved.'
        this.showMessage(baseMessage)
        this.webSocketManager.send('get connectionpoints')
      }
      this.webSocketManager.subscribe('common', 'set connectionpoints', onSaveResponse)
      saveTimeout = setTimeout(() => {
        this.webSocketManager.unsubscribe('common', 'set connectionpoints', onSaveResponse)
        this._saveInFlight = false
        this.showMessage('Save did not finish. Check that the Web Client backend is running, then try Save again.')
      }, SAVE_RESPONSE_TIMEOUT_MS)
      this.webSocketManager.send('set connectionpoints', null, saveUniqueId, saveObject)
    }, 250)
  }

  exportConnectionPoints () {
    const { connectionpoints, errors } = this.validateRowsAndBuildPayload()
    if (connectionpoints.length === 0) {
      this.showMessage(errors.length ? `Nothing exported. ${errors[0]}` : 'Nothing to export.')
      return
    }
    const payload = JSON.stringify({ schema_version: 1, connectionpoints }, null, 2) + '\n'
    const blob = new Blob([payload], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'connectionpoints.json'
    link.click()
    URL.revokeObjectURL(url)
    this.showMessage(`Exported ${connectionpoints.length} server${connectionpoints.length === 1 ? '' : 's'}.`)
  }

  async importConnectionPoints (file) {
    try {
      const payload = JSON.parse(await file.text())
      const loweredPayload = lowerCaseJsonKeys(payload) || {}
      const rawPoints = Array.isArray(loweredPayload.connectionpoints) ? loweredPayload.connectionpoints : []
      this.connectionPoints(rawPoints.map(normalizeConnectionPoint), this.webSocketManager, this.endpointTabGenerator)
      const { connectionpoints, errors } = this.validateRowsAndBuildPayload()
      this.showMessage(`Imported ${connectionpoints.length} server${connectionpoints.length === 1 ? '' : 's'}. Review and click Save.${errors.length ? ` ${errors.length} row${errors.length === 1 ? '' : 's'} need attention.` : ''}`)
    } catch (error) {
      this.showMessage(`Could not import server list: ${error.message || error}`)
    }
  }

  resetConnectionPoints () {
    if (typeof window.confirm === 'function' && !window.confirm('Reset the server list to defaults?')) {
      return
    }
    const resetUniqueId = globalThis.crypto?.randomUUID?.() || `reset-${Date.now()}`
    const onResetResponse = (msg, uniqueid) => {
      if (uniqueid !== resetUniqueId) return
      this.webSocketManager.unsubscribe('common', 'reset connectionpoints', onResetResponse)
      if (msg?.exception) {
        this.showMessage(`Could not reset server list: ${msg.exception}`)
        return
      }
      this.showMessage('Server list reset to defaults.')
      this.webSocketManager.send('get connectionpoints')
    }
    this.webSocketManager.subscribe('common', 'reset connectionpoints', onResetResponse)
    this.webSocketManager.send('reset connectionpoints', null, resetUniqueId, {})
  }

  testConnectionPoint (point, socket) {
    if (!isValidEndpointAddress(point.address)) {
      this._setConnectionState(point.address, 'Failed', 'Invalid endpoint')
      return
    }
    const testUniqueId = globalThis.crypto?.randomUUID?.() || `test-${Date.now()}`
    this._setConnectionState(point.address, 'Testing')
    let testTimeout = null
    let settled = false
    const cleanup = () => {
      if (testTimeout !== null) {
        clearTimeout(testTimeout)
        testTimeout = null
      }
      socket.unsubscribe(point.address, 'test connection', onTestResponse)
    }
    const finish = (status, errorText = '') => {
      if (settled) return
      settled = true
      cleanup()
      this._setConnectionState(point.address, status, errorText)
    }
    const onTestResponse = (msg, uniqueid) => {
      if (uniqueid !== testUniqueId) return
      if (msg?.exception) {
        finish('Failed', simplifyConnectionError(msg.exception))
        return
      }
      finish('Reachable')
    }
    socket.subscribe(point.address, 'test connection', onTestResponse)
    testTimeout = setTimeout(() => {
      finish('Failed', 'Test timed out')
    }, CONNECTION_TEST_TIMEOUT_MS)
    socket.send('test connection', point.address, testUniqueId, {})
  }

  /**
   * Display the different OPC UA servers that the saved list of endpoints contain
   * @param {*} msg the message received
   * @param {*} socket the socket to use to call the 'connect to'
   * @param {*} endpointTabGenerator The class that manages the graphical representation of the tabs
   */
  connectionPoints (msg, socket, endpointTabGenerator, settings) {
    this.webSocketManager = socket
    this.rows.innerHTML = ''
    const points = Array.isArray(msg) ? msg : []
    for (const rawPoint of points) {
      const point = normalizeConnectionPoint(rawPoint)
      this.makeConnectionPointRow(point, socket, endpointTabGenerator, settings)
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
      if (!isValidEndpointAddress(point.address)) {
        this._setConnectionState(point.address, 'Failed', 'Invalid endpoint')
        return
      }
      if (!endpointTabGenerator || typeof endpointTabGenerator.generateTab !== 'function') {
        this._setConnectionState(point.address, 'Failed', 'Endpoint tab generator unavailable')
        return
      }
      const existingTab = this.findExistingEndpointTab(point, endpointTabGenerator)
      if (existingTab) {
        existingTab.select()
        return
      }
      this._setConnectionState(point.address, 'Connecting')
      const onConnectResponse = (msg) => {
        socket.unsubscribe(point.address, 'connect to', onConnectResponse)
        if (msg?.exception) {
          this._setConnectionState(point.address, 'Failed', msg.exception)
          return
        }
        this._setConnectionState(point.address, 'Connected')
      }
      socket.subscribe(point.address, 'connect to', onConnectResponse)
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
      this._setConnectionState(point.address, 'Disconnected')
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
    const testButton = this.createButton('Test', null, () => {
      this.testConnectionPoint(normalizedPoint, socket)
    })
    const statusLabel = document.createElement('span')
    statusLabel.innerText = this._connectionStates.get(normalizedPoint.address)?.status || 'Disconnected'
    const row = this.makeServerRow(nameInput, addrInput, checkBox, testButton, statusLabel, deleteButton)
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
  makeServerRow (nameContent, endpointUrlContent, connectContent, testContent, statusContent, deleteContent) {
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

    const testArea = document.createElement('div')
    testArea.classList.add('serverTest')
    testArea.appendChild(testContent)
    row.appendChild(testArea)

    const statusArea = document.createElement('div')
    statusArea.classList.add('serverStatus')
    statusArea.appendChild(statusContent)
    row.appendChild(statusArea)

    const deleteArea = document.createElement('div')
    deleteArea.classList.add('serverDelete')
    deleteArea.appendChild(deleteContent)
    row.appendChild(deleteArea)

    return row
  }
}
