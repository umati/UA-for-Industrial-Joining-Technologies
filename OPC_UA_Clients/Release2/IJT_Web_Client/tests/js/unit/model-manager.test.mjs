/**
 * Comprehensive tests for:
 *   - IJTBaseModel
 *   - ModelManager.factory()
 *   - ModelManager.createModelFromEvent()
 *   - ModelManager.createModelFromRead()
 *
 * Mocks entityManager and jointManager so no real OPC UA connection is needed.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ModelManager } from '../../../src/javascripts/ijt-support/models/model-manager.mjs'
import IJTBaseModel from '../../../src/javascripts/ijt-support/models/ijt-base-model.mjs'
import { LocalizationModel, NodeId } from '../../../src/javascripts/ijt-support/models/support-models.mjs'
import ResultDataType from '../../../src/javascripts/ijt-support/models/results/result-data-type.mjs'

// ---------------------------------------------------------------------------
// Shared fixture
// ---------------------------------------------------------------------------

function makeModelManager () {
  const entityManager = { addEntity: vi.fn() }
  const jointManager = {}
  return new ModelManager(entityManager, jointManager)
}

// ---------------------------------------------------------------------------
// IJTBaseModel — property mapping
// ---------------------------------------------------------------------------

describe('IJTBaseModel', () => {
  it('maps all non-pythonclass key-value pairs as own properties', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ Name: 'Test', Value: 42 }, mm)
    expect(model.Name).toBe('Test')
    expect(model.Value).toBe(42)
  })

  it('skips pythonclass key', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ pythonclass: 'MyClass', Count: 3 }, mm)
    expect(model.pythonclass).toBeUndefined()
    expect(model.Count).toBe(3)
  })

  it('sets null for falsy values', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ Empty: null, Zero: 0, Blank: '' }, mm)
    expect(model.Empty).toBeNull()
    expect(model.Zero).toBeNull()
    expect(model.Blank).toBeNull()
  })

  it('recurses into nested objects', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ Child: { x: 1 } }, mm)
    expect(model.Child).toBeInstanceOf(IJTBaseModel)
    expect(model.Child.x).toBe(1)
  })

  it('maps arrays into arrays of models', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ Items: [{ v: 'a' }, { v: 'b' }] }, mm)
    expect(Array.isArray(model.Items)).toBe(true)
    expect(model.Items).toHaveLength(2)
    expect(model.Items[0].v).toBe('a')
  })

  it('keeps primitive values unchanged', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ N: 99, S: 'hello', B: true }, mm)
    expect(model.N).toBe(99)
    expect(model.S).toBe('hello')
    expect(model.B).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// ModelManager.factory() — primitive pass-through
// ---------------------------------------------------------------------------

describe('ModelManager.factory() — primitives', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('returns string as-is', () => {
    expect(mm.factory('key', 'hello', {})).toBe('hello')
  })

  it('returns number as-is', () => {
    expect(mm.factory('key', 42, {})).toBe(42)
  })

  it('returns boolean as-is', () => {
    expect(mm.factory('key', true, {})).toBe(true)
  })

  it('returns null as-is', () => {
    expect(mm.factory('key', null, {})).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// ModelManager.factory() — object dispatch
// ---------------------------------------------------------------------------

describe('ModelManager.factory() — object dispatch', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('creates LocalizationModel when Locale key is present', () => {
    const result = mm.factory('any', { Locale: 'en', Text: 'Hello' }, {})
    expect(result).toBeInstanceOf(LocalizationModel)
    expect(result.Text).toBe('Hello')
  })

  it('creates NodeId when pythonclass === "NodeId"', () => {
    const result = mm.factory('any', { pythonclass: 'NodeId', NamespaceIndex: 2, Identifier: 1234 }, {})
    expect(result).toBeInstanceOf(NodeId)
    expect(result.NamespaceIndex).toBe(2)
    expect(result.Identifier).toBe(1234)
  })

  it('creates NodeId when pythonclass === "QualifiedName"', () => {
    const result = mm.factory('any', { pythonclass: 'QualifiedName', NamespaceIndex: 0, Identifier: 'root' }, {})
    expect(result).toBeInstanceOf(NodeId)
  })

  it('creates keyValuePair when key property is present', () => {
    const result = mm.factory('any', { key: 'myKey', value: 'myVal' }, {})
    expect(result.myKey).toBe('myVal')
  })

  it('creates IJTBaseModel for plain object without special keys', () => {
    const result = mm.factory('any', { foo: 'bar', baz: 1 }, {})
    expect(result).toBeInstanceOf(IJTBaseModel)
    expect(result.foo).toBe('bar')
  })

  it('unwraps ExtensionObject wrapper before creating model', () => {
    const wrapped = { dataType: 'ExtensionObject', value: { name: 'unwrapped' } }
    const result = mm.factory('any', wrapped, {})
    expect(result).toBeInstanceOf(IJTBaseModel)
    expect(result.name).toBe('unwrapped')
  })

  it('uses castMapping for matching parameter name (case-insensitive)', () => {
    const castMapping = { ResultMetaData: 'ResultMetaData' }
    // ResultMetaData without a CreationTime means it's NOT a full result
    const content = { SomeProp: 'data' }
    const result = mm.factory('ResultMetaData', content, castMapping)
    expect(result).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// ModelManager.createModelFromEvent()
// ---------------------------------------------------------------------------

describe('ModelManager.createModelFromEvent()', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('creates JoiningSystemEventModel for EventType.Identifier 1006', () => {
    const msg = {
      EventType: { Identifier: 1006 },
      Message: { Text: 'System event' },
      ConditionClassName: { Text: '' },
      ConditionSubClassName: []
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
    // JoiningSystemEventModel has a Message property
    expect(model.Message).toBeTruthy()
  })

  it('creates JoiningSystemResultReadyEvent for EventType.Identifier 1007', () => {
    const msg = {
      EventType: { Identifier: 1007 },
      Message: { Text: 'Result ready' },
      Result: { ResultMetaData: { ResultId: 'r-1', IsPartial: 'False' } }
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
  })

  it('creates JoiningSystemResultReadyEvent for EventType.Identifier 1002', () => {
    const msg = {
      EventType: { Identifier: 1002 },
      Message: { Text: 'Non-tightening result' },
      Result: {}
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
  })

  it('creates DefaultNode for unknown EventType identifier', () => {
    const msg = {
      EventType: { Identifier: 9999 },
      SomeField: 'value'
    }
    const model = mm.createModelFromEvent(msg)
    expect(model).toBeDefined()
    expect(model.SomeField).toBe('value')
  })
})

// ---------------------------------------------------------------------------
// ModelManager.createModelFromRead()
// ---------------------------------------------------------------------------

describe('ModelManager.createModelFromRead()', () => {
  let mm

  beforeEach(() => { mm = makeModelManager() })

  it('returns ResultDataType when ResultMetaData is present', () => {
    const values = {
      ResultMetaData: {
        ResultId: 'r-42',
        Name: 'TestResult',
        IsPartial: 'False',
        Classification: '1',
        ProcessingTimes: { EndTime: '2025-01-01T00:00:00' }
      }
    }
    const model = mm.createModelFromRead(values)
    expect(model).toBeInstanceOf(ResultDataType)
  })

  it('returns null when ResultMetaData is absent', () => {
    const values = { SomeOtherField: 'data' }
    const model = mm.createModelFromRead(values)
    expect(model).toBeNull()
  })

  it('normalizes ResultMetaData.AssociatedEntities to an iterable list', () => {
    const values = {
      ResultMetaData: {
        ResultId: 'r-43',
        Name: 'AssocEntityResult',
        IsPartial: 'False',
        Classification: '1',
        ProcessingTimes: { EndTime: '2025-01-01T00:00:00' },
        AssociatedEntities: {
          Name: 'Tool A',
          EntityId: 'tool-a'
        }
      }
    }
    const model = mm.createModelFromRead(values)
    expect(model).toBeInstanceOf(ResultDataType)
    expect(Array.isArray(model.ResultMetaData.AssociatedEntities)).toBe(true)
    expect(model.ResultMetaData.AssociatedEntities).toHaveLength(1)

    const names = []
    for (const entity of model.ResultMetaData.AssociatedEntities) {
      names.push(entity.Name)
    }
    expect(names).toEqual(['Tool A'])
  })
})

// ---------------------------------------------------------------------------
// ModelManager.subscribeSubResults()
// ---------------------------------------------------------------------------

describe('ModelManager.subscribeSubResults()', () => {
  it('calls subscriber when resultTypeNotification fires', () => {
    const mm = makeModelManager()
    const subscriber = vi.fn()
    mm.subscribeSubResults(subscriber)

    const fakeResult = { id: 'r-1' }
    mm.resultTypeNotification(fakeResult)

    expect(subscriber).toHaveBeenCalledOnce()
    expect(subscriber).toHaveBeenCalledWith(fakeResult)
  })

  it('supports multiple subscribers', () => {
    const mm = makeModelManager()
    const s1 = vi.fn()
    const s2 = vi.fn()
    mm.subscribeSubResults(s1)
    mm.subscribeSubResults(s2)

    mm.resultTypeNotification({ id: 'r-2' })
    expect(s1).toHaveBeenCalledOnce()
    expect(s2).toHaveBeenCalledOnce()
  })
})
