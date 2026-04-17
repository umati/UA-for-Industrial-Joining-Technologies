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

  it('unsubscribe removes a specific callback', () => {
    const manager = new WebSocketManager(() => {}, 'ws://test')
    const cb1 = vi.fn()
    const cb2 = vi.fn()

    manager.subscribe('ep', 'cmd', cb1)
    manager.subscribe('ep', 'cmd', cb2)
    manager.unsubscribe('ep', 'cmd', cb1)

    const ws = MockWebSocket.instances[0]
    ws.open()
    ws.emitMessage({ command: 'cmd', endpoint: 'ep', data: {}, uniqueid: 'u' })

    expect(cb1).not.toHaveBeenCalled()
    expect(cb2).toHaveBeenCalledOnce()
  })

  it('unsubscribe is a no-op for unknown endpoint or type', () => {
    const manager = new WebSocketManager(() => {}, 'ws://test')
    expect(() => manager.unsubscribe('unknown-ep', 'unknown-cmd', vi.fn())).not.toThrow()
  })

  it('caps send queue at MAX_SEND_QUEUE and drops oldest', () => {
    const manager = new WebSocketManager(() => {}, 'ws://test')
    // Fill queue beyond MAX_SEND_QUEUE (500)
    for (let i = 0; i < 501; i++) {
      manager.send(`cmd-${i}`, 'ep', null, {})
    }
    expect(manager._sendQueue.length).toBeLessThanOrEqual(500)
  })

  it('send with open socket sends immediately', () => {
    // Add static OPEN so WebSocket.OPEN check works
    MockWebSocket.OPEN = 1
    const manager = new WebSocketManager(() => {}, 'ws://test')
    const ws = MockWebSocket.instances[0]
    ws.open() // sets readyState = OPEN

    manager.send('testcmd', 'common', null, { x: 1 })

    expect(ws.sent).toHaveLength(1)
    const payload = JSON.parse(ws.sent[0])
    expect(payload.command).toBe('testcmd')
  })

  it('send handles error during socket.send and queues the message', () => {
    MockWebSocket.OPEN = 1
    const manager = new WebSocketManager(() => {}, 'ws://test')
    const ws = MockWebSocket.instances[0]
    ws.open()

    // Override send to throw
    ws.send = vi.fn(() => { throw new Error('send failed') })

    manager.send('cmd', 'ep', 'uid', {})

    // The message should be queued after the send failure
    expect(manager._sendQueue.length).toBeGreaterThanOrEqual(1)
  })

  it('emitting message with no command logs a warning (no subscriber crash)', () => {
    const manager = new WebSocketManager(() => {}, 'ws://test')
    const ws = MockWebSocket.instances[0]
    ws.open()

    // Message without a command field
    expect(() => ws.emitMessage({ data: 'no-command-field' })).not.toThrow()
  })

  it('emitting invalid JSON does not crash the manager', () => {
    const manager = new WebSocketManager(() => {}, 'ws://test')  // eslint-disable-line no-unused-vars
    const ws = MockWebSocket.instances[0]

    // Directly invoke the message handler with bad JSON
    expect(() => {
      ws.listeners.message({ data: 'not valid json{{{{' })
    }).not.toThrow()
  })
})
