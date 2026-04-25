/**
 * Tests for node.mjs — NodeFactory + PartialNode hierarchy
 *
 * All three concrete node types (ObjectNode, VariableNode, MethodNode) inherit
 * from PartialNode which holds the full relation-traversal API.  NodeFactory
 * is a pure switch with no I/O — easy to exercise without DOM or network.
 */

import { NodeFactory } from 'ijt-support/address-space/node.mjs'

// ─── helpers ─────────────────────────────────────────────────────────────────

/**
 * Build a minimal node data object suitable for PartialNode.
 *
 * @param {object} overrides — merge into defaults
 */
function makeData ({
  nodeclass = { value: 1 },         // 1 = ObjectNode
  displayname = { value: { text: 'TestNode' } },
  nodeid = 'ns=1;i=42',
  nodeclass_value,
  relations = []
} = {}) {
  return { nodeclass, displayname, nodeid, relations }
}

/**
 * Build a relation entry as the OPC UA browse response would contain it.
 *
 * @param {object} opts
 */
function makeRelation ({
  referenceTypeId = 'ns=0;i=47',  // component (mapped)
  nodeId = 'ns=1;i=100',
  browseName = { name: 'ChildNode' },
  isForward = true,
  typeDefinition = 'ns=7;i=1005'
} = {}) {
  return { referenceTypeId, nodeId, browseName, isForward, typeDefinition }
}

// ─── NodeFactory ─────────────────────────────────────────────────────────────

describe('NodeFactory', () => {
  it('creates ObjectNode for nodeclass 1', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 1 } }))
    expect(node).toBeDefined()
    expect(node.nodeClass.value).toBe(1)
  })

  it('creates VariableNode for nodeclass 2', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 2 } }))
    expect(node).toBeDefined()
    expect(node.nodeClass.value).toBe(2)
  })

  it('creates MethodNode for nodeclass 4', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 4 } }))
    expect(node).toBeDefined()
    expect(node.nodeClass.value).toBe(4)
  })

  it('falls back to ObjectNode for unknown nodeclass', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 99 } }))
    expect(node).toBeDefined()
    expect(node.nodeClass.value).toBe(99)
  })

  it('sets aname on ObjectNode when displayname is present', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 1 }, displayname: { value: { text: 'Pump' } } }))
    expect(node.aname).toBe('Pump Object')
  })

  it('sets aname on VariableNode when displayname is present', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 2 }, displayname: { value: { text: 'Speed' } } }))
    expect(node.aname).toBe('SpeedVariable')
  })

  it('sets aname on MethodNode when displayname is present', () => {
    const node = NodeFactory(makeData({ nodeclass: { value: 4 }, displayname: { value: { text: 'Start' } } }))
    expect(node.aname).toBe('Start Method')
  })

  it('does not set aname when displayname is absent', () => {
    const node = NodeFactory({ nodeclass: { value: 1 }, nodeid: 'ns=1;i=1', relations: [] })
    expect(node.aname).toBeUndefined()
  })
})

// ─── PartialNode constructor — referenceTypeId mapping ───────────────────────

describe('PartialNode — constructor relation mapping', () => {
  const validIds = [
    ['ns=0;i=0',    'error'],
    ['ns=0;i=61',    'relation'],
    ['ns=0;i=40',    'hasTypeDefinition'],
    ['ns=0;i=46',    'hasProperty'],
    ['ns=0;i=35',    'organizes'],
    ['ns=0;i=41',    'generatesEvents'],
    ['ns=0;i=45',    'hasSubtype'],
    ['ns=0;i=47',    'component'],
    ['ns=0;i=48',    'hasNotifier'],
    ['ns=0;i=17603', 'hasInterface'],
    ['ns=0;i=17604', 'hasAddin'],
    ['ns=0;i=24137', 'association'],
  ]

  for (const [refId, expectedName] of validIds) {
    it(`maps referenceTypeId ${refId} → "${expectedName}"`, () => {
      const rel = makeRelation({ referenceTypeId: refId })
      const node = NodeFactory(makeData({ relations: [rel] }))
      expect(node.data.relations[0].referenceTypeName).toBe(expectedName)
    })
  }

  it('throws for an unmapped referenceTypeId', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0;i=9999' })
    expect(() => NodeFactory(makeData({ relations: [rel] }))).toThrow('referenceTypeId 9999 not mapped')
  })

  it('throws for a referenceTypeId with no i= segment', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0' })
    expect(() => NodeFactory(makeData({ relations: [rel] }))).toThrow()
  })
})

// ─── PartialNode getters ──────────────────────────────────────────────────────

describe('PartialNode getters', () => {
  let node

  beforeEach(() => {
    node = NodeFactory(makeData({
      nodeclass: { value: 1 },
      nodeid: 'ns=2;i=7',
      displayname: { value: { text: 'MyNode' } },
    }))
  })

  it('nodeId returns data.nodeid', () => {
    expect(node.nodeId).toBe('ns=2;i=7')
  })

  it('nodeClass returns data.nodeclass object', () => {
    expect(node.nodeClass).toEqual({ value: 1 })
  })

  it('browseName returns displayname text', () => {
    expect(node.browseName).toBe('MyNode')
  })

  it('displayName returns displayname text', () => {
    expect(node.displayName).toBe('MyNode')
  })
})

// ─── PartialNode relation queries ────────────────────────────────────────────

describe('PartialNode — getRelation()', () => {
  it('returns the relation matching nodeId', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0;i=47', nodeId: 'ns=1;i=200' })
    const node = NodeFactory(makeData({ relations: [rel] }))
    const found = node.getRelation('ns=1;i=200')
    expect(found).toBeDefined()
    expect(found.nodeId).toBe('ns=1;i=200')
  })

  it('returns undefined when nodeId does not match', () => {
    const rel = makeRelation({ nodeId: 'ns=1;i=200' })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getRelation('ns=1;i=999')).toBeUndefined()
  })
})

describe('PartialNode — getNamedRelation()', () => {
  it('returns relation with matching browseName.name', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0;i=47', browseName: { name: 'Actuator' } })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getNamedRelation('Actuator')).toBeDefined()
  })

  it('returns undefined for non-existent browseName', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0;i=47' })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getNamedRelation('Nobody')).toBeUndefined()
  })
})

describe('PartialNode — getRelations(type)', () => {
  it('returns all relations of the given referenceTypeName', () => {
    const r1 = makeRelation({ referenceTypeId: 'ns=0;i=47' })  // component
    const r2 = makeRelation({ referenceTypeId: 'ns=0;i=46' })  // hasProperty
    const r3 = makeRelation({ referenceTypeId: 'ns=0;i=47' })  // component
    const node = NodeFactory(makeData({ relations: [r1, r2, r3] }))
    const comps = node.getRelations('component')
    expect(comps).toHaveLength(2)
  })

  it('returns empty array when type not present', () => {
    const rel = makeRelation({ referenceTypeId: 'ns=0;i=46' })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getRelations('organizes')).toHaveLength(0)
  })
})

describe('PartialNode — getChildRelations(type)', () => {
  it('returns forward relations of the given type', () => {
    const forward = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: true })
    const backward = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: false })
    const node = NodeFactory(makeData({ relations: [forward, backward] }))
    expect(node.getChildRelations('component')).toHaveLength(1)
  })

  it('returns ALL forward relations when type is omitted', () => {
    const r1 = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: true })
    const r2 = makeRelation({ referenceTypeId: 'ns=0;i=46', isForward: true })
    const r3 = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: false })
    const node = NodeFactory(makeData({ relations: [r1, r2, r3] }))
    expect(node.getChildRelations()).toHaveLength(2)
  })
})

describe('PartialNode — getParentRelations()', () => {
  it('returns only backward (isForward=false) relations', () => {
    const parent = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: false })
    const child  = makeRelation({ referenceTypeId: 'ns=0;i=47', isForward: true })
    const node = NodeFactory(makeData({ relations: [parent, child] }))
    const parents = node.getParentRelations()
    expect(parents).toHaveLength(1)
    expect(parents[0].isForward).toBe(false)
  })

  it('returns empty array when no parent relations exist', () => {
    const node = NodeFactory(makeData({ relations: [] }))
    expect(node.getParentRelations()).toHaveLength(0)
  })
})

describe('PartialNode — getTypeDefinitionRelations(typeDefinition)', () => {
  it('matches relations where typeDefinition ends with the given i= value', () => {
    const rel = makeRelation({
      referenceTypeId: 'ns=0;i=40',
      typeDefinition: 'ns=7;i=1005'
    })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getTypeDefinitionRelations('1005')).toHaveLength(1)
  })

  it('returns empty array when i= value does not match', () => {
    const rel = makeRelation({
      referenceTypeId: 'ns=0;i=40',
      typeDefinition: 'ns=7;i=1005'
    })
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getTypeDefinitionRelations('9999')).toHaveLength(0)
  })

  it('handles multiple relations and returns only matching ones', () => {
    const r1 = makeRelation({ referenceTypeId: 'ns=0;i=40', typeDefinition: 'ns=7;i=1005' })
    const r2 = makeRelation({ referenceTypeId: 'ns=0;i=40', typeDefinition: 'ns=7;i=2001' })
    const r3 = makeRelation({ referenceTypeId: 'ns=0;i=40', typeDefinition: 'ns=7;i=1005' })
    const node = NodeFactory(makeData({ relations: [r1, r2, r3] }))
    expect(node.getTypeDefinitionRelations('1005')).toHaveLength(2)
  })
})
