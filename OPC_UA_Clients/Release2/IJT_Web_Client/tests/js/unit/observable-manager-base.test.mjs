import { afterEach, describe, expect, it, vi } from 'vitest'
import { ijtLog } from '../../../src/javascripts/ijt-support/ijt-logger.mjs'
import { ObservableManagerBase } from '../../../src/javascripts/ijt-support/observable-manager-base.mjs'

describe('ObservableManagerBase', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns a harmless unsubscribe function when callback is not callable', () => {
    const observable = new ObservableManagerBase('TestObservable')
    const unsubscribe = observable._subscribeTopic('state', null)

    expect(unsubscribe).toEqual(expect.any(Function))
    expect(() => unsubscribe()).not.toThrow()
    expect(observable._topics.size).toBe(0)
  })

  it('uses the default topic for empty topic names and removes it on unsubscribe', () => {
    const observable = new ObservableManagerBase('TestObservable')
    const callback = vi.fn()
    const unsubscribe = observable._subscribeTopic('', callback)

    observable._notifyTopic('', 'payload')
    unsubscribe()
    observable._notifyTopic('', 'ignored')

    expect(callback).toHaveBeenCalledTimes(1)
    expect(callback).toHaveBeenCalledWith('payload')
    expect(observable._topics.has('default')).toBe(false)
  })

  it('ignores unsubscribe requests for unknown callbacks and topics', () => {
    const observable = new ObservableManagerBase('TestObservable')
    const callback = vi.fn()
    const other = vi.fn()

    observable._subscribeTopic('topic', callback)
    expect(() => observable._unsubscribeTopic('missing', callback)).not.toThrow()
    expect(() => observable._unsubscribeTopic('topic', other)).not.toThrow()

    observable._notifyTopic('topic')
    expect(callback).toHaveBeenCalledOnce()
  })

  it('logs subscriber exceptions and continues notifying later subscribers', () => {
    const observable = new ObservableManagerBase('TestObservable')
    const errorSpy = vi.spyOn(ijtLog, 'error').mockImplementation(() => {})
    const throwing = vi.fn(() => { throw new Error('subscriber failed') })
    const receiving = vi.fn()

    observable._subscribeTopic('topic', throwing)
    observable._subscribeTopic('topic', receiving)
    observable._notifyTopic('topic', 'payload')

    expect(throwing).toHaveBeenCalledOnce()
    expect(receiving).toHaveBeenCalledWith('payload')
    expect(errorSpy).toHaveBeenCalledWith(
      'TestObservable callback for "topic" threw:',
      expect.any(Error)
    )
  })
})
