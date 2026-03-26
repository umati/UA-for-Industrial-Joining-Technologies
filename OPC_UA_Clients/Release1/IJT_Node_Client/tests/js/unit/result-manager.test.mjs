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
