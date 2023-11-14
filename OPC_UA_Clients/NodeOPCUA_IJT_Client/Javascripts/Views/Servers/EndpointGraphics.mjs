/**
 * EndpointGraphics creates tabs for the different views for a given endpoint connection
 */
import {
  AddressSpace,
  AssetManager,
  MethodManager,
  EventManager,
  ResultManager,
  ModelManager,
  SocketHandler
} from 'ijt-support/ijt-support.mjs'

import TraceGraphics from 'views/Trace/TraceGraphics.mjs'
import ServerGraphics from 'views/Servers/ServerGraphics.mjs'
import AddressSpaceGraphics from 'views/AddressSpace/AddressSpaceGraphics.mjs'
import EventGraphics from 'views/Events/EventGraphics.mjs'
import MethodGraphics from 'views/Methods/MethodGraphics.mjs'
import AssetGraphics from 'views/Assets/AssetGraphics.mjs'
import TabGenerator from 'views/GraphicSupport/TabGenerator.mjs'
import BasicScreen from 'views/GraphicSupport/BasicScreen.mjs'

export default class EndpointGraphics extends BasicScreen {
  constructor (title) {
    super(title)
    this.endpointUrl = ''
    // this.backGround.style.border = '2px solid green'
  }

  activate (state) {

  }

  instantiate (endpointUrl, socket) {
    this.socket = socket
    this.endpointUrl = endpointUrl
    this.backGround.innerHTML = 'endp: ' + endpointUrl
    this.socketHandler = new SocketHandler(socket, endpointUrl)

    // mixing background and current tab content here

    const tabGenerator = new TabGenerator(this.backGround, 'TabSelector' + endpointUrl)
    const modelManager = new ModelManager()

    // Initiate the different tab handlers
    // var servers = new ServerGraphics(tabGenerator.generateTab('Servers'), socketHandler)

    const servers = new ServerGraphics()
    tabGenerator.generateTab(servers)

    const addressSpace = new AddressSpace(this.socketHandler)
    const addressSpaceGraphics = new AddressSpaceGraphics(addressSpace)
    tabGenerator.generateTab(addressSpaceGraphics, true)
    const eventManager = new EventManager(this.socketHandler)
    const eventGraphics = new EventGraphics(eventManager, modelManager)
    tabGenerator.generateTab(eventGraphics, false)
    const resultManager = new ResultManager(eventManager)
    const assets = new AssetManager(addressSpace, this.socketHandler)
    const asstetGraphics = new AssetGraphics(assets)
    tabGenerator.generateTab(asstetGraphics)
    const traceGraphics = new TraceGraphics(['angle', 'torque'], resultManager)
    tabGenerator.generateTab(traceGraphics)
    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace)
    tabGenerator.generateTab(methodGraphics)

    /* ****************  Set up socket listeners to handle input from server ******************/

    // Listen to the data from the server regarding the tree of queriable data and display it
    this.socketHandler.registerMandatory('browseresult', function (msg) { })

    // Listen to result data and convert it into a javascript model then display it
    this.socketHandler.registerMandatory('readresult', function (msg) { })

    // Listen to pathtoid data and convert it into a javascript model then display it
    this.socketHandler.registerMandatory('pathtoidresult', function (msg) { })

    // Listen to subscribed events messages
    this.socketHandler.registerMandatory('subscribed event', function (msg, context) {
      if (msg && msg.result.SourceName && msg.result.SourceName.value) {
        console.log('Subscribed event triggered: ' + msg.result.SourceName.value)
      } else {
        console.log('Event lacking SourceName received')
      }
      eventManager.receivedEvent(msg)
    })

    // Listen to subscribed events messages
    this.socketHandler.registerMandatory('callresult', function (msg) { })

    // Listen to status messages from Node-OPCUA
    this.socketHandler.registerMandatory('status message', function (msg) {
      servers.messageDisplay(msg)
    })

    // Listen to the tree of possible connection points (Available OPC UA servers)
    this.socketHandler.registerMandatory('connection points', function (msg) {
      servers.connectionPoints(JSON.parse(msg).connectionpoints, socket)
    })

    // Ask for the currently stored connectionpoints
    this.socket.emit('get connectionpoints')

    // Listen to connection
    this.socketHandler.registerMandatory('connection established', function (msg) {
      servers.messageDisplay('Connection established')
    })

    // Listen to general subscription start
    // Here you could add code to actually subscribe to fields
    this.socketHandler.registerMandatory('subscription created', function (msg) {
      servers.messageDisplay('Subscription created')
      tabGenerator.setState('subscribed')
      eventManager.reset()
      resultManager.activate()
      addressSpace.addressSpacePromise().then(() => {
        tabGenerator.setState('tighteningsystem')
      })
    })

    // Listen to session start
    this.socketHandler.registerMandatory('session established', function (msg) {
      servers.messageDisplay('Session established')
      addressSpace.initiate()
      addressSpaceGraphics.initiateNodeTree()
    })

    // Listen to session closure
    this.socketHandler.registerMandatory('session closed', function (msg) {
      servers.messageDisplay('Session closed')
    })

    // Listen to error messages
    this.socketHandler.registerMandatory('error message', function (msg) {
      console.log(msg.message)
      servers.messageDisplay(msg.message)
      tabGenerator.displayError(msg)
    })

    socket.emit('connect to', endpointUrl)

    window.onbeforeunload = function () {
      // socket.emit('terminate connection')
    }
  }
}
