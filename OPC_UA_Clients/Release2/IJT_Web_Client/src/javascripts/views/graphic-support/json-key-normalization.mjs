export function lowerCaseJsonKeys (payload) {
  if (Array.isArray(payload)) {
    return payload.map((item) => lowerCaseJsonKeys(item))
  }
  if (payload && typeof payload === 'object') {
    const lowered = {}
    for (const [key, value] of Object.entries(payload)) {
      lowered[String(key).toLowerCase()] = lowerCaseJsonKeys(value)
    }
    return lowered
  }
  return payload
}
