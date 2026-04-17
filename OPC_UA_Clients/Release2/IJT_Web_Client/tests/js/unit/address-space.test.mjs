/**
 * Unit tests for AddressSpace.
 *
 * AddressSpace takes a connectionManager via constructor injection, so we build
 * lightweight mock objects for connectionManager and socketHandler rather than
 * mocking any module imports.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AddressSpace } from '../../../src/javascripts/ijt-support/address-space/address-space.mjs'

// ---------------------------------------------------------------------------
// Factories for mock dependencies
// ---------------------------------------------------------------------------

function makeMockSocketHandler () {
  return {
    readPromise: vi.fn(),
    namespacePromise: vi.fn(),
    methodCall: vi.fn(),
    subscribeEvent: vi.fn(),
    registerMandatory: vi.fn(),
    pathtoidPromise: vi.fn(),
    connect: vi.fn(),
    close: vi.fn()
  }
}

/**
 * Returns a mock connectionManager whose subscribe() captures callbacks so
 * tests can fire them via _fire(state, value).
 */
function makeMockConnectionManager (socketHandler) {
  const registered = []
  return {
    socketHandler,
    subscribe: vi.fn((state, cb) => registered.push({ state, cb })),
    trigger: vi.fn(),
    _fire (state, value) {
      for (const { state: s, cb } of registered) {
        if (s === state) cb(value)
      }
    }
  }
}

/** Minimal node data that satisfies NodeFactory and PartialNode constructor. */
function makeNodeMessage (nsIndex, identifier) {
  return {
    nodeid: `ns=${nsIndex};i=${identifier}`,
    attributes: {
      NodeId: { NamespaceIndex: nsIndex, Identifier: identifier },
      NodeClass: 1,
      DisplayName: { Text: `Node_${identifier}` },
      BrowseName: { Name: `Node_${identifier}` }
    },
    relations: [],
    value: null
  }
}

// ---------------------------------------------------------------------------
// Shared setup
// ---------------------------------------------------------------------------

let socketHandler
let connectionManager
let addressSpace

beforeEach(() => {
  socketHandler = makeMockSocketHandler()
  connectionManager = makeMockConnectionManager(socketHandler)
  addressSpace = new AddressSpace(connectionManager)
})

// ---------------------------------------------------------------------------
// constructor
// ---------------------------------------------------------------------------

describe('AddressSpace — constructor', () => {
  it('initialises nodeMapping as an empty object', () => {
    expect(addressSpace.nodeMapping).toEqual({})
  })

  it('initialises status as an empty array', () => {
    expect(addressSpace.status).toEqual([])
  })

  it('sets objectFolder to null', () => {
    expect(addressSpace.objectFolder).toBeNull()
  })

  it('subscribes to the "connection" state on connectionManager', () => {
    expect(connectionManager.subscribe).toHaveBeenCalledWith(
      'connection',
      expect.any(Function)
    )
  })
})

// ---------------------------------------------------------------------------
// parseMaybeJson
// ---------------------------------------------------------------------------

describe('AddressSpace — parseMaybeJson', () => {
  it('parses a plain JSON string', () => {
    expect(addressSpace.parseMaybeJson('{"a":1}')).toEqual({ a: 1 })
  })

  it('strips newlines/tabs before parsing', () => {
    expect(addressSpace.parseMaybeJson('{\n"a":\t1}')).toEqual({ a: 1 })
  })

  it('returns non-string values unchanged', () => {
    const obj = { a: 1 }
    expect(addressSpace.parseMaybeJson(obj)).toBe(obj)
  })

  it('returns null unchanged', () => {
    expect(addressSpace.parseMaybeJson(null)).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// addressSpacePromise / addressSpaceSetup
// ---------------------------------------------------------------------------

describe('AddressSpace — addressSpacePromise', () => {
  it('queues the promise when the address space is not yet ready', () => {
    const promise = addressSpace.addressSpacePromise()
    expect(promise).toBeInstanceOf(Promise)
    expect(addressSpace.listOfTSPromises).toHaveLength(1)
  })

  it('resolves immediately when tighteningsystem status is already set', async () => {
    const fakeSystem = { nodeId: 'ns=1;i=999' }
    addressSpace.tighteningSystem = fakeSystem
    addressSpace.status.push('tighteningsystem')
    const result = await addressSpace.addressSpacePromise()
    expect(result).toBe(fakeSystem)
  })
})

describe('AddressSpace — addressSpaceSetup', () => {
  it('resolves all queued promises when tighteningsystem is added', async () => {
    const promise = addressSpace.addressSpacePromise()
    const fakeSystem = { nodeId: 'ns=1;i=1000' }
    addressSpace.tighteningSystem = fakeSystem
    addressSpace.addressSpaceSetup('tighteningsystem')
    const result = await promise
    expect(result).toBe(fakeSystem)
  })

  it('clears listOfTSPromises after resolving them', () => {
    addressSpace.addressSpacePromise()
    expect(addressSpace.listOfTSPromises).toHaveLength(1)
    addressSpace.tighteningSystem = {}
    addressSpace.addressSpaceSetup('tighteningsystem')
    expect(addressSpace.listOfTSPromises).toHaveLength(0)
  })

  it('does not resolve promises for non-tighteningsystem statuses', async () => {
    let resolved = false
    addressSpace.addressSpacePromise().then(() => { resolved = true })
    addressSpace.addressSpaceSetup('namespaces')
    // Give microtasks a tick to settle
    await Promise.resolve()
    expect(resolved).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// findOrLoadNode — caching
// ---------------------------------------------------------------------------

describe('AddressSpace — findOrLoadNode', () => {
  it('calls socketHandler.readPromise on the first load of a node', async () => {
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(0, 84) })
    await addressSpace.findOrLoadNode('ns=0;i=84')
    expect(socketHandler.readPromise).toHaveBeenCalledOnce()
  })

  it('returns a cached node on subsequent calls without re-fetching', async () => {
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(0, 84) })
    const first = await addressSpace.findOrLoadNode('ns=0;i=84')
    const second = await addressSpace.findOrLoadNode('ns=0;i=84')
    expect(socketHandler.readPromise).toHaveBeenCalledOnce()
    expect(first).toBe(second)
  })

  it('resolves immediately for a pre-cached node (no async fetch)', async () => {
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(0, 84) })
    // Populate cache
    const first = await addressSpace.findOrLoadNode('ns=0;i=84')
    // Pre-cached path returns synchronously (no new readPromise call)
    socketHandler.readPromise.mockClear()
    const second = await addressSpace.findOrLoadNode('ns=0;i=84')
    expect(socketHandler.readPromise).not.toHaveBeenCalled()
    expect(second).toBe(first)
  })

  it('notifies newNodeSubscription callbacks when a new node is created', async () => {
    const onNew = vi.fn()
    addressSpace.subscribeToNewNode(onNew)
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(0, 84) })
    await addressSpace.findOrLoadNode('ns=0;i=84')
    expect(onNew).toHaveBeenCalledOnce()
  })
})

// ---------------------------------------------------------------------------
// methodCall
// ---------------------------------------------------------------------------

describe('AddressSpace — methodCall', () => {
  it('delegates to socketHandler.methodCall with the correct arguments', async () => {
    socketHandler.methodCall.mockResolvedValue({
      message: { output: JSON.stringify({ status: 'ok' }) }
    })
    await addressSpace.methodCall('loc-1', 'method-1', [42])
    expect(socketHandler.methodCall).toHaveBeenCalledWith('loc-1', 'method-1', [42])
  })

  it('resolves with the parsed output', async () => {
    const output = { key: 'value', count: 7 }
    socketHandler.methodCall.mockResolvedValue({
      message: { output: JSON.stringify(output) }
    })
    const result = await addressSpace.methodCall('loc', 'method', [])
    expect(result).toEqual(output)
  })

  it('rejects when socketHandler.methodCall rejects', async () => {
    socketHandler.methodCall.mockRejectedValue(new Error('method failed'))
    await expect(addressSpace.methodCall('loc', 'method', [])).rejects.toThrow('method failed')
  })
})

// ---------------------------------------------------------------------------
// relationsToNodes
// ---------------------------------------------------------------------------

describe('AddressSpace — relationsToNodes', () => {
  it('resolves all relations to nodes via findOrLoadNode', async () => {
    socketHandler.readPromise
      .mockResolvedValueOnce({ message: makeNodeMessage(1, 100) })
      .mockResolvedValueOnce({ message: makeNodeMessage(1, 200) })

    const relations = [{ NodeId: 'ns=1;i=100' }, { NodeId: 'ns=1;i=200' }]
    const nodes = await addressSpace.relationsToNodes(relations)
    expect(nodes).toHaveLength(2)
  })

  it('returns an empty array for an empty relations list', async () => {
    const nodes = await addressSpace.relationsToNodes([])
    expect(nodes).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// handleNamespaces
// ---------------------------------------------------------------------------

describe('AddressSpace — handleNamespaces', () => {
  const NAMESPACES = [
    'http://opcfoundation.org/UA/',
    'http://opcfoundation.org/UA/IJT/Base/',
    'http://opcfoundation.org/UA/IJT/Tightening/',
    'urn:AtlasCopco:IJT:Tightening:Server/',
    'http://opcfoundation.org/UA/Machinery/',
    'http://opcfoundation.org/UA/Machinery/Result/',
    'http://opcfoundation.org/UA/DI/'
  ]

  it('parses namespace indices from the message', () => {
    addressSpace.handleNamespaces({ namespaces: JSON.stringify(NAMESPACES) })
    expect(addressSpace.OPCUA).toBe(0)
    expect(addressSpace.nsIJT).toBe(1)
    expect(addressSpace.nsTightening).toBe(2)
    expect(addressSpace.nsTighteningServer).toBe(3)
    expect(addressSpace.nsMachinery).toBe(4)
    expect(addressSpace.nsMachineryResult).toBe(5)
    expect(addressSpace.nsDI).toBe(6)
  })

  it('returns -1 for a namespace URI not in the list', () => {
    addressSpace.handleNamespaces({ namespaces: JSON.stringify(['http://example.com/']) })
    expect(addressSpace.nsIJT).toBe(-1)
  })
})

// ---------------------------------------------------------------------------
// reset
// ---------------------------------------------------------------------------

describe('AddressSpace — reset', () => {
  it('clears all cached node mappings', async () => {
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(0, 1) })
    await addressSpace.findOrLoadNode('ns=0;i=1')
    expect(Object.keys(addressSpace.nodeMapping)).toHaveLength(1)
    addressSpace.reset()
    expect(addressSpace.nodeMapping).toEqual({})
  })
})

// ---------------------------------------------------------------------------
// subscribeToNewNode
// ---------------------------------------------------------------------------

describe('AddressSpace — subscribeToNewNode', () => {
  it('registers callback in newNodeSubscription', () => {
    const cb = vi.fn()
    addressSpace.subscribeToNewNode(cb)
    expect(addressSpace.newNodeSubscription).toContain(cb)
  })

  it('supports multiple callbacks', () => {
    const cb1 = vi.fn()
    const cb2 = vi.fn()
    addressSpace.subscribeToNewNode(cb1)
    addressSpace.subscribeToNewNode(cb2)
    expect(addressSpace.newNodeSubscription).toHaveLength(2)
  })
})

// ---------------------------------------------------------------------------
// getIS / getNodeMapping / setNodeMapping (internal helpers)
// ---------------------------------------------------------------------------

describe('AddressSpace — node mapping helpers', () => {
  it('getIS returns ;i= for numeric identifiers', () => {
    expect(addressSpace.getIS('42')).toBe(';i=')
  })

  it('getIS returns ;s= for string identifiers', () => {
    expect(addressSpace.getIS('MyNode')).toBe(';s=')
  })

  it('setNodeMapping / getNodeMapping round-trip with string nodeId', () => {
    const node = { nodeId: 'ns=2;s=TestNode' }
    addressSpace.setNodeMapping('ns=2;s=TestNode', node)
    expect(addressSpace.getNodeMapping('ns=2;s=TestNode')).toBe(node)
  })

  it('setNodeMapping / getNodeMapping round-trip with object nodeId', () => {
    const node = {}
    const nodeIdObj = { NamespaceIndex: 3, Identifier: 'MyString' }
    addressSpace.setNodeMapping(nodeIdObj, node)
    expect(addressSpace.getNodeMapping(nodeIdObj)).toBe(node)
  })
})

// ---------------------------------------------------------------------------
// findNodeFromPathPromise
// ---------------------------------------------------------------------------

describe('AddressSpace — findNodeFromPathPromise', () => {
  it('resolves to a node when path lookup succeeds', async () => {
    // Pre-load tighteningSystem
    const fakeSystem = { nodeId: { NamespaceIndex: 1, Identifier: 999 } }
    addressSpace.tighteningSystem = fakeSystem
    addressSpace.status.push('tighteningsystem')

    // Use object for nodeid so parseMaybeJson passes it through without JSON.parse
    socketHandler.pathtoidPromise.mockResolvedValue({
      message: { nodeid: { NamespaceIndex: 1, Identifier: 100 } }
    })
    socketHandler.readPromise.mockResolvedValue({ message: makeNodeMessage(1, 100) })

    const node = await addressSpace.findNodeFromPathPromise('"SomePath"')
    expect(node).toBeDefined()
    expect(socketHandler.pathtoidPromise).toHaveBeenCalledOnce()
  })

  it('rejects when pathtoidPromise rejects', async () => {
    const fakeSystem = { nodeId: { NamespaceIndex: 1, Identifier: 999 } }
    addressSpace.tighteningSystem = fakeSystem
    addressSpace.status.push('tighteningsystem')

    socketHandler.pathtoidPromise.mockRejectedValue(new Error('path not found'))

    await expect(addressSpace.findNodeFromPathPromise('"BadPath"')).rejects.toThrow('path not found')
  })
})

// ---------------------------------------------------------------------------
// read
// ---------------------------------------------------------------------------

describe('AddressSpace — read', () => {
  it('resolves with response.node from socketHandler.readPromise', async () => {
    const fakeNode = { nodeId: 'ns=1;i=42' }
    socketHandler.readPromise.mockResolvedValue({ node: fakeNode })

    const result = await addressSpace.read('ns=1;i=42', 'Value')
    expect(result).toBe(fakeNode)
    expect(socketHandler.readPromise).toHaveBeenCalledWith('ns=1;i=42', 'Value')
  })
})

// ---------------------------------------------------------------------------
// initiate (via connection callback)
// ---------------------------------------------------------------------------

describe('AddressSpace — initiate', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  function makeNodeMessageWithRelations (nsIndex, identifier, relations = []) {
    return {
      ...makeNodeMessage(nsIndex, identifier),
      relations
    }
  }

  it('finds tighteningSystem when connection fires with true', async () => {
    const tsRelation = {
      TypeDefinition: { Identifier: 1005 },
      ReferenceTypeId: { Identifier: 61 },
      NodeId: 'ns=1;i=1005',
      IsForward: true,
      BrowseName: { Name: 'TighteningSystem', NamespaceIndex: 1 }
    }

    socketHandler.readPromise
      .mockResolvedValueOnce({ message: makeNodeMessage(0, 84) })              // root
      .mockResolvedValueOnce({ message: makeNodeMessageWithRelations(0, 85, [tsRelation]) }) // objects folder
      .mockResolvedValueOnce({ message: makeNodeMessage(1, 1005) })            // tightening system

    socketHandler.namespacePromise.mockResolvedValue({
      message: { namespaces: JSON.stringify(['http://opcfoundation.org/UA/']) }
    })

    connectionManager._fire('connection', true)

    await vi.runAllTimersAsync()

    expect(addressSpace.tighteningSystem).toBeDefined()
  })

  it('handles error in initiate gracefully (no throw)', async () => {
    socketHandler.readPromise.mockRejectedValue(new Error('network error'))
    socketHandler.namespacePromise.mockResolvedValue({
      message: { namespaces: JSON.stringify([]) }
    })

    connectionManager._fire('connection', true)

    await vi.runAllTimersAsync()
    // No assertion needed — the key is that no unhandled rejection occurs
  })

  it('handles missing tightening system (no typerelations) gracefully', async () => {
    socketHandler.readPromise
      .mockResolvedValueOnce({ message: makeNodeMessage(0, 84) })
      .mockResolvedValueOnce({ message: makeNodeMessage(0, 85) })  // no relations

    socketHandler.namespacePromise.mockResolvedValue({
      message: { namespaces: JSON.stringify([]) }
    })

    connectionManager._fire('connection', true)
    await vi.runAllTimersAsync()
    // Should log error, not throw
  })

  it('fires with false skips initiate but still handles namespaces', async () => {
    socketHandler.namespacePromise.mockResolvedValue({
      message: { namespaces: JSON.stringify(['http://opcfoundation.org/UA/']) }
    })

    connectionManager._fire('connection', false)
    await vi.runAllTimersAsync()

    // initiate was not called (socketHandler.readPromise not invoked)
    expect(socketHandler.readPromise).not.toHaveBeenCalled()
    expect(addressSpace.OPCUA).toBe(0)
  })
})
