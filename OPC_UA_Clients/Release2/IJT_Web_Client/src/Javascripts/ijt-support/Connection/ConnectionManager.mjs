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

/** Named state constants — prevents typo bugs in trigger/subscribe calls. */
export const CONNECTION_STATES = Object.freeze({
  ATTEMPT_CONNECTION: 'attemptconnection',
  CONNECTION: 'connection',
  SUBSCRIPTION: 'subscription',
  ATTEMPT_CLOSE: 'attemptclose'
})

export class ConnectionManager {
  constructor (webSocketManager, endpointUrl) {
    this.socketHandler = new SocketHandler(webSocketManager, endpointUrl)
    this.callbacks = []

    this.socketHandler.registerMandatory('connection established', (_msg) => {
      this.trigger(CONNECTION_STATES.CONNECTION, true)
    })

    // Trigger 'subscription' state once the server confirms subscribe completed
    this.socketHandler.registerMandatory('subscribe', (_msg) => {
      this.trigger(CONNECTION_STATES.SUBSCRIPTION, true)
    })

    // Auto-subscribe to events once connection is established
    this.subscribe(CONNECTION_STATES.CONNECTION, (_connected) => {
      this.socketHandler.subscribeEvent()
    })

    this.trigger(CONNECTION_STATES.ATTEMPT_CONNECTION, true)
    this.socketHandler.connect()
  }

  /**
   * Register a callback for a specific state change.
   * @param {string} state    - one of CONNECTION_STATES values
   * @param {Function} callback
   */
  subscribe (state, callback) {
    this.callbacks.push({ state, callback })
  }

  /**
   * Fire all callbacks registered for `state` when `changeTo` differs from current value.
   * @param {string} state
   * @param {boolean} changeTo
   */
  trigger (state, changeTo) {
    if (this[state] !== changeTo) {
      for (const row of this.callbacks) {
        if (row.state === state) {
          try {
            row.callback(changeTo)
          } catch (err) {
            console.error(`ConnectionManager callback for "${state}" threw:`, err)
          }
        }
      }
      this[state] = changeTo
    }
  }

  /** Initiate a graceful close of the underlying socket. */
  close () {
    this.trigger(CONNECTION_STATES.ATTEMPT_CLOSE, true)
    this.socketHandler.close()
  }
}
