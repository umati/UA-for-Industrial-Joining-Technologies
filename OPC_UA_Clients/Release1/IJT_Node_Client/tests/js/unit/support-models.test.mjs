import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { KeyValuePair, LocalizationModel } from '../../../javascripts/ijt-support/models/support-models.mjs'
import IJTBaseModel from '../../../javascripts/ijt-support/models/ijt-base-model.mjs'

function makeModelManager () {
  return {
    factory: (key, value, mapping) => value
  }
}

describe('KeyValuePair', () => {
  it('is exported as a class', () => {
    expect(KeyValuePair).toBeDefined()
  })

  it('extends IJTBaseModel', () => {
    const mm = makeModelManager()
    const kv = new KeyValuePair({ key: 'myKey', value: 'myVal' }, mm)
    expect(kv).toBeInstanceOf(IJTBaseModel)
  })

  it('has key and value properties after construction', () => {
    const mm = makeModelManager()
    const kv = new KeyValuePair({ key: 'testKey', value: 'testVal' }, mm)
    expect(kv.key).toBe('testKey')
    expect(kv.value).toBe('testVal')
  })
})

describe('KeyValuePair — toHTML()', () => {
  beforeEach(() => {
    globalThis.document = {
      createElement: vi.fn((tag) => {
        const el = {
          tag,
          children: [],
          textContent: '',
          appendChild: vi.fn(function (child) { this.children.push(child); return child }),
        }
        return el
      })
    }
  })
  afterEach(() => {
    delete globalThis.document
  })

  it('toHTML() returns a container element', () => {
    const mm = makeModelManager()
    const kv = new KeyValuePair({ key: 'myKey', value: 'myVal' }, mm)
    const container = kv.toHTML(false, 'parent')
    expect(container).toBeDefined()
    expect(container.children.length).toBeGreaterThan(0)
  })

  it('toHTML() sets textContent with key and value', () => {
    const mm = makeModelManager()
    const kv = new KeyValuePair({ key: 'K', value: 'V' }, mm)
    const container = kv.toHTML(false, 'p')
    const li1 = container.children[0]
    expect(li1.textContent).toBe('K: V')
  })

  it('toHTML() attaches expandLong no-op override', () => {
    const mm = makeModelManager()
    const kv = new KeyValuePair({ key: 'x', value: '1' }, mm)
    const container = kv.toHTML()
    expect(typeof container.expandLong).toBe('function')
    expect(() => container.expandLong()).not.toThrow()
  })
})

describe('LocalizationModel', () => {
  it('extends IJTBaseModel', () => {
    const mm = makeModelManager()
    const lm = new LocalizationModel({ text: 'Hello' }, mm)
    expect(lm).toBeInstanceOf(IJTBaseModel)
  })

  it('has text property after construction', () => {
    const mm = makeModelManager()
    const lm = new LocalizationModel({ text: 'World' }, mm)
    expect(lm.text).toBe('World')
  })
})

describe('IJTBaseModel', () => {
  it('copies scalar properties from parameters', () => {
    const mm = makeModelManager()
    const model = new IJTBaseModel({ name: 'Test', count: 42 }, mm)
    expect(model.name).toBe('Test')
    expect(model.count).toBe(42)
  })

  it('stores debugValues reference', () => {
    const mm = makeModelManager()
    const params = { x: 1 }
    const model = new IJTBaseModel(params, mm)
    expect(model.debugValues).toBe(params)
  })

  it('maps array properties by calling factory for each element', () => {
    const mm = { factory: vi.fn((_key, val) => val) }
    const params = { items: [1, 2, 3] }
    const model = new IJTBaseModel(params, mm)
    expect(Array.isArray(model.items)).toBe(true)
    // factory was called for each element
    expect(mm.factory).toHaveBeenCalledTimes(3)
  })
})
