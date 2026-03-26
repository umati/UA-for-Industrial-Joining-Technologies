/**
 * The purpose of this class is to handle the asyncronous calls and responses to a specific joining system
 */

export class SocketHandler {
  constructor (webSocketManager, endpointUrl) {
    this.endpointUrl = endpointUrl
    this.webSocketManager = webSocketManager
    this.callMapping = {}
    this.failMapping = {}
    this.mandatoryLists = {}
    this.uniqueId = 1
    this.registerMandatory('read')
    this.registerMandatory('browseresult')
    this.registerMandatory('pathtoid')
    this.registerMandatory('callresult')
    this.registerMandatory('methodcall')
    this.registerMandatory('namespaces')
    this.registerMandatory('event', (_a, _b, _c) => {})
    this.registerMandatory('read product instance uri')
  }

  /**
   * Connect to the endpoint
   */
  connect () {
    this.webSocketManager.send('connect to', this.endpointUrl)
  }

  /**
   * Close the connection to the endpoint
   */
  close () {
    this.webSocketManager.send('terminate connection', this.endpointUrl)
  }

  /**
   * Subscribe to an event
   * @param {*} msg
   * @param {*} subscriberDetails - Optional label to help debugging
   */
  subscribeEvent (msg, subscriberDetails) {
    this.webSocketManager.send('subscribe', this.endpointUrl, null, { message: msg, details: subscriberDetails })
  }

  /**
   * Internal helper — registers a promise keyed by uniqueId, sends the request,
   * and returns the promise.  Resolves/rejects when the matching response arrives
   * via registerMandatory.
   * @param {string} command   WebSocket command string
   * @param {object} payload   Message payload
   * @returns {Promise}
   */
  _sendRequest (command, payload) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send(command, this.endpointUrl, this.uniqueId, payload)
    })
  }

  /**
   * A promise to get a nodeId from another nodeId following the path
   * @param {*} nodeId
   * @param {*} path
   * @returns {Promise}
   */
  pathtoidPromise (nodeId, path) {
    return this._sendRequest('pathtoid', { nodeid: nodeId, path })
  }

  /**
   * A promise to call a method
   * @param {*} objectNode
   * @param {*} methodNode
   * @param {*} inputArguments
   * @returns {Promise}
   */
  methodCall (objectNode, methodNode, inputArguments) {
    return this._sendRequest('methodcall', {
      objectnode: objectNode,
      methodnode: methodNode,
      arguments: inputArguments
    })
  }

  /**
   * A promise to read a node
   * @param {*} nodeid
   * @param {*} attribute
   * @returns {Promise}
   */
  readPromise (nodeid, attribute) {
    return this._sendRequest('read', { nodeid: this.stringify(nodeid), attribute })
  }

  /**
   * A promise to get the namespaces
   * @returns {Promise}
   */
  namespacePromise () {
    return this._sendRequest('namespaces', {})
  }

  /**
   * A promise to read all tool nodes and their ProductInstanceUri values.
   * @returns {Promise} Resolves with { message: { tools: [{toolName, productInstanceUri, path}] } }
   */
  readProductInstanceUri () {
    return this._sendRequest('read product instance uri', {})
  }

  /**
   * A promise to browse a node.
   * @param {*} nodeId
   * @param {*} details - if TRUE more relations are included in the response
   * @returns {Promise}
   */
  browsePromise (nodeId, details) {
    return this._sendRequest('browse', { nodeid: nodeId, details })
  }

  /**
   * Support function — converts a nodeId object or string to OPC UA node string format.
   * @param {string|object} nodeId
   * @returns {string}
   */
  stringify (nodeId) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      return nodeId
    }
    const sep = Number(nodeId.Identifier) ? ';i=' : ';s='
    return `ns=${nodeId.NamespaceIndex}${sep}${nodeId.Identifier}`
  }

  /**
   * The main function that listens to communication from the OPC-UA server interface.
   * @param {string}   responseString - The command string to listen for
   * @param {Function} [callback]     - Optional additional handler
   */
  registerMandatory (responseString, callback) {
    const applyAll = (functionList, msg) => {
      let returnValue
      for (const f of functionList) {
        if (f) {
          const nodeResult = f(msg)
          if (nodeResult) {
            returnValue = nodeResult
          }
        }
      }
      return returnValue
    }

    if (!this.mandatoryLists[responseString]) {
      this.mandatoryLists[responseString] = []
    }
    if (this.mandatoryLists[responseString].length === 0) {
      this.webSocketManager.subscribe(this.endpointUrl, responseString, (msg, uniqueid) => {
        const returnNode = applyAll(this.mandatoryLists[responseString], msg)

        if (msg && uniqueid) {
          if (msg.exception) {
            const failCall = this.failMapping[uniqueid]
            delete this.callMapping[uniqueid]
            delete this.failMapping[uniqueid]
            if (failCall) {
              failCall({ error: msg.exception, node: returnNode })
            }
          } else {
            const callbackFunction = this.callMapping[uniqueid]
            delete this.callMapping[uniqueid]
            delete this.failMapping[uniqueid]
            if (callbackFunction) {
              callbackFunction({ message: msg, node: returnNode })
            }
          }
        }
      })
    }

    this.mandatoryLists[responseString].push(callback)
  }
}
