/**
 * Centralized logger for IJT Node Client.
 * Controls log verbosity via LOG_LEVEL env var or ijtLog.setLevel().
 * Levels: 0=error, 1=warn, 2=info, 3=debug
 */
const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 }

class IjtLogger {
  constructor () { this._level = LEVELS.info }
  setLevel (level) { this._level = typeof level === 'string' ? (LEVELS[level] ?? LEVELS.info) : level }
  error (...args) { if (this._level >= LEVELS.error) console.error('[IJT ERROR]', ...args) }
  warn (...args) { if (this._level >= LEVELS.warn) console.warn('[IJT WARN]', ...args) }
  info (...args) { if (this._level >= LEVELS.info) console.info('[IJT INFO]', ...args) }
  debug (...args) { if (this._level >= LEVELS.debug) console.debug('[IJT DEBUG]', ...args) }
}

export const ijtLog = new IjtLogger()
