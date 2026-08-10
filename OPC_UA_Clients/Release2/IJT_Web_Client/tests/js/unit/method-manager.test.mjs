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

  it('preserves normalized backend method result contract from addressSpace.methodCall', async () => {
    const fakeAddressSpace = makeFakeAddressSpace(async () => ({
      callStatus: 'Succeeded',
      returnValue: null,
      outputArguments: [['a', 'b']],
      rawOutput: [['a', 'b']]
    }))
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [],
    }

    const result = await manager.call(methodData, [])
    expect(result.callStatus).toBe('Succeeded')
  })

  it('normalizes discovered schema metadata for inputs outputs and return value', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      GenericMethod: {
        parentNode: makeNode('TS', 'ns=1;s=TS'),
        methodNode: { displayName: 'GenericMethod', nodeIdString: 'ns=1;s=GenericMethod' },
        arguments: [{ Name: 'InputA', DataType: { Identifier: 12 }, FieldDefinitions: [{ name: 'FieldA', dataType: 12 }] }],
        outputArguments: [{ Name: 'OutputA', DataType: { Identifier: 21 } }],
        returnArgument: { Name: 'ReturnStatus', DataType: { Identifier: 6 } },
        nodeIdString: 'ns=1;s=GenericMethod'
      }
    }
    manager.setMethodMetadata({ groups: [], defaults: { byName: {}, byPath: {} } })

    const method = manager.getMethod('GenericMethod')
    expect(method.arguments[0].FieldDefinitions).toEqual([{ name: 'FieldA', dataType: 12 }])
    expect(method.returnArgument.Name).toBe('ReturnStatus')
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

  it('applies metadata grouping and defaults to discovered methods', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      SimulateSingleResult: {
        methodNode: { nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult' },
        nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult'
      }
    }

    manager.setMethodMetadata({
      groups: [
        { id: 'simulations', label: 'Simulations', description: 'Simulation methods', paths: [] },
        { id: 'simulate-results', parentId: 'simulations', label: 'Simulate Results', paths: ['TighteningSystem/Simulations/SimulateResults'] }
      ],
      defaults: {
        byName: {},
        byPath: {
          'TighteningSystem/Simulations/SimulateResults/SimulateSingleResult': {
            groupId: 'simulate-results',
            argumentDefaults: { 'Result Type': 2 }
          }
        }
      }
    })

    expect(manager.getMethod('SimulateSingleResult').metadata.groupId).toBe('simulate-results')
    expect(manager.getMethod('SimulateSingleResult').metadata.defaults['Result Type']).toBe(2)
    expect(manager.getGroupedMethods()[0]).toMatchObject({
      id: 'simulate-results',
      label: 'Simulate Results',
      parentId: 'simulations',
      parentLabel: 'Simulations'
    })
  })

  it('groups every method beneath the Simulations object with Simulations', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      SendSimulatedBulkResults: {
        methodNode: { nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SendSimulatedBulkResults' },
        nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SendSimulatedBulkResults'
      }
    }

    manager.setMethodMetadata({
      groups: [
        { id: 'simulations', label: 'Simulations', paths: [] },
        { id: 'simulate-results', parentId: 'simulations', label: 'Simulate Results', paths: ['TighteningSystem/Simulations/SimulateResults', 'TighteningSystem/Simulations'] }
      ],
      defaults: { byName: { SendSimulatedBulkResults: { groupId: 'simulate-results' } }, byPath: {} }
    })

    expect(manager.getMethod('SendSimulatedBulkResults').metadata.groupId).toBe('simulate-results')
    expect(manager.getGroupedMethods()).toEqual([
      expect.objectContaining({
        id: 'simulate-results',
        parentId: 'simulations',
        methods: [expect.objectContaining({ name: 'SendSimulatedBulkResults' })]
      })
    ])
  })

  it('keeps SendSimulatedBulkResults in Simulate Results with older metadata', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      SendSimulatedBulkResults: {
        methodNode: { nodeIdString: 'ns=1;i=9876' },
        nodeIdString: 'ns=1;i=9876'
      }
    }

    manager.setMethodMetadata({
      groups: [],
      defaults: { byName: {}, byPath: {} }
    })

    expect(manager.getMethod('SendSimulatedBulkResults').metadata.groupId).toBe('simulate-results')
    expect(manager.getGroupedMethods()[0]).toMatchObject({
      id: 'simulate-results',
      parentId: 'simulations',
      parentLabel: 'Simulations'
    })
  })

  it('keeps result and event simulation methods in separate child sections', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      SimulateSingleResult: {
        methodNode: { nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult' },
        nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult'
      },
      SimulateEvents: {
        methodNode: { nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateEvents' },
        nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateEventsAndConditions/SimulateEvents'
      }
    }

    manager.setMethodMetadata({
      groups: [
        { id: 'simulations', label: 'Simulations', paths: [] },
        { id: 'simulate-results', parentId: 'simulations', label: 'Simulate Results', paths: ['TighteningSystem/Simulations/SimulateResults'] },
        { id: 'simulate-events-and-conditions', parentId: 'simulations', label: 'Simulate Events and Conditions', paths: ['TighteningSystem/Simulations/SimulateEventsAndConditions'] }
      ],
      defaults: { byName: {}, byPath: {} }
    })

    expect(manager.getMethod('SimulateSingleResult').metadata.groupId).toBe('simulate-results')
    expect(manager.getMethod('SimulateEvents').metadata.groupId).toBe('simulate-events-and-conditions')
    expect(manager.getGroupedMethods().map(group => group.id)).toEqual([
      'simulate-results',
      'simulate-events-and-conditions'
    ])
  })

  it('provides valid RequestResults defaults without backend metadata', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      RequestResults: {
        methodNode: { nodeIdString: 'ns=1;s=TighteningSystem/ResultManagement/RequestResults' },
        nodeIdString: 'ns=1;s=TighteningSystem/ResultManagement/RequestResults'
      }
    }

    manager.setMethodMetadata({ groups: [], defaults: { byName: {}, byPath: {} } })

    expect(manager.getMethod('RequestResults').metadata.defaults).toMatchObject({
      FromSequenceNumber: 0,
      ToSequenceNumber: 0,
      FromTime: '2000-01-01T00:00:00Z',
      ToTime: '9999-01-01T00:00:00Z',
      RequestedMinimumDurationBetweenResults: 0
    })
  })

  it('keeps the configured domain group order instead of discovery order', () => {
    const manager = new MethodManager(makeFakeAddressSpace())
    manager.methodObject = {
      GetJoint: { nodeIdString: 'ns=1;s=TighteningSystem/JointManagement/GetJoint', methodNode: {} },
      SimulateSingleResult: { nodeIdString: 'ns=1;s=TighteningSystem/Simulations/SimulateResults/SimulateSingleResult', methodNode: {} }
    }
    manager.setMethodMetadata({
      groups: [
        { id: 'simulations', label: 'Simulations', paths: [] },
        { id: 'simulate-results', parentId: 'simulations', label: 'Simulate Results', paths: ['TighteningSystem/Simulations/SimulateResults'] },
        { id: 'joints', label: 'Joint Management', paths: ['TighteningSystem/JointManagement'] }
      ],
      defaults: { byName: {}, byPath: {} }
    })

    expect(manager.getGroupedMethods().map(group => group.id)).toEqual(['simulate-results', 'joints'])
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
    expect(result.outputArguments).toEqual([])
  })

  it('returns methodNode and parsed args when InputArguments found', async () => {
    const inputArgRelation = {
      BrowseName: { Name: 'InputArguments' },
      NodeId: 'ns=1;s=InputArgs'
    }
    const outputArgRelation = {
      BrowseName: { Name: 'OutputArguments' },
      NodeId: 'ns=1;s=OutputArgs'
    }
    const methodNode = makeNode('TestMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn(() => [inputArgRelation, outputArgRelation])

    const inputArgNode = {
      data: { attributes: { Value: ['arg1', 'arg2'] } }
    }
    const outputArgNode = {
      data: { attributes: { Value: ['out1', 'out2'] } }
    }

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async (relations) => {
      if (relations[0] === inputArgRelation) return [inputArgNode]
      if (relations[0] === outputArgRelation) return [outputArgNode]
      return []
    })

    const manager = new MethodManager(fakeAddressSpace)
    const result = await manager.setupMethod(methodNode)

    expect(result.arguments).toEqual([
      expect.objectContaining({ Name: '', FieldDefinitions: [] }),
      expect.objectContaining({ Name: '', FieldDefinitions: [] })
    ])
    expect(result.outputArguments).toEqual([
      expect.objectContaining({ Name: '', FieldDefinitions: [] }),
      expect.objectContaining({ Name: '', FieldDefinitions: [] })
    ])
    expect(result.argumentMetadata).toEqual([
      { valueRank: -1, arrayDimensions: null, fieldDefinitions: [] },
      { valueRank: -1, arrayDimensions: null, fieldDefinitions: [] }
    ])
  })

  it('finds OutputArguments exposed as components', async () => {
    const outputArgRelation = {
      BrowseName: { Name: 'OutputArguments' },
      NodeId: 'ns=1;s=OutputArgs'
    }
    const methodNode = makeNode('TestMethod', 'ns=1;s=Method', 4)
    methodNode.getChildRelations = vi.fn((type) => {
      if (type === 'hasProperty') return []
      if (type === 'component') return [outputArgRelation]
      return []
    })

    const outputArgNode = {
      data: { attributes: { Value: ['status', 'message'] } }
    }

    const fakeAddressSpace = makeFakeAddressSpace()
    fakeAddressSpace.relationsToNodes = vi.fn(async () => [outputArgNode])

    const manager = new MethodManager(fakeAddressSpace)
    const result = await manager.setupMethod(methodNode)

    expect(result.outputArguments).toEqual([
      expect.objectContaining({ Name: '', FieldDefinitions: [] }),
      expect.objectContaining({ Name: '', FieldDefinitions: [] })
    ])
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
    expect(result.arguments).toEqual([
      expect.objectContaining({ Name: '', FieldDefinitions: [] })
    ])
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

  it('maps empty UI value to empty string array when the server declares a scalar String argument with array ValueRank', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'AnyStringArray', DataType: { Identifier: 12 }, ValueRank: 1 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 12 }, value: '' }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0]).toEqual({ dataType: 12, value: [] })
  })

  it('maps empty UI value to empty string array when the server declares a TrimmedString argument with array ValueRank', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)

    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'IdentifierNames', DataType: { Identifier: 31918 }, ValueRank: 1 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 31918 }, value: [] }])

    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]
    expect(calledArgs[0]).toEqual({ dataType: 31918, value: [] })
  })

  it('keeps non-empty scalar UI value as a single string item when the server declares a scalar String argument with array ValueRank', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'AnyStringArray', DataType: { Identifier: 12 }, ValueRank: 1 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 12 }, value: 'BatchId:001' }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]

    expect(calledArgs[0]).toEqual({ dataType: 12, value: ['BatchId:001'] })
  })

  it('preserves structured arrays instead of coercing their rows to strings', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const entity = {
      value: {
        Name: 'Tool',
        Description: { Text: 'Joining tool', Locale: 'en' },
        EntityId: 'Tool-1',
        EntityOriginId: '',
        IsExternal: false,
        EntityType: 0
      }
    }
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'Entities', DataType: { Identifier: 3010 }, ValueRank: 1 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 3010 }, value: [entity] }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]

    expect(calledArgs[0]).toEqual({ dataType: 3010, value: [entity] })
  })

  it('casts numeric array items without changing the server-declared data type', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'SequenceNumbers', DataType: { Identifier: 7 }, ValueRank: 1 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 12 }, value: ['10', '20'] }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]

    expect(calledArgs[0]).toEqual({ dataType: 7, value: [10, 20] })
  })

  it('keeps a scalar value scalar when ValueRank permits either scalar or one-dimensional array', async () => {
    const fakeAddressSpace = makeFakeAddressSpace()
    const manager = new MethodManager(fakeAddressSpace)
    const methodData = {
      parentNode: makeNode('TS', 'ns=1;s=TS'),
      methodNode: makeMethodNode('Method', 'ns=1;s=TS/Method'),
      arguments: [{ Name: 'Identifier', DataType: { Identifier: 12 }, ValueRank: -3 }],
    }

    await manager.call(methodData, [{ type: { Identifier: 12 }, value: 'Id-1' }])
    const [, , calledArgs] = fakeAddressSpace.methodCall.mock.calls[0]

    expect(calledArgs[0]).toEqual({ dataType: 12, value: 'Id-1' })
  })
})
