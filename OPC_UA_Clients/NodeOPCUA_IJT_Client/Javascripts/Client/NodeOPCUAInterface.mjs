
import async from 'async'

import {
  AttributeIds,
  promoteOpaqueStructure,
  makeBrowsePath,
  StatusCodes,
  TimestampsToReturn
} from 'node-opcua'

export default class NodeOPCUAInterface {
  constructor (io, attributeIds) {
    this.attributeIds = attributeIds
    this.io = io
  }

  /**
   * Sets up the socket communication to listen to the calls from the webpage and direct them
   * to the applicable function
   * @param {*} endpointUrls
   * @param {*} displayFunction a function that displays messages
   * @param {*} OPCUAClient
   */
  setupSocketIO (endpointUrls, displayFunction, OPCUAClient) {
    const io = this.io
    this.displayFunction = displayFunction
    this.OPCUAClient = OPCUAClient
    this.endpointUrls = endpointUrls
    this.session = null

    io.on('connection', (socket) => {
      // ----------------------------------------------------------------------------------------- SOCKET: Interaction with items item
      socket.on('subscribe item', (callid, msg) => {
        this.addMonitor(callid, msg)
      })
      socket.on('read', (callid, msg) => {
        this.read(callid, msg)
      })

      socket.on('browse', (callid, nodeId, details) => {
        this.browse(callid, nodeId, details)
      })

      socket.on('pathtoid', (callid, nodeId, path) => {
        this.translateBrowsePath(callid, nodeId, path)
      })

      socket.on('terminate connection', () => {
        console.log('Recieving terminate session request')
        this.closeConnection()
      })

      // ----------------------------------------------------------------------------------------- SOCKET: Connect and establish a structure of items
      socket.on('connect to', msg => {
        console.log('Nodejs OPC UA client attempting to connect to ' + msg)
        if (msg) {
          this.setupClient(msg, this.displayFunction, this.OPCUAClient, this.io)
        }
      })

      // Send the listed access points IP addresses to the GUI
      this.io.emit('connection points', endpointUrls)
    })
  }

  setupClient (endpointUrl, displayFunction, OPCUAClient) {
    const io = this.io
    // let theSession;
    const thisContainer = this
    const client = OPCUAClient.create({ endpointMustExist: false })
    this.client = client
    this.endpointUrl = endpointUrl

    async.series([
      function (callback) { // Connect
        client.connect(endpointUrl, function (err) {
          if (err) {
            console.log('Cannot connect to endpoint :', endpointUrl)
          } else {
            console.log('Connection established.')
            io.emit('connection established')
          }
          callback(err)
        })
      },
      function (callback) { // Session
        client.createSession(function (err, session) {
          if (!err) {
            // theSession = session
            thisContainer.session = session

            io.emit('session established')
          }
          callback(err)
        })
      },
      function (callback) { // Namespaces
        thisContainer.session.readNamespaceArray((err, namespaces) => {
          if (err) {
            throw new Error(err)
          }
          console.log('Handling NameSpaces')
          io.emit('namespaces', namespaces)
        })
      }

    ],
    function (err) {
      if (err) {
        console.log('Failure during establishing connection to OPC UA server ', err)
        this.io.emit('error message', err.toString(), 'connection')
        process.exit(0)
      } else {
        console.log('Connection and session established.')
      }
    }
    )
  }

  /**
   * Read the content of a node
   * The result is communicated to the webpage  over the io socket using 'readresult'
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} nodeId The identity of the node to read
   */
  read (callid, nodeId) {
    (async () => {
      try {
        const dataValue = await this.session.read({
          nodeId,
          attributeId: AttributeIds.Value
        })

        const result = dataValue.value.value
        if (result && result.resultContent) {
          await promoteOpaqueStructure(this.session, [{ value: result.resultContent }])
        }

        // console.log('dataValue ' + dataValue.toString());

        this.io.emit('readresult', { callid, dataValue, stringValue: dataValue.toString(), nodeid: nodeId })
        return dataValue
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (reading): ' + err.message) // Display the error message first
        this.io.emit('error message', err.toString(), 'read') // (Then for debug purposes display all of it)
      }
    })()
  };

  /**
   * Get a nodeId from a start-node and a path.
   * The result is communicated to the webpage over the io socket using 'pathtoidresult'
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} nodeId The start node
   * @param {*} path The path
   */
  translateBrowsePath (callid, nodeId, path) {
    (async () => {
      try {
        // let nsIJT = 4;

        const bpr2 = await this.session.translateBrowsePath(
          makeBrowsePath(nodeId, path))

        if (bpr2.statusCode !== StatusCodes.Good) {
          console.log(`Cannot find the ${path} object. ${nodeId} - ${bpr2} `)
          return
        }
        const resultsNodeId = bpr2.targets[0].targetId
        this.io.emit('pathtoidresult', { callid, nodeid: resultsNodeId })
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (translateBrowsePath): ' + err.message) // Display the error message first
        this.io.emit('error message', err.toString(), 'translateBrowsePath')
      }
    })()
  };

  /**
   *
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} nodeId The identity of the node to browse
   * @param {*} details set this to true if you want relations in both directions (browseDirection: Both)
   */
  browse (callid, nodeId, details = false) {
    (async () => {
      try {
        const io = this.io
        let nodeToBrowse
        // console.log('Browse details: '+details);
        if (details) {
          nodeToBrowse = {
            nodeId,
            includeSubtypes: true,
            nodeClassMask: 0,
            browseDirection: 'Both',
            referenceTypeId: 'References',
            resultMask: 63
          }
        } else {
          nodeToBrowse = nodeId
        }
        await this.session.browse(nodeToBrowse,
          function (err, browseResult) {
            if (!err) {
              // browse_result.references.forEach(function (reference) {
              // console.log(reference.browseName);
              // });
              io.emit('browseresult', {
                callid,
                browseresult: browseResult,
                nodeid: nodeId
              })
            };
          }
        )
      } catch (err) {
        console.log('FAIL Browse call: ' + err.message + err)
        this.io.emit('error message', err, 'browse')
      }
    })()
  }

  closeConnection (callback) {
    console.log('Closing')
    if (!this || !this.session || !this.client) {
      console.log('Already closed')
      return
    }

    this.session.close(function () {
      console.log('Session closed')
    })

    this.client.disconnect(function () { })
    console.log('Client disconnected')
  }

  // Subscribe to some value.      Not tested    Total Rewrite???
  addMonitor (callid, path) {
    const itemToMonitor = {
      nodeId: path,
      attributeId: this.AttributeIds.Value
    };

    (async () => {
      try {
        const parameters = {
          samplingInterval: 100,
          discardOldest: true,
          queueSize: 100
        }
        const monitoredItem = await this.subscription.monitor(itemToMonitor, parameters, TimestampsToReturn.Both)

        monitoredItem.on('changed', (dataValue) => {
          console.log('******************* dataValue.value.value.toString()')
          this.io.emit('object message', dataValue)
        })
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (subscribing): ' + err.message)
        this.displayFunction(err)
        this.io.emit('error message', err, 'subscribe')
      }
    })()
  }
}
