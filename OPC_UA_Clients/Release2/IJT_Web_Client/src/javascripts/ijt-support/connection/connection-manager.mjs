/**
 * ConnectionManager — manages lifecycle states for a single OPC UA endpoint.
 *
 * State machine:
 *   attemptconnection → connection → subscription
 *   close             → attemptclose
 */
import {
  SocketHandler
} from 'ijt-support/ijt-support.mjs'
import { ObservableManagerBase } from '../observable-manager-base.mjs'

/** Named state constants — prevents typo bugs in trigger/subscribe calls. */
export const CONNECTION_STATES = Object.freeze({
  ATTEMPT_CONNECTION: 'attemptconnection',
  CONNECTION: 'connection',
  SUBSCRIPTION: 'subscription',
  METHODS: 'methods',
  TIGHTENING_SYSTEM: 'tighteningsystem',
  ATTEMPT_CLOSE: 'attemptclose'
})

function createSessionId () {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export class ConnectionManager extends ObservableManagerBase {
  constructor (webSocketManager, endpointUrl) {
    super('ConnectionManager')
    this.webSocketManager = webSocketManager
    this.endpointUrl = endpointUrl
    this.sessionId = createSessionId()
    this.connectionWanted = true
    this.closing = false
    this.socketHandler = new SocketHandler(webSocketManager, endpointUrl)

    this.socketHandler.registerMandatory('connection established', (_msg) => {
      this.trigger(CONNECTION_STATES.CONNECTION, true)
    })

    // Trigger 'subscription' state once the server confirms subscribe completed
    this.socketHandler.registerMandatory('subscribe', (_msg) => {
      this.trigger(CONNECTION_STATES.SUBSCRIPTION, true)
    })

    // Auto-subscribe to events once connection is established
    this.subscribe(CONNECTION_STATES.CONNECTION, (_connected) => {
      if (_connected) {
        this.socketHandler.subscribeEvent()
      }
    })

    this.subscribeToWebSocketState()

    this.trigger(CONNECTION_STATES.ATTEMPT_CONNECTION, true)
    this.socketHandler.connect()

    this.CONNECTION_STATES = CONNECTION_STATES
  }

  subscribeToWebSocketState () {
    if (typeof this.webSocketManager?.subscribeConnectionState !== 'function') {
      return
    }
    this.unsubscribeWebSocketState = this.webSocketManager.subscribeConnectionState((connected) => {
      if (!connected) {
        this.trigger(CONNECTION_STATES.SUBSCRIPTION, false)
        this.trigger(CONNECTION_STATES.CONNECTION, false)
        return
      }
      if (this.connectionWanted && !this.closing && !this[CONNECTION_STATES.CONNECTION]) {
        this.trigger(CONNECTION_STATES.ATTEMPT_CONNECTION, true)
        this.socketHandler.connect()
      }
    })
  }

  /**
   * Register a callback for a specific state change.
   * @param {string} state    - one of CONNECTION_STATES values
   * @param {Function} callback
   */
  subscribe (state, callback) {
    const unsubscribe = this._subscribeTopic(state, callback)
    if (this[state]) { // If this state is already reached, immediately call back
      callback(this[state])
    }
    return unsubscribe
  }

  /**
   * Fire all callbacks registered for `state` when `changeTo` differs from current value.
   * @param {string} state
   * @param {boolean} changeTo
   */
  trigger (state, changeTo = true) {
    if (this[state] !== changeTo) {
      this._notifyTopic(state, changeTo)
      this[state] = changeTo
    }
  }

  /** Initiate a graceful close of the underlying socket. */
  close () {
    this.connectionWanted = false
    this.closing = true
    if (typeof this.unsubscribeWebSocketState === 'function') {
      this.unsubscribeWebSocketState()
      this.unsubscribeWebSocketState = null
    }
    this.trigger(CONNECTION_STATES.ATTEMPT_CLOSE, true)
    this.socketHandler.close()
  }
}
