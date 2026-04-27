import { describe, it, expect, vi } from 'vitest'
import { ijtLog } from '../../../javascripts/ijt-support/ijt-logger.mjs'
import { ijtLog as barrelLog } from '../../../javascripts/ijt-support/ijt-support.mjs'

describe('ijtLog', () => {
  it('is exported as a singleton object', () => {
    expect(ijtLog).toBeDefined()
    expect(typeof ijtLog).toBe('object')
  })

  it('has error, warn, info, debug methods', () => {
    expect(typeof ijtLog.error).toBe('function')
    expect(typeof ijtLog.warn).toBe('function')
    expect(typeof ijtLog.info).toBe('function')
    expect(typeof ijtLog.debug).toBe('function')
  })

  it('has setLevel method', () => {
    expect(typeof ijtLog.setLevel).toBe('function')
  })

  it('info is called at default level', () => {
    const spy = vi.spyOn(console, 'info').mockImplementation(() => {})
    ijtLog.setLevel('info')
    ijtLog.info('test info message')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('debug is suppressed at info level', () => {
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    ijtLog.setLevel('info')
    ijtLog.debug('should not appear')
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
  })

  it('debug is called at debug level', () => {
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    ijtLog.setLevel('debug')
    ijtLog.debug('debug message')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
    ijtLog.setLevel('info') // restore default
  })

  it('setLevel("error") suppresses info, warn, debug', () => {
    const infSpy = vi.spyOn(console, 'info').mockImplementation(() => {})
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const dbgSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    ijtLog.setLevel('error')
    ijtLog.info('suppressed info')
    ijtLog.warn('suppressed warn')
    ijtLog.debug('suppressed debug')
    expect(infSpy).not.toHaveBeenCalled()
    expect(warnSpy).not.toHaveBeenCalled()
    expect(dbgSpy).not.toHaveBeenCalled()
    infSpy.mockRestore()
    warnSpy.mockRestore()
    dbgSpy.mockRestore()
    ijtLog.setLevel('info') // restore default
  })

  it('error is always called at error level', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    ijtLog.setLevel('error')
    ijtLog.error('an error')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
    ijtLog.setLevel('info')
  })

  it('same singleton is imported twice', async () => {
    const { ijtLog: secondImport } = await import('../../../javascripts/ijt-support/ijt-logger.mjs')
    expect(secondImport).toBe(ijtLog)
  })

  it('warn is called when level allows it', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    ijtLog.setLevel('info')
    ijtLog.warn('a warning')
    expect(spy).toHaveBeenCalledWith('[IJT WARN]', 'a warning')
    spy.mockRestore()
    ijtLog.setLevel('info')
  })

  it('setLevel accepts a numeric level value', () => {
    ijtLog.setLevel(3) // debug = 3
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    ijtLog.debug('numeric level debug')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
    ijtLog.setLevel('info')
  })

  it('setLevel falls back to info for unknown string level', () => {
    ijtLog.setLevel('verbose') // not in LEVELS → LEVELS.info (2)
    const spy = vi.spyOn(console, 'debug').mockImplementation(() => {})
    ijtLog.debug('should not appear at info level')
    expect(spy).not.toHaveBeenCalled()
    spy.mockRestore()
    ijtLog.setLevel('info')
  })
})

describe('ijt-support barrel — ijtLog smoke test', () => {
  it('ijtLog is exported from ijt-support.mjs', () => {
    expect(barrelLog).toBeDefined()
    expect(typeof barrelLog.setLevel).toBe('function')
  })
})
