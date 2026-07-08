/**
 * Extended unit tests for result-manager.mjs
 * Covers: subscribe/notify, resolve(), getUnfinished(), handlePartial false-branch
 */

import { describe, it, expect, vi } from 'vitest'
import { ResultManager } from '../../../src/javascripts/ijt-support/results/result-manager.mjs'
import { createResultBundle } from '../../../src/javascripts/ijt-support/results/result-serialization.mjs'

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

  it('uses explicit and direct max storage settings when they are valid', () => {
    const explicitProvider = {
      getMaxStoredResults: vi.fn(() => '7'),
      settings: { maxstoredresults: 3 },
      maxStoredResults: 2
    }
    const directProvider = {
      getMaxStoredResults: vi.fn(() => 'not-a-number'),
      settings: { maxstoredresults: 0 },
      maxStoredResults: 5
    }

    expect(new ResultManager(makeEventManager(), explicitProvider).getMaxStoredResults()).toBe(7)
    expect(new ResultManager(makeEventManager(), directProvider).getMaxStoredResults()).toBe(5)
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

  it('notifies evicted results in oldest-to-newest order with storage-limit payload', () => {
    const rm = new ResultManager(makeEventManager(), makeSettingsProvider(2))
    const evictedPayloads = []
    rm.subscribeEvicted((payload) => {
      evictedPayloads.push(payload)
    })

    const r1 = makeResult('evict-1', '1')
    const r2 = makeResult('evict-2', '2')
    const r3 = makeResult('evict-3', '3')
    const r4 = makeResult('evict-4', '4')

    rm.addResult(r1)
    rm.addResult(r2)
    rm.addResult(r3)
    rm.addResult(r4)

    expect(evictedPayloads).toHaveLength(2)
    expect(evictedPayloads[0]).toMatchObject({
      reason: 'storage-limit',
      resultId: 'evict-1',
      classification: '1',
      uniqueCounter: 0
    })
    expect(evictedPayloads[0].result).toBe(r1)
    expect(evictedPayloads[1]).toMatchObject({
      reason: 'storage-limit',
      resultId: 'evict-2',
      classification: '2',
      uniqueCounter: 1
    })
    expect(evictedPayloads[1].result).toBe(r2)
  })

  it('supports subscribeRemoved as alias of subscribeEvicted', () => {
    const rm = new ResultManager(makeEventManager(), makeSettingsProvider(1))
    const removedCb = vi.fn()
    rm.subscribeRemoved(removedCb)

    rm.addResult(makeResult('alias-1', '1'))
    rm.addResult(makeResult('alias-2', '1'))

    expect(removedCb).toHaveBeenCalledOnce()
    const firstPayload = removedCb.mock.calls[0][0]
    expect(firstPayload.reason).toBe('storage-limit')
    expect(firstPayload.resultId).toBe('alias-1')
  })
})

describe('ResultManager - export helpers', () => {
  it('returns null when every stored result is partial or a reference', () => {
    const rm = new ResultManager(makeEventManager())
    rm.addResult(makeResult('only-partial', '1', 'True'))
    rm.addResult(makeRefResult('only-reference'))

    expect(rm.getLatestFullResult()).toBeNull()
  })

  it('uses type filters and unresolved roots when exporting bundles', () => {
    const rm = new ResultManager(makeEventManager())
    const typeOne = makeResult('type-one', '1')
    const typeTwo = makeResult('type-two', '2')
    rm.addResult(typeOne)
    rm.addResult(typeTwo)

    const typeFiltered = rm.exportBundle({ typeFilter: 1 })
    const unresolved = rm.exportBundle({ includeUnresolved: true })

    expect(typeFiltered.selectedRootCount).toBe(1)
    expect(typeFiltered.bundle.results[0].ResultMetaData.ResultId).toBe('type-one')
    expect(unresolved.selectedRootCount).toBeGreaterThanOrEqual(2)
  })

  it('ignores falsy roots, null children, and roots without stable result ids', () => {
    const rm = new ResultManager(makeEventManager())
    const child = makeResult('duplicate-child', '1', 'False', [])
    child.ResultMetaData.CreationTime = '2026-01-01T00:00:00.000Z'
    const parent = makeResult('duplicate-parent', '4', 'False', [
      null,
      child
    ])
    const missingResultId = {
      id: 'id-only-root',
      ResultMetaData: {},
      ResultContent: [],
      ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } }
    }

    const exported = rm.exportBundle({ rootResults: [null, parent, missingResultId] })

    expect(exported.bundle.results.map((item) => item.ResultMetaData.ResultId))
      .toEqual(['duplicate-parent', 'duplicate-child'])
    expect(exported.selectedRootCount).toBe(2)
  })

  it('returns latest full result when latest is partial', () => {
    const rm = new ResultManager(makeEventManager())
    const full = makeResult('full-1', '1', 'False')
    const partial = makeResult('partial-1', '1', 'True')
    rm.addResult(full)
    rm.addResult(partial)
    expect(rm.getLatestFullResult()).toBe(full)
  })

  it('collects closure through referenced descendants', () => {
    const rm = new ResultManager(makeEventManager())
    const child = makeResult('child-a', '1', 'False', [])
    const parent = makeResult('parent-a', '4', 'False', [
      {
        id: 'child-a',
        isReference: true,
        ResultMetaData: { ResultId: 'child-a' },
        ResultContent: [],
        ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
        replaceReference: vi.fn()
      }
    ])
    rm.addResult(child)
    const closure = rm.collectResultClosure([parent])
    expect(closure.results.some((x) => x.id === 'parent-a')).toBe(true)
    expect(closure.results.some((x) => x.id === 'child-a')).toBe(true)
    expect(closure.warnings).toHaveLength(0)
  })

  it('reports warning when referenced descendant is missing during export', () => {
    const rm = new ResultManager(makeEventManager())
    const parent = makeResult('parent-missing', '4', 'False', [
      {
        id: 'missing-child',
        isReference: true,
        ResultMetaData: { ResultId: 'missing-child' },
        ResultContent: [],
        ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
        replaceReference: vi.fn()
      }
    ])
    const exported = rm.exportBundle({ rootResults: [parent] })
    expect(exported.warnings).toHaveLength(1)
    expect(exported.warnings[0].reason).toBe('missing_referenced_subresult')
  })

  it('keeps nested descendants embedded so export stays self-contained', () => {
    const rm = new ResultManager(makeEventManager())
    const child = makeResult('child-compact', '1', 'False', [])
    const parent = makeResult('parent-compact', '4', 'False', [child])
    rm.addResult(child)
    rm.addResult(parent)

    const exported = rm.exportBundle({ rootResults: [parent] })
    const exportedParent = exported.bundle.results.find((x) => x?.ResultMetaData?.ResultId === 'parent-compact')
    const exportedChild = exported.bundle.results.find((x) => x?.ResultMetaData?.ResultId === 'child-compact')

    expect(exportedParent).toBeTruthy()
    expect(exportedChild).toBeTruthy()
    expect(exportedParent.ResultContent).toHaveLength(1)
    expect(exportedParent.ResultContent[0]?.ResultMetaData?.ResultId).toBe('child-compact')
    expect(Array.isArray(exportedParent.ResultContent[0]?.ResultContent)).toBe(true)
  })
})

describe('ResultManager - bundle import', () => {
  it('rejects invalid import modes before mutating stored results', () => {
    const rm = new ResultManager(makeEventManager())
    const bundle = createResultBundle([])

    expect(() => rm.importBundleFromText(JSON.stringify(bundle), { mode: 'merge' }))
      .toThrow("Invalid import mode 'merge'")
    expect(rm.getAllResultsChronological()).toHaveLength(0)
  })

  it('imports valid results and skips invalid ones in best-effort mode', () => {
    const rm = new ResultManager(makeEventManager())
    vi.spyOn(rm, 'createRuntimeResultFromPayload').mockImplementation((payload) =>
      makeResult(payload.ResultMetaData.ResultId, payload.ResultMetaData.Classification || '1', 'False', payload.ResultContent || [])
    )

    const bundle = createResultBundle([
      { ResultMetaData: { ResultId: 'ok-1', Classification: '1' }, ResultContent: [] },
      { ResultMetaData: null, ResultContent: [] }
    ])
    const summary = rm.importBundleFromText(JSON.stringify(bundle), { mode: 'replace', strict: false })

    expect(summary.total).toBe(2)
    expect(summary.imported).toBe(1)
    expect(summary.skipped).toBe(1)
    expect(summary.skipReasons.invalid_result_shape).toBe(1)
    expect(rm.resultFromId('ok-1')).toBeTruthy()
  })

  it('supports skip-duplicates mode with deterministic skip reason', () => {
    const rm = new ResultManager(makeEventManager())
    vi.spyOn(rm, 'createRuntimeResultFromPayload').mockImplementation((payload) =>
      makeResult(payload.ResultMetaData.ResultId, payload.ResultMetaData.Classification || '1')
    )

    const bundle = createResultBundle([
      { ResultMetaData: { ResultId: 'dup-1', Classification: '1' }, ResultContent: [] },
      { ResultMetaData: { ResultId: 'dup-1', Classification: '1' }, ResultContent: [] }
    ])
    const summary = rm.importBundleFromText(JSON.stringify(bundle), { mode: 'skip-duplicates', strict: false })

    expect(summary.imported).toBe(1)
    expect(summary.skipped).toBe(1)
    expect(summary.skipReasons.duplicate_result_id).toBe(1)
  })

  it('counts replacements in replace mode', () => {
    const rm = new ResultManager(makeEventManager())
    const existing = makeResult('replace-1', '1', 'True', [])
    rm.addResult(existing)
    vi.spyOn(rm, 'createRuntimeResultFromPayload').mockImplementation((payload) =>
      makeResult(payload.ResultMetaData.ResultId, payload.ResultMetaData.Classification || '1', 'False')
    )

    const bundle = createResultBundle([
      { ResultMetaData: { ResultId: 'replace-1', Classification: '1' }, ResultContent: [] }
    ])
    const summary = rm.importBundleFromText(JSON.stringify(bundle), { mode: 'replace' })

    expect(summary.replaced).toBe(1)
    expect(summary.imported).toBe(0)
  })

  it('reports missing ids and conversion errors as best-effort skips', () => {
    const rm = new ResultManager(makeEventManager())
    vi.spyOn(rm, 'createRuntimeResultFromPayload').mockImplementation(() => {
      throw new Error('cannot convert')
    })

    const bundle = createResultBundle([
      { ResultMetaData: { Classification: '1' }, ResultContent: [] },
      { ResultMetaData: { ResultId: 'bad-model', Classification: '1' }, ResultContent: [] }
    ])
    const summary = rm.importBundleFromText(JSON.stringify(bundle), { strict: false })

    expect(summary.imported).toBe(0)
    expect(summary.skipped).toBe(2)
    expect(summary.skipReasons.missing_result_id).toBe(1)
    expect(summary.skipReasons.invalid_result_shape).toBe(1)
  })

  it('fails fast for missing ids and conversion errors in strict mode', () => {
    const rm = new ResultManager(makeEventManager())
    const missingIdBundle = createResultBundle([
      { ResultMetaData: { Classification: '1' }, ResultContent: [] }
    ])
    expect(() => rm.importBundleFromText(JSON.stringify(missingIdBundle), { strict: true }))
      .toThrow('Import failed: missing_result_id')

    vi.spyOn(rm, 'createRuntimeResultFromPayload').mockImplementation(() => {
      throw new Error('strict conversion failure')
    })
    const conversionBundle = createResultBundle([
      { ResultMetaData: { ResultId: 'strict-bad', Classification: '1' }, ResultContent: [] }
    ])
    expect(() => rm.importBundleFromText(JSON.stringify(conversionBundle), { strict: true }))
      .toThrow('strict conversion failure')
  })

  it('fails fast in strict mode for invalid result shape', () => {
    const rm = new ResultManager(makeEventManager())
    const bundle = createResultBundle([
      { ResultMetaData: null, ResultContent: [] }
    ])
    expect(() => rm.importBundleFromText(JSON.stringify(bundle), { strict: true })).toThrow('Import failed: invalid_result_shape')
  })
})

describe('ResultManager - runtime model and notification edge cases', () => {
  it('returns raw payloads when no model manager is available for conversion', () => {
    const rm = new ResultManager({ modelManager: { subscribeSubResults: vi.fn() } })
    rm.eventManager = {}
    const payload = { ResultMetaData: { ResultId: 'raw', Classification: '1' }, ResultContent: [] }

    expect(rm.createRuntimeResultFromPayload(payload)).toBe(payload)
  })

  it('initializes missing client rebuild state before storing results', () => {
    const rm = new ResultManager(makeEventManager())
    const missingClientData = {
      id: 'missing-client-data',
      classification: '1',
      ResultMetaData: { ResultId: 'missing-client-data', IsPartial: 'False' },
      ResultContent: [],
      replaceReference: vi.fn()
    }
    const missingRebuildState = {
      id: 'missing-rebuild-state',
      classification: '1',
      ResultMetaData: { ResultId: 'missing-rebuild-state', IsPartial: 'False' },
      ResultContent: [],
      ClientData: {},
      replaceReference: vi.fn()
    }

    rm.addResult(missingClientData)
    rm.addResult(missingRebuildState)

    expect(missingClientData.ClientData.rebuildState.partial).toBe(false)
    expect(missingRebuildState.ClientData.rebuildState.partial).toBe(false)
  })

  it('supports removed-result subscribers and ignores null eviction notifications', () => {
    const rm = new ResultManager(makeEventManager())
    const removed = vi.fn()
    rm.subscribeRemoved(removed)

    expect(() => rm.notifyEvictedResult(null)).not.toThrow()
    rm.notifyEvictedResult(makeResult('removed-1', '1'), 'manual')

    expect(removed).toHaveBeenCalledWith(expect.objectContaining({
      reason: 'manual',
      resultId: 'removed-1'
    }))
  })
})
