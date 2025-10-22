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
    this.browseList = []
    this.readList = []
    this.uniqueId = 1
    this.registerMandatory('read')
    this.registerMandatory('browseresult')
    this.registerMandatory('pathtoid')
    this.registerMandatory('callresult')
    this.registerMandatory('methodcall')
    this.registerMandatory('namespaces')
    this.registerMandatory('event', (a, b, c) => {
      console.log('Do this for all events !!!!')
    })
  }

  /**
   * Connect to the endpoint
   * @date 2/2/2024 - 8:44:02 AM
   */
  connect () {
    this.webSocketManager.send('connect to', this.endpointUrl)
  }

  /**
   * Close the connection to the endpoint
   * @date 2/2/2024 - 8:44:31 AM
   */
  close () {
    this.webSocketManager.send('terminate connection', this.endpointUrl)
  }

  /**
   * Subscribe to an event
   * @param {*} nodeId
   * @param {*} path
   * @param {*} subscriberDetails // Optional data to help debugging
   * @returns
   */
  subscribeEvent (msg, subscriberDetails) {
    this.webSocketManager.send('subscribe', this.endpointUrl, null, { message: msg, details: subscriberDetails })
  }

  /**
   * A promise to get a nodeId from another nodeId following the path
   * @param {*} nodeId
   * @param {*} path
   * @returns
   */
  pathtoidPromise (nodeId, path) {
    // console.log('LOOKING FOR: '+nodeId+path)
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send('pathtoid', this.endpointUrl, this.uniqueId, {
        nodeid: nodeId,
        path
      })
    })
  }

  /**
   * A promise to call a method
   * @param {*} methodToCall a structure with the method to call
   * @returns
   */
  methodCall (objectNode, methodNode, inputArguments) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send('methodcall', this.endpointUrl, this.uniqueId, {
        objectnode: objectNode,
        methodnode: methodNode,
        arguments: inputArguments
      })
    })
  }

  /**
   * A promise to read a node
   * @param {*} nodeId
   * @returns
   */
  readPromise (nodeid, attribute) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send('read', this.endpointUrl, this.uniqueId, {
        nodeid: this.stringify(nodeid), attribute
      })
    })
  }

  /**
   * A promise to get the namespaces
   * @param {*} nodeId
   * @returns
   */
  namespacePromise () {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send('namespaces', this.endpointUrl, this.uniqueId, {})
    })
  }

  /**
   * Supportfunction to create a node identity string of the right format
   * @date 2/2/2024 - 8:44:59 AM
   *
   * @param {*} nodeId the node string or object
   * @returns {*} a string representation
   */
  stringify (nodeId) {
    if (typeof nodeId === 'string' || nodeId instanceof String) {
      return nodeId
    } else {
      let st = ';s='

      if (Number(nodeId.Identifier)) {
        st = ';i='
      }
      return 'ns=' + nodeId.NamespaceIndex + st + nodeId.Identifier
    }
  }

  /**
   * A promise to browse a node. If details is TRUE then more relations are included in the response
   * @param {*} nodeId
   * @param {*} details
   * @returns
   */
  browsePromise (nodeId, details) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.webSocketManager.send('browse', this.endpointUrl, this.uniqueId, {
        nodeid: nodeId,
        details
      })
    })
  }

  /**
   * The main function that listens to the communication from the node OPC-UA server
   * interface mainly implemented in NodeOPCUAInterface.mjs
   * @param {*} responseString The string the socket should listen for.
   * @param {*} callback The function to call when the socket signals using the string
   */
  registerMandatory (responseString, callback) {
    function applyAll (functionList, msg) {
      if (msg && msg.exception) {
        // throw new Error('Response exception: ' + msg.exception)
      }
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
            this.callMapping[uniqueid] = null
            this.failMapping[uniqueid] = null
            if (failCall) {
              // console.log('typeList'+typeList+returnNode?.nodeId)
              failCall({ error: msg.exception, node: returnNode })
            }
          } else {
            const callbackFunction = this.callMapping[uniqueid]
            this.callMapping[uniqueid] = null
            this.failMapping[uniqueid] = null
            if (callbackFunction) {
            // console.log('typeList'+typeList+returnNode?.nodeId)
              callbackFunction({ message: msg, node: returnNode })
            }
          }
        }
      })
    }

    this.mandatoryLists[responseString].push(callback)
  }
}
