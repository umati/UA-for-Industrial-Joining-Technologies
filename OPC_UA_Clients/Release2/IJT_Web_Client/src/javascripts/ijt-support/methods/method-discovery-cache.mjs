export function joiningProcessIdFromEntry (entry) {
  const normalized = entry?.Value ?? entry
  const meta = normalized?.JoiningProcessMetaData
  for (const source of [normalized, meta]) {
    if (!source) continue
    const value = source.JoiningProcessId || source.Id || source.ProgramId
    if (value) return String(value).trim()
  }
  return typeof normalized === 'string' ? normalized.trim() : ''
}

export function joiningProcessOriginIdFromEntry (entry) {
  const normalized = entry?.Value ?? entry
  const meta = normalized?.JoiningProcessMetaData
  for (const source of [normalized, meta]) {
    if (!source) continue
    const value = source.JoiningProcessOriginId
    if (value) return String(value).trim()
  }
  return ''
}

export function joiningProcessSelectionNameFromEntry (entry) {
  const normalized = entry?.Value ?? entry
  const meta = normalized?.JoiningProcessMetaData
  for (const source of [normalized, meta]) {
    if (!source) continue
    const value = source.SelectionName || source.Name
    if (value) return String(value).trim()
  }
  return ''
}
