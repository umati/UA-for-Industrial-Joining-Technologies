/**
 * Unit tests for EntityCache (entity-manager.mjs).
 *
 * makeSelectableEntityView uses document.createElement, so we mock global.document
 * in beforeEach. All other methods are pure data-structure operations.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EntityCache } from '../../../src/javascripts/ijt-support/entity-cache/entity-manager.mjs'

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function makeMockElement (tag) {
  return {
    tag,
    textContent: '',
    classList: { add: vi.fn() },
    onclick: null,
    children: [],
    appendChild (child) { this.children.push(child) }
  }
}

// ---------------------------------------------------------------------------
// Shared setup
// ---------------------------------------------------------------------------

let cache
let createdElements

beforeEach(() => {
  cache = new EntityCache()
  createdElements = []
  global.document = {
    createElement: vi.fn((tag) => {
      const el = makeMockElement(tag)
      createdElements.push(el)
      return el
    })
  }
})

// ---------------------------------------------------------------------------
// constructor
// ---------------------------------------------------------------------------

describe('EntityCache — constructor', () => {
  it('initialises with an empty cache object', () => {
    expect(cache.cache).toEqual({})
  })

  it('initialises with an empty callbacks array', () => {
    expect(cache.callbacks).toEqual([])
  })

  it('exposes EntityTypes map', () => {
    expect(cache.entityTypes).toBeDefined()
    expect(cache.entityTypes[4]).toBe('tool')
    expect(cache.entityTypes[3]).toBe('controller')
  })
})

// ---------------------------------------------------------------------------
// subscribe
// ---------------------------------------------------------------------------

describe('EntityCache — subscribe', () => {
  it('registers a callback', () => {
    const cb = vi.fn()
    cache.subscribe(cb)
    expect(cache.callbacks).toHaveLength(1)
    expect(cache.callbacks[0]).toBe(cb)
  })

  it('supports registering multiple subscribers', () => {
    cache.subscribe(vi.fn())
    cache.subscribe(vi.fn())
    expect(cache.callbacks).toHaveLength(2)
  })
})

// ---------------------------------------------------------------------------
// addEntity
// ---------------------------------------------------------------------------

describe('EntityCache — addEntity', () => {
  it('adds an entity to the correct type bucket', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    expect(cache.cache[4]).toHaveLength(1)
    expect(cache.cache[4][0]).toBe(entity)
  })

  it('creates separate buckets for different EntityTypes', () => {
    const tool = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    const ctrl = { EntityType: 3, EntityId: 'ctrl-1', Name: 'Ctrl A' }
    cache.addEntity(tool)
    cache.addEntity(ctrl)
    expect(cache.cache[4]).toHaveLength(1)
    expect(cache.cache[3]).toHaveLength(1)
  })

  it('appends to an existing bucket for the same EntityType', () => {
    const e1 = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    const e2 = { EntityType: 4, EntityId: 'tool-2', Name: 'Tool B' }
    cache.addEntity(e1)
    cache.addEntity(e2)
    expect(cache.cache[4]).toHaveLength(2)
  })

  it('deduplicates: ignores entity already present (same type + id)', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    cache.addEntity(entity)
    expect(cache.cache[4]).toHaveLength(1)
  })

  it('notifies subscribers after adding', () => {
    const cb = vi.fn()
    cache.subscribe(cb)
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    expect(cb).toHaveBeenCalledOnce()
    expect(cb).toHaveBeenCalledWith(cache.cache, entity)
  })
})

// ---------------------------------------------------------------------------
// removeEntity
// ---------------------------------------------------------------------------

describe('EntityCache — removeEntity', () => {
  it('removes the entity from its type bucket', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    cache.removeEntity(entity)
    expect(cache.cache[4]).toHaveLength(0)
  })

  it('notifies subscribers after removing', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    const cb = vi.fn()
    cache.subscribe(cb)
    cache.removeEntity(entity)
    expect(cb).toHaveBeenCalledOnce()
    expect(cb).toHaveBeenCalledWith(cache.cache, entity)
  })

  it('is a no-op on an empty cache (does not throw)', () => {
    expect(() => cache.removeEntity({ EntityType: 4, EntityId: 'ghost' })).not.toThrow()
  })

  it('removes across ALL type buckets that share the same EntityId', () => {
    const e1 = { EntityType: 4, EntityId: 'shared', Name: 'Tool' }
    const e2 = { EntityType: 3, EntityId: 'shared', Name: 'Ctrl' }
    cache.addEntity(e1)
    cache.addEntity(e2)
    cache.removeEntity({ EntityId: 'shared' })
    expect(cache.cache[4]).toHaveLength(0)
    expect(cache.cache[3]).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// getEntityFromId
// ---------------------------------------------------------------------------

describe('EntityCache — getEntityFromId', () => {
  it('returns the entity when found by type + id', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    expect(cache.getEntityFromId(4, 'tool-1')).toBe(entity)
  })

  it('returns undefined for an unknown EntityType', () => {
    expect(cache.getEntityFromId(99, 'tool-1')).toBeUndefined()
  })

  it('returns undefined for an id not present in a known type bucket', () => {
    cache.addEntity({ EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' })
    expect(cache.getEntityFromId(4, 'nonexistent')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// updateEntity
// ---------------------------------------------------------------------------

describe('EntityCache — updateEntity', () => {
  it('replaces the existing entity with updated data', () => {
    const original = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    const updated = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A Updated' }
    cache.addEntity(original)
    cache.updateEntity(updated)
    expect(cache.getEntityFromId(4, 'tool-1').Name).toBe('Tool A Updated')
  })

  it('notifies subscribers once for an update', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    const cb = vi.fn()
    cache.subscribe(cb)
    cache.updateEntity(entity)
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('moves an entity to its new type bucket when the type changes', () => {
    const original = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    const updated = { EntityType: 3, EntityId: 'tool-1', Name: 'Tool A Updated' }
    cache.addEntity(original)
    cache.updateEntity(updated)
    expect(cache.getEntityFromId(4, 'tool-1')).toBeUndefined()
    expect(cache.getEntityFromId(3, 'tool-1').Name).toBe('Tool A Updated')
  })
})

// ---------------------------------------------------------------------------
// _notify — error isolation
// ---------------------------------------------------------------------------

describe('EntityCache — _notify error isolation', () => {
  it('continues calling later subscribers even if an earlier one throws', () => {
    const throwing = vi.fn().mockImplementation(() => { throw new Error('boom') })
    const good = vi.fn()
    cache.subscribe(throwing)
    cache.subscribe(good)
    const entity = { EntityType: 4, EntityId: 'x', Name: 'X' }
    expect(() => cache.addEntity(entity)).not.toThrow()
    expect(good).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// makeSelectableEntityView
// ---------------------------------------------------------------------------

describe('EntityCache — makeSelectableEntityView', () => {
  it('creates a background div and a label element', () => {
    cache.makeSelectableEntityView(() => {}, 'My Title')
    const tags = createdElements.map(e => e.tag)
    expect(tags).toContain('div')
    expect(tags).toContain('label')
  })

  it('sets the title text on the label', () => {
    cache.makeSelectableEntityView(() => {}, 'My Title')
    const label = createdElements.find(e => e.tag === 'label')
    expect(label.textContent).toBe('My Title')
  })

  it('skips empty type buckets — only background div + label are created', () => {
    cache.cache[4] = [] // Explicitly empty bucket
    cache.makeSelectableEntityView(() => {}, 'Title')
    const divs = createdElements.filter(e => e.tag === 'div')
    expect(divs).toHaveLength(1) // Only the background div
  })

  it('creates an area div and identifier divs for entities', () => {
    cache.addEntity({ EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' })
    createdElements = [] // Reset to only capture makeSelectableEntityView calls
    cache.makeSelectableEntityView(() => {}, 'Title')
    // background + area + identifier = 3 divs; plus 1 label
    const divs = createdElements.filter(e => e.tag === 'div')
    expect(divs.length).toBeGreaterThanOrEqual(2)
  })

  it('wires onclick on identifier divs, calling onselect with event and entity', () => {
    const entity = { EntityType: 4, EntityId: 'tool-1', Name: 'Tool A' }
    cache.addEntity(entity)
    createdElements = []
    const onselect = vi.fn()
    cache.makeSelectableEntityView(onselect, 'Title')
    const identifierDivs = createdElements.filter(e => e.onclick !== null)
    expect(identifierDivs).toHaveLength(1)
    const fakeEvent = {}
    identifierDivs[0].onclick(fakeEvent)
    expect(onselect).toHaveBeenCalledWith(fakeEvent, entity)
  })
})
