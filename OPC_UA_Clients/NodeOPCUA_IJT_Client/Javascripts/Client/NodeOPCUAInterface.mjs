import async from 'async'

import {
  AttributeIds,
  promoteOpaqueStructure,
  makeBrowsePath,
  StatusCodes,
  // TimestampsToReturn,
  constructEventFilter,
  ClientMonitoredItem,
  DataType,
  coerceNodeId
  // resolveNodeId,
  // ObjectIds
} from 'node-opcua'

export default class NodeOPCUAInterface {
  constructor (io, attributeIds) {
    console.log('Establishing interface')
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
    console.log('Establishing sockets')
    const io = this.io
    this.displayFunction = displayFunction
    this.OPCUAClient = OPCUAClient
    this.endpointUrls = endpointUrls
    this.session = null

    io.on('connection', (socket) => {
      socket.on('subscribe item', (callid, msg) => {
        this.addMonitor(callid, msg)
      })
      socket.on('read', (callid, msg) => {
        this.read(callid, msg)
      })

      socket.on('browse', (callid, nodeId, details) => {
        this.browse(callid, nodeId, details)
      })

      socket.on('methodcall', (callid, objectNode, methodNode, inputArgs) => {
        this.methodCall(callid, objectNode, methodNode, inputArgs)
      })

      socket.on('pathtoid', (callid, nodeId, path) => {
        this.translateBrowsePath(callid, nodeId, path)
      })

      socket.on('terminate connection', () => {
        console.log('Recieving terminate session request')
        this.closeConnection()
      })

      socket.on('connect to', msg => {
        console.log('Nodejs OPC UA client attempting to connect to ' + msg)
        if (msg) {
          this.setupClient(msg, this.displayFunction, this.OPCUAClient, this.io)
        }
      })

      socket.on('subscribe event', msg => {
        // console.log('Nodejs OPC UA client attempting to subscribe to ' + msg)
        if (msg) {
          this.eventSubscription(msg, this.displayFunction, this.OPCUAClient)
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
      // ----------------------------------------------------------------------------------
      // create connection
      // ----------------------------------------------------------------------------------
      function (callback) {
        console.log('Establishing connection')
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
      // ----------------------------------------------------------------------------------
      // create session
      // ----------------------------------------------------------------------------------
      function (callback) {
        client.createSession(function (err, session) {
          if (!err) {
            thisContainer.session = session
            console.log('Session established.')
            io.emit('session established')
          }
          callback(err)
        })
      },
      // ----------------------------------------------------------------------------------
      // create subscription (on events)
      // ----------------------------------------------------------------------------------
      function (callback) {
        const parameters = {
          maxNotificationsPerPublish: 10,
          priority: 10,
          publishingEnabled: true,
          requestedLifetimeCount: 1000,
          requestedMaxKeepAliveCount: 12,
          requestedPublishingInterval: 2000
        }
        thisContainer.session.createSubscription2(parameters, function (err, subscription) {
          if (!err) {
            thisContainer.subscription = subscription

            console.log('Subscription established')
            io.emit('subscription created')
          }
          callback(err)
        })
      },
      function (callback) { // DataTypes
        console.log('Handling Datatypes')
        io.emit('datatypes', DataType)
        callback()
      },
      function (callback) { // Namespaces
        thisContainer.session.readNamespaceArray((err, namespaces) => {
          if (err) {
            throw new Error(err)
          }
          console.log('Handling NameSpaces')
          io.emit('namespaces', namespaces)
          callback(err)
        })
      }
    ],
    function (err) {
      if (err) {
        console.log('Failure during establishing connection to OPC UA server ', err)
        // this.io.emit('error message', err.toString(), 'connection')
        this.io.emit('error message', { error: err, context: 'connection', message: err.message })
        process.exit(0)
      } else {
        console.log('Connection and session established.')
      }
    })
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
        // this.io.emit('error message', err.toString(), 'read') // (Then for debug purposes display all of it)
        this.io.emit('error message', { error: err, context: 'read', message: err.message })
      }
    })()
  }

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
        const bpr2 = await this.session.translateBrowsePath(makeBrowsePath(nodeId, path))

        // console.log(`XXX ${nodeId} object.  ${path} `)

        if (bpr2.statusCode !== StatusCodes.Good) {
          console.log(`Cannot find the ${nodeId} object.  ${path} `)
          return
        }
        const resultsNodeId = bpr2.targets[0].targetId
        this.io.emit('pathtoidresult', { callid, nodeid: resultsNodeId })
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (translateBrowsePath): ' + err.message) // Display the error message first
        // this.io.emit('error message', err.toString(), 'translateBrowsePath')
        this.io.emit('error message', { error: err, context: 'translateBrowsePath', message: err.message })
      }
    })()
  }

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
        const nodeToBrowse = {
          nodeId,
          includeSubtypes: true,
          nodeClassMask: 0,
          referenceTypeId: 'References',
          resultMask: 63
        }
        if (details) {
          nodeToBrowse.browseDirection = 'Both'
        }
        await this.session.browse(nodeToBrowse,
          function (err, browseResult) {
            if (!err) {
              // browse_result.references.forEach(function (reference) {
              // console.log(reference.browseName);
              // });
              // console.log(nodeId)
              // console.log(browseResult)
              io.emit('browseresult', {
                callid,
                browseresult: browseResult,
                nodeid: nodeId,
                details
              })
            };
          }
        )
      } catch (err) {
        console.log('FAIL Browse call: ' + err.message + err)
        this.io.emit('error message', { error: err, context: 'browse', message: err.message })
      }
    })()
  }

  /**
   *
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} methodToCall The information about the method to call
   */
  methodCall (callid, objectNode, methodNode, inputArguments) {
    (async () => {
      const theSession = this.session
      try {
        const io = this.io
        const objectId = coerceNodeId(objectNode) // SERVER
        const methodId = coerceNodeId(methodNode) // GetMonitoredItems

        const methodToCall2 = {
          objectId,
          methodId,
          inputArguments
        }

        theSession.call(methodToCall2, (err, results) => {
          if (err) {
            console.log('FAIL Method call (in callback): ' + err)
          } else {
            io.emit('callresult', {
              callid,
              results
            })
          }
        })
      } catch (err) {
        console.log('FAIL method call: ' + err)
        this.io.emit('error message', { error: err, context: 'method', message: err.message })
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

  /*
  // Subscribe to some value.      Not tested    Total Rewrite???
  addMonitor (callid, path) {
    const itemToMonitor = {
      nodeId: path,
      attributeId: this.AttributeIds.Value
    }

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

  async function main () {
    const client = OPCUAClient.create({})

    const endpointUrl = 'opc.tcp://opcua.demo-this.com:62544/Quickstarts/AlarmConditionServer'

    const subscriptionParamters = {
      requestedPublishingInterval: 1000,
      maxNotificationsPerPublish: 100,
      publishingEnabled: true,
      priority: 10
    } */

  async eventSubscription (msg) {
    // const baseEventTypeId = 'i=2041'
    const serverObjectId = 'i=2253'

    const fields = [
      'EventId',
      'EventType',
      'SourceNode',
      'SourceName',
      'Time',
      'ReceiveTime',
      'Message',
      'Severity',
      'Result'

    ]
    const eventFilter = constructEventFilter(fields)

    const eventMonitoringItem = ClientMonitoredItem.create(
      this.subscription,
      {
        attributeId: AttributeIds.EventNotifier,
        nodeId: serverObjectId
      },
      {
        discardOldest: true,
        filter: eventFilter,
        queueSize: 100000
      }
    )

    eventMonitoringItem.on('initialized', () => {
      console.log('event_monitoringItem initialized (' + msg + ')')
    })

    eventMonitoringItem.on('changed', (events) => {
      (async () => {
        try {
          for (let i = 0; i < events.length; i++) {
            // console.log(fields[i], '=', events[i].toString())
            // console.log(events[i].value.resultContent)

            if (fields[i] === 'Result') {
              if (events[i] && events[i].value && events[i].value.resultContent) {
                await promoteOpaqueStructure(this.session, [{ value: events[i].value.resultContent }])
              }
            }

            // this.io.emit('subscribed event', { field: fields[i], value: events[i].value, stringValue: events[i].toString() })
            // console.log(events[i].value)
          }
          const result = {}
          for (let i = 0; i < events.length; i++) {
            result[fields[i]] = events[i]
          }
          this.io.emit('subscribed event', result)
        } catch (err) {
          this.displayFunction('Node.js OPC UA client error (eventMonitoring): ' + err.message) // Display the error message first
          // this.io.emit('error message', err.toString(), 'eventMonitoring')
          this.io.emit('error message', { error: err, context: 'eventMonitoring', message: err.message }) // (Then for debug purposes display all of it)
        }
      })()
    })

    await new Promise((resolve) => process.once('SIGINT', resolve))
  }
}
