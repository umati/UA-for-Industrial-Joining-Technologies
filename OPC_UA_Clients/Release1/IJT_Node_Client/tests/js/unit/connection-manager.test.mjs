import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ConnectionManager } from '../../../javascripts/ijt-support/connection/connection-manager.mjs'

function makeSocket () {
  const listeners = {}
  return {
    emit: vi.fn(),
    on: vi.fn((event, cb) => { listeners[event] = cb }),
    _trigger: (event, msg) => { if (listeners[event]) listeners[event](msg) },
  }
}

describe('ConnectionManager', () => {
  let socket, manager
  const endpoint = 'opc.tcp://localhost:40451'

  beforeEach(() => {
    socket = makeSocket()
    manager = new ConnectionManager(socket, endpoint)
  })

  it('creates a socketHandler on construction', () => {
    expect(manager.socketHandler).toBeDefined()
  })

  it('calls connect() on socketHandler during construction', () => {
    expect(socket.emit).toHaveBeenCalledWith('connect to', endpoint)
  })

  it('triggers "attemptconnection" during construction', () => {
    expect(manager.attemptconnection).toBe(true)
  })

  it('subscribe() stores callback for a state', () => {
    const cb = vi.fn()
    manager.subscribe('connection', cb)
    expect(manager.callbacks.some(c => c.state === 'connection')).toBe(true)
  })

  it('subscribe() calls callback immediately if state is already set', () => {
    const cb = vi.fn()
    manager.subscribe('attemptconnection', cb)
    expect(cb).toHaveBeenCalledWith(true)
  })

  it('trigger() sets state and calls matching callbacks', () => {
    const cb = vi.fn()
    manager.subscribe('connection', cb)
    manager.trigger('connection', true)
    expect(cb).toHaveBeenCalledWith(true)
    expect(manager.connection).toBe(true)
  })

  it('trigger() does not call callback if state unchanged', () => {
    manager.trigger('connection', true)
    const cb = vi.fn()
    manager.subscribe('connection', cb)
    cb.mockClear()
    manager.trigger('connection', true) // same value, no change
    expect(cb).not.toHaveBeenCalled()
  })

  it('close() emits "terminate connection"', () => {
    manager.close()
    expect(socket.emit).toHaveBeenCalledWith('terminate connection', endpoint)
  })
})
