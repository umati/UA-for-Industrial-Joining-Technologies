/**
 * Unit tests for ijt-logger.mjs and ijt-support.mjs (re-export barrel).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ijtLog } from '../../../src/javascripts/ijt-support/ijt-logger.mjs'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function spyOnConsole () {
  return {
    error: vi.spyOn(console, 'error').mockImplementation(() => {}),
    warn:  vi.spyOn(console, 'warn').mockImplementation(() => {}),
    info:  vi.spyOn(console, 'info').mockImplementation(() => {}),
    debug: vi.spyOn(console, 'debug').mockImplementation(() => {})
  }
}

beforeEach(() => {
  // Reset to default level (info) before each test
  ijtLog.setLevel('info')
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// ijtLog.error
// ---------------------------------------------------------------------------

describe('ijtLog.error', () => {
  it('always calls console.error regardless of level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('error')
    ijtLog.error('err msg', 42)
    expect(spies.error).toHaveBeenCalledWith('err msg', 42)
  })

  it('calls console.error even when level is warn', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('warn')
    ijtLog.error('always visible')
    expect(spies.error).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// ijtLog.warn
// ---------------------------------------------------------------------------

describe('ijtLog.warn', () => {
  it('calls console.warn when level >= warn', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('warn')
    ijtLog.warn('warn msg')
    expect(spies.warn).toHaveBeenCalledWith('warn msg')
  })

  it('calls console.warn at info level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('info')
    ijtLog.warn('warn visible at info')
    expect(spies.warn).toHaveBeenCalledOnce()
  })

  it('calls console.warn at debug level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('debug')
    ijtLog.warn('warn visible at debug')
    expect(spies.warn).toHaveBeenCalledOnce()
  })

  it('does NOT call console.warn when level is error', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('error')
    ijtLog.warn('should be silent')
    expect(spies.warn).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// ijtLog.info
// ---------------------------------------------------------------------------

describe('ijtLog.info', () => {
  it('calls console.info at info level (default)', () => {
    const spies = spyOnConsole()
    ijtLog.info('info msg')
    expect(spies.info).toHaveBeenCalledWith('info msg')
  })

  it('calls console.info at debug level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('debug')
    ijtLog.info('info at debug')
    expect(spies.info).toHaveBeenCalledOnce()
  })

  it('does NOT call console.info at warn level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('warn')
    ijtLog.info('silent info')
    expect(spies.info).not.toHaveBeenCalled()
  })

  it('does NOT call console.info at error level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('error')
    ijtLog.info('silent info')
    expect(spies.info).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// ijtLog.debug
// ---------------------------------------------------------------------------

describe('ijtLog.debug', () => {
  it('calls console.debug at debug level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('debug')
    ijtLog.debug('debug msg')
    expect(spies.debug).toHaveBeenCalledWith('debug msg')
  })

  it('does NOT call console.debug at info level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('info')
    ijtLog.debug('silent debug')
    expect(spies.debug).not.toHaveBeenCalled()
  })

  it('does NOT call console.debug at warn level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('warn')
    ijtLog.debug('silent debug')
    expect(spies.debug).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// ijtLog.setLevel — unknown level falls back to info
// ---------------------------------------------------------------------------

describe('ijtLog.setLevel', () => {
  it('falls back to info for an unknown level string', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('verbose') // unknown level → info
    ijtLog.info('visible')
    ijtLog.debug('hidden')
    expect(spies.info).toHaveBeenCalledOnce()
    expect(spies.debug).not.toHaveBeenCalled()
  })

  it('accepts "error" level', () => {
    const spies = spyOnConsole()
    ijtLog.setLevel('error')
    ijtLog.warn('no warn')
    ijtLog.info('no info')
    ijtLog.debug('no debug')
    expect(spies.warn).not.toHaveBeenCalled()
    expect(spies.info).not.toHaveBeenCalled()
    expect(spies.debug).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// ijt-support.mjs — barrel re-exports
// ---------------------------------------------------------------------------

describe('ijt-support.mjs barrel re-exports', () => {
  it('re-exports ijtLog', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.ijtLog).toBeDefined()
    expect(typeof mod.ijtLog.error).toBe('function')
  })

  it('re-exports AddressSpace', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.AddressSpace).toBeDefined()
  })

  it('re-exports AssetManager', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.AssetManager).toBeDefined()
  })

  it('re-exports EventManager', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.EventManager).toBeDefined()
  })

  it('re-exports ModelManager', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.ModelManager).toBeDefined()
  })

  it('re-exports ConnectionManager', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.ConnectionManager).toBeDefined()
  })

  it('re-exports EntityCache', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.EntityCache).toBeDefined()
  })

  it('re-exports JointManager', async () => {
    const mod = await import('../../../src/javascripts/ijt-support/ijt-support.mjs')
    expect(mod.JointManager).toBeDefined()
  })
})
