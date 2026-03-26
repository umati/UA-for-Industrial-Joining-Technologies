import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EventManager } from '../../../javascripts/ijt-support/events/event-manager.mjs'

function makeConnectionManager () {
  const subCallbacks = []
  const socketListeners = {}
  return {
    socketHandler: {
      registerMandatory: vi.fn((event, cb) => { socketListeners[event] = cb }),
      subscribeEvent: vi.fn(),
      _trigger: (event, msg) => { if (socketListeners[event]) socketListeners[event](msg) }
    },
    subscribe: vi.fn((state, cb) => { subCallbacks.push({ state, cb }) }),
    _subCallbacks: subCallbacks,
    _trigger: function (state, val) {
      this._subCallbacks.filter(c => c.state === state).forEach(c => c.cb(val))
    }
  }
}

describe('EventManager', () => {
  let em, connectionManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    em = new EventManager(connectionManager)
  })

  it('registers "subscribed event" mandatory handler on construction', () => {
    expect(connectionManager.socketHandler.registerMandatory).toHaveBeenCalledWith(
      'subscribed event', expect.any(Function)
    )
  })

  it('listenEvent() adds a callback entry', () => {
    const filter = vi.fn(() => true)
    const callback = vi.fn()
    em.listenEvent(filter, callback, 'test')
    expect(em.callbacks.length).toBe(1)
    expect(em.callbacks[0].filter).toBe(filter)
    expect(em.callbacks[0].callback).toBe(callback)
  })

  it('receivedEvent() calls callback when filter returns true', () => {
    const filter = vi.fn(() => true)
    const callback = vi.fn()
    em.listenEvent(filter, callback)
    em.receivedEvent({ result: 'data' })
    expect(callback).toHaveBeenCalled()
  })

  it('receivedEvent() does not call callback when filter returns false', () => {
    const filter = vi.fn(() => false)
    const callback = vi.fn()
    em.listenEvent(filter, callback)
    em.receivedEvent({ result: 'data' })
    expect(callback).not.toHaveBeenCalled()
  })

  it('multiple callbacks are all invoked', () => {
    const cb1 = vi.fn()
    const cb2 = vi.fn()
    em.listenEvent(() => true, cb1, 'cb1')
    em.listenEvent(() => true, cb2, 'cb2')
    em.receivedEvent({ someField: 'value' })
    expect(cb1).toHaveBeenCalled()
    expect(cb2).toHaveBeenCalled()
  })

  it('reset() clears all callbacks', () => {
    em.listenEvent(() => true, vi.fn())
    em.listenEvent(() => true, vi.fn())
    em.reset()
    expect(em.callbacks.length).toBe(0)
  })

  it('subscribeEvent() triggers ensureServerSubscription', () => {
    em.subscribeEvent(['EventId'], null, vi.fn(), 'test')
    expect(connectionManager.socketHandler.subscribeEvent).toHaveBeenCalled()
  })

  it('ensureServerSubscription() only subscribes once (serverSubscriptionActive flag)', () => {
    em.ensureServerSubscription(['EventId'])
    em.ensureServerSubscription(['EventId'])
    expect(connectionManager.socketHandler.subscribeEvent).toHaveBeenCalledTimes(1)
  })

  it('receivedEvent() passes msg.result as payload when present', () => {
    const filter = vi.fn(payload => payload.myField === 'hello')
    const callback = vi.fn()
    em.listenEvent(filter, callback)
    em.receivedEvent({ result: { myField: 'hello' } })
    expect(callback).toHaveBeenCalledWith({ myField: 'hello' })
  })
})
