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
    safeStorage()?.setItem(methodPresetStorageKey(methodKey), JSON.stringify(values))
    return true
  } catch (error) {
    ijtLog.warn('Could not save method values:', error)
    return false
  }
}

export function clearMethodValues (methodKey) {
  try {
    safeStorage()?.removeItem(methodPresetStorageKey(methodKey))
    return true
  } catch (error) {
    ijtLog.warn('Could not clear saved method values:', error)
    return false
  }
}
