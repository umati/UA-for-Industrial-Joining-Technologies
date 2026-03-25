/**
 * Comprehensive tests for:
 *   - SupportModels: NodeId.stringify(), NodeId.compare()
 *   - SupportModels: LocalizationModel, ErrorInformationDataType, ProcessingTimesDataType
 *   - EntityDataType + EntityTypes enum
 *   - EventManager: subscribe, receivedEvent, queueState, dequeue, reset, makeCalls
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NodeId, LocalizationModel, ErrorInformationDataType, ProcessingTimesDataType } from '../../../src/Javascripts/ijt-support/Models/SupportModels.mjs'
import { EntityDataType, EntityTypes } from '../../../src/Javascripts/ijt-support/Models/Entities/EntityDataType.mjs'
import { EventManager } from '../../../src/Javascripts/ijt-support/Events/EventManager.mjs'

// ---------------------------------------------------------------------------
// Shared model manager stub (no OPC UA needed)
// ---------------------------------------------------------------------------

function makeModelManager (createModelFn = null) {
  const mm = {
    entityManager: { addEntity: vi.fn() },
    createModelFromEvent: createModelFn || vi.fn(msg => ({ ...msg, _model: true }))
  }
  return mm
}

// ---------------------------------------------------------------------------
// NodeId.stringify()
// ---------------------------------------------------------------------------

describe('NodeId.stringify()', () => {
  const mm = makeModelManager()

  it('uses ;i= for numeric identifier', () => {
    const node = new NodeId({ NamespaceIndex: 2, Identifier: 1234 }, mm)
    expect(node.stringify()).toBe('ns=2;i=1234')
  })

  it('uses ;s= for non-numeric string identifier', () => {
    const node = new NodeId({ NamespaceIndex: 1, Identifier: 'TighteningSystem' }, mm)
    expect(node.stringify()).toBe('ns=1;s=TighteningSystem')
  })

  it('uses ;i= for string that looks like a number', () => {
    const node = new NodeId({ NamespaceIndex: 0, Identifier: '84' }, mm)
    expect(node.stringify()).toBe('ns=0;i=84')
  })

  it('includes namespace index 0', () => {
    const node = new NodeId({ NamespaceIndex: 0, Identifier: 2258 }, mm)
    expect(node.stringify()).toMatch(/^ns=0;/)
  })
})

// ---------------------------------------------------------------------------
// NodeId.compare()
// ---------------------------------------------------------------------------

describe('NodeId.compare()', () => {
  const mm = makeModelManager()

  it('returns true when identity matches and namespace is not checked', () => {
    const node = new NodeId({ NamespaceIndex: 2, Identifier: 1000 }, mm)
    expect(node.compare(1000)).toBe(true)
  })

  it('returns false when identity does not match', () => {
    const node = new NodeId({ NamespaceIndex: 2, Identifier: 1000 }, mm)
    expect(node.compare(9999)).toBe(false)
  })

  it('returns true when both identity and namespace match', () => {
    const node = new NodeId({ NamespaceIndex: 2, Identifier: 1000 }, mm)
    expect(node.compare(1000, 2)).toBe(true)
  })

  it('returns false when identity matches but namespace does not', () => {
    const node = new NodeId({ NamespaceIndex: 2, Identifier: 1000 }, mm)
    expect(node.compare(1000, 99)).toBe(false)
  })

  it('returns true when namespace argument is 0 and namespace index is 0', () => {
    const node = new NodeId({ NamespaceIndex: 0, Identifier: 84 }, mm)
    expect(node.compare(84, 0)).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// LocalizationModel
// ---------------------------------------------------------------------------

describe('LocalizationModel', () => {
  const mm = makeModelManager()

  it('stores Locale and Text', () => {
    const lt = new LocalizationModel({ Locale: 'en', Text: 'Hello' }, mm)
    expect(lt.Locale).toBe('en')
    expect(lt.Text).toBe('Hello')
  })

  it('handles empty text', () => {
    const lt = new LocalizationModel({ Locale: 'en', Text: '' }, mm)
    expect(lt.Text).toBeNull() // falsy → null per IJTBaseModel
  })
})

// ---------------------------------------------------------------------------
// EntityDataType
// ---------------------------------------------------------------------------

describe('EntityDataType', () => {
  it('calls entityManager.addEntity on construction', () => {
    const mm = makeModelManager()
    const entity = new EntityDataType({
      Name: 'Tool1',
      EntityId: 'T001',
      EntityType: 4,
      IsExternal: false
    }, mm)
    expect(mm.entityManager.addEntity).toHaveBeenCalledOnce()
    expect(mm.entityManager.addEntity).toHaveBeenCalledWith(entity)
  })

  it('maps properties from parameters', () => {
    const mm = makeModelManager()
    const entity = new EntityDataType({
      Name: 'Sensor',
      EntityId: 'S001',
      EntityType: 7
    }, mm)
    expect(entity.Name).toBe('Sensor')
    expect(entity.EntityId).toBe('S001')
    expect(entity.EntityType).toBe(7)
  })

  it('does not crash when modelManager has no entityManager', () => {
    const entity = new EntityDataType({ Name: 'X' }, {})
    expect(entity.Name).toBe('X')
  })
})

// ---------------------------------------------------------------------------
// EntityTypes enum
// ---------------------------------------------------------------------------

describe('EntityTypes enum', () => {
  it('has correct entry for tool (4)', () => {
    expect(EntityTypes[4]).toBe('tool')
  })

  it('has correct entry for undefined (0)', () => {
    expect(EntityTypes[0]).toBe('undefined')
  })

  it('has correct entry for joint (23)', () => {
    expect(EntityTypes[23]).toBe('joint')
  })

  it('has correct entry for virtual_station (41)', () => {
    expect(EntityTypes[41]).toBe('virtual_station')
  })

  it('covers all entries from 0 to 41', () => {
    for (let i = 0; i <= 41; i++) {
      expect(EntityTypes[i]).toBeDefined()
    }
  })
})

// ---------------------------------------------------------------------------
// EventManager
// ---------------------------------------------------------------------------

function makeConnectionManager (socketHandlerCallbacks = {}) {
  const socketHandler = {
    registerMandatory: vi.fn((cmd, cb) => {
      socketHandlerCallbacks[cmd] = cb
    })
  }
  return {
    socketHandler,
    subscribe: vi.fn(),
    _callbacks: socketHandlerCallbacks
  }
}

describe('EventManager', () => {
  let connMgr, callbacks, mm, em

  beforeEach(() => {
    callbacks = {}
    connMgr = makeConnectionManager(callbacks)
    mm = makeModelManager()
    em = new EventManager(connMgr, mm)
  })

  it('registers mandatory "event" handler on construction', () => {
    expect(connMgr.socketHandler.registerMandatory).toHaveBeenCalledWith('event', expect.any(Function))
  })

  it('subscribeEvent adds filter/callback pair', () => {
    const filter = vi.fn(() => true)
    const callback = vi.fn()
    em.subscribeEvent(filter, callback)
    expect(em.callbacks).toHaveLength(1)
  })

  it('subscribeEvent ignores null filter', () => {
    em.subscribeEvent(null, vi.fn())
    expect(em.callbacks).toHaveLength(0)
  })

  it('listenEvent adds filter/callback pair', () => {
    const filter = vi.fn(() => true)
    const callback = vi.fn()
    em.listenEvent(filter, callback)
    expect(em.callbacks).toHaveLength(1)
  })

  it('receivedEvent calls makeCalls when queue is null', () => {
    const filter = vi.fn(() => true)
    const callback = vi.fn()
    em.subscribeEvent(filter, callback)

    const msg = { EventType: { Identifier: 9999 }, data: 'test' }
    em.receivedEvent(msg)

    expect(mm.createModelFromEvent).toHaveBeenCalledWith(msg)
    expect(filter).toHaveBeenCalled()
    expect(callback).toHaveBeenCalled()
  })

  it('receivedEvent enqueues when queue is active', () => {
    em.queueState(true)
    const msg = { EventType: { Identifier: 9999 } }
    em.receivedEvent(msg)
    expect(em.queue.size()).toBe(1)
    expect(mm.createModelFromEvent).not.toHaveBeenCalled()
  })

  it('queueState(false) disables queuing', () => {
    em.queueState(true)
    em.queueState(false)
    expect(em.queue).toBeNull()
  })

  it('makeCalls invokes only callbacks where filter returns true', () => {
    const cbTrue = vi.fn()
    const cbFalse = vi.fn()
    em.subscribeEvent(() => true, cbTrue)
    em.subscribeEvent(() => false, cbFalse)

    const msg = { EventType: { Identifier: 9999 } }
    em.makeCalls(msg)

    expect(cbTrue).toHaveBeenCalledOnce()
    expect(cbFalse).not.toHaveBeenCalled()
  })

  it('dequeue processes queued event and returns model', () => {
    em.queueState(true)
    const msg = { EventType: { Identifier: 9999 }, tag: 'first' }
    em.receivedEvent(msg)

    const model = em.dequeue()
    expect(model).toBeDefined()
    expect(mm.createModelFromEvent).toHaveBeenCalledWith(msg)
  })

  it('reset clears all callbacks', () => {
    em.subscribeEvent(() => true, vi.fn())
    em.subscribeEvent(() => false, vi.fn())
    em.reset()
    expect(em.callbacks).toHaveLength(0)
  })

  it('callback exception does not propagate to caller', () => {
    em.subscribeEvent(() => true, () => { throw new Error('broken callback') })
    const msg = { EventType: { Identifier: 9999 } }
    // Should not throw
    expect(() => em.makeCalls(msg)).not.toThrow()
  })
})
