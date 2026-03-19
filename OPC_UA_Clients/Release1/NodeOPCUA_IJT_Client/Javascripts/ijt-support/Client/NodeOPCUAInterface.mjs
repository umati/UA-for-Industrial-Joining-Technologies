import { promises as fs } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const connectionPointsPath = path.resolve(__dirname, '../../../Resources/connectionpoints.json')

/**
 * Support function to read a file
 * @param {*} filePath  the name of the file including file path
 * @returns the data in the file
 */
async function readFile (filePath) {
  try {
    const data = await fs.readFile(filePath)
    // console.log(data.toString())
    return data
  } catch (error) {
    console.error(`Got an error trying to read the file: ${error.message}`)
  }
}

/**
 * Support function to store a file
 * @param {*} filePath the name of the file including file path
 * @param {*} content the Content to be stored
 */
async function writeFile (filePath, content) {
  try {
    await fs.writeFile(filePath, content)
  } catch (error) {
    console.error(`Got an error trying to write the file: ${error.message}`)
  }
}

/**
 * A class that encapsulates the Websocket communication between the webpage
 * and the Node.js OPC UA implementation
 */
export class NodeOPCUAInterface {
  constructor (io, attributeIds) {
    console.log('Establishing interface')
    this.attributeIds = attributeIds
    this.io = io
    this.connectionList = {}
  }

  /**
   * Sets up the socket communication to listen to the calls from the webpage and direct them
   * to the applicable function
   * @param {*} OPCUAClient
   */
  setupSocketIO (OPCUAClient) {
    // This is the function used to display status messages comming from the server
    function displayFunction (msg) {
      // console.log(msg);
      console.log('status message: ' + msg)
      io.emit('status message', msg)
    }

    console.log('Establishing sockets')
    const io = this.io
    this.displayFunction = displayFunction
    this.OPCUAClient = OPCUAClient

    this.session = null

    io.on('connection', (socket) => {
      /* socket.on('subscribe item', (endpoint, callid, msg) => {
        this.addMonitor(endpoint, callid, msg)
      }) */

      socket.on('read', (endpoint, callid, msg, attribute) => {
        const connectionObject = this.connectionList[endpoint]
        if (!connectionObject) {
          return
        }
        connectionObject.read(callid, msg, attribute)
      })

      socket.on('browse', (endpoint, callid, nodeId, details) => {
        const connectionObject = this.connectionList[endpoint]
        if (!connectionObject) {
          return
        }

        connectionObject.browse(callid, nodeId, details)
      })

      socket.on('methodcall', (endpoint, callid, objectNode, methodNode, inputArgs) => {
        const connectionObject = this.connectionList[endpoint]
        if (!connectionObject) {
          return
        }
        connectionObject.methodCall(callid, objectNode, methodNode, inputArgs)
      })

      socket.on('pathtoid', (endpoint, callid, nodeId, path) => {
        const connectionObject = this.connectionList[endpoint]
        if (!connectionObject) {
          return
        }
        connectionObject.translateBrowsePath(callid, nodeId, path)
      })

      socket.on('terminate connection', (endpointUrl) => {
        console.log('**********************************************------------------------')
        console.log('Recieving terminate session request (' + endpointUrl + ')')
        const connectionObject = this.connectionList[endpointUrl]
        if (!connectionObject) {
          console.log('Nodejs OPC UA client failed to find EndpointUrl ' + endpointUrl + ' for termination')
          return
        }
        connectionObject.closeConnection()
        this.connectionList[endpointUrl] = null
      })

      socket.on('disconnect from', endpointUrl => {
        console.log('**********************************************------------------------')
        console.log('Nodejs OPC UA client attempting to disconnect from ' + endpointUrl)
        if (endpointUrl) {
          const connection = this.connectionList[endpointUrl]
          if (connection) {
            connection.closeConnection()
          }
          this.connectionList[endpointUrl] = null
        }
      })

      socket.on('get connectionpoints', () => {
        readFile(connectionPointsPath).then((filecontent) => {
          this.io.emit('connection points', filecontent?.toString() ?? '[]')
        })
      })

      socket.on('set connectionpoints', (connectionpoints) => {
        console.log(connectionpoints)
        void writeFile(connectionPointsPath, connectionpoints)
      })

      socket.on('connect to', endpointUrl => {
        console.log('**********************************************')
        console.log('Nodejs OPC UA client attempting to connect to ' + endpointUrl)
        if (endpointUrl) {
          const existingConnection = this.connectionList[endpointUrl]
          if (existingConnection && typeof existingConnection.isActive === 'function' && existingConnection.isActive()) {
            console.log('Skipping duplicate connect request for ' + endpointUrl)
            return
          }
          const newConnection = new Connection(endpointUrl, this.displayFunction, this.OPCUAClient, this.io, this.attributeIds)
          newConnection.setupClient()
          this.connectionList[endpointUrl] = newConnection
        }
      })

      socket.on('subscribe event', (endpoint, msg, subscriberDetails) => {
        // console.log('Nodejs OPC UA client attempting to subscribe to ' + msg)
        const connectionObject = this.connectionList[endpoint]
        if (!connectionObject) {
          return
        }
        if (msg) {
          connectionObject.eventSubscription(msg, this.displayFunction, this.OPCUAClient, subscriberDetails)
        }
      })
    })
  }
}

/**
 * An object to store a specific connection
 */
class Connection {
  constructor (endpointUrl, displayFunction, opcua, io, attributeIds) {
    this.endpointUrl = endpointUrl
    this.io = io
    this.displayFunction = displayFunction
    this.opcua = opcua
    this.attributeIds = attributeIds
    this.debugNr = 0
    this.eventMonitoringItems = []
    this.connectionState = 'idle'
    this._closingPromise = null
  }

  isActive () {
    return this.connectionState === 'connecting' || this.connectionState === 'connected'
  }

  /**
   * Create the actual connection
   */
  setupClient () {
    if (this.isActive()) {
      console.log('Ignoring duplicate setupClient call for ' + this.endpointUrl)
      return
    }
    const io = this.io
    const endpointUrl = this.endpointUrl
    const preferredEndpointUrl = endpointUrl
    const connectRetries = Number(process.env.OPCUA_CONNECT_RETRIES ?? 3)
    const connectDelaySec = Number(process.env.OPCUA_CONNECT_DELAY_SEC ?? 0.5)
    const connectMaxDelaySec = Number(process.env.OPCUA_CONNECT_MAX_DELAY_SEC ?? 2)
    const client = this.opcua.OPCUAClient.create({
      endpointMustExist: false,
      connectionStrategy: {
        maxRetry: connectRetries,
        initialDelay: Math.max(0.1, connectDelaySec) * 1000,
        maxDelay: Math.max(0.2, connectMaxDelaySec) * 1000
      }
    })
    this.connectionState = 'connecting'
    this.client = client
    this.endpointUrl = endpointUrl

    client.on('backoff', (retryCount, delay) => {
      console.log(`Retry ${retryCount}: reconnecting to ${preferredEndpointUrl} in ${delay} ms`)
    })

    ;(async () => {
      try {
        console.log('Attempting to establish connection to ' + preferredEndpointUrl)
        await client.connect(preferredEndpointUrl)
        console.log('Connection established to endpoint ' + preferredEndpointUrl)
        io.emit('connection established', { endpointurl: endpointUrl })

        this.session = await client.createSession()
        console.log('*************** Session established. (' + preferredEndpointUrl + ')')
        io.emit('session established', { endpointurl: endpointUrl })

        const parameters = {
          maxNotificationsPerPublish: 10,
          priority: 10,
          publishingEnabled: true,
          requestedLifetimeCount: 1000,
          requestedMaxKeepAliveCount: 12,
          requestedPublishingInterval: 2000
        }
        this.subscription = await this.session.createSubscription2(parameters)
        console.log('Subscription established. (' + preferredEndpointUrl + ')')
        io.emit('subscription created', { endpointurl: endpointUrl })

        console.log('Handling Datatypes')
        io.emit('datatypes', { endpointurl: endpointUrl, datatype: this.opcua.DataType })

        const namespaces = await this.session.readNamespaceArray()
        console.log('Handling NameSpaces')
        io.emit('namespaces', { endpointurl: endpointUrl, namespaces })

        this.connectionState = 'connected'
        console.log('Connection and session established.')
      } catch (err) {
        this.connectionState = 'error'
        console.log('Failure during establishing connection to OPC UA server ', err)
        this.io.emit('error message', { error: err, context: 'connection', message: err.message, endpointUrl })
      }
    })()
  }

  /**
   * Read the content of a node
   * The result is communicated to the webpage  over the io socket using 'readresult'
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} nodeId The identity of the node to read
   * @param {*} attribute The attribute to read. Default is 'DisplayName'
   */
  read (callid, nodeId, attribute) {
    (async () => {
      try {
        if (!attribute) {
          attribute = 'DisplayName'
        }
        const dataValue = await this.session.read({
          nodeId,
          attributeId: this.attributeIds[attribute]
        })

        const result = dataValue.value.value
        if (result && result.resultContent) {
          await this.opcua.promoteOpaqueStructure(this.session, [{ value: result.resultContent }])
        }

        this.io.emit('readresult', { endpointurl: this.endpointUrl, callid, dataValue, stringValue: dataValue.toString(), nodeid: nodeId, attribute })
        return dataValue
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (reading): ' + err.message) // Display the error message first
        this.io.emit('error message', { error: err, context: 'read', message: err.message, endpointurl: this.endpointUrl })
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
        const bpr2 = await this.session.translateBrowsePath(this.opcua.makeBrowsePath(nodeId, path))

        if (bpr2.statusCode !== this.opcua.StatusCodes.Good) {
          console.log(`Cannot find the ${nodeId} object.  ${path} `)
          return
        }
        const resultsNodeId = bpr2.targets[0].targetId

        this.io.emit('pathtoidresult', { endpointurl: this.endpointUrl, callid, nodeid: resultsNodeId })
      } catch (err) {
        this.displayFunction('Node.js OPC UA client error (translateBrowsePath): ' + err.message) // Display the error message first
        // this.io.emit('error message', err.toString(), 'translateBrowsePath')
        this.io.emit('error message', { error: err, context: 'translateBrowsePath', message: err.message })
      }
    })()
  }

  /**
   * Browse the content of a node
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} nodeId The identity of the node to browse
   * @param {*} details set this to true if you want relations in both directions (browseDirection: Both)
   */
  browse (callid, nodeId, details = false) {
    (async () => {
      try {
        const io = this.io
        const endpointurl = this.endpointUrl
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
                endpointurl,
                callid,
                browseresult: browseResult,
                nodeid: nodeId,
                details
              })
            };
          }
        )
      } catch (err) {
        console.log('************  FAIL Browse call: ' + err.message + err)
        this.io.emit('error message', { error: err, context: 'browse', message: err.message, endpointurl: this.endpointUrl })
      }
    })()
  }

  /**
   * Call a given method
   * @param {*} callid A unique identifier to match a query to OPC UA with a response
   * @param {*} methodToCall The information about the method to call
   */
  methodCall (callid, objectNode, methodNode, inputArguments) {
    (async () => {
      const theSession = this.session
      try {
        const io = this.io
        const objectId = this.opcua.coerceNodeId(objectNode) // SERVER
        const methodId = this.opcua.coerceNodeId(methodNode) // GetMonitoredItems

        const methodToCall2 = {
          objectId,
          methodId,
          inputArguments
        }

        theSession.call(methodToCall2, (err, results) => {
          if (err) {
            console.log('************  FAIL Method call (in callback): ' + err)
          } else {
            // console.log('Callresult: ' + results)

            io.emit('callresult', {
              endpointurl: this.endpointUrl,
              callid,
              results
            })
          }
        })
      } catch (err) {
        console.log('************ FAIL method call: ' + err)
        this.io.emit('error message', { error: err, context: 'method', message: err.message })
      }
    })()
  }

  /**
   * Close a connection and clean everything up
   */
  async closeConnection () {
    if (this._closingPromise) {
      return this._closingPromise
    }

    const settleCallback = (fn) => new Promise((resolve) => {
      try {
        fn(() => resolve())
      } catch {
        resolve()
      }
    })

    this._closingPromise = (async () => {
      this.connectionState = 'closing'

      try {
        console.log('Terminate eventmonitoring')
        for (const monitor of this.eventMonitoringItems) {
          await settleCallback((done) => monitor.terminate(done))
          console.log('Eventmonitoring terminated ' + this.endpointUrl)
        }
      } catch (err) {
        console.log('************ FAIL to close down EventMonitor: ' + err)
        this.io.emit('error message', { error: err, context: 'closedown', message: err.message })
      } finally {
        this.eventMonitoringItems = []
      }

      try {
        console.log('Unsubscribe')
        if (this.subscription) {
          await this.subscription.terminate()
          console.log('Unsubscribed')
        }
      } catch (err) {
        console.log('************ FAIL to unsubscribe: ' + err)
        this.io.emit('error message', { error: err, context: 'closedown', message: err.message })
      } finally {
        this.subscription = null
      }

      try {
        console.log('Closing session')
        if (this.session) {
          await this.session.close(true)
          console.log('Session closed')
        } else {
          console.log('Session already closed')
        }
      } catch (err) {
        console.log('************ FAIL to close session: ' + err)
        this.io.emit('error message', { error: err, context: 'closedown', message: err.message })
      } finally {
        this.session = null
      }

      try {
        console.log('Disconnect client. (' + this.endpointUrl + ')')
        if (this.client) {
          await this.client.disconnect()
        }
      } catch (err) {
        console.log('************ FAIL to disconnect client: ' + err)
        this.io.emit('error message', { error: err, context: 'closedown', message: err.message })
      } finally {
        this.client = null
      }

      this.connectionState = 'closed'
      console.log('Client disconnected.\n=========================================')
      this.io.emit('client disconnected', { endpointurl: this.endpointUrl })
    })()

    return this._closingPromise
  }

  /**
   * Subscribe to an event
   * @param {*} fields The fields you want to subscribe to
   * @param {*} subscriberDetails contains a string that is carried over into the responses of the subscription
   */
  async eventSubscription (fields, subscriberDetails) {
    const serverObjectId = 'i=2253'
    const eventFilter = this.opcua.constructEventFilter(fields)

    // const subscribeDebugNr = this.debugNr++

    const eventMonitoringItem = this.opcua.ClientMonitoredItem.create(
      this.subscription,
      {
        attributeId: this.attributeIds.EventNotifier,
        nodeId: serverObjectId
      },
      {
        discardOldest: true,
        filter: eventFilter,
        queueSize: 100000
      }
    )

    console.log('eventsubscription reached ')

    eventMonitoringItem.on('initialized', () => {
      console.log('event_monitoringItem initialized (' + fields + ')')
    })

    console.log('================= 3')

    eventMonitoringItem.on('changed', (events) => {
      (async () => {
        try {
          if (this.connectionState !== 'connected') {
            return
          }
          console.log('================= RECIEVED EVENT')
          for (let i = 0; i < events.length; i++) {
            // console.log('================= LOOPING OVER ARGUMENTS ' + i)
            // console.log('FIELD: ' + fields[i], '=', events[i].toString())
            // console.log(events[i].value.resultContent)

            if (fields[i] === 'Result') {
              // console.log('=================================================')
              // console.log('======EVENT RESULT VALUE' + events[i].value)
              // console.log('=================================================')
              if (events[i] && events[i].value) {
                await this.opcua.promoteOpaqueStructure(this.session, [{ value: events[i].value }])
              }
              // console.log('------------ Opaque structure promoted')
              // console.log(events[i].value)
            }
            // this.io.emit('subscribed event', { field: fields[i], value: events[i].value, stringValue: events[i].toString() })
          }
          const result = {}
          for (let i = 0; i < events.length; i++) {
            result[fields[i]] = events[i]
          }
          result.subscriberDetails = subscriberDetails
          // console.log('eventsubscription triggered  (' + this.endpointUrl + ')')
          this.io.emit('subscribed event', { endpointurl: this.endpointUrl, result })
        } catch (err) {
          this.displayFunction('Node.js OPC UA client error (eventMonitoring): ' + err.message) // Display the error message first
          this.io.emit('error message', { error: err, context: 'eventMonitoring', message: err.message, endpointurl: this.endpointUrl }) // (Then for debug purposes display all of it)
        }
      })()
    })

    this.eventMonitoringItems.push(eventMonitoringItem)
  }
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
