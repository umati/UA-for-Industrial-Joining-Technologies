const EXPORT_TYPE = 'ijt-result-export'
const EXPORT_VERSION = 1
const DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
const DEFAULT_MAX_RESULTS_COUNT = 5000
const DEFAULT_MAX_DEPTH = 10000

const BLOCKED_KEYS = new Set(['__proto__', 'constructor', 'prototype'])
const BLOCKED_PARENT_RELATION_KEYS = new Set([
  'parent',
  'parentid',
  'parentresult',
  'parentresultid',
  'parentnode',
  'parentnodeid',
  'parentreference',
  'upstream',
  'ancestor'
])
const RUNTIME_ONLY_KEYS = new Set([
  'ClientData',
  'clientLatestRecievedTime',
  'uniqueCounter'
])

function byteLengthOfText (text) {
  if (typeof TextEncoder === 'function') {
    return new TextEncoder().encode(text).length
  }
  return String(text).length
}

function sanitizeValue (value, depth = 0, maxDepth = DEFAULT_MAX_DEPTH, ancestors = null, path = '$') {
  if (depth > maxDepth) {
    throw new Error(`Max serialization depth exceeded (${maxDepth}) at '${path}'`)
  }

  if (value === null || value === undefined) {
    return null
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value
  }

  if (Array.isArray(value)) {
    const lineage = ancestors || new WeakSet()
    if (lineage.has(value)) {
      throw new Error(`Circular reference detected at '${path}'`)
    }
    lineage.add(value)
    const sanitizedArray = value.map((item, index) => sanitizeValue(item, depth + 1, maxDepth, lineage, `${path}[${index}]`))
    lineage.delete(value)
    return sanitizedArray
  }

  if (typeof value !== 'object') {
    return null
  }

  // linkedValue wrappers are runtime shortcuts (e.g. StepResultId.link).
  // Persist only the stable source value and rebuild links during import.
  if (value?.type === 'linkedValue') {
    return sanitizeValue(value?.value, depth + 1, maxDepth, ancestors, `${path}.value`)
  }

  const lineage = ancestors || new WeakSet()
  if (lineage.has(value)) {
    throw new Error(`Circular reference detected at '${path}'`)
  }
  lineage.add(value)

  const plain = {}
  for (const [key, raw] of Object.entries(value)) {
    if (BLOCKED_KEYS.has(key) || RUNTIME_ONLY_KEYS.has(key)) {
      continue
    }
    if (BLOCKED_PARENT_RELATION_KEYS.has(String(key).toLowerCase())) {
      continue
    }
    if (typeof raw === 'function') {
      continue
    }
    if (key.startsWith('_')) {
      continue
    }
    plain[key] = sanitizeValue(raw, depth + 1, maxDepth, lineage, `${path}.${key}`)
  }
  lineage.delete(value)
  return plain
}

function normalizeBundleShape (bundle) {
  if (Array.isArray(bundle)) {
    return {
      type: EXPORT_TYPE,
      version: EXPORT_VERSION,
      exportedAt: null,
      source: { app: 'legacy', format: 'legacy-array' },
      results: bundle,
      legacy: true
    }
  }

  const legacyObject = bundle && typeof bundle === 'object' && Array.isArray(bundle.results) &&
    (bundle.type === undefined || bundle.version === undefined)

  if (legacyObject) {
    return {
      type: EXPORT_TYPE,
      version: EXPORT_VERSION,
      exportedAt: bundle?.exportedAt || null,
      source: bundle?.source || { app: 'legacy', format: 'legacy-object' },
      results: bundle.results,
      legacy: true
    }
  }

  return {
    type: bundle?.type,
    version: bundle?.version,
    exportedAt: bundle?.exportedAt,
    source: bundle?.source,
    results: Array.isArray(bundle?.results) ? bundle.results : [],
    legacy: false
  }
}

export function serializeResultForStorage (resultModel, options = {}) {
  if (!resultModel || typeof resultModel !== 'object') {
    return null
  }
  const maxDepth = Number.isFinite(options.maxDepth) ? options.maxDepth : DEFAULT_MAX_DEPTH
  const sanitized = sanitizeValue(resultModel, 0, maxDepth)
  if (!sanitized || typeof sanitized !== 'object') {
    return null
  }
  if (!sanitized.ResultMetaData || typeof sanitized.ResultMetaData !== 'object') {
    return null
  }
  if (!sanitized.ResultContent) {
    sanitized.ResultContent = []
  }
  return sanitized
}

export function createResultBundle (results, options = {}) {
  const source = options.source || {}
  return {
    type: EXPORT_TYPE,
    version: EXPORT_VERSION,
    exportedAt: new Date().toISOString(),
    source: {
      app: source.app || 'ijt-web-client',
      format: source.format || 'result-bundle'
    },
    results: Array.isArray(results) ? results : []
  }
}

export function validateResultBundle (bundle, options = {}) {
  const maxResultsCount = Number.isFinite(options.maxResultsCount) ? options.maxResultsCount : DEFAULT_MAX_RESULTS_COUNT
  const allowLegacy = options.allowLegacy !== false
  const normalized = normalizeBundleShape(bundle)

  if (!normalized.legacy || !allowLegacy) {
    if (normalized.type !== EXPORT_TYPE) {
      throw new Error(`Invalid bundle type '${String(normalized.type)}'`)
    }
    if (normalized.version !== EXPORT_VERSION) {
      throw new Error(`Unsupported bundle version '${String(normalized.version)}'`)
    }
  }

  if (!Array.isArray(normalized.results)) {
    throw new Error('Invalid bundle: results must be an array')
  }
  if (normalized.results.length > maxResultsCount) {
    throw new Error(`Too many results in bundle (${normalized.results.length} > ${maxResultsCount})`)
  }
}

export function parseResultBundle (rawText, options = {}) {
  if (typeof rawText !== 'string') {
    throw new Error('Import payload must be text')
  }
  const maxFileSizeBytes = Number.isFinite(options.maxFileSizeBytes) ? options.maxFileSizeBytes : DEFAULT_MAX_FILE_SIZE_BYTES
  const byteLength = byteLengthOfText(rawText)
  if (byteLength > maxFileSizeBytes) {
    throw new Error(`Import file exceeds size limit (${byteLength} > ${maxFileSizeBytes})`)
  }

  let parsed
  try {
    parsed = JSON.parse(rawText)
  } catch (error) {
    throw new Error(`Invalid JSON: ${error?.message || error}`)
  }

  validateResultBundle(parsed, options)

  const normalized = normalizeBundleShape(parsed)
  return {
    ...normalized,
    results: normalized.results
  }
}

export const RESULT_BUNDLE_CONSTANTS = Object.freeze({
  EXPORT_TYPE,
  EXPORT_VERSION,
  DEFAULT_MAX_FILE_SIZE_BYTES,
  DEFAULT_MAX_RESULTS_COUNT,
  DEFAULT_MAX_DEPTH
})
