import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NodeFactory } from '../../../javascripts/ijt-support/address-space/node.mjs'

function makeNodeData (nodeclass, nodeid = 'ns=1;i=100', relations = []) {
  return {
    nodeid,
    nodeclass: { value: nodeclass },
    displayname: { value: { text: 'TestNode' } },
    relations
  }
}

describe('NodeFactory', () => {
  it('creates ObjectNode for nodeclass 1', () => {
    const node = NodeFactory(makeNodeData(1))
    expect(node.nodeId).toBe('ns=1;i=100')
    expect(node.displayName).toBe('TestNode')
  })

  it('creates VariableNode for nodeclass 2', () => {
    const node = NodeFactory(makeNodeData(2))
    expect(node.nodeId).toBe('ns=1;i=100')
  })

  it('creates MethodNode for nodeclass 4', () => {
    const node = NodeFactory(makeNodeData(4))
    expect(node.nodeId).toBe('ns=1;i=100')
  })

  it('falls back to ObjectNode for unknown nodeclass', () => {
    const node = NodeFactory(makeNodeData(99))
    expect(node).toBeDefined()
    expect(node.nodeId).toBe('ns=1;i=100')
  })

  it('node.browseName returns display text', () => {
    const node = NodeFactory(makeNodeData(1))
    expect(node.browseName).toBe('TestNode')
  })

  it('getChildRelations() returns only forward relations', () => {
    const relations = [
      { referenceTypeId: 'ns=0;i=47', isForward: true, browseName: { name: 'Child1' }, nodeId: 'ns=1;i=200', typeDefinition: 'ns=0;i=58', referenceTypeName: 'component' },
      { referenceTypeId: 'ns=0;i=47', isForward: false, browseName: { name: 'Parent' }, nodeId: 'ns=1;i=50', typeDefinition: 'ns=0;i=58', referenceTypeName: 'component' }
    ]
    const node = NodeFactory(makeNodeData(1, 'ns=1;i=100', relations))
    const children = node.getChildRelations('component')
    expect(children.length).toBe(1)
    expect(children[0].browseName.name).toBe('Child1')
  })

  it('getParentRelations() returns only backward relations', () => {
    const relations = [
      { referenceTypeId: 'ns=0;i=47', isForward: false, browseName: { name: 'Parent' }, nodeId: 'ns=1;i=50', typeDefinition: 'ns=0;i=58', referenceTypeName: 'component' }
    ]
    const node = NodeFactory(makeNodeData(1, 'ns=1;i=100', relations))
    expect(node.getParentRelations().length).toBe(1)
  })

  it('throws on unmapped referenceTypeId', () => {
    const relations = [
      { referenceTypeId: 'ns=0;i=99999', isForward: true, browseName: { name: 'X' }, nodeId: 'ns=1;i=200', typeDefinition: 'ns=0;i=58' }
    ]
    expect(() => NodeFactory(makeNodeData(1, 'ns=1;i=100', relations))).toThrow()
  })
})

describe('AddressSpace', () => {
  it('imports cleanly', async () => {
    const { AddressSpace } = await import('../../../javascripts/ijt-support/address-space/address-space.mjs')
    expect(AddressSpace).toBeDefined()
    expect(typeof AddressSpace).toBe('function')
  })
})
