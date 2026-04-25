import { describe, it, expect, vi, beforeEach } from 'vitest'
import AddressSpaceGraphics from '../../../../javascripts/views/address-space/address-space-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeSocketHandler () {
  return {
    registerMandatory: vi.fn()
  }
}

function makeConnectionManager () {
  const subs = []
  return {
    socketHandler: makeSocketHandler(),
    subscribe: vi.fn((trigger, cb) => subs.push({ trigger, cb })),
    _trigger (t, v) { subs.filter(s => s.trigger === t).forEach(s => s.cb(v)) }
  }
}

function makeAddressSpace (cm) {
  return {
    connectionManager: cm,
    reset: vi.fn(),
    socketHandler: makeSocketHandler(),
    // Return a never-resolving promise so the .then() callback never fires,
    // preventing 'Cannot read properties of undefined (reading children)' errors
    findOrLoadNode: vi.fn(() => new Promise(() => {}))
  }
}

function makeNode (overrides = {}) {
  return {
    nodeId: 'ns=0;i=84',
    browseName: 'Objects',
    browseButton: null,
    getChildRelations: vi.fn(() => []),
    ...overrides
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AddressSpaceGraphics', () => {
  let cm, as, asg

  beforeEach(() => {
    cm = makeConnectionManager()
    as = makeAddressSpace(cm)
    asg = new AddressSpaceGraphics(as)
    asg.messages = asg.messages || document.createElement('div')
    asg.messages.scrollTo = vi.fn()
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('title is "Address Space"', () => {
    expect(asg.title).toBe('Address Space')
  })

  it('stores addressSpace', () => {
    expect(asg.addressSpace).toBe(as)
  })

  it('subscribes to "session" on connectionManager', () => {
    expect(cm.subscribe).toHaveBeenCalledWith('session', expect.any(Function))
  })

  it('calls initiateNodeTree when session fires true', async () => {
    const spy = vi.spyOn(asg, 'initiateNodeTree')
    cm._trigger('session', true)
    expect(spy).toHaveBeenCalled()
  })

  it('does not call initiateNodeTree when session fires false', () => {
    const spy = vi.spyOn(asg, 'initiateNodeTree')
    cm._trigger('session', false)
    expect(spy).not.toHaveBeenCalled()
  })

  // ── initiateNodeTree ─────────────────────────────────────────────────────────

  describe('initiateNodeTree', () => {
    it('calls addressSpace.reset()', () => {
      asg.initiateNodeTree()
      expect(as.reset).toHaveBeenCalled()
    })

    it('registers "browseresult" mandatory handler', () => {
      asg.initiateNodeTree()
      expect(as.socketHandler.registerMandatory).toHaveBeenCalledWith(
        'browseresult', expect.any(Function)
      )
    })

    it('registers "readresult" mandatory handler', () => {
      asg.initiateNodeTree()
      expect(as.socketHandler.registerMandatory).toHaveBeenCalledWith(
        'readresult', expect.any(Function)
      )
    })

    it('calls findOrLoadNode with root ns=0;i=84', () => {
      asg.initiateNodeTree()
      expect(as.findOrLoadNode).toHaveBeenCalledWith('ns=0;i=84')
    })
  })

  // ── createGUINode ────────────────────────────────────────────────────────────

  describe('createGUINode', () => {
    it('returns a div', () => {
      const node = makeNode()
      const area = asg.createGUINode(node)
      expect(area.tagName).toBe('DIV')
    })

    it('uses controlArea as default context', () => {
      const node = makeNode()
      const area = asg.createGUINode(node)
      expect(asg.controlArea.contains(area)).toBe(true)
    })

    it('uses the supplied context', () => {
      const ctx = document.createElement('div')
      const node = makeNode()
      const area = asg.createGUINode(node, ctx)
      expect(ctx.contains(area)).toBe(true)
    })

    it('creates a browse button with the node name', () => {
      const node = makeNode({ browseName: 'Objects' })
      const area = asg.createGUINode(node)
      const btn = area.querySelector('button')
      expect(btn.textContent).toBe('Objects')
    })

    it('uses "undefined" when node has no browseName', () => {
      const node = makeNode({ browseName: null })
      const area = asg.createGUINode(node)
      const btn = area.querySelector('button')
      expect(btn.textContent).toBe('undefined')
    })

    it('assigns nodeId to the area', () => {
      const node = makeNode({ nodeId: 'ns=1;i=42' })
      const area = asg.createGUINode(node)
      expect(area.nodeId).toBe('ns=1;i=42')
    })

    it('stores browse button on the node', () => {
      const node = makeNode()
      asg.createGUINode(node)
      expect(node.browseButton).not.toBeNull()
    })

    it('does not create a second button when browseButton already set', () => {
      const node = makeNode()
      const existing = document.createElement('button')
      node.browseButton = existing
      const area = asg.createGUINode(node)
      expect(area.querySelectorAll('button').length).toBe(0)
    })

    it('replaces an existing child with the same nodeId', () => {
      const ctx = document.createElement('div')
      const nodeId = 'ns=0;i=100'
      // First insertion
      const node = makeNode({ nodeId })
      asg.createGUINode(node, ctx)
      // Second insertion with same nodeId — should replace, not double-append
      node.browseButton = null
      asg.createGUINode(node, ctx)
      const sameIdChildren = Array.from(ctx.children).filter(c => c.nodeId === nodeId)
      expect(sameIdChildren).toHaveLength(1)
    })
  })

  // ── createRelation ───────────────────────────────────────────────────────────

  describe('createRelation', () => {
    it('returns a browse button', () => {
      const ctx = document.createElement('div')
      const relation = { nodeId: 'ns=1;i=1', browseName: { name: 'Child' }, nodeClass: 'Object' }
      const btn = asg.createRelation(relation, ctx, vi.fn())
      expect(btn.tagName).toBe('BUTTON')
    })

    it('button text is relation.browseName.name', () => {
      const ctx = document.createElement('div')
      const relation = { nodeId: 'ns=1;i=2', browseName: { name: 'ChildNode' }, nodeClass: 'Variable' }
      const btn = asg.createRelation(relation, ctx, vi.fn())
      expect(btn.textContent).toBe('ChildNode')
    })

    it('clicking the button calls the callback', () => {
      const ctx = document.createElement('div')
      const cb = vi.fn()
      const relation = { nodeId: 'ns=1;i=3', browseName: { name: 'N' }, nodeClass: 'Object' }
      const btn = asg.createRelation(relation, ctx, cb)
      btn.onclick()
      expect(cb).toHaveBeenCalled()
    })

    it('sets button color from nodeClassColor map', () => {
      const ctx = document.createElement('div')
      const relation = { nodeId: 'ns=1;i=4', browseName: { name: 'N' }, nodeClass: 'Method' }
      const btn = asg.createRelation(relation, ctx, vi.fn())
      expect(btn.style.color).toBe('green')
    })
  })

  // ── cleanse ──────────────────────────────────────────────────────────────────

  describe('cleanse', () => {
    it('removes all children beyond the first', () => {
      const area = document.createElement('div')
      area.appendChild(document.createElement('button'))
      area.appendChild(document.createElement('div'))
      area.appendChild(document.createElement('div'))
      asg.cleanse(area)
      expect(area.children.length).toBe(1)
    })

    it('does nothing when area has 0 or 1 children', () => {
      const area = document.createElement('div')
      area.appendChild(document.createElement('span'))
      asg.cleanse(area)
      expect(area.children.length).toBe(1)
    })

    it('handles empty area without throwing', () => {
      const area = document.createElement('div')
      expect(() => asg.cleanse(area)).not.toThrow()
    })
  })

  // ── toggleNodeContent ─────────────────────────────────────────────────────────

  describe('toggleNodeContent', () => {
    it('calls cleanse when buttonArea has multiple children (collapse)', () => {
      const node = makeNode()
      const area = document.createElement('div')
      area.appendChild(document.createElement('button'))
      area.appendChild(document.createElement('div'))
      const cleanseSpy = vi.spyOn(asg, 'cleanse')
      asg.toggleNodeContent(node, area)
      expect(cleanseSpy).toHaveBeenCalled()
    })

    it('creates relations when buttonArea has only 1 child (expand)', () => {
      const relation = { nodeId: 'ns=1;i=5', browseName: { name: 'R' }, nodeClass: 'Object', referenceTypeName: 'HasComponent' }
      const node = makeNode({ getChildRelations: vi.fn(() => [relation]) })
      const area = document.createElement('div')
      area.appendChild(document.createElement('button'))
      asg.toggleNodeContent(node, area)
      // A relation button should have been added
      expect(area.querySelectorAll('button').length).toBeGreaterThan(1)
    })

    it('skips hasTypeDefinition relations', () => {
      const relation = {
        nodeId: 'ns=1;i=6',
        browseName: { name: 'FolderType' },
        nodeClass: 'Object',
        referenceTypeName: 'hasTypeDefinition'
      }
      const node = makeNode({ getChildRelations: vi.fn(() => [relation]) })
      const area = document.createElement('div')
      area.appendChild(document.createElement('button'))
      asg.toggleNodeContent(node, area)
      // hasTypeDefinition is skipped → only original button remains
      expect(area.querySelectorAll('button').length).toBe(1)
    })
  })

  // ── convertRelationToNode ─────────────────────────────────────────────────────

  describe('convertRelationToNode', () => {
    it('calls findOrLoadNode for Object nodeClass', async () => {
      const relation = { nodeId: 'ns=1;i=10', nodeClass: 'Object' }
      const area = document.createElement('div')
      area.appendChild(document.createElement('button'))
      asg.convertRelationToNode(relation, area)
      expect(as.findOrLoadNode).toHaveBeenCalledWith('ns=1;i=10')
    })

    it('calls findOrLoadNode for Variable nodeClass', async () => {
      const relation = { nodeId: 'ns=1;i=11', nodeClass: 'Variable' }
      const area = document.createElement('div')
      asg.convertRelationToNode(relation, area)
      expect(as.findOrLoadNode).toHaveBeenCalledWith('ns=1;i=11')
    })

    it('does not call findOrLoadNode for Method nodeClass', () => {
      const relation = { nodeId: 'ns=1;i=12', nodeClass: 'Method' }
      const area = document.createElement('div')
      as.findOrLoadNode.mockClear()
      asg.convertRelationToNode(relation, area)
      expect(as.findOrLoadNode).not.toHaveBeenCalled()
    })
  })
})
