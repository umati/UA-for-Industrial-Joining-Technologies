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

// ── Additional edge-case tests ─────────────────────────────────────────────

describe('EventManager — simpleSubscribeEvent', () => {
  let em, connectionManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    em = new EventManager(connectionManager)
  })

  it('simpleSubscribeEvent() includes default fields plus extra fields', () => {
    const callback = vi.fn()
    const filter = vi.fn(() => true)
    em.simpleSubscribeEvent(['ExtraField1', 'ExtraField2'], filter, callback, 'test')

    // Should have called subscribeEvent on socketHandler with merged field list
    const callArgs = connectionManager.socketHandler.subscribeEvent.mock.calls[0]
    expect(callArgs[0]).toContain('EventId')
    expect(callArgs[0]).toContain('Result')
    expect(callArgs[0]).toContain('ExtraField1')
    expect(callArgs[0]).toContain('ExtraField2')
  })

  it('simpleSubscribeEvent() adds callback to callbacks list when filter is provided', () => {
    const callback = vi.fn()
    const filter = vi.fn(() => true)
    em.simpleSubscribeEvent(['ExtraField'], filter, callback, 'test')
    expect(em.callbacks.length).toBe(1)
  })
})

describe('EventManager — subscribeEvent', () => {
  let em, connectionManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    em = new EventManager(connectionManager)
  })

  it('subscribeEvent() with null filter still triggers ensureServerSubscription', () => {
    em.subscribeEvent(['EventId'], null, vi.fn(), 'test')
    expect(connectionManager.socketHandler.subscribeEvent).toHaveBeenCalled()
  })

  it('subscribeEvent() with null filter does NOT add a callback entry', () => {
    em.subscribeEvent(['EventId'], null, vi.fn(), 'test')
    // No filter → callbacks array unchanged
    expect(em.callbacks.length).toBe(0)
  })

  it('subscribeEvent() with filter adds a callback entry', () => {
    const filter = vi.fn(() => true)
    em.subscribeEvent(['EventId'], filter, vi.fn(), 'test')
    expect(em.callbacks.length).toBe(1)
    expect(em.callbacks[0].filter).toBe(filter)
  })
})

describe('EventManager — subscription state changes', () => {
  let em, connectionManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    em = new EventManager(connectionManager)
  })

  it('subscription = true triggers ensureServerSubscription', () => {
    const spy = vi.spyOn(em, 'ensureServerSubscription')
    connectionManager._trigger('subscription', true)
    expect(spy).toHaveBeenCalled()
  })

  it('subscription = false sets serverSubscriptionActive to false', () => {
    em.serverSubscriptionActive = true
    connectionManager._trigger('subscription', false)
    expect(em.serverSubscriptionActive).toBe(false)
  })
})

describe('EventManager — event socket integration', () => {
  let em, connectionManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    em = new EventManager(connectionManager)
  })

  it('receives socket event and calls matching callback', () => {
    const callback = vi.fn()
    em.listenEvent(payload => payload.EventType?.value === 'TestEvent', callback)

    connectionManager.socketHandler._trigger('subscribed event', {
      result: { EventType: { value: 'TestEvent' }, SourceName: { value: 'TestSource' } }
    })
    expect(callback).toHaveBeenCalled()
  })

  it('handles event without SourceName gracefully', () => {
    const callback = vi.fn()
    em.listenEvent(() => true, callback)

    // Should not throw even when SourceName is missing
    expect(() => {
      connectionManager.socketHandler._trigger('subscribed event', { result: {} })
    }).not.toThrow()
    expect(callback).toHaveBeenCalled()
  })

  it('receivedEvent() uses msg directly when msg.result is absent', () => {
    const filter = vi.fn(payload => payload.directField === 'value')
    const callback = vi.fn()
    em.listenEvent(filter, callback)
    em.receivedEvent({ directField: 'value' })
    expect(callback).toHaveBeenCalledWith({ directField: 'value' })
  })

  it('ensureServerSubscription() uses defaultFields when fields argument is undefined', () => {
    em.ensureServerSubscription(undefined)
    const callArgs = connectionManager.socketHandler.subscribeEvent.mock.calls[0]
    expect(callArgs[0]).toContain('EventId')
    expect(callArgs[0]).toContain('Result')
  })
})
