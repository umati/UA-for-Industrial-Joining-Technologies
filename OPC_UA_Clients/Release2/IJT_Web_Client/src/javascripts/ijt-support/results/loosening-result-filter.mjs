const LOOSENING_TEXT_PATTERN = /\bloosen(?:ing)?\b/i

const BOOLEAN_LOOSENING_KEYS = new Set([
  'isloosening',
  'loosening'
])

const TEXT_LOOSENING_KEYS = new Set([
  'tag',
  'tags',
  'label',
  'labels',
  'category',
  'type',
  'resulttype',
  'operation',
  'operationtype',
  'joiningprocesstype',
  'name'
])

const LOOSENING_ASSEMBLY_TYPE = 2

export function isLooseningResult (result) {
  if (!result || typeof result !== 'object') {
    return false
  }

  return inspectCandidate(result) ||
    inspectCandidate(result.ResultMetaData) ||
    inspectCandidate(result.ClientData) ||
    inspectAssociatedEntities(result.ResultMetaData?.AssociatedEntities)
}

function inspectAssociatedEntities (entities) {
  if (!Array.isArray(entities)) {
    return inspectCandidate(entities)
  }
  return entities.some((entity) => inspectCandidate(entity))
}

function inspectCandidate (candidate) {
  if (!candidate || typeof candidate !== 'object') {
    return false
  }
  for (const [key, value] of Object.entries(candidate)) {
    const normalizedKey = normalizeKey(key)
    if (normalizedKey === 'assemblytype' && isLooseningAssemblyType(value)) {
      return true
    }
    if (BOOLEAN_LOOSENING_KEYS.has(normalizedKey) && isTruthyFlag(value)) {
      return true
    }
    if (TEXT_LOOSENING_KEYS.has(normalizedKey) && valueContainsLooseningTag(value)) {
      return true
    }
  }
  return false
}

function isLooseningAssemblyType (value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric === LOOSENING_ASSEMBLY_TYPE
}

function valueContainsLooseningTag (value) {
  if (typeof value === 'string') {
    return LOOSENING_TEXT_PATTERN.test(value)
  }
  if (Array.isArray(value)) {
    return value.some((item) => valueContainsLooseningTag(item))
  }
  if (value && typeof value === 'object') {
    return Object.values(value).some((item) => valueContainsLooseningTag(item))
  }
  return false
}

function isTruthyFlag (value) {
  if (value === true || value === 1) {
    return true
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    return normalized === 'true' || normalized === '1' || normalized === 'yes'
  }
  return false
}

function normalizeKey (key) {
  return String(key || '').replace(/[^a-z0-9]/gi, '').toLowerCase()
}
