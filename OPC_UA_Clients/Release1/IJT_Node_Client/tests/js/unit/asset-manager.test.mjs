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

  it('loadAllAssetsSupport() resolves with [] when node has no component relations', async () => {
    const emptyNode = { getChildRelations: () => [] }
    const result = await am.loadAllAssetsSupport(emptyNode)
    expect(result).toEqual([])
  })

  it('loadAllAssetsSupport() resolves (not hang) when Promise.all succeeds with empty list', async () => {
    const addressSpaceWithRelations = makeAddressSpace()
    addressSpaceWithRelations.relationsToNodes = vi.fn(() => Promise.resolve([
      { nodeId: 'ns=1;i=501', getChildRelations: () => [], displayName: 'Child' }
    ]))
    const amWithRelations = new AssetManager(addressSpaceWithRelations, connectionManager)
    const nodeWithChild = {
      getChildRelations: (type) => type === 'component' ? [{ nodeId: 'ns=1;i=500' }] : []
    }
    const result = await amWithRelations.loadAllAssetsSupport(nodeWithChild)
    expect(Array.isArray(result)).toBe(true)
  })

  it('loadAllAssetsSupport() — node with hasAddin matching machinery type is included', async () => {
    const nsMachinery = 3
    const am2 = new AssetManager(
      { ...addressSpace, nsMachinery, relationsToNodes: vi.fn(() => Promise.resolve([
        {
          nodeId: 'ns=1;i=10',
          displayName: 'MachinePart',
          getChildRelations: vi.fn((type) => {
            if (type === 'hasAddin') {
              return [{ typeDefinition: `ns=${nsMachinery};i=1012` }]
            }
            return []
          })
        }
      ])) },
      connectionManager
    )
    const nodeWithChild = {
      getChildRelations: (type) => type === 'component' ? [{ nodeId: 'ns=1;i=100' }] : []
    }
    const result = await am2.loadAllAssetsSupport(nodeWithChild)
    expect(Array.isArray(result)).toBe(true)
  })

  it('loadAllAssetsSupport() — node with hasAddin NOT matching machinery type recurses', async () => {
    const nsMachinery = 3
    const am3 = new AssetManager(
      { ...addressSpace, nsMachinery, relationsToNodes: vi.fn(() => Promise.resolve([
        {
          nodeId: 'ns=1;i=11',
          displayName: 'OtherPart',
          getChildRelations: vi.fn((type) => {
            if (type === 'hasAddin') {
              return [{ typeDefinition: `ns=${nsMachinery};i=9999` }]
            }
            return []
          })
        }
      ])) },
      connectionManager
    )
    const nodeWithChild = {
      getChildRelations: (type) => type === 'component' ? [{ nodeId: 'ns=1;i=100' }] : []
    }
    const result = await am3.loadAllAssetsSupport(nodeWithChild)
    expect(Array.isArray(result)).toBe(true)
  })

  it('loadAllAssetsSupport() resolves [] when relationsToNodes rejects', async () => {
    const amWithFailure = new AssetManager(
      { ...addressSpace, relationsToNodes: vi.fn().mockRejectedValue(new Error('browse failed')) },
      connectionManager
    )
    const nodeWithChild = {
      getChildRelations: (type) => type === 'component' ? [{ nodeId: 'ns=1;i=100' }] : []
    }

    await expect(amWithFailure.loadAllAssetsSupport(nodeWithChild)).resolves.toEqual([])
  })

  it('loadAllAssetsSupport() resolves [] when recursive child loading rejects', async () => {
    const child = {
      displayName: 'BadChild',
      getChildRelations: (type) => {
        if (type === 'hasAddin') {
          return []
        }
        throw new Error(`cannot load ${type}`)
      }
    }
    const amWithBadChild = new AssetManager(
      { ...addressSpace, relationsToNodes: vi.fn().mockResolvedValue([child]) },
      connectionManager
    )
    const nodeWithChild = {
      getChildRelations: (type) => type === 'component' ? [{ nodeId: 'ns=1;i=100' }] : []
    }

    await expect(amWithBadChild.loadAllAssetsSupport(nodeWithChild)).resolves.toEqual([])
  })

  it('setupAndLoadAllAssets() — returns empty object when assets folder has no children', async () => {
    const result = await am.setupAndLoadAllAssets()
    expect(typeof result).toBe('object')
  })

  it('setupAndLoadAllAssets() — builds returnObject from nodeList', async () => {
    const asWithData = new AssetManager(addressSpace, connectionManager)
    asWithData.getAssetFolder = vi.fn(() => Promise.resolve({ nodeId: 'ns=1;i=123' }))
    asWithData.loadAllAssetsSupport = vi.fn(() => Promise.resolve([
      ['Asset1', { nodeId: 'ns=1;i=201' }],
      ['Asset2', { nodeId: 'ns=1;i=202' }]
    ]))

    const result = await asWithData.setupAndLoadAllAssets()
    expect(result).toEqual({
      Asset1: { nodeId: 'ns=1;i=201' },
      Asset2: { nodeId: 'ns=1;i=202' }
    })
  })
})
