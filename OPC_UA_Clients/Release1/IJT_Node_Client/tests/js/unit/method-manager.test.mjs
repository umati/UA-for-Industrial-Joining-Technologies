import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MethodManager } from '../../../javascripts/ijt-support/methods/method-manager.mjs'

function makeAddressSpace () {
  return {
    addressSpacePromise: vi.fn(() => Promise.resolve({})),
    findNodeFromPathPromise: vi.fn(() => Promise.resolve({})),
    relationsToNodes: vi.fn(() => Promise.resolve([])),
    methodCall: vi.fn(() => Promise.resolve({ message: {}, node: null })),
    dataTypeEnumeration: {}
  }
}

describe('MethodManager', () => {
  let mm, addressSpace

  beforeEach(() => {
    addressSpace = makeAddressSpace()
    mm = new MethodManager(addressSpace)
  })

  it('constructor stores addressSpace', () => {
    expect(mm.addressSpace).toBe(addressSpace)
  })

  it('getMethodNames() returns empty array before setup', () => {
    mm.methodObject = {}
    expect(mm.getMethodNames()).toEqual([])
  })

  it('getMethod() returns undefined for unknown method', () => {
    mm.methodObject = {}
    expect(mm.getMethod('NonExistent')).toBeUndefined()
  })

  it('getMethod() returns method data when set', () => {
    const methodData = { parentNode: {}, methodNode: {}, arguments: [] }
    mm.methodObject = { TestMethod: methodData }
    expect(mm.getMethod('TestMethod')).toBe(methodData)
  })

  it('call() invokes addressSpace.methodCall with correct args', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    mm.call(methodData, [{ type: 'i=7', value: '42' }])
    expect(addressSpace.methodCall).toHaveBeenCalledWith(
      'ns=1;i=10',
      'ns=1;i=20',
      [{ dataType: 7, value: 42 }]
    )
  })

  it('call() catches and logs errors from methodCall rejection', async () => {
    addressSpace.methodCall.mockRejectedValueOnce(new Error('OPC UA error'))
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    // Should not throw — error is caught internally
    expect(() => mm.call(methodData, [])).not.toThrow()
    // Allow microtask queue to flush so the .catch() runs
    await Promise.resolve()
  })
})

// ── Additional edge-case tests ─────────────────────────────────────────────

describe('MethodManager — getMethodNames and getMethod with data', () => {
  let mm, addressSpace

  beforeEach(() => {
    addressSpace = {
      addressSpacePromise: vi.fn(() => Promise.resolve({})),
      findNodeFromPathPromise: vi.fn(() => Promise.resolve({})),
      relationsToNodes: vi.fn(() => Promise.resolve([])),
      methodCall: vi.fn(() => Promise.resolve({ message: {}, node: null })),
      dataTypeEnumeration: {}
    }
    mm = new MethodManager(addressSpace)
  })

  it('getMethodNames() returns all keys when methodObject is populated', () => {
    mm.methodObject = {
      'GetResult': {},
      'RequestResult': {},
      'AcknowledgeResult': {}
    }
    const names = mm.getMethodNames()
    expect(names).toContain('GetResult')
    expect(names).toContain('RequestResult')
    expect(names).toContain('AcknowledgeResult')
    expect(names).toHaveLength(3)
  })

  it('getMethod() returns correct method data for each name', () => {
    const getResultData = { parentNode: { nodeId: 'ns=1;i=1' }, methodNode: { nodeId: 'ns=1;i=2' }, arguments: [] }
    const ackResultData = { parentNode: { nodeId: 'ns=1;i=3' }, methodNode: { nodeId: 'ns=1;i=4' }, arguments: [] }
    mm.methodObject = { GetResult: getResultData, AckResult: ackResultData }
    expect(mm.getMethod('GetResult')).toBe(getResultData)
    expect(mm.getMethod('AckResult')).toBe(ackResultData)
  })
})

describe('MethodManager.call() — type handling', () => {
  let mm, addressSpace

  beforeEach(() => {
    addressSpace = {
      addressSpacePromise: vi.fn(() => Promise.resolve({})),
      findNodeFromPathPromise: vi.fn(() => Promise.resolve({})),
      relationsToNodes: vi.fn(() => Promise.resolve([])),
      methodCall: vi.fn(() => Promise.resolve({ message: {}, node: null })),
      dataTypeEnumeration: {}
    }
    mm = new MethodManager(addressSpace)
  })

  it('call() converts type i=1 (string) without parseInt', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    mm.call(methodData, [{ type: 'ns=0;i=1', value: 'hello world' }])
    expect(addressSpace.methodCall).toHaveBeenCalledWith(
      'ns=1;i=10',
      'ns=1;i=20',
      [{ dataType: 1, value: 'hello world' }]
    )
  })

  it('call() converts type i=7 (integer) with parseInt', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    mm.call(methodData, [{ type: 'ns=0;i=7', value: '42' }])
    expect(addressSpace.methodCall).toHaveBeenCalledWith(
      'ns=1;i=10',
      'ns=1;i=20',
      [{ dataType: 7, value: 42 }]
    )
  })

  it('call() passes raw value for unrecognised types (e.g. i=12 String)', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    // i=12 is OPC UA String type — not in the explicit switch cases.
    // The default branch must pass the value through unchanged, not produce undefined.
    mm.call(methodData, [{ type: 'ns=0;i=12', value: 'some-string' }])
    expect(addressSpace.methodCall).toHaveBeenCalledWith(
      'ns=1;i=10',
      'ns=1;i=20',
      [{ dataType: 12, value: 'some-string' }]
    )
  })

  it('call() sends empty inputArguments when inputs is empty array', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    mm.call(methodData, [])
    expect(addressSpace.methodCall).toHaveBeenCalledWith('ns=1;i=10', 'ns=1;i=20', [])
  })

  it('call() sends multiple arguments in correct order', () => {
    const methodData = {
      parentNode: { nodeId: 'ns=1;i=10' },
      methodNode: { nodeId: 'ns=1;i=20', displayName: 'TestMethod' },
      arguments: []
    }
    mm.call(methodData, [
      { type: 'i=7', value: '100' },
      { type: 'i=1', value: 'result-handle' }
    ])
    expect(addressSpace.methodCall).toHaveBeenCalledWith(
      'ns=1;i=10',
      'ns=1;i=20',
      [
        { dataType: 7, value: 100 },
        { dataType: 1, value: 'result-handle' }
      ]
    )
  })
})

describe('MethodManager.setupMethodsInFolders()', () => {
  it('rejects when addressSpacePromise rejects', async () => {
    const addressSpace = {
      addressSpacePromise: vi.fn(() => Promise.reject(new Error('not ready'))),
      findNodeFromPathPromise: vi.fn(),
      relationsToNodes: vi.fn(),
      methodCall: vi.fn(),
      dataTypeEnumeration: {}
    }
    const mm = new MethodManager(addressSpace)
    await expect(mm.setupMethodsInFolders(['MethodsFolder'])).rejects.toThrow('not ready')
  })

  it('resolves with empty methodObject when addressSpace has no method nodes', async () => {
    const tighteningSystemNode = {
      nodeId: 'ns=7;i=1001',
      getChildRelations: vi.fn(() => [])
    }
    const addressSpace = {
      addressSpacePromise: vi.fn(() => Promise.resolve(tighteningSystemNode)),
      findNodeFromPathPromise: vi.fn(() => Promise.resolve(tighteningSystemNode)),
      relationsToNodes: vi.fn(() => Promise.resolve([])),
      methodCall: vi.fn(),
      dataTypeEnumeration: {}
    }
    const mm = new MethodManager(addressSpace)
    mm.methodObject = {}
    await mm.setupMethodsInFolders([''])
    // Empty methodFolders with empty path resolves immediately
    expect(mm.methodObject).toEqual({})
  })
})

describe('MethodManager.addressFolder() and folderPromise()', () => {
  let mm, addressSpace

  beforeEach(() => {
    addressSpace = {
      addressSpacePromise: vi.fn(() => Promise.resolve({ nodeId: 'ns=7;i=1' })),
      findNodeFromPathPromise: vi.fn(() => Promise.resolve({
        nodeId: 'ns=7;i=2',
        getChildRelations: vi.fn(() => [])
      })),
      relationsToNodes: vi.fn(() => Promise.resolve([])),
      methodCall: vi.fn(),
      dataTypeEnumeration: {}
    }
    mm = new MethodManager(addressSpace)
    mm.methodObject = {}
  })

  it('addressFolder with empty path calls folderPromise on tighteningSystemNode', async () => {
    mm.tighteningSystemNode = {
      nodeId: 'ns=7;i=1',
      getChildRelations: vi.fn(() => [])
    }
    await mm.addressFolder('')
    expect(addressSpace.relationsToNodes).toHaveBeenCalled()
  })

  it('addressFolder with non-empty path calls findNodeFromPathPromise', async () => {
    mm.tighteningSystemNode = { nodeId: 'ns=7;i=1' }
    await mm.addressFolder('2:MethodsFolder')
    expect(addressSpace.findNodeFromPathPromise).toHaveBeenCalledWith('2:MethodsFolder')
  })

  it('folderPromise with nodeclass=4 child calls setupMethod', async () => {
    const mockInputArgNode = {
      data: {
        value: {
          message: {
            dataValue: { value: { value: [] } }
          }
        }
      }
    }
    addressSpace.relationsToNodes = vi.fn()
      .mockResolvedValueOnce([
        {
          nodeId: 'ns=7;i=10',
          displayName: 'SimulateJobResult',
          data: { nodeclass: { value: 4 } },
          getChildRelations: vi.fn(() => [{ browseName: { name: 'InputArguments' } }])
        }
      ])
      .mockResolvedValueOnce([mockInputArgNode])

    mm.methodObject = {}
    const folderNode = {
      nodeId: 'ns=7;i=5',
      getChildRelations: vi.fn(() => [{ nodeId: 'ns=7;i=6' }])
    }
    await mm.folderPromise(folderNode)
    expect(Object.keys(mm.methodObject)).toHaveLength(1)
  })
})

describe('MethodManager.setupMethod()', () => {
  let mm, addressSpace

  beforeEach(() => {
    addressSpace = {
      addressSpacePromise: vi.fn(),
      findNodeFromPathPromise: vi.fn(),
      relationsToNodes: vi.fn(),
      methodCall: vi.fn(),
      dataTypeEnumeration: { '12': 'String', '7': 'Int32' }
    }
    mm = new MethodManager(addressSpace)
    mm.methodObject = {}
  })

  it('setupMethod resolves with methodNode and empty arguments when no input args data', async () => {
    const mockInputArgNode = {
      data: {
        value: {
          message: {
            dataValue: { value: { value: [] } }
          }
        }
      }
    }
    addressSpace.relationsToNodes = vi.fn(() => Promise.resolve([mockInputArgNode]))

    const methodNode = {
      displayName: 'TestMethod',
      getChildRelations: vi.fn(() => [{ browseName: { name: 'InputArguments' } }])
    }
    const result = await mm.setupMethod(methodNode)
    expect(result.methodNode).toBe(methodNode)
    expect(result.arguments).toEqual([])
  })

  it('setupMethod resolves with argument that has typeName when dataType in enumeration', async () => {
    const argContent = { dataType: '12', typeName: undefined }
    const mockInputArgNode = {
      data: {
        value: {
          message: {
            dataValue: { value: { value: [argContent] } }
          }
        }
      }
    }
    addressSpace.relationsToNodes = vi.fn(() => Promise.resolve([mockInputArgNode]))

    const methodNode = {
      displayName: 'TestMethod2',
      getChildRelations: vi.fn(() => [{ browseName: { name: 'InputArguments' } }])
    }
    const result = await mm.setupMethod(methodNode)
    expect(result.arguments).toHaveLength(1)
    expect(result.arguments[0].typeName).toBe('String')
  })
})
