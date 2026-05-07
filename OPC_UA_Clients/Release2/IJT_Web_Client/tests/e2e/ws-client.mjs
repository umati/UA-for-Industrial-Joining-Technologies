/**
 * Lightweight WebSocket test client for direct backend functional testing.
 *
 * Works in Node.js 22+ (native globalThis.WebSocket) — the project
 * already requires Node >= 24 (package.json engines field).
 *
 * Usage:
 *   const client = new WsTestClient(process.env.WS_TEST_URL, process.env.OPCUA_TEST_ENDPOINT)
 *   await client.connect()
 *   const resp = await client.send('namespaces')
 *   await client.close()
 */

const DEFAULT_TIMEOUT_MS = 15_000

/** Returns true if a WebSocket handshake succeeds within `timeoutMs`. */
export async function isBackendReachable (wsUrl, timeoutMs = 3_000) {
  return new Promise((resolve) => {
    let done = false
    const finish = (val) => {
      if (done) return
      done = true
      clearTimeout(timer)
      try { ws.close() } catch { /* ignore */ }
      resolve(val)
    }
    let ws
    const timer = setTimeout(() => finish(false), timeoutMs)
    try {
      ws = new globalThis.WebSocket(wsUrl)
      ws.onopen = () => finish(true)
      ws.onerror = () => finish(false)
      ws.onclose = () => finish(false)
    } catch {
      finish(false)
    }
  })
}

export class WsTestClient {
  #ws = null
  #pending = new Map()   // uniqueid → { resolve, reject, timer }
  #events = []           // all received "event" command messages
  #raw = []              // all received messages
  #nextId = 1
  #endpoint

  constructor (wsUrl, opcuaEndpoint) {
    this.wsUrl = wsUrl
    this.#endpoint = opcuaEndpoint
  }

  get events () { return [...this.#events] }
  get raw () { return [...this.#raw] }

  connect () {
    return new Promise((resolve, reject) => {
      this.#ws = new globalThis.WebSocket(this.wsUrl)
      this.#ws.onopen = () => resolve(this)
      this.#ws.onerror = (e) => reject(new Error(`WS connect failed: ${e.message ?? e}`))
      this.#ws.onmessage = ({ data }) => this.#handleMessage(data)
    })
  }

  async close () {
    // Cancel all pending requests
    for (const { reject, timer } of this.#pending.values()) {
      clearTimeout(timer)
      reject(new Error('WsTestClient closed'))
    }
    this.#pending.clear()
    if (this.#ws && this.#ws.readyState === globalThis.WebSocket.OPEN) {
      this.#ws.close()
    }
    this.#ws = null
  }

  /**
   * Send a command to the backend and wait for the matching uniqueid response.
   * @param {string} command - backend command (e.g. 'namespaces', 'read', 'methodcall')
   * @param {object} [body]  - additional payload fields
   * @param {number} [timeoutMs]
   */
  send (command, body = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
    const uid = this.#nextId++
    const payload = { ...body, command, endpoint: this.#endpoint, uniqueid: uid }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.#pending.delete(uid)
        reject(new Error(`WS timeout waiting for response to '${command}' (uid=${uid})`))
      }, timeoutMs)
      this.#pending.set(uid, { resolve, reject, timer })
      this.#ws.send(JSON.stringify(payload))
    })
  }

  /**
   * Send a fire-and-forget command (no response expected, e.g. 'subscribe', 'connect to').
   */
  sendNoWait (command, body = {}) {
    const payload = { ...body, command, endpoint: this.#endpoint }
    this.#ws.send(JSON.stringify(payload))
  }

  /**
   * Wait until at least `minCount` "event" messages have been received
   * or `timeoutMs` elapses.
   */
  waitForEvents (minCount = 1, timeoutMs = 15_000) {
    return new Promise((resolve, reject) => {
      if (this.#events.length >= minCount) { resolve(this.#events); return }
      const timer = setTimeout(() => {
        reject(new Error(`Timed out waiting for ${minCount} event(s); got ${this.#events.length}`))
      }, timeoutMs)
      const poll = setInterval(() => {
        if (this.#events.length >= minCount) {
          clearInterval(poll)
          clearTimeout(timer)
          resolve([...this.#events])
        }
      }, 100)
    })
  }

  /** Clear the collected events list. */
  clearEvents () { this.#events.length = 0 }

  #handleMessage (data) {
    let payload
    try { payload = JSON.parse(data) } catch { return }
    this.#raw.push(payload)

    if (payload.command === 'event') {
      this.#events.push(payload)
    }

    const uid = payload.uniqueid
    if (uid != null && this.#pending.has(uid)) {
      const { resolve, timer } = this.#pending.get(uid)
      clearTimeout(timer)
      this.#pending.delete(uid)
      resolve(payload)
    }
  }
}
