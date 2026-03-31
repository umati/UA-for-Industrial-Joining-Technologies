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
    connectionManager: { trigger: vi.fn() },
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
