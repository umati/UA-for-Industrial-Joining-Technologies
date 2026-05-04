import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  createResultBundle,
  parseResultBundle,
  RESULT_BUNDLE_CONSTANTS,
  serializeResultForStorage,
  validateResultBundle
} from '../../../src/javascripts/ijt-support/results/result-serialization.mjs'

describe('result-serialization', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('serializes result payload and removes runtime keys', () => {
    const serialized = serializeResultForStorage({
      ResultMetaData: { ResultId: 'r1', Classification: '1' },
      ResultContent: [],
      ClientData: { rebuildState: { partial: false } },
      uniqueCounter: 10,
      clientLatestRecievedTime: 1234
    })

    expect(serialized.ResultMetaData.ResultId).toBe('r1')
    expect(serialized.ClientData).toBeUndefined()
    expect(serialized.uniqueCounter).toBeUndefined()
    expect(serialized.clientLatestRecievedTime).toBeUndefined()
  })

  it('parses valid bundle and returns normalized results array', () => {
    const bundle = createResultBundle([
      { ResultMetaData: { ResultId: 'r2', Classification: '3' }, ResultContent: [] }
    ])
    const parsed = parseResultBundle(JSON.stringify(bundle))
    expect(parsed.results).toHaveLength(1)
    expect(parsed.results[0].ResultMetaData.ResultId).toBe('r2')
  })

  it('rejects malformed bundle type', () => {
    const invalid = {
      type: 'wrong',
      version: 1,
      results: []
    }
    expect(() => parseResultBundle(JSON.stringify(invalid))).toThrow()
  })

  it('rejects dangerous prototype keys in payload by sanitizing them out', () => {
    const bundle = createResultBundle([
      {
        ResultMetaData: { ResultId: 'r3', Classification: '1' },
        ResultContent: [],
        __proto__: { polluted: true }
      }
    ])
    const parsed = parseResultBundle(JSON.stringify(bundle))
    expect(parsed.results).toHaveLength(1)
    expect({}.polluted).toBeUndefined()
  })

  it('accepts legacy bundle object without type/version', () => {
    const legacy = {
      exportedAt: '2026-01-01T00:00:00.000Z',
      results: [
        { ResultMetaData: { ResultId: 'legacy-1', Classification: '1' }, ResultContent: [] }
      ]
    }
    const parsed = parseResultBundle(JSON.stringify(legacy))
    expect(parsed.legacy).toBe(true)
    expect(parsed.results).toHaveLength(1)
  })

  it('accepts legacy raw array format', () => {
    const legacy = [
      { ResultMetaData: { ResultId: 'legacy-2', Classification: '1' }, ResultContent: [] }
    ]
    const parsed = parseResultBundle(JSON.stringify(legacy))
    expect(parsed.legacy).toBe(true)
    expect(parsed.results).toHaveLength(1)
  })

  it('rejects circular payloads to prevent infinite recursion', () => {
    const cyclic = {
      ResultMetaData: { ResultId: 'loop-1', Classification: '1' },
      ResultContent: []
    }
    cyclic.loop = cyclic
    expect(() => serializeResultForStorage(cyclic)).toThrow(/Circular reference detected/)
    expect(() => serializeResultForStorage(cyclic)).toThrow(/\.loop'/)
  })

  it('skips parent relations instead of recursing upward', () => {
    const top = {
      ResultMetaData: { ResultId: 'top-1', Classification: '4' },
      ResultContent: []
    }
    const child = {
      ResultMetaData: { ResultId: 'child-1', Classification: '1' },
      ResultContent: [],
      ParentResult: top,
      parent: top
    }
    top.ResultContent.push(child)

    const serialized = serializeResultForStorage(top)
    expect(serialized.ResultContent[0].ParentResult).toBeUndefined()
    expect(serialized.ResultContent[0].parent).toBeUndefined()
  })

  it('does not persist linkedValue shortcuts and keeps only stable ids', () => {
    const serialized = serializeResultForStorage({
      ResultMetaData: { ResultId: 'r-link-1', Classification: '1' },
      ResultContent: [{
        Trace: {
          StepTraces: [{
            StepResultId: {
              type: 'linkedValue',
              value: 'step-result-1',
              link: { StepResultId: 'step-result-1' }
            }
          }]
        },
        StepResults: [{
          StepResultId: 'step-result-1',
          StepTraceId: {
            type: 'linkedValue',
            value: 'step-trace-1',
            link: { stepTraceId: 'step-trace-1' }
          }
        }]
      }]
    })

    expect(serialized.ResultContent[0].Trace.StepTraces[0].StepResultId).toBe('step-result-1')
    expect(serialized.ResultContent[0].StepResults[0].StepTraceId).toBe('step-trace-1')
  })

  it('returns null for unsupported storage shapes and adds missing ResultContent', () => {
    expect(serializeResultForStorage(null)).toBeNull()
    expect(serializeResultForStorage('not-a-result')).toBeNull()
    expect(serializeResultForStorage({ ResultContent: [] })).toBeNull()

    const serialized = serializeResultForStorage({
      ResultMetaData: { ResultId: 'r-minimal', Classification: '1' }
    })
    expect(serialized.ResultContent).toEqual([])
  })

  it('strips functions and private runtime keys during storage serialization', () => {
    const serialized = serializeResultForStorage({
      ResultMetaData: { ResultId: 'r-private', Classification: '1' },
      ResultContent: [],
      transform: () => 'runtime-only',
      _localSelection: true
    })

    expect(serialized.transform).toBeUndefined()
    expect(serialized._localSelection).toBeUndefined()
  })

  it('rejects payloads deeper than the configured import depth', () => {
    const payload = {
      ResultMetaData: { ResultId: 'r-depth', Classification: '1' },
      ResultContent: [{ nested: true }]
    }

    expect(() => serializeResultForStorage(payload, { maxDepth: 1 }))
      .toThrow(/Max serialization depth exceeded/)
  })

  it('uses string length for file-size checks when TextEncoder is unavailable', () => {
    vi.stubGlobal('TextEncoder', undefined)
    const bundle = createResultBundle([
      { ResultMetaData: { ResultId: 'r-size', Classification: '1' }, ResultContent: [] }
    ])
    const raw = JSON.stringify(bundle)

    expect(() => parseResultBundle(raw, { maxFileSizeBytes: raw.length - 1 }))
      .toThrow(/Import file exceeds size limit/)
  })

  it('rejects invalid parse inputs and malformed JSON with actionable messages', () => {
    expect(() => parseResultBundle({})).toThrow('Import payload must be text')
    expect(() => parseResultBundle('{bad-json')).toThrow(/Invalid JSON/)
  })

  it('rejects unsupported bundle versions and oversized result sets', () => {
    expect(() => validateResultBundle({
      type: RESULT_BUNDLE_CONSTANTS.EXPORT_TYPE,
      version: 999,
      results: []
    })).toThrow("Unsupported bundle version '999'")

    expect(() => validateResultBundle({
      type: RESULT_BUNDLE_CONSTANTS.EXPORT_TYPE,
      version: RESULT_BUNDLE_CONSTANTS.EXPORT_VERSION,
      results: [{ ResultMetaData: { ResultId: 'one' }, ResultContent: [] }]
    }, { maxResultsCount: 0 })).toThrow(/Too many results in bundle/)
  })
})
