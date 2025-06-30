/**
 * EndpointGraphics  creates the graphics with tabs for the various ways to interact with the OPC UA server
 */
import {
  AddressSpace,
  AssetManager,
  MethodManager,
  EventManager,
  ResultManager,
  ModelManager,
  ConnectionManager,
  EntityCache
} from 'ijt-support/ijt-support.mjs'

import TraceGraphics from 'views/Trace/TraceGraphics.mjs'
import AddressSpaceGraphics from 'views/AddressSpace/AddressSpaceGraphics.mjs'
import EventGraphics from 'views/Events/EventGraphics.mjs'
import MethodGraphics from 'views/Methods/MethodGraphics.mjs'
import USDemo from 'views/Demo/USDemo.mjs'
import AssetGraphics from 'views/Assets/AssetGraphics.mjs'
import EntityCacheView from 'views/Entities/Entities.mjs'
import ConnectionGraphics from 'views/Connection/ConnectionGraphics.mjs'
import ResultGraphics from 'views/ComplexResult/ResultGraphics.mjs'
import TabGenerator from 'views/GraphicSupport/TabGenerator.mjs'
import BasicScreen from 'views/GraphicSupport/BasicScreen.mjs'
//import EnvelopeScreen from 'views/Envelope/EnvelopeGraphics.mjs'

export default class EndpointGraphics extends BasicScreen {
  constructor (title, settings) {
    super(title)
    this.endpointUrl = ''
    this.tabGenerator = null
    this.settings = settings
  }

  close () {
    this.connectionManager.close()
  }

  activate (state) {

  }

  changeViewLevel (newLevel) {
    this.tabGenerator.changeViewLevel(newLevel)
  }

  instantiate (endpointUrl, webSocketManager) {
    this.endpointUrl = endpointUrl

    // Setting up tab handling and model handling

    const entityCache = new EntityCache()

    const tabGenerator = new TabGenerator(this.backGround, 3) // XXXXXXX
    this.tabGenerator = tabGenerator
    const urlDiv = document.createElement('div')
    urlDiv.innerText = endpointUrl
    tabGenerator.setRightInfo(urlDiv)

    const modelManager = new ModelManager(entityCache)

    // Initiate the different tab handlers

    this.connectionManager = new ConnectionManager(webSocketManager, endpointUrl)
    const connectionGraphics = new ConnectionGraphics(this.connectionManager)

    const addressSpace = new AddressSpace(this.connectionManager)
    const addressSpaceGraphics = new AddressSpaceGraphics(addressSpace)

    const eventManager = new EventManager(this.connectionManager, modelManager)
    const eventGraphics = new EventGraphics(eventManager)

    const resultManager = new ResultManager(eventManager)

    const assets = new AssetManager(addressSpace, this.connectionManager)
    const assetGraphics = new AssetGraphics(assets)

    const traceGraphics = new TraceGraphics(['angle', 'torque'], addressSpace, resultManager)

    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace, this.settings, entityCache)

    const demoGraphics = new USDemo(methodManager, resultManager, this.connectionManager, this.settings)

    const resultGraphics = new ResultGraphics(resultManager)

    const entityCacheView = new EntityCacheView(entityCache)

    let envelopeScreen = null
    if (this.settings.envelope) {
      envelopeScreen = new EnvelopeScreen(this.connectionManager, resultManager, this.settings)
    }

    tabGenerator.generateTab(connectionGraphics, 2)
    tabGenerator.generateTab(demoGraphics, 1)
    tabGenerator.generateTab(traceGraphics, 2)
    tabGenerator.generateTab(methodGraphics, 2)
    tabGenerator.generateTab(eventGraphics, 2, false)

    tabGenerator.generateTab(addressSpaceGraphics, 3, false)
    tabGenerator.generateTab(resultGraphics, 4)
    tabGenerator.generateTab(assetGraphics, 5)
    tabGenerator.generateTab(entityCacheView, 3)
    if (envelopeScreen) {
      tabGenerator.generateTab(envelopeScreen, 3)
    }

    tabGenerator.changeViewLevel(2)
  }
}
