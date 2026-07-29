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
import {
  initializeEndpointTabState,
  markEndpointTabClosing,
  setEndpointTabState
} from './endpoint-tab-state.mjs'

/** Default view level shown when a new endpoint tab is opened (Detailed = 3). */
const DEFAULT_VIEW_LEVEL = 3
const ENVELOPE_EXPORT_REQUEST_COMMAND = 'run envelope limits export'
const ENVELOPE_EXPORT_RESPONSE_COMMAND = 'run envelope limits export result'
const ENVELOPE_EXPORT_TIMEOUT_MS = 20_000

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

  bindEndpointTab (tab) {
    const button = tab?.button
    const states = this.connectionManager?.CONNECTION_STATES
    if (!button || !states) {
      return
    }

    initializeEndpointTabState(button, this.endpointUrl, this.connectionManager.sessionId)

    this.connectionManager.subscribe(states.CONNECTION, (connected) => {
      setEndpointTabState(button, 'connection', connected)
    })
    this.connectionManager.subscribe(states.SUBSCRIPTION, (connected) => {
      setEndpointTabState(button, 'subscription', connected)
    })
    this.connectionManager.subscribe(states.ATTEMPT_CLOSE, () => {
      markEndpointTabClosing(button)
    })
  }

  resolveControllerIpFromEndpoint () {
    const endpointUrl = String(this.connectionManager?.endpointUrl || this.endpointUrl || '').trim()
    if (!endpointUrl) {
      return ''
    }
    const match = endpointUrl.match(/^[a-z]+:\/\/([^/:\]]+|\[[^\]]+\])/i)
    if (!match?.[1]) {
      return ''
    }
    return match[1].replace(/^\[/, '').replace(/\]$/, '')
  }

  normalizeControllerIp (value) {
    const text = String(value || '').trim()
    if (!text) {
      return ''
    }
    const match = text.match(/^[a-z]+:\/\/([^/:\]]+|\[[^\]]+\])/i)
    if (match?.[1]) {
      return match[1].replace(/^\[/, '').replace(/\]$/, '')
    }
    return text
  }

  runEnvelopeLimitsExportViaWebSocket ({ jsonText, filename }) {
    const webSocketManager = this.connectionManager?.webSocketManager
    if (!webSocketManager) {
      return Promise.reject(new Error('WebSocket manager not available for envelope export runner.'))
    }

    const endpointUrl = this.connectionManager?.endpointUrl || this.endpointUrl
    const controllerIp = this.normalizeControllerIp(this.resolveControllerIpFromEndpoint())
    const uniqueId = `envelope-export-${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`

    return new Promise((resolve, reject) => {
      let settled = false
      let timeoutHandle = null

      const cleanup = () => {
        if (timeoutHandle) {
          clearTimeout(timeoutHandle)
        }
        webSocketManager.unsubscribe(endpointUrl, ENVELOPE_EXPORT_RESPONSE_COMMAND, onResponse)
      }

      const finishResolve = (value) => {
        if (settled) {
          return
        }
        settled = true
        cleanup()
        resolve(value)
      }

      const finishReject = (error) => {
        if (settled) {
          return
        }
        settled = true
        cleanup()
        reject(error)
      }

      const onResponse = (msg, responseUniqueId) => {
        if (responseUniqueId !== uniqueId) {
          return
        }

        if (msg?.exception) {
          finishReject(new Error(msg.exception))
          return
        }

        if (msg?.ok === false) {
          const detailParts = []
          if (typeof msg?.error === 'string' && msg.error.trim().length > 0) {
            detailParts.push(msg.error.trim())
          }
          if (msg?.exitCode !== undefined && msg.exitCode !== null) {
            detailParts.push(`exitCode=${msg.exitCode}`)
          }
          if (typeof msg?.scriptPath === 'string' && msg.scriptPath.trim().length > 0) {
            detailParts.push(`scriptPath=${msg.scriptPath}`)
          }
          if (typeof msg?.stderr === 'string' && msg.stderr.trim().length > 0) {
            detailParts.push(`stderr=${msg.stderr.trim()}`)
          }
          if (typeof msg?.stdout === 'string' && msg.stdout.trim().length > 0) {
            detailParts.push(`stdout=${msg.stdout.trim()}`)
          }
          if (typeof msg?.command === 'string' && msg.command.trim().length > 0) {
            detailParts.push(`command=${msg.command}`)
          }
          finishReject(new Error(detailParts.join(' | ') || 'Envelope export runner failed.'))
          return
        }

        finishResolve(msg || { ok: true })
      }

      timeoutHandle = setTimeout(() => {
        finishReject(new Error(
          'Timed out waiting for envelope export runner response. ' +
          `Expected websocket command '${ENVELOPE_EXPORT_RESPONSE_COMMAND}'.`
        ))
      }, ENVELOPE_EXPORT_TIMEOUT_MS)

      webSocketManager.subscribe(endpointUrl, ENVELOPE_EXPORT_RESPONSE_COMMAND, onResponse)
      ijtLog.info('[Envelope Export] websocket payload', {
        endpointUrl,
        controllerIp,
        uniqueId
      })
      webSocketManager.send(ENVELOPE_EXPORT_REQUEST_COMMAND, endpointUrl, uniqueId, {
        filename,
        json: jsonText,
        controllerIp,
        endpointUrl
      })
    })
  }

  ensureEnvelopeExportRunnerHook () {
    if (typeof this.settings?.runEnvelopeLimitsExport === 'function') {
      return
    }

    const existingSettings = (this.settings && typeof this.settings === 'object') ? this.settings : {}
    this.settings = {
      ...existingSettings,
      runEnvelopeLimitsExport: async ({ jsonText, filename }) => {
        ijtLog.info('[Envelope Export] invoking websocket host runner', {
          endpointUrl: this.connectionManager?.endpointUrl || this.endpointUrl,
          filename
        })
        return this.runEnvelopeLimitsExportViaWebSocket({ jsonText, filename })
      }
    }
  }

  async loadOptionalEnvelopeTab (tabGenerator, resultManager, methodManager, addressSpace) {
    const modulePath = '/src/javascripts/views/envelope/ui/envelope-graphics.mjs'
    try {
      const { default: EnvelopeScreen } = await import(modulePath)
      if (EnvelopeScreen) {
        this.ensureEnvelopeExportRunnerHook()
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
