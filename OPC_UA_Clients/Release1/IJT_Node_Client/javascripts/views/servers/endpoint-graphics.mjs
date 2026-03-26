/**
 * EndpointGraphics creates the graphics with tabs for the various ways to interact with the OPC UA server
 */
import {
  AddressSpace,
  MethodManager,
  EventManager,
  ResultManager,
  ModelManager,
  ConnectionManager,
  ijtLog
} from 'ijt-support/ijt-support.mjs'

import TraceGraphics from 'views/trace/trace-graphics.mjs'
import AddressSpaceGraphics from 'views/address-space/address-space-graphics.mjs'
import EventGraphics from 'views/events/event-graphics.mjs'
import MethodGraphics from 'views/methods/method-graphics.mjs'
import ConnectionGraphics from 'views/connection/connection-graphics.mjs'
import TabGenerator from 'views/graphic-support/tab-generator.mjs'
import BasicScreen from 'views/graphic-support/basic-screen.mjs'

export default class EndpointGraphics extends BasicScreen {
  constructor (title) {
    super(title)
    this.endpointUrl = ''
  }

  close () {
    this.connectionManager.close()
  }

  activate () {}

  instantiate (endpointUrl, socket) {
    this.socket = socket
    this.endpointUrl = endpointUrl
    this.backGround.innerHTML = 'EndpointUrl: ' + endpointUrl

    // Setting up tab handling and model handling

    const tabGenerator = new TabGenerator(this.backGround, 'TabSelector' + endpointUrl)
    const modelManager = new ModelManager()

    // Initiate the different tab handlers

    this.connectionManager = new ConnectionManager(socket, endpointUrl)
    const connectionGraphics = new ConnectionGraphics(this.connectionManager)
    tabGenerator.generateTab(connectionGraphics, true)

    const addressSpace = new AddressSpace(this.connectionManager)
    const addressSpaceGraphics = new AddressSpaceGraphics(addressSpace)
    tabGenerator.generateTab(addressSpaceGraphics, false)

    const eventManager = new EventManager(this.connectionManager)
    const eventGraphics = new EventGraphics(eventManager, modelManager)
    tabGenerator.generateTab(eventGraphics, false)

    const resultManager = new ResultManager(this.connectionManager, eventManager)

    // const assets = new AssetManager(addressSpace, this.connectionManager)
    // const assetGraphics = new AssetGraphics(assets)
    // tabGenerator.generateTab(assetGraphics)

    const traceGraphics = new TraceGraphics(['angle', 'torque'], addressSpace, resultManager)
    tabGenerator.generateTab(traceGraphics)

    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace)
    tabGenerator.generateTab(methodGraphics)

    /* ****************  Set up socket listeners to handle input from server ******************/

    // Listen to error messages
    this.connectionManager.socketHandler.registerMandatory('error message', function (msg) {
      ijtLog.info(msg.message)
      tabGenerator.displayError(msg)
    })
  }
}
