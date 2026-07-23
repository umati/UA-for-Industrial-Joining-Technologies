import { describe, expect, it, vi } from 'vitest'
import { ResultManager } from '../../../src/javascripts/ijt-support/results/result-manager.mjs'

function makeEventManager () {
  return {
    modelManager: {
      subscribeSubResults: () => {}
    }
  }
}

function makeResult (id, classification = '2', partial = 'False', content = []) {
  return {
    id,
    classification,
    ResultMetaData: { ResultId: id, IsPartial: partial },
    ResultContent: content,
    ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
    replaceReference: vi.fn()
  }
}

describe('ResultManager', () => {
  it('stores a new result and exposes it by type and latest', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('r-1', '2')

    rm.addResult(r)

    expect(rm.getLatest(2)).toBe(r)
    expect(rm.getResultOfType(2)).toContain(r)
    expect(rm.resultFromId('r-1')).toBe(r)
  })

  it('merges partial updates while preserving claimed flag', () => {
    const rm = new ResultManager(makeEventManager())

    const stored = makeResult('r-2', '1', 'True', [{ id: 'a' }])
    stored.ClientData.rebuildState.claimed = true

    const update = makeResult('r-2', '1', 'False', [{ id: 'a' }, { id: 'b' }])
    const merged = rm.handlePartial(stored, update)

    expect(merged).toBe(true)
    expect(stored.ResultContent).toHaveLength(2)
    expect(stored.ResultMetaData.IsPartial).toBe('False')
    expect(stored.ClientData.rebuildState.claimed).toBe(true)
  })

  it('handlePartial does not pollute prototype via __proto__ key', () => {
    const rm = new ResultManager(makeEventManager())
    const stored = makeResult('r-safe', '2', 'True', [])
    const evilUpdate = makeResult('r-safe', '2', 'False', [{ id: 'x' }])
    // Simulate what JSON.parse('{"__proto__":{"injected":true}}') would produce
    Object.defineProperty(evilUpdate, '__proto__', { value: { injected: true }, enumerable: true, configurable: true })
    // handlePartial must not copy __proto__ key to stored
    rm.handlePartial(stored, evilUpdate)
    const fresh = {}
    expect(fresh.injected).toBeUndefined()
  })

  it('handlePartial does not copy constructor key from update', () => {
    const rm = new ResultManager(makeEventManager())
    const stored = makeResult('r-ctor', '2', 'True', [])
    const update = makeResult('r-ctor', '2', 'False', [{ id: 'y' }])
    const originalConstructor = stored.constructor
    rm.handlePartial(stored, update)
    expect(stored.constructor).toBe(originalConstructor)
  })

  it('drops loosening results before storing or notifying subscribers when enabled', () => {
    const rm = new ResultManager(makeEventManager(), {
      getIgnoreLoosenings: () => true
    })
    const cb = vi.fn()
    rm.subscribe(cb)
    const loosening = makeResult('loosen-1', '1')
    loosening.ResultMetaData.AssemblyType = 2

    const added = rm.addResult(loosening)

    expect(added).toBe(false)
    expect(rm.resultFromId('loosen-1')).toBeUndefined()
    expect(cb).not.toHaveBeenCalled()
  })

  it('keeps non-loosening results when loosening filtering is enabled', () => {
    const rm = new ResultManager(makeEventManager(), {
      settings: { ignoreloosenings: 'true' }
    })
    const cb = vi.fn()
    rm.subscribe(cb)
    const tightening = makeResult('tighten-1', '1')
    tightening.ResultMetaData.AssemblyType = 1

    const added = rm.addResult(tightening)

    expect(added).toBe(true)
    expect(rm.resultFromId('tighten-1')).toBe(tightening)
    expect(cb).toHaveBeenCalledWith(tightening)
  })
})
