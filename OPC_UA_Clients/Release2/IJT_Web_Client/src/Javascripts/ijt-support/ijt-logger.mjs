/**
 * @module ijt-logger
 * Centralised logger — mirrors the Python ijt_log object from ijt_logger.py.
 *
 * Log levels (lowest → highest): error, warn, info, debug
 * Default level: info  (error, warn and info are visible; debug is silent)
 *
 * Change level at runtime in the browser DevTools console:
 *   import { ijtLog } from '/src/javascripts/ijt-support/ijt-logger.mjs'
 *   ijtLog.setLevel('debug')
 */

const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 }
let _level = LEVELS.info

export const ijtLog = {
  error (msg, ...args) { console.error(msg, ...args) },
  warn (msg, ...args) { if (_level >= LEVELS.warn) console.warn(msg, ...args) },
  info (msg, ...args) { if (_level >= LEVELS.info) console.info(msg, ...args) },
  debug (msg, ...args) { if (_level >= LEVELS.debug) console.debug(msg, ...args) },
  setLevel (level) { _level = LEVELS[level] ?? LEVELS.info }
}
