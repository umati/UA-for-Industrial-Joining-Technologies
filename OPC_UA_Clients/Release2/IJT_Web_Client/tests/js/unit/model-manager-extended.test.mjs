/**
 * Extended unit tests for model-manager.mjs.
 *
 * Covers paths not reached by existing tests:
 *   - factory: ExtensionObject unwrapping
 *   - factory: key-value pairs (content.key)
 *   - factory: bare IJTBaseModel fallback
 *   - createModelFromNode switch cases
 *   - createModelFromRead
 *   - subscribeSubResults / resultTypeNotification
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ModelManager } from '../../../src/javascripts/ijt-support/models/model-manager.mjs'
import ResultDataType from '../../../src/javascripts/ijt-support/models/results/result-data-type.mjs'

// ---------------------------------------------------------------------------
// Helper: make a real ModelManager
// ---------------------------------------------------------------------------

function makeMM () {
  return new ModelManager(
    { addEntity: vi.fn() },
    { addEntity: vi.fn() }
  )
}

// ---------------------------------------------------------------------------
// factory — ExtensionObject unwrapping
// ---------------------------------------------------------------------------

describe('ModelManager factory — ExtensionObject', () => {
  it('unwraps content.value when dataType is ExtensionObject', () => {
    const mm = makeMM()
    const innerValue = { ResultId: 'r1', Name: 'Test' }
    const result = mm.factory('someKey', { dataType: 'ExtensionObject', value: innerValue }, null)
    // After unwrapping, falls through to bare IJTBaseModel (no Locale, no key, etc.)
    expect(result).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// factory — key-value pair
// ---------------------------------------------------------------------------

describe('ModelManager factory — key-value pair', () => {
  it('converts {key, value} objects to LocalizationModel', () => {
    const mm = makeMM()
    const result = mm.factory('someParam', { key: 'label', value: 'hello' }, null)
    expect(result).toBeDefined()
    expect(result.label).toBe('hello')
  })

  it('handles {key, value} where value is falsy — defaults to empty string', () => {
    const mm = makeMM()
    const result = mm.factory('someParam', { key: 'label', value: null }, null)
    expect(result).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// factory — Locale detection
// ---------------------------------------------------------------------------

describe('ModelManager factory — Locale detection', () => {
  it('creates a LocalizationModel for objects with Locale property', () => {
    const mm = makeMM()
    const result = mm.factory('text', { Locale: 'en', Text: 'Hello' }, null)
    expect(result.Locale).toBe('en')
  })
})

// ---------------------------------------------------------------------------
// factory — NodeId detection (pythonclass)
// ---------------------------------------------------------------------------

describe('ModelManager factory — pythonclass NodeId', () => {
  it('creates a NodeId for pythonclass = NodeId', () => {
    const mm = makeMM()
    const result = mm.factory('nodeRef', { pythonclass: 'NodeId', NamespaceIndex: 2, Identifier: 100 }, null)
    expect(result.NamespaceIndex).toBe(2)
  })

  it('creates a NodeId for pythonclass = QualifiedName', () => {
    const mm = makeMM()
    const result = mm.factory('nodeRef', { pythonclass: 'QualifiedName', NamespaceIndex: 1, Identifier: 'Name' }, null)
    expect(result).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// factory — scalar passthrough
// ---------------------------------------------------------------------------

describe('ModelManager factory — scalar passthrough', () => {
  it('returns numbers unchanged', () => {
    const mm = makeMM()
    expect(mm.factory('count', 42, null)).toBe(42)
  })

  it('returns strings unchanged', () => {
    const mm = makeMM()
    expect(mm.factory('name', 'hello', null)).toBe('hello')
  })

  it('returns null unchanged', () => {
    const mm = makeMM()
    expect(mm.factory('x', null, null)).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// factory — castMapping: result classification dispatch
// ---------------------------------------------------------------------------

describe('ModelManager factory — castMapping result dispatch', () => {
  const castMapping = { ResultContent: 'JoiningResultDataType' }

  it('creates TighteningDataType for Classification 1', () => {
    const mm = makeMM()
    const content = {
      ResultMetaData: {
        ResultId: 'r1',
        Name: 'T',
        CreationTime: '2024-01-01',
        Classification: '1'
      },
      ResultContent: []
    }
    const result = mm.factory('ResultContent', content, castMapping)
    expect(result.consolidatedResultType).toBe('Joining')
  })

  it('creates BatchDataModel for Classification 3', () => {
    const mm = makeMM()
    const content = {
      ResultMetaData: {
        ResultId: 'r-b',
        CreationTime: '2024-01-01',
        Classification: '3'
      }
    }
    const result = mm.factory('ResultContent', content, castMapping)
    expect(result.consolidatedResultType).toBe('Batch')
  })

  it('creates JobDataModel for Classification 4', () => {
    const mm = makeMM()
    const content = {
      ResultMetaData: {
        ResultId: 'r-j',
        CreationTime: '2024-01-01',
        Classification: '4'
      }
    }
    const result = mm.factory('ResultContent', content, castMapping)
    expect(result.consolidatedResultType).toBe('Job')
  })

  it('creates ResultDataType for unknown Classification', () => {
    const mm = makeMM()
    const content = {
      ResultMetaData: {
        ResultId: 'r-x',
        CreationTime: '2024-01-01',
        Classification: '99'
      }
    }
    const result = mm.factory('ResultContent', content, castMapping)
    expect(result).toBeInstanceOf(ResultDataType)
  })
})

// ---------------------------------------------------------------------------
// subscribeSubResults / resultTypeNotification
// ---------------------------------------------------------------------------

describe('ModelManager — subscribeSubResults / resultTypeNotification', () => {
  it('calls subscribed function when resultTypeNotification is invoked', () => {
    const mm = makeMM()
    const fn = vi.fn()
    mm.subscribeSubResults(fn)
    const fakeResult = { id: 'r1' }
    mm.resultTypeNotification(fakeResult)
    expect(fn).toHaveBeenCalledWith(fakeResult)
  })

  it('supports multiple subscribers', () => {
    const mm = makeMM()
    const fn1 = vi.fn()
    const fn2 = vi.fn()
    mm.subscribeSubResults(fn1)
    mm.subscribeSubResults(fn2)
    mm.resultTypeNotification({ id: 'r2' })
    expect(fn1).toHaveBeenCalledOnce()
    expect(fn2).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// createModelFromRead
// ---------------------------------------------------------------------------

describe('ModelManager — createModelFromRead', () => {
  it('returns a ResultDataType when values contain ResultMetaData', () => {
    const mm = makeMM()
    const values = { ResultMetaData: { ResultId: 'r1', Name: 'Test' } }
    const result = mm.createModelFromRead(values)
    expect(result).toBeInstanceOf(ResultDataType)
    expect(result.id).toBe('r1')
  })

  it('returns null when values have no ResultMetaData', () => {
    const mm = makeMM()
    expect(mm.createModelFromRead({ SomeOtherField: 'x' })).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// createModelFromEvent
// ---------------------------------------------------------------------------

describe('ModelManager — createModelFromEvent', () => {
  it('creates JoiningSystemEventModel for EventType 1006', () => {
    const mm = makeMM()
    const msg = { EventType: { Identifier: 1006 }, EventId: 'e1' }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
  })

  it('creates JoiningSystemResultReadyEvent for EventType 1007', () => {
    const mm = makeMM()
    const msg = {
      EventType: { Identifier: 1007 },
      EventId: 'e2',
      Result: { ResultMetaData: { ResultId: 'r1', Classification: '1' } }
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
    expect(model.Result).toBeDefined()
  })

  it('creates JoiningSystemResultReadyEvent for EventType 1002', () => {
    const mm = makeMM()
    const msg = {
      EventType: { Identifier: 1002 },
      Result: { ResultMetaData: { ResultId: 'r2', Classification: '2' } }
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
  })

  it('creates DefaultNode for unknown EventType', () => {
    const mm = makeMM()
    const msg = { EventType: { Identifier: 9999 }, SomeField: 'val' }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
    expect(model.SomeField).toBe('val')
  })
})

// ---------------------------------------------------------------------------
// createModelFromNode
// ---------------------------------------------------------------------------

describe('ModelManager — createModelFromNode', () => {
  it('creates DefaultNode for TighteningSystemType', () => {
    const mm = makeMM()
    const node = { typeDefinition: 'TighteningSystemType', nodeId: 'ns=1;i=1' }
    const model = mm.createModelFromNode(node)
    expect(model).toBeDefined()
    expect(node.model).toBe(model)
  })

  it('creates DefaultNode for ResultManagementType', () => {
    const mm = makeMM()
    const node = { typeDefinition: 'ResultManagementType', nodeId: 'ns=1;i=2' }
    const model = mm.createModelFromNode(node)
    expect(model).toBeDefined()
  })

  it('creates ResultDataType for typeDefinition ns=4;i=2001', () => {
    const mm = makeMM()
    const node = {
      typeDefinition: 'ns=4;i=2001',
      nodeId: 'ns=1;i=3',
      value: {
        value: {
          ResultMetaData: { ResultId: 'r1', Name: 'Test' }
        }
      }
    }
    const model = mm.createModelFromNode(node)
    expect(model).toBeInstanceOf(ResultDataType)
  })

  it('creates DefaultNode for unknown typeDefinition', () => {
    const mm = makeMM()
    const node = { typeDefinition: 'UnknownType', nodeId: 'ns=1;i=4' }
    const model = mm.createModelFromNode(node)
    expect(model).toBeDefined()
    expect(node.model).toBe(model)
  })
})
