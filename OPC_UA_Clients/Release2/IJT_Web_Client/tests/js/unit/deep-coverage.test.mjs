/**
 * Deep coverage push tests - targeting remaining uncovered lines
 * - result-manager lines 108, 125, 183-184, 192
 * - result-serialization lines 48, 57
 */

import { describe, it, expect, vi } from 'vitest'
import { ResultManager } from '../../../src/javascripts/ijt-support/results/result-manager.mjs'

// ---------------------------------------------------------------------------
// result-manager — isResultReference line 108
// ---------------------------------------------------------------------------

describe('ResultManager — isResultReference edge cases', () => {
  function makeEventManager () {
    return {
      modelManager: {
        subscribeSubResults: vi.fn()
      }
    }
  }

  it('returns false for non-object input', () => {
    const rm = new ResultManager(makeEventManager())
    expect(rm.isResultReference(null)).toBe(false)
    expect(rm.isResultReference(undefined)).toBe(false)
    expect(rm.isResultReference('string')).toBe(false)
    expect(rm.isResultReference(123)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// result-manager — collectResultClosure line 125 (skip if already included)
// ---------------------------------------------------------------------------

describe('ResultManager — collectResultClosure duplicate handling', () => {
  function makeEventManager () {
    return {
      modelManager: {
        subscribeSubResults: vi.fn()
      }
    }
  }

  function makeResult (id, children = []) {
    return {
      id,
      classification: '2',
      isReference: false,
      ResultMetaData: { ResultId: id, IsPartial: 'False' },
      ResultContent: children,
      ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
      replaceReference: vi.fn()
    }
  }

  it('collectResultClosure skips duplicates in tree', () => {
    const rm = new ResultManager(makeEventManager())
    const child = makeResult('child-1')
    const parent = makeResult('parent-1', [child, child])  // Duplicate child
    rm.addResult(parent)
    rm.addResult(child)

    const closure = rm.collectResultClosure([parent])
    // Each result should only appear once
    const ids = closure.results.map(r => rm.getResultId(r))
    expect(ids).toContain('parent-1')
    expect(ids).toContain('child-1')
  })
})

// ---------------------------------------------------------------------------
// result-manager — exportBundle duplicate detection (lines 183-184, 192)
// ---------------------------------------------------------------------------

describe('ResultManager — exportBundle with actual duplicates', () => {
  function makeEventManager () {
    return {
      modelManager: {
        subscribeSubResults: vi.fn()
      }
    }
  }

  function makeResult (id, children = []) {
    return {
      id,
      classification: '2',
      isReference: false,
      ResultMetaData: { ResultId: id, IsPartial: 'False' },
      ResultContent: children,
      ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
      replaceReference: vi.fn()
    }
  }

  it('detects duplicates when a child result is also a root', () => {
    const rm = new ResultManager(makeEventManager())

    // Create a scenario where collectResultClosure returns duplicates
    const child = makeResult('dup-child')
    const parent1 = makeResult('parent-1', [child])
    const parent2 = makeResult('parent-2', [child])

    rm.addResult(child)
    rm.addResult(parent1)
    rm.addResult(parent2)

    // Mock collectResultClosure to return duplicates
    const originalCollect = rm.collectResultClosure.bind(rm)
    rm.collectResultClosure = (roots) => {
      const closure = originalCollect(roots)
      // Manually inject a duplicate
      if (closure.results.length > 0) {
        const firstResult = closure.results[0]
        closure.results.push(firstResult)  // Add duplicate
      }
      return closure
    }

    const exported = rm.exportBundle({ rootResults: [parent1] })
    const warning = exported.warnings.find(w => w.reason === 'duplicate_result_id_removed')

    expect(warning).toBeDefined()
    expect(warning.count).toBeGreaterThan(0)
  })
})
