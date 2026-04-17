/**
 * Extended coverage tests for:
 *   - models/support-models.mjs  (KeyValuePair.toHTML)
 *   - models/tag-data-type.mjs   (import/instantiate)
 *   - models/default-node.mjs    (node.value branch)
 *   - ijt-support.mjs            (re-export coverage)
 *   - entity-cache/entity-manager.mjs (import)
 *   - joints/joint-manager.mjs   (import)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// ijt-support.mjs — re-export index (needs import to cover re-export statements)
// ---------------------------------------------------------------------------

describe('ijt-support.mjs — re-export index', () => {
  it('exports EntityCacheBase from ijt-support.mjs', async () => {
    const { EntityCacheBase } = await import('ijt-support/ijt-support.mjs')
    expect(EntityCacheBase).toBeDefined()
  })

  it('exports ijtLog from ijt-support.mjs', async () => {
    const { ijtLog } = await import('ijt-support/ijt-support.mjs')
    expect(ijtLog).toBeDefined()
  })

  it('exports EntityCache from ijt-support.mjs', async () => {
    const { EntityCache } = await import('ijt-support/ijt-support.mjs')
    expect(EntityCache).toBeDefined()
  })

  it('exports JointManager from ijt-support.mjs', async () => {
    const { JointManager } = await import('ijt-support/ijt-support.mjs')
    expect(JointManager).toBeDefined()
  })

  it('exports MethodManager from ijt-support.mjs', async () => {
    const { MethodManager } = await import('ijt-support/ijt-support.mjs')
    expect(MethodManager).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// entity-cache/entity-manager.mjs
// ---------------------------------------------------------------------------

import { EntityCache } from '../../../src/javascripts/ijt-support/entity-cache/entity-manager.mjs'
import { JointManager } from '../../../src/javascripts/ijt-support/joints/joint-manager.mjs'

describe('EntityCache (entity-manager.mjs)', () => {
  it('can be instantiated as EntityCache', () => {
    const cache = new EntityCache()
    expect(cache).toBeInstanceOf(EntityCache)
  })

  it('inherits EntityCacheBase methods', () => {
    const cache = new EntityCache()
    expect(typeof cache.addEntity).toBe('function')
    expect(typeof cache.subscribe).toBe('function')
  })
})

// ---------------------------------------------------------------------------
// joints/joint-manager.mjs
// ---------------------------------------------------------------------------

describe('JointManager (joint-manager.mjs)', () => {
  it('can be instantiated as JointManager', () => {
    const jm = new JointManager()
    expect(jm).toBeInstanceOf(JointManager)
  })

  it('inherits EntityCacheBase methods', () => {
    const jm = new JointManager()
    expect(typeof jm.addEntity).toBe('function')
    expect(typeof jm.subscribe).toBe('function')
  })
})

// ---------------------------------------------------------------------------
// models/support-models.mjs — KeyValuePair.toHTML (lines 14-19)
// ---------------------------------------------------------------------------

import { KeyValuePair, LocalizationModel, NodeId as NodeIdModel } from '../../../src/javascripts/ijt-support/models/support-models.mjs'

function makeMockElement (tag) {
  return {
    tag,
    textContent: '',
    classList: { add: vi.fn() },
    onclick: null,
    children: [],
    appendChild (child) { this.children.push(child) },
    expandLong: null
  }
}

describe('support-models.mjs — KeyValuePair.toHTML', () => {
  beforeEach(() => {
    const createdElements = []
    global.document = {
      createElement: vi.fn((tag) => {
        const el = makeMockElement(tag)
        createdElements.push(el)
        return el
      })
    }
  })

  it('creates a container li with child li containing key: value text', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const kv = new KeyValuePair({ key: 'myKey', value: 'myValue' }, mockModelManager, {})
    const container = kv.toHTML(false, 'parent')
    expect(container).toBeDefined()
    expect(global.document.createElement).toHaveBeenCalledWith('li')
    // The child li should have textContent 'myKey: myValue'
    const childLi = container.children[0]
    expect(childLi.textContent).toBe('myKey: myValue')
  })

  it('container has expandLong as a no-op function', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const kv = new KeyValuePair({ key: 'k', value: 'v' }, mockModelManager, {})
    const container = kv.toHTML(true, 'p')
    expect(typeof container.expandLong).toBe('function')
    expect(() => container.expandLong()).not.toThrow()
  })
})

describe('support-models.mjs — LocalizationModel', () => {
  it('can be instantiated', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const lm = new LocalizationModel({ text: 'hello' }, mockModelManager, {})
    expect(lm).toBeDefined()
  })
})

describe('support-models.mjs — NodeId', () => {
  it('stringify returns ns=0;i=42 for numeric identifier', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeId = new NodeIdModel({ NamespaceIndex: 0, Identifier: 42 }, mockModelManager, {})
    expect(nodeId.stringify()).toBe('ns=0;i=42')
  })

  it('stringify returns ns=1;s=MyNode for string identifier', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeId = new NodeIdModel({ NamespaceIndex: 1, Identifier: 'MyNode' }, mockModelManager, {})
    expect(nodeId.stringify()).toBe('ns=1;s=MyNode')
  })

  it('compare returns true for matching identifier', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeId = new NodeIdModel({ NamespaceIndex: 2, Identifier: 'TestId' }, mockModelManager, {})
    expect(nodeId.compare('TestId')).toBe(true)
  })

  it('compare returns false for non-matching identifier', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeId = new NodeIdModel({ NamespaceIndex: 2, Identifier: 'TestId' }, mockModelManager, {})
    expect(nodeId.compare('OtherId')).toBe(false)
  })

  it('compare returns false when namespace does not match', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeId = new NodeIdModel({ NamespaceIndex: 2, Identifier: 'TestId' }, mockModelManager, {})
    expect(nodeId.compare('TestId', 99)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// models/tag-data-type.mjs  (0% — empty class, import to register module)
// ---------------------------------------------------------------------------

import TagDataType from '../../../src/javascripts/ijt-support/models/tag-data-type.mjs'

describe('models/tag-data-type.mjs — TagDataType', () => {
  it('TagDataType is importable', () => {
    expect(TagDataType).toBeDefined()
  })

  it('can be instantiated with empty parameters', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const tag = new TagDataType({}, mockModelManager, {})
    expect(tag).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// models/default-node.mjs — line 14 (node.value branch)
// ---------------------------------------------------------------------------

import { DefaultNode } from '../../../src/javascripts/ijt-support/models/default-node.mjs'

describe('models/default-node.mjs — DefaultNode', () => {
  it('sets this.value when node.value is provided', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeData = {
      browseData: { NodeId: 'ns=1;i=1' },
      value: 'test-value',
      relations: []
    }
    const dn = new DefaultNode(nodeData, mockModelManager)
    expect(dn.value).toBe('test-value')
  })

  it('does not set this.value when node.value is absent', () => {
    const mockModelManager = { factory: vi.fn((key, val) => val) }
    const nodeData = { browseData: {} }
    const dn = new DefaultNode(nodeData, mockModelManager)
    expect(dn.value).toBeUndefined()
  })
})
