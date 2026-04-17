/**
 * Unit tests for:
 *   - models/joints/joint-data-type.mjs  (JointDataType)
 *   - joints/joint-manager.mjs           (JointManager)
 *   - entity-cache/entity-manager.mjs    (EntityCache — thin subclass)
 *   - models/events/base-event-model.mjs (BaseEventType)
 *   - models/events/joining-system-event-model.mjs
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { JointDataType } from '../../../src/javascripts/ijt-support/models/joints/joint-data-type.mjs'
import { JointManager } from '../../../src/javascripts/ijt-support/joints/joint-manager.mjs'
import { EntityCache } from '../../../src/javascripts/ijt-support/entity-cache/entity-manager.mjs'
import BaseEventType from '../../../src/javascripts/ijt-support/models/events/base-event-model.mjs'
import JoiningSystemEventModel from '../../../src/javascripts/ijt-support/models/events/joining-system-event-model.mjs'
import JoiningSystemResultReadyEventModel from '../../../src/javascripts/ijt-support/models/events/joining-system-result-ready-event-model.mjs'
import { ModelManager } from '../../../src/javascripts/ijt-support/models/model-manager.mjs'

// ---------------------------------------------------------------------------
// Minimal model manager stubs
// ---------------------------------------------------------------------------

function makeSimpleMM (overrides = {}) {
  return {
    entityManager: { addEntity: vi.fn() },
    jointManager: { addEntity: vi.fn() },
    factory (key, value) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) return value
      return value
    },
    ...overrides
  }
}

function makeRealMM () {
  return new ModelManager(
    { addEntity: vi.fn() },
    { addEntity: vi.fn() }
  )
}

// ---------------------------------------------------------------------------
// JointDataType
// ---------------------------------------------------------------------------

describe('JointDataType', () => {
  it('constructs from parameters', () => {
    const mm = makeSimpleMM()
    const joint = new JointDataType({ Name: 'Joint1', EntityId: 'J1', EntityType: 23 }, mm)
    expect(joint.Name).toBe('Joint1')
    expect(joint.EntityId).toBe('J1')
  })

  it('calls jointManager.addEntity when jointManager is present', () => {
    const mm = makeSimpleMM()
    const joint = new JointDataType({ Name: 'J1', EntityId: 'j1' }, mm)
    expect(mm.jointManager.addEntity).toHaveBeenCalledWith(joint)
  })

  it('does NOT call jointManager.addEntity when modelManager has no jointManager', () => {
    const mm = makeSimpleMM({ jointManager: undefined })
    expect(() => new JointDataType({ Name: 'J1' }, mm)).not.toThrow()
  })

  it('does NOT call jointManager.addEntity when modelManager is absent', () => {
    // Passing a factory-only stub without jointManager
    const mm = { factory: (k, v) => v }
    expect(() => new JointDataType({ Name: 'J1' }, mm)).not.toThrow()
  })

  it('works with empty parameters', () => {
    const mm = makeSimpleMM()
    const joint = new JointDataType({}, mm)
    expect(joint).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// JointManager
// ---------------------------------------------------------------------------

describe('JointManager', () => {
  let jm

  beforeEach(() => {
    jm = new JointManager()
  })

  it('initialises with an empty cache', () => {
    expect(jm.cache).toEqual({})
  })

  it('adds and retrieves a joint by type+id', () => {
    const joint = { EntityType: 23, EntityId: 'j1', Name: 'Joint A' }
    jm.addEntity(joint)
    expect(jm.getEntityFromId(23, 'j1')).toBe(joint)
  })

  it('deduplicates joints', () => {
    const joint = { EntityType: 23, EntityId: 'j1', Name: 'J' }
    jm.addEntity(joint)
    jm.addEntity(joint)
    expect(jm.cache[23]).toHaveLength(1)
  })

  it('removes joints', () => {
    const joint = { EntityType: 23, EntityId: 'j1', Name: 'J' }
    jm.addEntity(joint)
    jm.removeEntity(joint)
    expect(jm.cache[23]).toHaveLength(0)
  })

  it('notifies subscribers on add', () => {
    const cb = vi.fn()
    jm.subscribe(cb)
    const joint = { EntityType: 23, EntityId: 'j2', Name: 'J2' }
    jm.addEntity(joint)
    expect(cb).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// EntityCache (thin subclass of EntityCacheBase)
// ---------------------------------------------------------------------------

describe('EntityCache', () => {
  let cache

  beforeEach(() => {
    cache = new EntityCache()
  })

  it('is a distinct class from JointManager', () => {
    expect(cache).toBeInstanceOf(EntityCache)
    expect(cache).not.toBeInstanceOf(JointManager)
  })

  it('initialises with empty cache and callbacks', () => {
    expect(cache.cache).toEqual({})
    expect(cache.callbacks).toEqual([])
  })

  it('operates identically to its base — add, get, remove', () => {
    const entity = { EntityType: 4, EntityId: 'e1', Name: 'E' }
    cache.addEntity(entity)
    expect(cache.getEntityFromId(4, 'e1')).toBe(entity)
    cache.removeEntity(entity)
    expect(cache.getEntityFromId(4, 'e1')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// BaseEventType — getEventName()
// ---------------------------------------------------------------------------

describe('BaseEventType — getEventName', () => {
  it('returns formatted name with ConditionClassName and ConditionSubClassName', () => {
    const mm = makeSimpleMM()
    const evt = new BaseEventType({
      ConditionClassName: 'Alarm',
      ConditionSubClassName: ['High', 'Critical']
    }, mm)
    const name = evt.getEventName()
    expect(name).toContain('Alarm')
    expect(name).toContain('High')
    expect(name).toContain('Critical')
  })

  it('returns "ResultEvent" when no ConditionClassName but Result is present', () => {
    const mm = makeSimpleMM()
    const evt = new BaseEventType({ Result: { ResultId: 'r1' } }, mm)
    expect(evt.getEventName()).toBe('ResultEvent')
  })

  it('returns undefined when neither ConditionClassName nor Result is present', () => {
    const mm = makeSimpleMM()
    const evt = new BaseEventType({ EventType: 'SomeType' }, mm)
    expect(evt.getEventName()).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// JoiningSystemEventModel
// ---------------------------------------------------------------------------

describe('JoiningSystemEventModel', () => {
  it('constructs, stripping Result-prefixed keys', () => {
    const mm = makeRealMM()
    const params = {
      EventType: { NamespaceIndex: 2, Identifier: 1006 },
      ResultStatus: 'some-status',
      EventId: 'evt-1',
      Message: 'Hello'
    }
    const model = new JoiningSystemEventModel(params, mm)
    // ResultStatus starts with 'Result' → stripped
    expect(model.ResultStatus).toBeUndefined()
    // EventId does not start with Result or JoiningSystemEventContent → kept
    expect(model.EventId).toBe('evt-1')
  })

  it('strips JoiningSystemEventContent prefix keys that lack a slash', () => {
    const mm = makeRealMM()
    const params = {
      JoiningSystemEventContent: 'top-level', // no slash → dropped
      'JoiningSystemEventContent/EventCode': 'EC-42'
    }
    const model = new JoiningSystemEventModel(params, mm)
    expect(model.JoiningSystemEventContent).toBeUndefined()
    // Slash-containing key → last part is extracted
    expect(model.EventCode).toBe('EC-42')
  })

  it('keeps ordinary keys unchanged', () => {
    const mm = makeRealMM()
    const params = { Severity: 500, EventId: 'evt-2' }
    const model = new JoiningSystemEventModel(params, mm)
    expect(model.Severity).toBe(500)
  })
})

// ---------------------------------------------------------------------------
// JoiningSystemResultReadyEventModel
// ---------------------------------------------------------------------------

describe('JoiningSystemResultReadyEventModel', () => {
  function makeResultParams (resultId = 'r1') {
    return {
      EventType: { NamespaceIndex: 2, Identifier: 1007 },
      EventId: 'e1',
      // A bare Result key with a minimal ResultMetaData (no CreationTime → reference)
      Result: {
        ResultMetaData: { ResultId: resultId, Name: 'Test', Classification: '1' }
      }
    }
  }

  it('constructs without throwing', () => {
    const mm = makeRealMM()
    expect(() => new JoiningSystemResultReadyEventModel(makeResultParams(), mm)).not.toThrow()
  })

  it('exposes a Result property', () => {
    const mm = makeRealMM()
    const model = new JoiningSystemResultReadyEventModel(makeResultParams(), mm)
    expect(model.Result).toBeDefined()
  })

  it('initialises Result.ClientData when missing', () => {
    const mm = makeRealMM()
    const model = new JoiningSystemResultReadyEventModel(makeResultParams('r-init'), mm)
    expect(model.Result.ClientData).toBeDefined()
  })

  it('strips JoiningSystemEventContent-prefixed keys', () => {
    const mm = makeRealMM()
    const params = {
      ...makeResultParams(),
      'JoiningSystemEventContent/SomeKey': 'val'
    }
    const model = new JoiningSystemResultReadyEventModel(params, mm)
    expect(model.SomeKey).toBeUndefined()
    expect(model['JoiningSystemEventContent/SomeKey']).toBeUndefined()
  })

  it('keeps non-Result, non-JoiningSystem keys', () => {
    const mm = makeRealMM()
    const params = { ...makeResultParams(), Severity: 700 }
    const model = new JoiningSystemResultReadyEventModel(params, mm)
    expect(model.Severity).toBe(700)
  })
})
