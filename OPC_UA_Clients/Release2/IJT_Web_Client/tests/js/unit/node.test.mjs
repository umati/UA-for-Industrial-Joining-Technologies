/**
 * Unit tests for address-space/node.mjs
 * Tests PartialNode, ObjectNode, VariableNode, MethodNode, NodeFactory
 */

import { describe, it, expect } from 'vitest'
import { NodeFactory } from '../../../src/javascripts/ijt-support/address-space/node.mjs'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeData (overrides = {}) {
  return {
    attributes: {
      NodeId: { NamespaceIndex: 2, Identifier: 100 },
      NodeClass: 1,
      DisplayName: { Text: 'TestNode' },
      BrowseName: { Name: 'TestNode' },
      ...overrides.attributes
    },
    relations: overrides.relations ?? [],
    value: overrides.value ?? null,
    browseName: overrides.browseName,
    displayname: overrides.displayname
  }
}

function makeRelation (typeId, isForward = true, browseName = 'Child', typeDefId = null) {
  return {
    ReferenceTypeId: { Identifier: typeId },
    IsForward: isForward,
    BrowseName: { Name: browseName },
    NodeId: `ns=1;i=${Math.floor(Math.random() * 9000) + 1000}`,
    TypeDefinition: typeDefId ? { Identifier: typeDefId } : undefined
  }
}

// ---------------------------------------------------------------------------
// NodeFactory
// ---------------------------------------------------------------------------

describe('NodeFactory — NodeClass dispatch', () => {
  it('creates an ObjectNode for NodeClass 1', () => {
    const node = NodeFactory(makeData())
    expect(node.nodeClass).toBe(1)
  })

  it('creates a VariableNode for NodeClass 2', () => {
    const data = makeData({ attributes: { NodeClass: 2, NodeId: { NamespaceIndex: 0, Identifier: 1 }, DisplayName: { Text: 'V' }, BrowseName: { Name: 'V' } } })
    const node = NodeFactory(data)
    expect(node.nodeClass).toBe(2)
  })

  it('creates a MethodNode for NodeClass 4', () => {
    const data = makeData({ attributes: { NodeClass: 4, NodeId: { NamespaceIndex: 0, Identifier: 2 }, DisplayName: { Text: 'M' }, BrowseName: { Name: 'M' } } })
    const node = NodeFactory(data)
    expect(node.nodeClass).toBe(4)
  })

  it('falls back to ObjectNode for unknown NodeClass', () => {
    const data = makeData({ attributes: { NodeClass: 99, NodeId: { NamespaceIndex: 0, Identifier: 3 }, DisplayName: { Text: 'X' }, BrowseName: { Name: 'X' } } })
    const node = NodeFactory(data)
    // Default case → ObjectNode which has nodeClass 99
    expect(node.nodeClass).toBe(99)
  })

  it('handles missing NodeClass (undefined) — falls back to ObjectNode', () => {
    const node = NodeFactory({})
    expect(node).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// PartialNode — constructor defaults
// ---------------------------------------------------------------------------

describe('PartialNode — constructor initialisation', () => {
  it('initialises nodeId from attributes', () => {
    const node = NodeFactory(makeData())
    expect(node.nodeId).toEqual({ NamespaceIndex: 2, Identifier: 100 })
  })

  it('initialises with empty relations when none provided', () => {
    const node = NodeFactory(makeData({ relations: [] }))
    expect(node.data.relations).toEqual([])
  })

  it('sets default NodeId (0,0) when attributes.NodeId is missing', () => {
    const data = { attributes: {}, relations: [] }
    const node = NodeFactory(data)
    expect(node.nodeId).toEqual({ NamespaceIndex: 0, Identifier: 0 })
  })

  it('sets data.attributes when attributes is missing', () => {
    const node = NodeFactory({})
    expect(node.data.attributes).toBeDefined()
  })

  it('skips invalid (non-object) relation entries', () => {
    const data = makeData({ relations: [null, undefined, 'invalid', 42] })
    const node = NodeFactory(data)
    expect(node.data.relations).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// PartialNode — getters
// ---------------------------------------------------------------------------

describe('PartialNode — nodeIdString getter', () => {
  it('returns ;i= format for numeric identifier', () => {
    const node = NodeFactory(makeData())
    expect(node.nodeIdString).toBe('ns=2;i=100')
  })

  it('returns ;s= format for string identifier', () => {
    const data = makeData({ attributes: { NodeId: { NamespaceIndex: 1, Identifier: 'MyNode' }, NodeClass: 1, DisplayName: { Text: 'X' }, BrowseName: { Name: 'X' } } })
    const node = NodeFactory(data)
    expect(node.nodeIdString).toBe('ns=1;s=MyNode')
  })

  it('returns ;s=0 when NodeId Identifier is 0 (falsy number)', () => {
    const data = { attributes: {}, relations: [] }
    const node = NodeFactory(data)
    // Identifier is 0 (falsy) so Number(0) is 0 → uses ;s=
    expect(node.nodeIdString).toBe('ns=0;s=0')
  })
})

describe('PartialNode — value getter', () => {
  it('returns data.value', () => {
    const node = NodeFactory(makeData({ value: 42 }))
    expect(node.value).toBe(42)
  })

  it('returns null when no value', () => {
    const node = NodeFactory(makeData())
    expect(node.value).toBeNull()
  })
})

describe('PartialNode — browseName getter', () => {
  it('returns BrowseName.Name', () => {
    const node = NodeFactory(makeData())
    expect(node.browseName).toBe('TestNode')
  })
})

describe('PartialNode — displayName getter', () => {
  it('returns DisplayName.Text', () => {
    const node = NodeFactory(makeData())
    expect(node.displayName).toBe('TestNode')
  })
})

// ---------------------------------------------------------------------------
// PartialNode — relation methods
// ---------------------------------------------------------------------------

describe('PartialNode — getRelation', () => {
  it('finds a relation by nodeId', () => {
    const rel = makeRelation(47, true, 'Child')
    rel.nodeId = 'ns=1;i=999'
    const node = NodeFactory(makeData({ relations: [rel] }))
    const found = node.getRelation('ns=1;i=999')
    expect(found).toBe(rel)
    expect(node.getRelation('ns=0;i=0')).toBeUndefined()
  })
})

describe('PartialNode — getNamedRelation', () => {
  it('finds a relation by BrowseName.Name', () => {
    const rel = makeRelation(47, true, 'SpecialChild')
    const node = NodeFactory(makeData({ relations: [rel] }))
    const found = node.getNamedRelation('SpecialChild')
    expect(found).toBeDefined()
    expect(found.BrowseName.Name).toBe('SpecialChild')
  })

  it('returns undefined when browseName not found', () => {
    const node = NodeFactory(makeData({ relations: [] }))
    expect(node.getNamedRelation('Ghost')).toBeUndefined()
  })
})

describe('PartialNode — getRelations', () => {
  it('returns all relations matching the given referenceTypeName', () => {
    const comp1 = makeRelation(47, true, 'A') // component
    const comp2 = makeRelation(47, true, 'B') // component
    const prop  = makeRelation(46, true, 'C') // hasProperty
    const node = NodeFactory(makeData({ relations: [comp1, comp2, prop] }))
    const components = node.getRelations('component')
    expect(components).toHaveLength(2)
  })

  it('returns empty array when no match', () => {
    const node = NodeFactory(makeData({ relations: [] }))
    expect(node.getRelations('organizes')).toHaveLength(0)
  })
})

describe('PartialNode — getChildRelations', () => {
  it('returns only forward relations', () => {
    const forward  = makeRelation(47, true, 'Forward')
    const backward = makeRelation(47, false, 'Backward')
    const node = NodeFactory(makeData({ relations: [forward, backward] }))
    const children = node.getChildRelations()
    expect(children).toHaveLength(1)
    expect(children[0].BrowseName.Name).toBe('Forward')
  })

  it('filters by type when type is given', () => {
    const comp  = makeRelation(47, true, 'C')  // component
    const prop  = makeRelation(46, true, 'P')  // hasProperty
    const node  = NodeFactory(makeData({ relations: [comp, prop] }))
    expect(node.getChildRelations('component')).toHaveLength(1)
    expect(node.getChildRelations('hasProperty')).toHaveLength(1)
  })

  it('handles IsForward as string "True"', () => {
    const rel = makeRelation(47, 'True', 'StringTrue')
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.getChildRelations()).toHaveLength(1)
  })
})

describe('PartialNode — getParentRelations', () => {
  it('returns only backward (non-forward) relations', () => {
    const forward  = makeRelation(47, true,  'F')
    const backward = makeRelation(47, false, 'B')
    const node = NodeFactory(makeData({ relations: [forward, backward] }))
    const parents = node.getParentRelations()
    expect(parents).toHaveLength(1)
    expect(parents[0].BrowseName.Name).toBe('B')
  })
})

describe('PartialNode — getTypeDefinitionRelations', () => {
  it('returns relations whose TypeDefinition.Identifier matches', () => {
    const rel1 = makeRelation(40, true, 'TD1', '2001')
    const rel2 = makeRelation(40, true, 'TD2', '2002')
    const node = NodeFactory(makeData({ relations: [rel1, rel2] }))
    const found = node.getTypeDefinitionRelations('2001')
    expect(found).toHaveLength(1)
  })

  it('returns empty array when no match', () => {
    const node = NodeFactory(makeData({ relations: [] }))
    expect(node.getTypeDefinitionRelations('9999')).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// ObjectNode — browseName aname
// ---------------------------------------------------------------------------

describe('ObjectNode — aname debugging hint', () => {
  it('sets aname when browseName is provided on data', () => {
    const data = makeData({ browseName: 'RootFolder' })
    data.browseName = 'RootFolder'
    const node = NodeFactory(data)
    expect(node.aname).toContain('Object')
  })
})

// ---------------------------------------------------------------------------
// VariableNode — aname debugging hint
// ---------------------------------------------------------------------------

describe('VariableNode — aname debugging hint', () => {
  it('sets aname when displayname.value.text is provided', () => {
    const data = makeData({
      attributes: { NodeClass: 2, NodeId: { NamespaceIndex: 0, Identifier: 10 }, DisplayName: { Text: 'V' }, BrowseName: { Name: 'V' } }
    })
    data.displayname = { value: { text: 'MyVar' } }
    const node = NodeFactory(data)
    expect(node.aname).toContain('Variable')
  })

  it('does not set aname when displayname is missing', () => {
    const data = makeData({
      attributes: { NodeClass: 2, NodeId: { NamespaceIndex: 0, Identifier: 10 }, DisplayName: { Text: 'V' }, BrowseName: { Name: 'V' } }
    })
    const node = NodeFactory(data)
    expect(node.aname).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// MethodNode — aname debugging hint
// ---------------------------------------------------------------------------

describe('MethodNode — aname debugging hint', () => {
  it('sets aname when displayname.value.text is provided', () => {
    const data = makeData({
      attributes: { NodeClass: 4, NodeId: { NamespaceIndex: 0, Identifier: 20 }, DisplayName: { Text: 'M' }, BrowseName: { Name: 'M' } }
    })
    data.displayname = { value: { text: 'DoStuff' } }
    const node = NodeFactory(data)
    expect(node.aname).toContain('Method')
  })
})

// ---------------------------------------------------------------------------
// Type mapping — unknown reference type identifier
// ---------------------------------------------------------------------------

describe('PartialNode — relation normalisation', () => {
  it('maps identifier 47 to "component"', () => {
    const rel = makeRelation(47, true, 'Child')
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.data.relations[0].referenceTypeName).toBe('component')
  })

  it('maps identifier 46 to "hasProperty"', () => {
    const rel = makeRelation(46, true, 'P')
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.data.relations[0].referenceTypeName).toBe('hasProperty')
  })

  it('uses "relation" for unknown reference type identifiers', () => {
    const rel = makeRelation(99999, true, 'Unknown')
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.data.relations[0].referenceTypeName).toBe('relation')
  })

  it('uses "relation" when ReferenceTypeId is missing', () => {
    const rel = { IsForward: true, BrowseName: { Name: 'X' }, NodeId: 'ns=0;i=1' }
    const node = NodeFactory(makeData({ relations: [rel] }))
    expect(node.data.relations[0].referenceTypeName).toBe('relation')
  })
})
