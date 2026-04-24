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
  EntityCache,
  JointManager,
  ijtLog
} from 'ijt-support/ijt-support.mjs'

import TraceGraphics from 'views/trace/trace-graphics.mjs'
import ResultGraphics from 'views/complex-result/result-graphics.mjs'
import AddressSpaceGraphics from 'views/address-space/address-space-graphics.mjs'
import EventGraphics from 'views/events/event-graphics.mjs'
import MethodGraphics from 'views/methods/method-graphics.mjs'
import AssetGraphics from 'views/assets/asset-graphics.mjs'
import EntityCacheView from 'views/entities/entities.mjs'
import ConnectionGraphics from 'views/connection/connection-graphics.mjs'
import TabGenerator from 'views/graphic-support/tab-generator.mjs'
import BasicScreen from 'views/graphic-support/basic-screen.mjs'
import { createDemoTabs } from 'views/tab-setup/demo-tabs.mjs'
import { createDetailsTabs } from 'views/tab-setup/details-tabs.mjs'

/** Default view level shown when a new endpoint tab is opened (Detailed = 3). */
const DEFAULT_VIEW_LEVEL = 3

export default class EndpointGraphics extends BasicScreen {
  constructor (title, settings) {
    super(title)
    this.tabHelpText = 'Workspace for this endpoint. Open connection status, methods, events, traces, demos, and data views.'
    this.endpointUrl = ''
    this.tabGenerator = null
    this.settings = settings
  }

  close () {
    this.connectionManager.close()
  }

  activate () {

  }

  changeViewLevel (newLevel) {
    this.tabGenerator.changeViewLevel(newLevel)
  }

  async loadOptionalEnvelopeTab (tabGenerator, resultManager, methodManager, addressSpace) {
    const modulePath = '/src/javascripts/views/envelope/ui/envelope-graphics.mjs'
    try {
      const { default: EnvelopeScreen } = await import(modulePath)
      if (EnvelopeScreen) {
        const envelopeScreen = new EnvelopeScreen(
          this.connectionManager,
          resultManager,
          this.settings,
          methodManager,
          addressSpace
        )
        tabGenerator.generateTab(envelopeScreen, 2, true)
      }
    } catch (error) {
      // Envelope view is optional. Skip quietly if unavailable.
      ijtLog.warn('Optional Envelope tab unavailable:', error)
    }
  }

  instantiate (endpointUrl, webSocketManager) {
    this.endpointUrl = endpointUrl

    // Setting up tab handling and model handling
    const entityCache = new EntityCache()
    const jointManager = new JointManager()

    const tabGenerator = new TabGenerator(this.backGround, DEFAULT_VIEW_LEVEL)
    this.tabGenerator = tabGenerator
    const urlDiv = document.createElement('div')
    urlDiv.innerText = endpointUrl
    tabGenerator.setRightInfo(urlDiv)

    const modelManager = new ModelManager(entityCache, jointManager)

    // Initiate the different tab handlers

    this.connectionManager = new ConnectionManager(webSocketManager, endpointUrl)
    const connectionGraphics = new ConnectionGraphics(this.connectionManager)

    const addressSpace = new AddressSpace(this.connectionManager)
    const addressSpaceGraphics = new AddressSpaceGraphics(addressSpace)

    const eventManager = new EventManager(this.connectionManager, modelManager)
    const eventGraphics = new EventGraphics(eventManager)

    const resultManager = new ResultManager(eventManager, this.settings)

    // Asset view is not critical
    let assetGraphics = null
    try {
      const assets = new AssetManager(addressSpace, this.connectionManager)
      assetGraphics = new AssetGraphics(assets)
    } catch (error) {
      ijtLog.error(error)
    }

    const methodManager = new MethodManager(addressSpace)
    const methodGraphics = new MethodGraphics(methodManager, addressSpace, this.settings, entityCache)

    // Optional local-only tab: load if module exists, otherwise skip silently.
    this.loadOptionalEnvelopeTab(tabGenerator, resultManager, methodManager, addressSpace)

    // Trace view is not critical
    let traceGraphics = null
    try {
      traceGraphics = new TraceGraphics(['angle', 'torque'], addressSpace, resultManager)
    } catch (error) {
      ijtLog.error(error)
    }

    // Consolidated result view is not critical
    let resultGraphics = null
    try {
      resultGraphics = new ResultGraphics(resultManager, methodManager, addressSpace, eventManager, this.settings)
    } catch (error) {
      ijtLog.error(error)
    }

    // Entity view is not critical
    let entityCacheView = null
    try {
      entityCacheView = new EntityCacheView(entityCache)
    } catch (error) {
      ijtLog.error(error)
    }

    tabGenerator.changeViewLevel(2)

    const demosTabGraphics = createDemoTabs({
      methodManager,
      resultManager,
      connectionManager: this.connectionManager,
      addressSpace,
      settings: this.settings,
      currentViewLevel: DEFAULT_VIEW_LEVEL
    })
    const detailsTabGraphics = createDetailsTabs({
      entityCacheView,
      assetGraphics,
      currentViewLevel: DEFAULT_VIEW_LEVEL
    })

    tabGenerator.generateTab(connectionGraphics, 2)
    if (demosTabGraphics) {
      tabGenerator.generateTab(demosTabGraphics, 2, true)
    }

    tabGenerator.generateTab(methodGraphics, 2)
    tabGenerator.generateTab(eventGraphics, 2, false)

    if (traceGraphics) {
      tabGenerator.generateTab(traceGraphics, 2)
    }
    if (resultGraphics) {
      tabGenerator.generateTab(resultGraphics, 2)
    }

    tabGenerator.generateTab(addressSpaceGraphics, 3, false)
    if (detailsTabGraphics) {
      tabGenerator.generateTab(detailsTabGraphics, 3)
    }

    // Joints tab intentionally hidden.
  }
}
