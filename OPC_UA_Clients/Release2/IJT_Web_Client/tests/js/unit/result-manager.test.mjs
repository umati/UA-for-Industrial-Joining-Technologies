import { describe, expect, it, vi } from 'vitest'
import { ResultManager } from '../../../Javascripts/ijt-support/Results/ResultManager.mjs'

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
})
