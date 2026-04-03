import { describe, it, expect, vi } from 'vitest'
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

  it('uses Array constructor check (Array === value.constructor) for arrays', () => {
    const mm = { factory: vi.fn((_key, val) => val) }
    const params = { items: [1, 2, 3] }
    const model = new IJTBaseModel(params, mm)
    expect(Array.isArray(model.items)).toBe(true)
    // factory was called for each element
    expect(mm.factory).toHaveBeenCalledTimes(3)
  })
})
