/**
 * Tests for AddressSpace class — covers the OPC UA node cache, namespace
 * handling, subscription model, and async promise helpers.
 *
 * AddressSpace is already imported in address-space.test.mjs (which only
 * tests methodCall and the cached-node path). These tests cover all the
 * remaining methods to push line coverage well above the existing floor.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AddressSpace } from '../../../javascripts/ijt-support/address-space/address-space.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeNodeData (nodeid, nodeclass = 1, relations = []) {
  return {
    nodeid,
    nodeclass: { value: nodeclass },
    displayname: { value: { text: `Node_${nodeid}` } },
    relations
  }
}

function makeSocketHandler (overrides = {}) {
  return {
    registerMandatory: vi.fn(),
    browsePromise: vi.fn(),
    readPromise: vi.fn(),
    methodCall: vi.fn(),
    subscribeEvent: vi.fn(),
    pathtoidPromise: vi.fn(),
    ...overrides
  }
}

function makeConnectionManager (socketHandler) {
  const subscribeCallbacks = []
  return {
    socketHandler,
    subscribe: vi.fn((state, cb) => subscribeCallbacks.push({ state, cb })),
    trigger: vi.fn(),
    _subscribeCallbacks: subscribeCallbacks,
    _triggerState (state, val) {
      subscribeCallbacks.filter(c => c.state === state).forEach(c => c.cb(val))
    }
  }
}

function makeBrowseResponse (nodeid, nodeclass = 1) {
  return {
    message: {
      nodeid,
      browseresult: { references: [] }
    }
  }
}

function makeReadResponse (value, type = 'text') {
  if (type === 'nodeclass') {
    return { message: { dataValue: { value: { value: 1 } } } }
  }
  return { message: { dataValue: { value: { text: `DisplayName_${nodeid}` } } } }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AddressSpace — construction', () => {
  it('registers namespaces and datatypes mandatory handlers', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    new AddressSpace(cm)
    expect(sh.registerMandatory).toHaveBeenCalledWith('namespaces', expect.any(Function))
    expect(sh.registerMandatory).toHaveBeenCalledWith('datatypes', expect.any(Function))
  })

  it('subscribes to session state on construction', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    new AddressSpace(cm)
    expect(cm.subscribe).toHaveBeenCalledWith('session', expect.any(Function))
  })

  it('initialises with empty nodeMapping and null objectFolder', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    expect(as.nodeMapping).toEqual({})
    expect(as.objectFolder).toBeNull()
    expect(as.status).toEqual([])
  })
})

describe('AddressSpace.reset()', () => {
  it('clears nodeMapping when called', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.nodeMapping['ns=1;i=100'] = { nodeId: 'ns=1;i=100' }
    as.nodeMapping['ns=1;i=200'] = { nodeId: 'ns=1;i=200' }
    as.reset()
    expect(as.nodeMapping).toEqual({})
  })
})

describe('AddressSpace.handleNamespaces()', () => {
  it('populates namespace index properties from array', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const namespaceMsg = {
      namespaces: [
        'http://opcfoundation.org/UA/',
        'http://www.atlascopco.com/TighteningApplication/',
        'http://opcfoundation.org/UA/DI/',
        'http://opcfoundation.org/UA/AMB/',
        'http://opcfoundation.org/UA/IA/',
        'http://opcfoundation.org/UA/Machinery/',
        'http://opcfoundation.org/UA/Machinery/Result/',
        'http://opcfoundation.org/UA/IJT/Base/',
        'http://opcfoundation.org/UA/IJT/Tightening/',
        'urn:AtlasCopco:IJT:Tightening:Server/'
      ]
    }
    as.handleNamespaces(namespaceMsg)
    expect(as.OPCUA).toBe(0)
    expect(as.nsDI).toBe(2)
    expect(as.nsMachinery).toBe(5)
    expect(as.nsMachineryResult).toBe(6)
    expect(as.nsIJT).toBe(7)
    expect(as.nsTightening).toBe(8)
    expect(as.nsTighteningServer).toBe(9)
  })

  it('sets -1 for namespace not in the array', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.handleNamespaces({ namespaces: ['http://opcfoundation.org/UA/'] })
    expect(as.nsIJT).toBe(-1)
    expect(as.nsTightening).toBe(-1)
  })
})

describe('AddressSpace.addressSpaceCheck()', () => {
  it('returns falsy when no status entries', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    expect(as.addressSpaceCheck()).toBeFalsy()
  })

  it('returns falsy when only namespaces set', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.status = ['namespaces']
    expect(as.addressSpaceCheck()).toBeFalsy()
  })

  it('returns falsy when namespaces + datatypes but no tighteningsystem', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.status = ['namespaces', 'datatypes']
    expect(as.addressSpaceCheck()).toBeFalsy()
  })

  it('returns truthy when all three status entries present', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.status = ['namespaces', 'datatypes', 'tighteningsystem']
    expect(as.addressSpaceCheck()).toBeTruthy()
  })
})

describe('AddressSpace.addressSpaceSetup()', () => {
  it('pushes status string into status array', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.addressSpaceSetup('namespaces')
    expect(as.status).toContain('namespaces')
  })

  it('resolves queued promises when all three statuses complete', async () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const fakeTS = { nodeId: 'ns=7;i=1001' }
    as.tighteningSystem = fakeTS

    // Queue a promise BEFORE all statuses are set
    const promiseResult = as.addressSpacePromise()

    // Now set all statuses — third call should flush the queue
    as.addressSpaceSetup('namespaces')
    as.addressSpaceSetup('datatypes')
    as.addressSpaceSetup('tighteningsystem')

    await expect(promiseResult).resolves.toBe(fakeTS)
    expect(as.listOfTSPromises).toHaveLength(0)
  })

  it('does not resolve until all three statuses are present', async () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.tighteningSystem = { nodeId: 'ns=7;i=1001' }

    let resolved = false
    as.addressSpacePromise().then(() => { resolved = true })

    as.addressSpaceSetup('namespaces')
    as.addressSpaceSetup('datatypes')
    // Third not yet — promise still pending
    await Promise.resolve()
    expect(resolved).toBe(false)

    as.addressSpaceSetup('tighteningsystem')
    await Promise.resolve()
    expect(resolved).toBe(true)
  })
})

describe('AddressSpace.addressSpacePromise()', () => {
  it('resolves immediately when address space already set up', async () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.status = ['namespaces', 'datatypes', 'tighteningsystem']
    const fakeTS = { nodeId: 'ns=7;i=1001' }
    as.tighteningSystem = fakeTS

    const result = await as.addressSpacePromise()
    expect(result).toBe(fakeTS)
  })

  it('queues promise when not yet set up (listOfTSPromises grows)', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.addressSpacePromise()
    expect(as.listOfTSPromises).toHaveLength(1)
  })

  it('queues multiple promises independently', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    as.addressSpacePromise()
    as.addressSpacePromise()
    as.addressSpacePromise()
    expect(as.listOfTSPromises).toHaveLength(3)
  })
})

describe('AddressSpace.subscribeToNewNode()', () => {
  it('stores callback in newNodeSubscription array', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const cb = vi.fn()
    as.subscribeToNewNode(cb)
    expect(as.newNodeSubscription).toContain(cb)
  })

  it('multiple callbacks are all stored', () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const cb1 = vi.fn()
    const cb2 = vi.fn()
    as.subscribeToNewNode(cb1)
    as.subscribeToNewNode(cb2)
    expect(as.newNodeSubscription).toHaveLength(2)
  })
})

describe('AddressSpace.findOrLoadNode() — cache miss path', () => {
  it('calls browsePromise and readPromise when node not cached', async () => {
    const nodeid = 'ns=1;i=300'
    const sh = makeSocketHandler({
      browsePromise: vi.fn().mockResolvedValue({
        message: { nodeid, browseresult: { references: [] } }
      }),
      readPromise: vi.fn()
        .mockResolvedValueOnce({ message: { dataValue: { value: { text: 'TestNode' } } } })   // DisplayName
        .mockResolvedValueOnce({ message: { dataValue: { value: { value: 1 } } } })           // NodeClass
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    const node = await as.findOrLoadNode(nodeid)
    expect(sh.browsePromise).toHaveBeenCalledWith(nodeid, true)
    expect(node).toBeDefined()
    expect(node.nodeId).toBe(nodeid)
  })

  it('caches newly loaded node so second call does not re-browse', async () => {
    const nodeid = 'ns=1;i=400'
    const sh = makeSocketHandler({
      browsePromise: vi.fn().mockResolvedValue({
        message: { nodeid, browseresult: { references: [] } }
      }),
      readPromise: vi.fn()
        .mockResolvedValueOnce({ message: { dataValue: { value: { text: 'Cached' } } } })
        .mockResolvedValueOnce({ message: { dataValue: { value: { value: 1 } } } })
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    await as.findOrLoadNode(nodeid)
    await as.findOrLoadNode(nodeid)
    // Browse should only be called once (second call hits cache)
    expect(sh.browsePromise).toHaveBeenCalledTimes(1)
  })

  it('notifies newNodeSubscription callbacks when a new node is created', async () => {
    const nodeid = 'ns=1;i=500'
    const sh = makeSocketHandler({
      browsePromise: vi.fn().mockResolvedValue({
        message: { nodeid, browseresult: { references: [] } }
      }),
      readPromise: vi.fn()
        .mockResolvedValueOnce({ message: { dataValue: { value: { text: 'NewNode' } } } })
        .mockResolvedValueOnce({ message: { dataValue: { value: { value: 1 } } } })
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const cb = vi.fn()
    as.subscribeToNewNode(cb)

    await as.findOrLoadNode(nodeid)
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('reads Value attribute for VariableNode (nodeclass 2)', async () => {
    const nodeid = 'ns=1;i=600'
    const sh = makeSocketHandler({
      browsePromise: vi.fn().mockResolvedValue({
        message: { nodeid, browseresult: { references: [] } }
      }),
      readPromise: vi.fn()
        .mockResolvedValueOnce({ message: { dataValue: { value: { text: 'VarNode' } } } })   // DisplayName
        .mockResolvedValueOnce({ message: { dataValue: { value: { value: 2 } } } })           // NodeClass = 2
        .mockResolvedValueOnce({ message: { dataValue: { value: 42 } } })                      // Value
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    const node = await as.findOrLoadNode(nodeid)
    // Value read should have been called (third readPromise call)
    expect(sh.readPromise).toHaveBeenCalledTimes(3)
    expect(node.nodeId).toBe(nodeid)
  })
})

describe('AddressSpace.relationsToNodes()', () => {
  it('returns empty array for empty relations list', async () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const result = await as.relationsToNodes([])
    expect(result).toEqual([])
  })

  it('resolves each relation to a cached node', async () => {
    const sh = makeSocketHandler()
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const fakeNode1 = { nodeId: 'ns=1;i=10' }
    const fakeNode2 = { nodeId: 'ns=1;i=20' }
    as.nodeMapping['ns=1;i=10'] = fakeNode1
    as.nodeMapping['ns=1;i=20'] = fakeNode2

    const result = await as.relationsToNodes([
      { nodeId: 'ns=1;i=10' },
      { nodeId: 'ns=1;i=20' }
    ])
    expect(result).toHaveLength(2)
    expect(result[0]).toBe(fakeNode1)
    expect(result[1]).toBe(fakeNode2)
  })
})

describe('AddressSpace.read()', () => {
  it('returns node from socketHandler.readPromise on success', async () => {
    const fakeNode = { nodeId: 'ns=1;i=99' }
    const sh = makeSocketHandler({
      readPromise: vi.fn().mockResolvedValue({ node: fakeNode })
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    const result = await as.read('ns=1;i=99', 'Value')
    expect(result).toBe(fakeNode)
  })

  it('returns null and does not throw when readPromise rejects', async () => {
    const sh = makeSocketHandler({
      readPromise: vi.fn().mockRejectedValue(new Error('timeout'))
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    const result = await as.read('ns=1;i=99', 'Value')
    expect(result).toBeNull()
  })
})

describe('AddressSpace — session state trigger', () => {
  it('does not call initiate() when session triggers false', () => {
    const sh = makeSocketHandler({
      browsePromise: vi.fn(),
      readPromise: vi.fn()
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const initiateSpy = vi.spyOn(as, 'initiate')

    cm._triggerState('session', false)
    expect(initiateSpy).not.toHaveBeenCalled()
  })

  it('calls initiate() when session triggers true', () => {
    const sh = makeSocketHandler({
      browsePromise: vi.fn().mockRejectedValue(new Error('no server')),
      readPromise: vi.fn()
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const initiateSpy = vi.spyOn(as, 'initiate').mockImplementation(() => {})

    cm._triggerState('session', true)
    expect(initiateSpy).toHaveBeenCalled()
  })
})

describe('AddressSpace — namespaces handler via registerMandatory', () => {
  it('handleNamespaces is called when namespaces message arrives', () => {
    // Capture the handler registered for 'namespaces'
    const handlers = {}
    const sh = makeSocketHandler({
      registerMandatory: vi.fn((event, cb) => { handlers[event] = cb })
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)
    const handleSpy = vi.spyOn(as, 'handleNamespaces')

    // Simulate the server pushing a namespaces message
    handlers.namespaces({
      namespaces: ['http://opcfoundation.org/UA/', 'http://opcfoundation.org/UA/IJT/Base/']
    })
    expect(handleSpy).toHaveBeenCalled()
  })

  it('dataTypeEnumeration is set when datatypes message arrives', () => {
    const handlers = {}
    const sh = makeSocketHandler({
      registerMandatory: vi.fn((event, cb) => { handlers[event] = cb })
    })
    const cm = makeConnectionManager(sh)
    const as = new AddressSpace(cm)

    const fakeDataTypes = { 1: 'Boolean', 7: 'UInt32' }
    handlers.datatypes({ datatype: fakeDataTypes })
    expect(as.dataTypeEnumeration).toEqual(fakeDataTypes)
  })
})
