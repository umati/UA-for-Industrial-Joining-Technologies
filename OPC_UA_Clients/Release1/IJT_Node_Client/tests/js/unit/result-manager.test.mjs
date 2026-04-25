import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ResultManager } from '../../../javascripts/ijt-support/results/result-manager.mjs'

function makeConnectionManager () {
  const callbacks = []
  return {
    socketHandler: {
      registerMandatory: vi.fn(),
      subscribeEvent: vi.fn()
    },
    subscribe: vi.fn((state, cb) => { callbacks.push({ state, cb }) }),
    _callbacks: callbacks,
    _trigger: function (state, val) {
      this._callbacks.filter(c => c.state === state).forEach(c => c.cb(val))
    }
  }
}

function makeEventManager () {
  return {
    listenEvent: vi.fn()
  }
}

describe('ResultManager', () => {
  let rm, connectionManager, eventManager

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    eventManager = makeEventManager()
    rm = new ResultManager(connectionManager, eventManager)
  })

  it('initializes with empty results dict', () => {
    expect(rm.results).toEqual({})
  })

  it('addResult() stores result keyed by resultId', () => {
    const result = { resultId: 'abc-123' }
    rm.addResult(result)
    expect(rm.results['abc-123']).toBe(result)
  })

  it('addResult() notifies subscribers', () => {
    const cb = vi.fn()
    rm.subscribe(cb)
    const result = { resultId: 'xyz' }
    rm.addResult(result)
    expect(cb).toHaveBeenCalledWith(result)
  })

  it('subscribe() stores callback in subscribers array', () => {
    const cb = vi.fn()
    rm.subscribe(cb)
    expect(rm.subscribers).toContain(cb)
  })

  it('multiple subscribers all receive addResult notification', () => {
    const cb1 = vi.fn()
    const cb2 = vi.fn()
    rm.subscribe(cb1)
    rm.subscribe(cb2)
    const result = { resultId: 'multi' }
    rm.addResult(result)
    expect(cb1).toHaveBeenCalledWith(result)
    expect(cb2).toHaveBeenCalledWith(result)
  })

  it('activate() is called when subscription event fires', () => {
    const activateSpy = vi.spyOn(rm, 'activate')
    connectionManager._trigger('subscription', true)
    expect(activateSpy).toHaveBeenCalled()
  })

  it('activate() registers a listenEvent handler', () => {
    connectionManager._trigger('subscription', true)
    expect(eventManager.listenEvent).toHaveBeenCalled()
  })
})

// ── Additional edge-case tests ─────────────────────────────────────────────

describe('ResultManager — addResult and subscribe edge cases', () => {
  let rm, connectionManager, eventManager

  function makeConnectionManager () {
    const callbacks = []
    return {
      socketHandler: { registerMandatory: vi.fn(), subscribeEvent: vi.fn() },
      subscribe: vi.fn((state, cb) => { callbacks.push({ state, cb }) }),
      _callbacks: callbacks,
      _trigger: function (state, val) {
        this._callbacks.filter(c => c.state === state).forEach(c => c.cb(val))
      }
    }
  }

  function makeEventManager () {
    return { listenEvent: vi.fn() }
  }

  beforeEach(() => {
    connectionManager = makeConnectionManager()
    eventManager = makeEventManager()
    rm = new ResultManager(connectionManager, eventManager)
  })

  it('addResult() stores multiple results with different resultIds', () => {
    rm.addResult({ resultId: 'r-1' })
    rm.addResult({ resultId: 'r-2' })
    rm.addResult({ resultId: 'r-3' })
    expect(Object.keys(rm.results)).toHaveLength(3)
    expect(rm.results['r-1']).toBeDefined()
    expect(rm.results['r-2']).toBeDefined()
    expect(rm.results['r-3']).toBeDefined()
  })

  it('addResult() overwrites existing result with same resultId', () => {
    const result1 = { resultId: 'r-1', torque: 10 }
    const result2 = { resultId: 'r-1', torque: 20 }
    rm.addResult(result1)
    rm.addResult(result2)
    expect(rm.results['r-1']).toBe(result2)
  })

  it('addResult() calls all subscribers in order', () => {
    const order = []
    rm.subscribe(() => order.push('first'))
    rm.subscribe(() => order.push('second'))
    rm.subscribe(() => order.push('third'))
    rm.addResult({ resultId: 'r-1' })
    expect(order).toEqual(['first', 'second', 'third'])
  })

  it('subscribe() with no results still adds the callback', () => {
    expect(rm.subscribers).toHaveLength(0)
    rm.subscribe(vi.fn())
    expect(rm.subscribers).toHaveLength(1)
  })

  it('subscription = false does not activate', () => {
    connectionManager._trigger('subscription', false)
    expect(eventManager.listenEvent).not.toHaveBeenCalled()
  })

  it('subscription = true multiple times only registers listenEvent once per activation', () => {
    connectionManager._trigger('subscription', true)
    connectionManager._trigger('subscription', true)
    // Each true trigger calls activate() which calls listenEvent
    expect(eventManager.listenEvent).toHaveBeenCalledTimes(2)
  })
})

describe('ResultManager — activate() filter and callback logic', () => {
  it('activate() filter accepts events with Result.value', () => {
    const callbacks = []
    const connectionManager = {
      socketHandler: { registerMandatory: vi.fn(), subscribeEvent: vi.fn() },
      subscribe: vi.fn((state, cb) => { callbacks.push({ state, cb }) }),
      _callbacks: callbacks,
      _trigger (state, val) { this._callbacks.filter(c => c.state === state).forEach(c => c.cb(val)) }
    }
    let capturedFilter, capturedCallback
    const eventManager = {
      listenEvent: vi.fn((filter, callback) => {
        capturedFilter = filter
        capturedCallback = callback
      })
    }
    const rm = new ResultManager(connectionManager, eventManager)
    connectionManager._trigger('subscription', true)

    // Test the captured filter
    expect(capturedFilter({ Result: { value: { resultId: 'r-1' } } })).toBeTruthy()
    expect(capturedFilter({ Result: { value: null } })).toBeFalsy()
    expect(capturedFilter({})).toBeFalsy()
  })

  it('activate() callback creates model and calls addResult', () => {
    const callbacks = []
    const connectionManager = {
      socketHandler: { registerMandatory: vi.fn(), subscribeEvent: vi.fn() },
      subscribe: vi.fn((state, cb) => { callbacks.push({ state, cb }) }),
      _callbacks: callbacks,
      _trigger (state, val) { this._callbacks.filter(c => c.state === state).forEach(c => c.cb(val)) }
    }
    let capturedCallback
    const eventManager = {
      listenEvent: vi.fn((filter, callback) => { capturedCallback = callback })
    }
    const rm = new ResultManager(connectionManager, eventManager)
    connectionManager._trigger('subscription', true)

    const addResultSpy = vi.spyOn(rm, 'addResult')
    capturedCallback({ Result: { value: { resultId: 'from-event-001' } } })
    expect(addResultSpy).toHaveBeenCalled()
  })
})
