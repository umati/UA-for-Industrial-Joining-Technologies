import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AssetManager } from '../../../javascripts/ijt-support/assets/asset-manager.mjs'

function makeAddressSpace () {
  return {
    addressSpacePromise: vi.fn(() => Promise.resolve({ nodeId: 'ns=1;i=1000' })),
    findOrLoadNode: vi.fn(() => Promise.resolve({ nodeId: 'ns=1;i=1001', getChildRelations: () => [] })),
    nsIJT: 2,
    nsMachinery: 3
  }
}

function makeConnectionManager () {
  return {
    socketHandler: {
      pathtoidPromise: vi.fn(() => Promise.resolve({ message: { nodeid: 'ns=1;i=999' } }))
    }
  }
}

describe('AssetManager', () => {
  let am, addressSpace, connectionManager

  beforeEach(() => {
    addressSpace = makeAddressSpace()
    connectionManager = makeConnectionManager()
    am = new AssetManager(addressSpace, connectionManager)
  })

  it('constructor stores socketHandler', () => {
    expect(am.socketHandler).toBe(connectionManager.socketHandler)
  })

  it('constructor stores addressSpace', () => {
    expect(am.addressSpace).toBe(addressSpace)
  })

  it('constructor initializes counter to 0', () => {
    expect(am.counter).toBe(0)
  })

  it('getAssetFolder() uses pathtoidPromise', async () => {
    addressSpace.findOrLoadNode.mockResolvedValue({
      nodeId: 'ns=1;i=999',
      getChildRelations: () => []
    })
    await am.getAssetFolder({ nodeId: 'ns=1;i=1000' })
    expect(connectionManager.socketHandler.pathtoidPromise).toHaveBeenCalledWith(
      'ns=1;i=1000',
      expect.stringContaining('AssetManagement')
    )
  })
})
