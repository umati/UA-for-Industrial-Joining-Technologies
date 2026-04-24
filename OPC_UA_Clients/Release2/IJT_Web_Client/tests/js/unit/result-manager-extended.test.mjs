/**
 * Extended unit tests for result-manager.mjs
 * Covers: subscribe/notify, resolve(), getUnfinished(), handlePartial false-branch
 */

import { describe, it, expect, vi } from 'vitest'
import { ResultManager } from '../../../src/javascripts/ijt-support/results/result-manager.mjs'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeEventManager () {
  return {
    modelManager: {
      subscribeSubResults: vi.fn()
    }
  }
}

function makeSettingsProvider (maxStoredResults) {
  return {
    settings: {
      maxstoredresults: maxStoredResults
    }
  }
}

function makeResult (id, classification = '2', partial = 'False', content = []) {
  return {
    id,
    classification,
    isReference: false,
    ResultMetaData: { ResultId: id, IsPartial: partial },
    ResultContent: content,
    ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
    replaceReference: vi.fn()
  }
}

function makeRefResult (id) {
  return {
    id,
    classification: '0',
    isReference: true,
    ResultMetaData: { ResultId: id, IsPartial: 'False' },
    ResultContent: [],
    ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
    replaceReference: vi.fn()
  }
}

// ---------------------------------------------------------------------------
// subscribe — callback is invoked on addResult
// ---------------------------------------------------------------------------

describe('ResultManager — subscribe / addResult notify', () => {
  it('calls subscriber when a new result is added', () => {
    const rm = new ResultManager(makeEventManager())
    const cb = vi.fn()
    rm.subscribe(cb)
    const r = makeResult('r-1')
    rm.addResult(r)
    expect(cb).toHaveBeenCalledWith(r)
  })

  it('supports multiple subscribers', () => {
    const rm = new ResultManager(makeEventManager())
    const cb1 = vi.fn()
    const cb2 = vi.fn()
    rm.subscribe(cb1)
    rm.subscribe(cb2)
    rm.addResult(makeResult('r-multi'))
    expect(cb1).toHaveBeenCalledOnce()
    expect(cb2).toHaveBeenCalledOnce()
  })

  it('continues notifying later subscribers even if an earlier one throws', () => {
    const rm = new ResultManager(makeEventManager())
    const throwing = vi.fn(() => { throw new Error('boom') })
    const good = vi.fn()
    rm.subscribe(throwing)
    rm.subscribe(good)
    expect(() => rm.addResult(makeResult('r-err'))).not.toThrow()
    expect(good).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// resultFromId with selectType
// ---------------------------------------------------------------------------

describe('ResultManager — resultFromId with selectType', () => {
  it('finds result using narrowed type search', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('r-narrow', '1')
    rm.addResult(r)
    expect(rm.resultFromId('r-narrow', 1)).toBe(r)
  })

  it('returns undefined when selectType is wrong', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('r-type', '1')
    rm.addResult(r)
    expect(rm.resultFromId('r-type', 2)).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// resolve
// ---------------------------------------------------------------------------

describe('ResultManager — resolve', () => {
  it('resolves a reference result by looking up by id', () => {
    const rm = new ResultManager(makeEventManager())
    const realResult = makeResult('ref-id')
    rm.addResult(realResult)

    const ref = makeRefResult('ref-id')
    const resolved = rm.resolve(ref)
    expect(resolved).toBe(realResult)
  })

  it('marks resolved=true when all children are non-references', () => {
    const rm = new ResultManager(makeEventManager())
    const child = { ...makeResult('child-1'), isReference: false, ResultContent: [] }
    child.ClientData = { rebuildState: { claimed: false, resolved: false, partial: false } }
    const parent = makeResult('parent-1', '3', 'False', [child])
    parent.isReference = false

    const result = rm.resolve(parent)
    expect(result).toBeTruthy()
    expect(parent.ClientData.rebuildState.resolved).toBe(true)
  })

  it('marks claimed=true on resolved child', () => {
    const rm = new ResultManager(makeEventManager())
    const child = makeResult('child-2')
    child.isReference = false
    child.ResultContent = []
    rm.addResult(child)

    const parent = makeResult('parent-2', '3', 'False', [child])
    parent.isReference = false

    rm.resolve(parent)
    expect(child.ClientData.rebuildState.claimed).toBe(true)
  })

  it('returns false when a child reference cannot be resolved', () => {
    const rm = new ResultManager(makeEventManager())
    const unresolvedRef = makeRefResult('missing-id')
    const parent = makeResult('parent-3', '3', 'False', [unresolvedRef])
    parent.isReference = false

    const result = rm.resolve(parent)
    expect(result).toBe(false)
    expect(parent.ClientData.rebuildState.resolved).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// getUnfinished
// ---------------------------------------------------------------------------

describe('ResultManager — getUnfinished', () => {
  it('returns results that are not yet claimed', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('unclaimed')
    rm.addResult(r)
    const unfinished = rm.getUnfinished()
    expect(unfinished.some(x => x.id === 'unclaimed')).toBe(true)
  })

  it('includes resolved+unclaimed results', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('resolved-unclaimed')
    r.ClientData.rebuildState.claimed = false
    r.ClientData.rebuildState.resolved = true
    rm.addResult(r)
    const unfinished = rm.getUnfinished()
    expect(unfinished.some(x => x.id === 'resolved-unclaimed')).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// handlePartial — false branch (new data not larger/partial)
// ---------------------------------------------------------------------------

describe('ResultManager — handlePartial false branch', () => {
  it('returns false when new result has same or fewer items and IsPartial is not False', () => {
    const rm = new ResultManager(makeEventManager())
    const stored = makeResult('r-same', '1', 'True', [{ id: 'a' }])
    const update = makeResult('r-same', '1', 'True', [{ id: 'a' }]) // same length, still partial
    const merged = rm.handlePartial(stored, update)
    expect(merged).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// resolveOld — removes fully resolved results from unresolved list
// ---------------------------------------------------------------------------

describe('ResultManager — resolveOld', () => {
  it('removes a resolvable entry that was manually pushed into unresolved', () => {
    const rm = new ResultManager(makeEventManager())
    const r = makeResult('r-res')
    // Manually push without going through addResult so we control the state
    rm.unresolved.push(r)
    expect(rm.unresolved).toHaveLength(1)
    rm.resolveOld()
    // r has no ResultContent and isReference=false so resolve() returns it (truthy)
    expect(rm.unresolved).toHaveLength(0)
  })

  it('keeps an unresolvable reference result in unresolved', () => {
    const rm = new ResultManager(makeEventManager())
    const ref = makeRefResult('r-missing')
    // isReference=true but resultFromId('r-missing') returns undefined → not resolved
    rm.unresolved.push(ref)
    rm.resolveOld()
    expect(rm.unresolved).toHaveLength(1)
  })
})

describe('ResultManager - max storage cap', () => {
  it('uses default max storage limit when settings are missing', () => {
    const rm = new ResultManager(makeEventManager())
    expect(rm.getMaxStoredResults()).toBe(200)
  })

  it('prunes oldest results above configured limit', () => {
    const rm = new ResultManager(makeEventManager(), makeSettingsProvider(2))
    const r1 = makeResult('cap-1', '1')
    const r2 = makeResult('cap-2', '1')
    const r3 = makeResult('cap-3', '1')

    rm.addResult(r1)
    rm.addResult(r2)
    rm.addResult(r3)

    expect(rm.resultFromId('cap-1')).toBeUndefined()
    expect(rm.resultFromId('cap-2')).toBe(r2)
    expect(rm.resultFromId('cap-3')).toBe(r3)
    expect(rm.lastResult).toBe(r3)
    expect(rm.getResultOfType(1)).toHaveLength(2)
  })

  it('falls back to default when configured limit is invalid', () => {
    const rm = new ResultManager(makeEventManager(), makeSettingsProvider(0))
    expect(rm.getMaxStoredResults()).toBe(200)
  })
})
