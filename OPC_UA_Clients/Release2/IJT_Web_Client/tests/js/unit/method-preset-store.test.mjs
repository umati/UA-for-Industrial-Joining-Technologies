import { afterEach, describe, expect, it } from 'vitest'
import {
  clearMethodValues,
  loadMethodValues,
  methodPresetStorageKey,
  saveMethodValues
} from '../../../src/javascripts/ijt-support/methods/method-preset-store.mjs'

function createStorage () {
  const values = new Map()
  return {
    getItem: key => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key)
  }
}

afterEach(() => {
  delete global.window
})

describe('method preset store', () => {
  it('uses a stable isolated key per method', () => {
    expect(methodPresetStorageKey('ns=1;s=TighteningSystem/Method A'))
      .not.toBe(methodPresetStorageKey('ns=1;s=TighteningSystem/Method B'))
  })

  it('round-trips saved method arguments through local storage', () => {
    global.window = { localStorage: createStorage() }
    const values = [{ type: { Identifier: 12 }, value: 'urn:tool:1' }, { type: { Identifier: 1 }, value: true }]

    expect(saveMethodValues('GetJointList', values)).toBe(true)
    expect(loadMethodValues('GetJointList')).toEqual(values)
    expect(clearMethodValues('GetJointList')).toBe(true)
    expect(loadMethodValues('GetJointList')).toBeNull()
  })

  it('does not throw when browser storage is unavailable', () => {
    expect(saveMethodValues('GetJointList', [])).toBe(true)
    expect(loadMethodValues('GetJointList')).toBeNull()
    expect(clearMethodValues('GetJointList')).toBe(true)
  })
})
