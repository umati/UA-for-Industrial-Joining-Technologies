import { ijtLog } from '../ijt-logger.mjs'

const STORAGE_PREFIX = 'ijt.methods.values.'

function safeStorage () {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

export function methodPresetStorageKey (methodKey) {
  return `${STORAGE_PREFIX}${encodeURIComponent(String(methodKey || '').trim())}`
}

export function loadMethodValues (methodKey) {
  try {
    const raw = safeStorage()?.getItem(methodPresetStorageKey(methodKey))
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : null
  } catch (error) {
    ijtLog.warn('Could not read saved method values:', error)
    return null
  }
}

export function saveMethodValues (methodKey, values) {
  try {
    if (!Array.isArray(values)) return false
    const storage = safeStorage()
    if (!storage) return false
    storage.setItem(methodPresetStorageKey(methodKey), JSON.stringify(values))
    return true
  } catch (error) {
    ijtLog.warn('Could not save method values:', error)
    return false
  }
}

export function clearMethodValues (methodKey) {
  try {
    const storage = safeStorage()
    if (!storage) return false
    storage.removeItem(methodPresetStorageKey(methodKey))
    return true
  } catch (error) {
    ijtLog.warn('Could not clear saved method values:', error)
    return false
  }
}

export function loadMethodPreferences (methodKey) {
  try {
    const raw = safeStorage()?.getItem(`${methodPresetStorageKey(methodKey)}.prefs`)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    ijtLog.warn('Could not read method preferences:', error)
    return {}
  }
}

export function saveMethodPreferences (methodKey, preferences) {
  try {
    if (!preferences || typeof preferences !== 'object') return false
    const storage = safeStorage()
    if (!storage) return false
    storage.setItem(`${methodPresetStorageKey(methodKey)}.prefs`, JSON.stringify(preferences))
    return true
  } catch (error) {
    ijtLog.warn('Could not save method preferences:', error)
    return false
  }
}
