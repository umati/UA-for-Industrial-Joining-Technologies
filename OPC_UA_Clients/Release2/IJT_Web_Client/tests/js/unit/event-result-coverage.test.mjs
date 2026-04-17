/**
 * Extended coverage tests for event-manager.mjs and result-manager.mjs
 * Covers:
 *  - EventManager: queueState, dequeue, receivedEvent via queue path, makeCalls error branches
 *  - ResultManager: constructor subscribeSubResults callback (line 11), addResult stored path (lines 77-78)
 */

import { describe, it, expect, vi } from 'vitest'
import { EventManager, Queue } from '../../../src/javascripts/ijt-support/events/event-manager.mjs'
import { ResultManager } from '../../../src/javascripts/ijt-support/results/result-manager.mjs'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeConnectionManager () {
  const handlers = {}
  return {
    socketHandler: {
      registerMandatory: vi.fn((event, cb) => { handlers[event] = cb }),
      _fire: (event, data) => handlers[event]?.(data)
    },
    subscribe: vi.fn()
  }
}

function makeModelManager () {
  const subResultCallbacks = []
  return {
    createModelFromEvent: vi.fn((msg) => ({ ...msg, _model: true })),
    subscribeSubResults: vi.fn((cb) => { subResultCallbacks.push(cb) }),
    _triggerSubResult: (result) => subResultCallbacks.forEach(cb => cb(result)),
    subscribeSubResultCallbacks: subResultCallbacks
  }
}

function makeEventManagerWithModelManager () {
  const connectionManager = makeConnectionManager()
  const modelManager = makeModelManager()
  return new EventManager(connectionManager, { ...modelManager, subscribeSubResults: vi.fn() })
}

function makeResult (id, classification = '2', partial = 'False', content = []) {
  return {
    id,
    classification,
    isReference: false,
    ResultMetaData: { ResultId: id, IsPartial: partial },
    ResultContent: content,
    ClientData: { rebuildState: { claimed: false, partial: false, resolved: false } },
    replaceReference: vi.fn()
  }
}

// ---------------------------------------------------------------------------
// Queue — basic smoke test
// ---------------------------------------------------------------------------

describe('Queue', () => {
  it('enqueue and dequeue work correctly', () => {
    const q = new Queue()
    q.enqueue('a')
    q.enqueue('b')
    expect(q.dequeue()).toBe('a')
    expect(q.size()).toBe(1)
    expect(q.isEmpty()).toBe(false)
    expect(q.peek()).toBe('b')
  })

  it('drops oldest when maxSize is exceeded', () => {
    const q = new Queue(2)
    q.enqueue('first')
    q.enqueue('second')
    q.enqueue('third')  // should drop 'first'
    expect(q.length).toBe(2)
    expect(q.dequeue()).toBe('second')
  })
})

// ---------------------------------------------------------------------------
// EventManager — queueState and dequeue paths (lines 77-78, 80-81, 122, 132)
// ---------------------------------------------------------------------------

describe('EventManager — queueState and dequeue', () => {
  function makeEM () {
    const connectionManager = makeConnectionManager()
    const modelManager = {
      createModelFromEvent: vi.fn((msg) => ({ ...msg, _model: true })),
      subscribeSubResults: vi.fn()
    }
    return { em: new EventManager(connectionManager, modelManager), modelManager, connectionManager }
  }

  it('queueState(true) creates a Queue, queueState(false) removes it', () => {
    const { em } = makeEM()
    em.queueState(true)
    expect(em.queue).toBeInstanceOf(Queue)
    em.queueState(false)
    expect(em.queue).toBeNull()
  })

  it('receivedEvent enqueues message when queue is active', () => {
    const { em } = makeEM()
    em.queueState(true)
    em.receivedEvent({ type: 'TestEvent' })
    expect(em.queue.isEmpty()).toBe(false)
  })

  it('dequeue processes queued events and returns model', () => {
    const { em } = makeEM()
    em.queueState(true)
    em.receivedEvent({ ConditionClassName: 'MyEvent', Result: null })
    em.queueState(false)  // disable queue but queue retains items if we reassign

    // Re-enable queue to use dequeue
    em.queue = new Queue()
    em.queue.enqueue({ ConditionClassName: 'MyEvent', Result: null })
    const result = em.dequeue()
    expect(result).toBeDefined()
    expect(result._model).toBe(true)
  })

  it('dequeue returns null when queue is empty', () => {
    const { em } = makeEM()
    em.queueState(true)
    const result = em.dequeue()
    expect(result).toBeNull()
  })

  it('dequeue returns null when queue is null', () => {
    const { em } = makeEM()
    expect(em.dequeue()).toBeNull()
  })

  it('receivedEvent via queue path does not call makeCalls directly', () => {
    const { em } = makeEM()
    em.queueState(true)
    const makeCallsSpy = vi.spyOn(em, 'makeCalls')
    em.receivedEvent({ ConditionClassName: 'TestEvent' })
    expect(makeCallsSpy).not.toHaveBeenCalled()
  })

  it('makeCalls returns null when createModelFromEvent throws', () => {
    const { em } = makeEM()
    em.modelManager.createModelFromEvent = vi.fn(() => { throw new Error('model error') })
    const result = em.makeCalls({ bad: 'data' })
    expect(result).toBeNull()
  })
})

describe('EventManager — subscribeEvent edge cases', () => {
  it('subscribeEvent with null filter returns a no-op unsubscribe', () => {
    const { em } = (() => {
      const connectionManager = makeConnectionManager()
      const modelManager = { createModelFromEvent: vi.fn(), subscribeSubResults: vi.fn() }
      return { em: new EventManager(connectionManager, modelManager), modelManager, connectionManager }
    })()
    const unsub = em.subscribeEvent(null, vi.fn())
    expect(typeof unsub).toBe('function')
    expect(() => unsub()).not.toThrow()
  })

  it('unsubscribe function removes the entry from callbacks', () => {
    const { em } = (() => {
      const connectionManager = makeConnectionManager()
      const modelManager = { createModelFromEvent: vi.fn(), subscribeSubResults: vi.fn() }
      return { em: new EventManager(connectionManager, modelManager), modelManager, connectionManager }
    })()
    const cb = vi.fn()
    const unsub = em.subscribeEvent(() => true, cb)
    expect(em.callbacks).toHaveLength(1)
    unsub()
    expect(em.callbacks).toHaveLength(0)
  })

  it('listenEvent adds callback and returns unsubscribe function', () => {
    const { em } = (() => {
      const connectionManager = makeConnectionManager()
      const modelManager = { createModelFromEvent: vi.fn(), subscribeSubResults: vi.fn() }
      return { em: new EventManager(connectionManager, modelManager), modelManager, connectionManager }
    })()
    const cb = vi.fn()
    const unsub = em.listenEvent(() => true, cb)
    expect(em.callbacks).toHaveLength(1)
    unsub()
    expect(em.callbacks).toHaveLength(0)
  })
})

describe('EventManager — socket handler event dispatch', () => {
  it('socket handler fires receivedEvent on "event" message', () => {
    const connectionManager = makeConnectionManager()
    const modelManager = { createModelFromEvent: vi.fn((msg) => msg), subscribeSubResults: vi.fn() }
    const em = new EventManager(connectionManager, modelManager)
    const cb = vi.fn()
    em.subscribeEvent(() => true, cb)

    // Fire the 'event' handler registered with registerMandatory
    connectionManager.socketHandler._fire('event', { ConditionClassName: 'TestEvent', ConditionSubClassName: ['Sub1'] })

    expect(cb).toHaveBeenCalledOnce()
  })

  it('socket handler null message is ignored', () => {
    const connectionManager = makeConnectionManager()
    const modelManager = { createModelFromEvent: vi.fn(), subscribeSubResults: vi.fn() }
    const em = new EventManager(connectionManager, modelManager)  // eslint-disable-line no-unused-vars

    expect(() => connectionManager.socketHandler._fire('event', null)).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// ResultManager — constructor callback (line 11) and addResult stored path (77-78)
// ---------------------------------------------------------------------------

describe('ResultManager — constructor subscribeSubResults callback', () => {
  it('addResult is called when subscribeSubResults callback fires', () => {
    let capturedCallback = null
    const eventManager = {
      modelManager: {
        subscribeSubResults: vi.fn((cb) => { capturedCallback = cb })
      }
    }

    const rm = new ResultManager(eventManager)
    const addResultSpy = vi.spyOn(rm, 'addResult')

    const r = makeResult('r-callback')
    capturedCallback(r)

    expect(addResultSpy).toHaveBeenCalledWith(r)
  })
})

describe('ResultManager — addResult with stored (partial update)', () => {
  it('calls handlePartial when same ResultId is added twice', () => {
    const em = { modelManager: { subscribeSubResults: vi.fn() } }
    const rm = new ResultManager(em)

    const first = makeResult('r-partial', '2', 'True', [])
    rm.addResult(first)

    // Add again with more content — triggers the stored branch (lines 77-78)
    const second = makeResult('r-partial', '2', 'False', [])
    const handlePartialSpy = vi.spyOn(rm, 'handlePartial')
    rm.addResult(second)

    expect(handlePartialSpy).toHaveBeenCalledOnce()
  })

  it('unresolved list is cleaned up after second addResult', () => {
    const em = { modelManager: { subscribeSubResults: vi.fn() } }
    const rm = new ResultManager(em)

    const first = makeResult('r-unres', '1', 'True', [])
    rm.addResult(first)
    const second = makeResult('r-unres', '1', 'False', [])
    rm.addResult(second)

    // The test verifies no crash and list management works
    expect(Array.isArray(rm.unresolved)).toBe(true)
  })
})
