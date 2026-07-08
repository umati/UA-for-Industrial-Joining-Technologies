import { describe, expect, it, vi, afterEach } from 'vitest'
import Settings from '../../../src/javascripts/views/graphic-support/settings.mjs'
import {
  DEFAULT_IGNORE_LOOSENINGS,
  DEFAULT_RESULT_SESSION_AUTO_RESTORE,
  DEFAULT_RESULT_SESSION_AUTO_SAVE,
  RESULT_SESSION_STORAGE_KEY
} from '../../../src/javascripts/ijt-support/results/result-storage-constants.mjs'

function makeSettingsLike () {
  const settings = Object.create(Settings.prototype)
  settings.ensureStatusBanner = vi.fn()
  settings.setStatusBanner = vi.fn()
  settings.resultSessionAutoSave = DEFAULT_RESULT_SESSION_AUTO_SAVE
  settings.resultSessionAutoRestore = DEFAULT_RESULT_SESSION_AUTO_RESTORE
  settings.ignoreLoosenings = DEFAULT_IGNORE_LOOSENINGS
  return settings
}

afterEach(() => {
  vi.restoreAllMocks()
  delete global.window
})

describe('Settings boolean session options', () => {
  it('normalizes boolean values and string booleans', () => {
    const settings = makeSettingsLike()
    expect(settings.normalizeBooleanSetting(true, false)).toBe(true)
    expect(settings.normalizeBooleanSetting(false, true)).toBe(false)
    expect(settings.normalizeBooleanSetting('true', false)).toBe(true)
    expect(settings.normalizeBooleanSetting('FALSE', true)).toBe(false)
    expect(settings.normalizeBooleanSetting('invalid', true)).toBe(true)
  })

  it('returns normalized auto-save and auto-restore flags', () => {
    const settings = makeSettingsLike()
    settings.resultSessionAutoSave = 'false'
    settings.resultSessionAutoRestore = 'true'
    settings.ignoreLoosenings = 'true'
    expect(settings.getResultSessionAutoSave()).toBe(false)
    expect(settings.getResultSessionAutoRestore()).toBe(true)
    expect(settings.getIgnoreLoosenings()).toBe(true)
  })
})

describe('Settings local result session clearing', () => {
  it('clears local result session key and sets success status', () => {
    const settings = makeSettingsLike()
    const removeItem = vi.fn()
    global.window = { localStorage: { removeItem } }

    settings.clearLocalResultSession()

    expect(removeItem).toHaveBeenCalledWith(RESULT_SESSION_STORAGE_KEY)
    expect(settings.setStatusBanner).toHaveBeenCalledWith('settings', 'success', 'Cleared local result session storage.')
  })

  it('sets error status when localStorage access fails', () => {
    const settings = makeSettingsLike()
    const removeItem = vi.fn(() => { throw new Error('fail') })
    global.window = { localStorage: { removeItem } }

    settings.clearLocalResultSession()

    expect(settings.setStatusBanner).toHaveBeenCalledWith('settings', 'error', 'Unable to clear local result session storage.')
  })
})
