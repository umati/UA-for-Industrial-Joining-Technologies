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
import Settings from 'views/Servers/Settings.mjs'
import USDemo from 'views/Demo/USDemo.mjs'
import AssetGraphics from 'views/Assets/AssetGraphics.mjs'
import EntityCacheView from 'views/Entities/Entities.mjs'
import ConnectionGraphics from 'views/Connection/ConnectionGraphics.mjs'
import ResultGraphics from 'views/ComplexResult/ResultGraphics.mjs'
import TabGenerator from 'views/GraphicSupport/TabGenerator.mjs'
import BasicScreen from 'views/GraphicSupport/BasicScreen.mjs'

export default class EndpointGraphics extends BasicScreen {
  constructor (title) {
    super(title)
    this.endpointUrl = ''
  }

  close () {
    this.connectionManager.close()
  }

  activate (state) {

  }

  instantiate (endpointUrl, webSocketManager) {
    this.endpointUrl = endpointUrl
    // this.backGround.innerHTML = 'EndpointUrl: ' + endpointUrl
    // Setting up tab handling and model handling

    const entityCache = new EntityCache()

    const tabGenerator = new TabGenerator(this.backGround, 'TabSelector' + endpointUrl)
    const urlDiv = document.createElement('div')
    urlDiv.innerText = endpointUrl
    tabGenerator.setRightInfo(urlDiv)
    const modelManager = new ModelManager(entityCache)

    // Initiate the different tab handlers

    this.connectionManager = new ConnectionManager(webSocketManager, endpointUrl)
    const connectionGraphics = new ConnectionGraphics(this.connectionManager)
    tabGenerator.generateTab(connectionGraphics, true)

    const settings = new Settings(webSocketManager)

    const addressSpace = new AddressSpace(this.connectionManager)
    const addressSpaceGraphics = new AddressSpaceGraphics(addressSpace)

    const eventManager = new EventManager(this.connectionManager, modelManager)
    const eventGraphics = new EventGraphics(eventManager)

    const resultManager = new ResultManager(this.connectionManager, eventManager)

    const assets = new AssetManager(addressSpace, this.connectionManager)
    const assetGraphics = new AssetGraphics(assets)

    const traceGraphics = new TraceGraphics(['angle', 'torque'], addressSpace, resultManager)

    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace, settings, entityCache)

    const demoGraphics = new USDemo(methodManager, resultManager, this.connectionManager, settings)

    const resultGraphics = new ResultGraphics(resultManager)

    const entityCacheView = new EntityCacheView(entityCache)

    tabGenerator.generateTab(demoGraphics)
    tabGenerator.generateTab(traceGraphics)
    tabGenerator.generateTab(methodGraphics)
    tabGenerator.generateTab(eventGraphics, false)

    tabGenerator.generateTab(addressSpaceGraphics, false)
    tabGenerator.generateTab(resultGraphics)
    tabGenerator.generateTab(assetGraphics)
    tabGenerator.generateTab(entityCacheView)
    tabGenerator.generateTab(settings)
  }
}
