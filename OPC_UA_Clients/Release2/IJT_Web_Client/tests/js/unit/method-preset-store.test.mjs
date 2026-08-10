import { afterEach, describe, expect, it } from 'vitest'
import {
  clearMethodValues,
  loadMethodPreferences,
  loadMethodValues,
  methodPresetStorageKey,
  saveMethodPreferences,
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
    expect(methodPresetStorageKey(' Method / A ')).toBe('ijt.methods.values.Method%20%2F%20A')
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
    expect(saveMethodValues('GetJointList', [])).toBe(false)
    expect(loadMethodValues('GetJointList')).toBeNull()
    expect(clearMethodValues('GetJointList')).toBe(false)
    expect(saveMethodPreferences('GetJointList', {})).toBe(false)
  })

  it('rejects invalid saved-value payloads', () => {
    const storage = createStorage()
    global.window = { localStorage: storage }

    expect(saveMethodValues('GetJointList', {})).toBe(false)
    storage.setItem(methodPresetStorageKey('GetJointList'), '{"not":"an array"}')
    expect(loadMethodValues('GetJointList')).toBeNull()
    storage.setItem(methodPresetStorageKey('GetJointList'), 'not-json')
    expect(loadMethodValues('GetJointList')).toBeNull()
  })

  it('round-trips method preferences and rejects invalid values', () => {
    const storage = createStorage()
    global.window = { localStorage: storage }

    expect(loadMethodPreferences('SelectJoint')).toEqual({})
    expect(saveMethodPreferences('SelectJoint', { profile: 'defaults' })).toBe(true)
    expect(loadMethodPreferences('SelectJoint')).toEqual({ profile: 'defaults' })
    expect(saveMethodPreferences('SelectJoint', null)).toBe(false)

    storage.setItem(`${methodPresetStorageKey('SelectJoint')}.prefs`, '[]')
    expect(loadMethodPreferences('SelectJoint')).toEqual([])
    storage.setItem(`${methodPresetStorageKey('SelectJoint')}.prefs`, 'not-json')
    expect(loadMethodPreferences('SelectJoint')).toEqual({})
  })

  it('surfaces storage operation failures as safe return values', () => {
    global.window = {
      localStorage: {
        getItem: () => { throw new Error('read denied') },
        setItem: () => { throw new Error('write denied') },
        removeItem: () => { throw new Error('remove denied') }
      }
    }

    expect(loadMethodValues('Method')).toBeNull()
    expect(saveMethodValues('Method', [])).toBe(false)
    expect(clearMethodValues('Method')).toBe(false)
    expect(loadMethodPreferences('Method')).toEqual({})
    expect(saveMethodPreferences('Method', {})).toBe(false)
  })

  it('handles browsers that deny access to localStorage itself', () => {
    global.window = {}
    Object.defineProperty(global.window, 'localStorage', {
      get: () => { throw new Error('storage blocked') }
    })

    expect(loadMethodValues('Method')).toBeNull()
    expect(saveMethodValues('Method', [])).toBe(false)
    expect(clearMethodValues('Method')).toBe(false)
  })
})
