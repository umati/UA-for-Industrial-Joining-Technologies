
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

  read (nodeId, callback) {
    this.uniqueId++
    this.callMapping[this.uniqueId] = callback
    this.socket.emit('read', this.uniqueId, nodeId)
  }

  browse (nodeId, callback, details) {
    this.uniqueId++
    this.callMapping[this.uniqueId] = callback
    this.socket.emit('browse', this.uniqueId, nodeId, details)
  }

  pathtoid (nodeId, path, callback) {
    this.uniqueId++
    this.callMapping[this.uniqueId] = callback
    this.socket.emit('pathtoid', this.uniqueId, nodeId, path)
  }

  pathtoidPromise (nodeId, path) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.socket.emit('pathtoid', this.uniqueId, nodeId, path)
    })
  }

  readPromise (nodeId) {
    return new Promise((resolve, reject) => {
      this.uniqueId++
      this.callMapping[this.uniqueId] = resolve
      this.failMapping[this.uniqueId] = reject
      this.socket.emit('read', this.uniqueId, nodeId)
    })
  }

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
