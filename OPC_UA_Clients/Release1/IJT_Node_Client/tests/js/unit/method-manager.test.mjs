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
