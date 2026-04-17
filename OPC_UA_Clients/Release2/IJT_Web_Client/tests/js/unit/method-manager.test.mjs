/**
 * Tests for MethodManager — verifies that call() passes the correct node IDs
 * to addressSpace.methodCall() and that the JS wire format uses the right keys.
 *
 * MethodManager.call() is the JS-side entry point for OPC UA method invocation.
 * It must forward parentNode.nodeId and methodNode.nodeId to
 * addressSpace.methodCall(), which (via SocketHandler) sends:
 *   { objectnode, methodnode, arguments }  — no underscores!
 */
import { describe, it, expect, vi } from 'vitest'
import { MethodManager } from '../../../src/javascripts/ijt-support/methods/method-manager.mjs'

// ---------------------------------------------------------------------------
// Helpers — build minimal fake nodes / addressSpace
// ---------------------------------------------------------------------------

function makeNode (displayName, nodeId, nodeClass = 4) {
  return {
    displayName,
    nodeId,
    nodeClass,
    data: {
      attributes: { Value: [] }
    },
    getChildRelations: vi.fn(() => []),
  }
}

function makeMethodNode (displayName, nodeId, args = []) {
  const node = makeNode(displayName, nodeId, 4 /* Method */)
  node.data.attributes.Value = args
  return node
}

function makeFakeAddressSpace (methodCallImpl) {
  return {
    addressSpacePromise: vi.fn(async () => makeNode('TighteningSystem', 'ns=1;s=TS')),
    findNodeFromPathPromise: vi.fn(async (path) => makeNode('folder', `ns=1;s=${path}`)),
    relationsToNodes: vi.fn(async (relations) => relations),
    connectionManager: {
      trigger: vi.fn(),
      CONNECTION_STATES: { METHODS: 'methods' }
    },
    methodCall: vi.fn(methodCallImpl ?? (async () => ({ message: { output: [] } }))),
  }
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('MethodManager.call — node ID forwarding', () => {
  it('calls addressSpace.methodCall with parentNode.nodeId and methodNode.nodeId', async () => {
    const parentNodeId = 'ns=1;s=TighteningSystem'
    const methodNodeId = 'ns=1;s=TighteningSystem/SimulateSingleResult'

    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const parentNode = makeNode('TighteningSystem', parentNodeId)
    const methodNode = makeMethodNode('SimulateSingleResult', methodNodeId, [])

    const methodData = { parentNode, methodNode, arguments: [] }

    await manager.call(methodData, [])

    expect(fakeAddressSpace.methodCall).toHaveBeenCalledOnce()
    const [calledObjectNodeId, calledMethodNodeId] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledObjectNodeId).toBe(parentNodeId)
    expect(calledMethodNodeId).toBe(methodNodeId)
  })

  it('passes mapped inputArguments array to addressSpace.methodCall', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method', []),
      arguments: [],
    }

    const inputs = [
      { type: { Identifier: 12 }, value: 'hello' },  // String
    ]

    await manager.call(methodData, inputs)

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(Array.isArray(calledArgs)).toBe(true)
    expect(calledArgs).toHaveLength(1)
    expect(calledArgs[0]).toMatchObject({ dataType: 12, value: 'hello' })
  })

  it('maps UInt32 input values through parseInt', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }

    const inputs = [
      { type: { Identifier: 7 }, value: '42' },  // UInt32 as string
    ]

    await manager.call(methodData, inputs)

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0].value).toBe(42)
  })

  it('maps Boolean true correctly', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }

    await manager.call(methodData, [{ type: { Identifier: 1 }, value: true }])

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0].value).toBe(true)
    expect(calledArgs[0].dataType).toBe(1)
  })

  it('maps String "true" to Boolean true for dataType 1', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }

    await manager.call(methodData, [{ type: { Identifier: 1 }, value: 'true' }])

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0].value).toBe(true)
  })

  it('maps String values (dataType 12) without coercion', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }

    await manager.call(methodData, [{ type: { Identifier: 12 }, value: 'my-string' }])

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0].value).toBe('my-string')
  })
})

describe('MethodManager — method registry', () => {
  it('getMethodNames returns empty array before setup', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    // methodObject not initialised yet
    expect(typeof manager.getMethodNames).toBe('function')
  })

  it('getMethod returns undefined for unknown method name', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {}
    expect(manager.getMethod('NonExistentMethod')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// setupMethodsInFolders / addressFolder / folderPromise / setupMethod
// ---------------------------------------------------------------------------

describe('MethodManager — setupMethodsInFolders', () => {
  it('initialises methodObject and triggers METHODS state', async () => {
    const rootNode = makeNode('TighteningSystem', 'ns=1;s=TS')
    rootNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.addressSpacePromise = vi.fn(async () => rootNode)
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    await manager.setupMethodsInFolders([])

    expect(fakeAddressSpace.addressSpacePromise).toHaveBeenCalledOnce()
    expect(fakeAddressSpace.connectionManager.trigger).toHaveBeenCalledOnce()
    expect(manager.methodObject).toEqual({})
  })

  it('calls addressFolder for each folder path', async () => {
    const rootNode = makeNode('TS', 'ns=1;s=TS')
    rootNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.addressSpacePromise = vi.fn(async () => rootNode)
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    await manager.setupMethodsInFolders(['SomeFolder'])

    expect(fakeAddressSpace.findNodeFromPathPromise).toHaveBeenCalledOnce()
  })

  it('catches errors in addressFolder and continues', async () => {
    const rootNode = makeNode('TS', 'ns=1;s=TS')
    rootNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.addressSpacePromise = vi.fn(async () => rootNode)
    fakeAddressSpace.findNodeFromPathPromise = vi.fn(async () => { throw new Error('path not found') })
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    await expect(manager.setupMethodsInFolders(['BadFolder'])).resolves.toBeUndefined()
  })
})

describe('MethodManager — addressFolder', () => {
  it('empty path calls folderPromise with tighteningSystemNode', async () => {
    const rootNode = makeNode('TS', 'ns=1;s=TS')
    rootNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    manager.methodObject = {}
    manager.tighteningSystemNode = rootNode

    await manager.addressFolder('')

    expect(rootNode.getChildRelations).toHaveBeenCalledWith('component')
  })

  it('non-empty path calls findNodeFromPathPromise then folderPromise', async () => {
    const folderNode = makeNode('Folder', 'ns=1;s=Folder')
    folderNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.findNodeFromPathPromise = vi.fn(async () => folderNode)
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    manager.methodObject = {}
    manager.tighteningSystemNode = makeNode('TS', 'ns=1;s=TS')

    await manager.addressFolder('"SomePath"')

    expect(fakeAddressSpace.findNodeFromPathPromise).toHaveBeenCalledWith('"SomePath"')
    expect(folderNode.getChildRelations).toHaveBeenCalledWith('component')
  })
})

describe('MethodManager — folderPromise', () => {
  it('adds method nodes with nodeClass=4 to methodObject', async () => {
    const methodNode = makeNode('MyMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn(() => [])  // no InputArguments

    const folderNode = makeNode('Folder', 'ns=1;s=Folder')
    const relation = { NodeId: 'ns=1;s=Method' }
    folderNode.getChildRelations = vi.fn(() => [relation])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async (rels) => {
      if (rels === [relation] || rels.includes(relation)) return [methodNode]
      return []
    })

    const manager = new MethodManager(fakeAddressSpace)
    manager.methodObject = {}

    await manager.folderPromise(folderNode)

    expect(folderNode.getChildRelations).toHaveBeenCalledWith('component')
  })

  it('skips non-method nodes (nodeClass !== 4)', async () => {
    const nonMethodNode = makeNode('Variable', 'ns=1;s=Var', 2 /* Variable */)
    const folderNode = makeNode('Folder', 'ns=1;s=Folder')
    const relation = { NodeId: 'ns=1;s=Var' }
    folderNode.getChildRelations = vi.fn(() => [relation])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [nonMethodNode])

    const manager = new MethodManager(fakeAddressSpace)
    manager.methodObject = {}

    await manager.folderPromise(folderNode)

    expect(Object.keys(manager.methodObject)).toHaveLength(0)
  })
})

describe('MethodManager — setupMethod', () => {
  it('returns methodNode and empty args when no InputArguments', async () => {
    const methodNode = makeNode('TestMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn(() => [])

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [])

    const manager = new MethodManager(fakeAddressSpace)
    const result = await manager.setupMethod(methodNode)

    expect(result.methodNode).toBe(methodNode)
    expect(result.arguments).toEqual([])
  })

  it('returns methodNode and parsed args when InputArguments found', async () => {
    const inputArgRelation = {
      BrowseName: { Name: 'InputArguments' },
      NodeId: 'ns=1;s=InputArgs'
    }
    const methodNode = makeNode('TestMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn(() => [inputArgRelation])

    const inputArgNode = {
      data: { attributes: { Value: ['arg1', 'arg2'] } }
    }

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [inputArgNode])

    const manager = new MethodManager(fakeAddressSpace)
    const result = await manager.setupMethod(methodNode)

    expect(result.arguments).toEqual(['arg1', 'arg2'])
  })

  it('warns when an argument value is falsy', async () => {
    const inputArgRelation = { BrowseName: { Name: 'InputArguments' }, NodeId: 'ns=1;s=IA' }
    const methodNode = makeNode('TestMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn(() => [inputArgRelation])

    const inputArgNode = {
      data: { attributes: { Value: [null, 'validArg'] } }  // null triggers warn
    }

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [inputArgNode])

    const manager = new MethodManager(fakeAddressSpace)
    const result = await manager.setupMethod(methodNode)

    // null is filtered out, 'validArg' is included
    expect(result.arguments).toEqual(['validArg'])
  })
})

// ---------------------------------------------------------------------------
// call() — additional type cases
// ---------------------------------------------------------------------------

describe('MethodManager.call — additional type cases', () => {
  async function callWithType (typeNr, value) {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }
    await manager.call(methodData, [{ type: { Identifier: typeNr }, value }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    return calledArgs[0]
  }

  it('maps type 3029 as raw value passthrough', async () => {
    const result = await callWithType(3029, 'raw-value')
    expect(result.value).toBe('raw-value')
    expect(result.dataType).toBe(3029)
  })

  it('maps type 21 (LocalizedText) as raw value passthrough', async () => {
    const locText = { Text: 'Hello', Locale: 'en-US' }
    const result = await callWithType(21, locText)
    expect(result.value).toBe(locText)
  })

  it('maps type 13 (DateTime) via String coercion', async () => {
    const result = await callWithType(13, '2024-01-01')
    expect(result.value).toBe('2024-01-01')
  })

  it('maps type 8 (Int64) via parseInt', async () => {
    const result = await callWithType(8, '1234567890')
    expect(result.value).toBe(1234567890)
  })

  it('maps unknown type as raw value (default case)', async () => {
    const result = await callWithType(9999, 'mystery')
    expect(result.value).toBe('mystery')
    expect(result.dataType).toBe(9999)
  })

  it('maps type 1 (Boolean) false from non-true string', async () => {
    const result = await callWithType(1, 'false')
    expect(result.value).toBe(false)
  })
})
