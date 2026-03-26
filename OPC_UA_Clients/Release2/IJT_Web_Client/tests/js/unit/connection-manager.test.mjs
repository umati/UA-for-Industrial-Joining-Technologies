/**
 * Unit tests for ConnectionManager.
 *
 * ConnectionManager creates a SocketHandler internally via
 * `import { SocketHandler } from 'ijt-support/ijt-support.mjs'`.
 * We intercept that import with vi.mock() + vi.hoisted() so the real
 * WebSocket / OPC UA stack is never instantiated.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// MockSocketHandler — must be hoisted so vi.mock() can reference it.
// ---------------------------------------------------------------------------

const { MockSocketHandler } = vi.hoisted(() => {
  class MockSocketHandlerClass {
    static instances = []

    constructor (wsm, endpoint) {
      this.wsm = wsm
      this.endpoint = endpoint
      this.mandatoryCallbacks = {}
      // Fresh vi.fn() per instance so assertions don't bleed between tests.
      this.connect = vi.fn()
      this.close = vi.fn()
      this.subscribeEvent = vi.fn()
      MockSocketHandlerClass.instances.push(this)
    }

    registerMandatory (event, callback) {
      if (!this.mandatoryCallbacks[event]) {
        this.mandatoryCallbacks[event] = []
      }
      if (callback) {
        this.mandatoryCallbacks[event].push(callback)
      }
    }

    /** Helper used in tests to fire registered mandatory callbacks. */
    simulateEvent (event, msg) {
      const cbs = this.mandatoryCallbacks[event] ?? []
      for (const cb of cbs) cb(msg)
    }
  }

  return { MockSocketHandler: MockSocketHandlerClass }
})

vi.mock('ijt-support/ijt-support.mjs', () => ({
  SocketHandler: MockSocketHandler
}))

// Import AFTER the mock is declared (vi.mock is hoisted above imports).
import { ConnectionManager, CONNECTION_STATES } from '../../../src/javascripts/ijt-support/connection/connection-manager.mjs'

// ---------------------------------------------------------------------------
// Shared setup
// ---------------------------------------------------------------------------

let manager
let mockSocket

beforeEach(() => {
  MockSocketHandler.instances = []
  manager = new ConnectionManager(null, 'opc.tcp://test:4840')
  mockSocket = MockSocketHandler.instances[0]
})

// ---------------------------------------------------------------------------
// constructor
// ---------------------------------------------------------------------------

describe('ConnectionManager — constructor', () => {
  it('immediately triggers ATTEMPT_CONNECTION state', () => {
    expect(manager[CONNECTION_STATES.ATTEMPT_CONNECTION]).toBe(true)
  })

  it('calls socketHandler.connect() once during construction', () => {
    expect(mockSocket.connect).toHaveBeenCalledOnce()
  })

  it('passes the endpoint URL to the SocketHandler', () => {
    expect(mockSocket.endpoint).toBe('opc.tcp://test:4840')
  })

  it('exposes socketHandler on the instance', () => {
    expect(manager.socketHandler).toBe(mockSocket)
  })
})

// ---------------------------------------------------------------------------
// subscribe / trigger
// ---------------------------------------------------------------------------

describe('ConnectionManager — subscribe and trigger', () => {
  it('calls the registered callback when state changes', () => {
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, cb)
    manager.trigger(CONNECTION_STATES.CONNECTION, true)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('does NOT call the callback when the state value is unchanged', () => {
    manager[CONNECTION_STATES.CONNECTION] = true // pre-set
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, cb)
    manager.trigger(CONNECTION_STATES.CONNECTION, true) // same value → no-op
    expect(cb).not.toHaveBeenCalled()
  })

  it('fires callback when state transitions from true to false', () => {
    manager[CONNECTION_STATES.CONNECTION] = true
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, cb)
    manager.trigger(CONNECTION_STATES.CONNECTION, false)
    expect(cb).toHaveBeenCalledWith(false)
  })

  it('only notifies callbacks registered for the triggered state', () => {
    const cbConn = vi.fn()
    const cbSub = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, cbConn)
    manager.subscribe(CONNECTION_STATES.SUBSCRIPTION, cbSub)
    manager.trigger(CONNECTION_STATES.CONNECTION, true)
    expect(cbConn).toHaveBeenCalledOnce()
    expect(cbSub).not.toHaveBeenCalled()
  })

  it('updates this[state] after firing callbacks', () => {
    manager.trigger(CONNECTION_STATES.SUBSCRIPTION, true)
    expect(manager[CONNECTION_STATES.SUBSCRIPTION]).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// State machine via mandatory event callbacks
// ---------------------------------------------------------------------------

describe('ConnectionManager — state machine via mandatory callbacks', () => {
  it('transitions to CONNECTION state when "connection established" fires', () => {
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, cb)
    mockSocket.simulateEvent('connection established', {})
    expect(manager[CONNECTION_STATES.CONNECTION]).toBe(true)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('auto-calls subscribeEvent when connection is established', () => {
    mockSocket.simulateEvent('connection established', {})
    expect(mockSocket.subscribeEvent).toHaveBeenCalled()
  })

  it('transitions to SUBSCRIPTION state when "subscribe" fires', () => {
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.SUBSCRIPTION, cb)
    mockSocket.simulateEvent('subscribe', {})
    expect(manager[CONNECTION_STATES.SUBSCRIPTION]).toBe(true)
    expect(cb).toHaveBeenCalledWith(true)
  })
})

// ---------------------------------------------------------------------------
// close()
// ---------------------------------------------------------------------------

describe('ConnectionManager — close()', () => {
  it('triggers ATTEMPT_CLOSE state', () => {
    const cb = vi.fn()
    manager.subscribe(CONNECTION_STATES.ATTEMPT_CLOSE, cb)
    manager.close()
    expect(cb).toHaveBeenCalledWith(true)
    expect(manager[CONNECTION_STATES.ATTEMPT_CLOSE]).toBe(true)
  })

  it('calls socketHandler.close()', () => {
    manager.close()
    expect(mockSocket.close).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// Callback error isolation
// ---------------------------------------------------------------------------

describe('ConnectionManager — callback error isolation', () => {
  it('continues invoking later callbacks even if an earlier one throws', () => {
    const throwing = vi.fn().mockImplementation(() => { throw new Error('boom') })
    const good = vi.fn()
    manager.subscribe(CONNECTION_STATES.CONNECTION, throwing)
    manager.subscribe(CONNECTION_STATES.CONNECTION, good)
    expect(() => manager.trigger(CONNECTION_STATES.CONNECTION, true)).not.toThrow()
    expect(good).toHaveBeenCalledOnce()
  })
})
