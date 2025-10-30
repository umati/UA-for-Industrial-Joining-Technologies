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
import JointDemo from 'views/Demo/JointDemo.mjs'
import AssetGraphics from 'views/Assets/AssetGraphics.mjs'
import EntityCacheView from 'views/Entities/Entities.mjs'
import ConnectionGraphics from 'views/Connection/ConnectionGraphics.mjs'
import ResultGraphics from 'views/ComplexResult/ResultGraphics.mjs'
import TabGenerator from 'views/GraphicSupport/TabGenerator.mjs'
import BasicScreen from 'views/GraphicSupport/BasicScreen.mjs'

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

    // Dynamic load
    import('../Envelope/EnvelopeGraphics.mjs')
      .then((EnvelopeScreen) => {
        try {
          const envelopeScreen = new EnvelopeScreen.Envelope(this.connectionManager, resultManager, this.settings)
          tabGenerator.generateTab(envelopeScreen, 3, true)
        } catch (error) {
          console.log(error)
        }
      })
      .catch((err) => {
        console.log(err)
      })

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

    // Asset view is not critical
    let assetGraphics = null
    try {
      const assets = new AssetManager(addressSpace, this.connectionManager)
      assetGraphics = new AssetGraphics(assets)
    } catch (error) {
      console.log(error)
    }

    // Trace view is not critical
    let traceGraphics = null
    try {
      traceGraphics = new TraceGraphics(['angle', 'torque'], addressSpace, resultManager)
    } catch (error) {
      console.log(error)
    }

    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace, this.settings, entityCache)

    // USDemo view is not critical
    let demoGraphics = null
    try {
      demoGraphics = new USDemo(methodManager, resultManager, this.connectionManager, this.settings)
    } catch (error) {
      console.log(error)
    }

    // JointDemo view is not critical
    let jointDemoGraphics = null
    try {
      jointDemoGraphics = new JointDemo(methodManager, resultManager, this.connectionManager, this.settings)
    } catch (error) {
      console.log(error)
    }

    // Consolidated view is not critical
    let resultGraphics = null
    try {
      resultGraphics = new ResultGraphics(resultManager)
    } catch (error) {
      console.log(error)
    }

    // Entity view is not critical
    let entityCacheView = null
    try {
      entityCacheView = new EntityCacheView(entityCache)
    } catch (error) {
      console.log(error)
    }

    tabGenerator.changeViewLevel(2)

    tabGenerator.generateTab(connectionGraphics, 2)
    if (demoGraphics) {
      tabGenerator.generateTab(demoGraphics, 1)
    }
    if (jointDemoGraphics) {
      tabGenerator.generateTab(jointDemoGraphics, 1)
    }

    if (traceGraphics) {
      tabGenerator.generateTab(traceGraphics, 2)
    }
    tabGenerator.generateTab(methodGraphics, 2)
    tabGenerator.generateTab(eventGraphics, 2, false)

    tabGenerator.generateTab(addressSpaceGraphics, 3, false)
    if (resultGraphics) {
      tabGenerator.generateTab(resultGraphics, 4)
    }
    if (assetGraphics) {
      tabGenerator.generateTab(assetGraphics, 5)
    }
    if (entityCacheView) {
      tabGenerator.generateTab(entityCacheView, 3)
    }
  }
}
