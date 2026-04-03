/**
 * Handle browser <-> backend websocket communication.
 *
 * Improvements over original:
 *  - Exponential-backoff auto-reconnect (capped at 30 s)
 *  - Reconnect lock prevents simultaneous reconnect races
 *  - Queues outbound messages during reconnect instead of dropping them
 *  - Preserves all subscriptions across reconnects
 */
import { ijtLog } from '../ijt-logger.mjs'

const RECONNECT_BASE_MS = 1_000
const RECONNECT_MAX_MS = 30_000
const RECONNECT_FACTOR = 2
const MAX_SEND_QUEUE = 500  // cap outbound buffer to prevent unbounded memory growth during prolonged disconnects

export class WebSocketManager {
  constructor (establishedCallback, websocketUrl) {
    this.subscribers = {}
    this.connection = false
    this.websocketUrl = websocketUrl || 'ws://localhost:8001/'
    this.establishedCallback = establishedCallback
    this._reconnectAttempt = 0
    this._reconnecting = false
    this._sendQueue = []          // messages buffered while reconnecting
    this._messageHandler = null   // keep ref so we can remove it on recreate
    this.establishWebSocket(this.establishedCallback, this.websocketUrl)
  }

  establishWebSocket (establishedCallback, websocketUrl) {
    const url = websocketUrl || this.websocketUrl

    // Remove stale listener from a previous socket if any
    if (this.websocket && this._messageHandler) {
      this.websocket.removeEventListener('message', this._messageHandler)
    }

    this.websocket = new WebSocket(url)

    this.websocket.onopen = () => {
      ijtLog.info('WebSocket connected')
      this.connection = true
      this._reconnectAttempt = 0
      this._reconnecting = false
      establishedCallback(this)
      // Flush messages that were queued during reconnect
      while (this._sendQueue.length > 0) {
        const queued = this._sendQueue.shift()
        try { this.websocket.send(queued) } catch (e) { ijtLog.error('Flush send failed:', e) }
      }
    }

    this.websocket.onclose = (evt) => {
      ijtLog.warn(`WebSocket closed (code=${evt.code})`)
      this.connection = false
      this._scheduleReconnect()
    }

    this.websocket.onerror = (err) => {
      ijtLog.error('WebSocket error', err)
      this.connection = false
      // onclose will fire after onerror — reconnect is handled there
    }

    this._messageHandler = ({ data }) => {
      let event
      try {
        event = JSON.parse(data)
      } catch (error) {
        ijtLog.error('Invalid websocket payload:', error)
        return
      }

      if (!event?.command) {
        ijtLog.warn('Ignoring websocket payload without command')
        return
      }

      const { command, endpoint, data: msgData, uniqueid } = event
      const endpointSubscribes = this.subscribers[endpoint]
      if (endpointSubscribes?.[command]) {
        for (const subscription of endpointSubscribes[command]) {
          if (subscription) {
            try {
              subscription(msgData, uniqueid)
            } catch (error) {
              ijtLog.error('Subscriber callback failed:', error)
            }
          }
        }
      }
    }

    this.websocket.addEventListener('message', this._messageHandler)
  }

  /** Exponential-backoff reconnect with jitter. */
  _scheduleReconnect () {
    if (this._reconnecting) return
    this._reconnecting = true

    const delay = Math.min(
      RECONNECT_MAX_MS,
      RECONNECT_BASE_MS * Math.pow(RECONNECT_FACTOR, this._reconnectAttempt)
    )
    const jitter = Math.random() * 500
    this._reconnectAttempt++

    ijtLog.info(`WebSocket reconnect in ${Math.round(delay + jitter)} ms (attempt ${this._reconnectAttempt})`)
    setTimeout(() => {
      this._reconnecting = false
      this.establishWebSocket(this.establishedCallback, this.websocketUrl)
    }, delay + jitter)
  }

  subscribe (endpoint, type, callback) {
    const ep = endpoint || 'common'
    if (!this.subscribers[ep]) {
      this.subscribers[ep] = {}
    }
    if (!this.subscribers[ep][type]) {
      this.subscribers[ep][type] = []
    }
    this.subscribers[ep][type].push(callback)
  }

  unsubscribe (endpoint, type, callback) {
    const ep = endpoint || 'common'
    const callerObject = this.subscribers[ep]
    if (callerObject?.[type]) {
      callerObject[type] = callerObject[type].filter((cb) => cb !== callback)
    }
  }

  send (command, endpoint, uniqueId, event) {
    const payload = event ?? {}
    payload.command = command
    payload.endpoint = endpoint ?? 'common'
    if (uniqueId) payload.uniqueid = uniqueId

    const serialized = JSON.stringify(payload)

    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      ijtLog.info('WebSocket not ready — queuing message and triggering reconnect')
      if (this._sendQueue.length >= MAX_SEND_QUEUE) {
        ijtLog.warn(`Send queue full (${MAX_SEND_QUEUE}); dropping oldest message`)
        this._sendQueue.shift()
      }
      this._sendQueue.push(serialized)
      if (!this.connection && !this._reconnecting) {
        this._scheduleReconnect()
      }
      return
    }

    try {
      this.websocket.send(serialized)
    } catch (err) {
      ijtLog.error('WebSocket send failed:', err)
      this._sendQueue.push(serialized)
      this._scheduleReconnect()
    }
  }
}
