import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { WebSocketManager } from '../../../src/javascripts/ijt-support/connection/websocket-manager.mjs'

class MockWebSocket {
  static instances = []

  constructor (url) {
    this.url = url
    this.readyState = 0
    this.OPEN = 1
    this.sent = []
    this.listeners = {}
    MockWebSocket.instances.push(this)
  }

  addEventListener (name, callback) {
    this.listeners[name] = callback
  }

  removeEventListener (name, callback) {
    if (this.listeners[name] === callback) delete this.listeners[name]
  }

  send (payload) {
    this.sent.push(payload)
  }

  open () {
    this.readyState = this.OPEN
    if (this.onopen) this.onopen()
  }

  emitMessage (obj) {
    this.listeners.message({ data: JSON.stringify(obj) })
  }
}

describe('WebSocketManager', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    global.WebSocket = MockWebSocket
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('delivers subscribed events by endpoint and command', () => {
    const established = vi.fn()
    const manager = new WebSocketManager(established, 'ws://test')
    const ws = MockWebSocket.instances[0]
    const callback = vi.fn()

    manager.subscribe('ep1', 'state', callback)
    ws.open()
    ws.emitMessage({ command: 'state', endpoint: 'ep1', data: { ok: true }, uniqueid: 'u1' })

    expect(established).toHaveBeenCalledOnce()
    expect(callback).toHaveBeenCalledWith({ ok: true }, 'u1')
  })

  it('re-establishes connection and flushes queued message after reconnect', () => {
    const manager = new WebSocketManager(() => {}, 'ws://first')

    // Socket exists but is not open (readyState=0); send queues + schedules reconnect
    manager.send('ping', 'ep2', 'id-1', { value: 42 })

    // Advance timers past the reconnect delay so the new socket is created
    vi.runAllTimers()

    expect(MockWebSocket.instances).toHaveLength(2)
    const reconnected = MockWebSocket.instances[1]

    // Simulate the reconnected socket opening — queued message must be flushed
    reconnected.open()

    expect(reconnected.sent).toHaveLength(1)
    const payload = JSON.parse(reconnected.sent[0])
    expect(payload.command).toBe('ping')
    expect(payload.endpoint).toBe('ep2')
    expect(payload.uniqueid).toBe('id-1')
    expect(payload.value).toBe(42)
  })
})
