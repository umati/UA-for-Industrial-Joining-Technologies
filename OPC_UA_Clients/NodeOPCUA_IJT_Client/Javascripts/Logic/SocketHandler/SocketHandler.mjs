export default class SocketHandler {
  constructor (socket) {
    this.socket = socket
    this.callMapping = {}
    this.failMapping = {}
    this.mandatoryLists = {}
    this.browseList = []
    this.readList = []
    this.uniqueId = 1
    this.registerMandatory('readresult')
    this.registerMandatory('browseresult')
    this.registerMandatory('pathtoidresult')
  }

  /**
   * Subscribe to an event
   * @param {*} nodeId
   * @param {*} path
   * @param {*} subscriberDetails // Optional data to help debugging
   * @returns
   */
  subscribeEvent (msg, subscriberDetails) {
    this.socket.emit('subscribe event', msg, subscriberDetails)
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
      this.socket.emit('pathtoid', this.uniqueId, nodeId, path)
    })
  }

  /**
   * A promise to get a construct an extension
   * @param {*} nodeId
   * @param {*} parameters
   * @returns
   */
  constructExtensionObjectPromise (nodeId, parameters) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.socket.emit('constructextension', this.uniqueId, nodeId, parameters)
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
      this.socket.emit('methodcall', this.uniqueId, objectNode, methodNode, inputArguments)
    })
  }

  /**
   * A promise to read a node
   * @param {*} nodeId
   * @returns
   */
  readPromise (nodeId, attribute) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.socket.emit('read', this.uniqueId, nodeId, attribute)
    })
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
      this.socket.emit('browse', this.uniqueId, nodeId, details)
    })
  }

  /**
   * The main function that listens to the communication from the node OPC-UA server
   * interface mainly implemented in NodeOPCUAInterface.mjs
   * @param {*} responseString The string the socket should listen to.
   * @param {*} callback The function to call when the socket signals using the string
   */
  registerMandatory (responseString, callback) {
    function applyAll (functionList, msg) {
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
      this.socket.on(responseString, (msg) => {
        const returnNode = applyAll(this.mandatoryLists[responseString], msg)

        if (msg && msg.callid) {
          const callbackFunction = this.callMapping[msg.callid]
          this.callMapping[msg.callid] = null
          if (callbackFunction) {
            // console.log('typeList'+typeList+returnNode?.nodeId)
            callbackFunction({ message: msg, node: returnNode })
          }
        }
      })
    }

    this.mandatoryLists[responseString].push(callback)
  }
}
