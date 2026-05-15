import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ConnectionManager } from '../../../javascripts/ijt-support/connection/connection-manager.mjs'

function makeSocket () {
  const listeners = {}
  return {
    emit: vi.fn(),
    on: vi.fn((event, cb) => { listeners[event] = cb }),
    _trigger: (event, msg) => { if (listeners[event]) listeners[event](msg) }
  }
}

describe('ConnectionManager event handlers', () => {
  let socket, manager

  beforeEach(() => {
    socket = makeSocket()
    manager = new ConnectionManager(socket, 'opc.tcp://localhost:40451')
  })

  it('triggers connection state on "connection established"', () => {
    const cb = vi.fn()
    manager.subscribe('connection', cb)

    socket._trigger('connection established', {})

    expect(manager.connection).toBe(true)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('triggers session state on "session established"', () => {
    const cb = vi.fn()
    manager.subscribe('session', cb)

    socket._trigger('session established', {})

    expect(manager.session).toBe(true)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('triggers subscription state on "subscription created"', () => {
    const cb = vi.fn()
    manager.subscribe('subscription', cb)

    socket._trigger('subscription created', {})

    expect(manager.subscription).toBe(true)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('resets session state on "session closed"', () => {
    // First establish session
    socket._trigger('session established', {})
    expect(manager.session).toBe(true)

    const cb = vi.fn()
    manager.subscribe('session', cb)
    cb.mockClear()

    socket._trigger('session closed', {})

    expect(manager.session).toBe(false)
    expect(cb).toHaveBeenCalledWith(false)
  })
})
