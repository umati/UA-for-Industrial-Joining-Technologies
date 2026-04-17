/**
 * Unit tests for AssetManager.
 *
 * AssetManager depends on addressSpace and connectionManager via constructor
 * injection, so we can test it fully with mocks — no live server required.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AssetManager } from '../../../src/javascripts/ijt-support/assets/asset-manager.mjs'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMockSocketHandler () {
  return {
    pathtoidPromise: vi.fn()
  }
}

function makeMockConnectionManager (socketHandler) {
  return { socketHandler }
}

function makeMockNode (displayName = 'Node', relations = []) {
  return {
    displayName,
    nodeId: 'ns=1;i=100',
    getChildRelations: vi.fn((type) => relations.filter(r => r._type === type || !type)),
    _relations: relations
  }
}

function makeMockAddressSpace (tighteningSystem = null) {
  return {
    nsIJT: 2,
    addressSpacePromise: vi.fn().mockResolvedValue(tighteningSystem ?? makeMockNode('TighteningSystem')),
    relationsToNodes: vi.fn().mockResolvedValue([]),
    findOrLoadNode: vi.fn(),
    parseMaybeJson: vi.fn(v => (typeof v === 'string' ? JSON.parse(v) : v))
  }
}

// ---------------------------------------------------------------------------
// constructor
// ---------------------------------------------------------------------------

describe('AssetManager — constructor', () => {
  it('stores socketHandler reference from connectionManager', () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)
    const as = makeMockAddressSpace()
    const mgr = new AssetManager(as, cm)
    expect(mgr.socketHandler).toBe(sh)
  })

  it('stores addressSpace reference', () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)
    const as = makeMockAddressSpace()
    const mgr = new AssetManager(as, cm)
    expect(mgr.addressSpace).toBe(as)
  })

  it('initialises counter to 0', () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)
    const as = makeMockAddressSpace()
    const mgr = new AssetManager(as, cm)
    expect(mgr.counter).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// loadAllAssetsSupport — empty folder
// ---------------------------------------------------------------------------

describe('AssetManager — loadAllAssetsSupport', () => {
  it('returns empty array when folder has no component relations', async () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)
    const as = makeMockAddressSpace()
    const mgr = new AssetManager(as, cm)

    const emptyFolder = makeMockNode('EmptyFolder', [])
    emptyFolder.getChildRelations = vi.fn(() => [])

    const result = await mgr.loadAllAssetsSupport(emptyFolder)
    expect(result).toEqual([])
  })

  it('returns [displayName, []] for a leaf folder with no components', async () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)

    const leafNode = makeMockNode('Leaf', [])
    leafNode.getChildRelations = vi.fn(() => []) // no children

    const parentRelations = [{ _type: 'component' }]
    const parentFolder = makeMockNode('Parent', parentRelations)
    parentFolder.getChildRelations = vi.fn(() => parentRelations)

    const as = makeMockAddressSpace()
    as.relationsToNodes.mockResolvedValue([leafNode])

    const mgr = new AssetManager(as, cm)
    const result = await mgr.loadAllAssetsSupport(parentFolder)
    expect(result).toHaveLength(1)
    expect(result[0][0]).toBe('Leaf')
    expect(result[0][1]).toEqual([])
  })

  it('detects a machine node containing MachineryBuildingBlocks', async () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)

    const machineComponents = [{ BrowseName: { Name: 'MachineryBuildingBlocks' } }]
    const machineNode = makeMockNode('Machine')
    machineNode.getChildRelations = vi.fn(() => machineComponents)

    const parentRelations = [{ _type: 'component' }]
    const parentFolder = makeMockNode('Assets', parentRelations)
    parentFolder.getChildRelations = vi.fn(() => parentRelations)

    const as = makeMockAddressSpace()
    as.relationsToNodes.mockResolvedValue([machineNode])

    const mgr = new AssetManager(as, cm)
    const result = await mgr.loadAllAssetsSupport(parentFolder)
    // Machine node is returned directly (not as [name, list])
    expect(result[0]).toBe(machineNode)
  })
})

// ---------------------------------------------------------------------------
// getAssetFolder
// ---------------------------------------------------------------------------

describe('AssetManager — getAssetFolder', () => {
  it('calls pathtoidPromise with correct path and returns node via findOrLoadNode', async () => {
    const sh = makeMockSocketHandler()
    const fakeNodeId = { NamespaceIndex: 2, Identifier: 999 }
    sh.pathtoidPromise = vi.fn().mockResolvedValue({
      message: { nodeid: JSON.stringify(fakeNodeId) }
    })
    const cm = makeMockConnectionManager(sh)

    const fakeNode = makeMockNode('Assets')
    const as = makeMockAddressSpace()
    as.parseMaybeJson = vi.fn(v => (typeof v === 'string' ? JSON.parse(v) : v))
    as.findOrLoadNode = vi.fn().mockResolvedValue(fakeNode)

    const tighteningSystem = makeMockNode('TighteningSystem')

    const mgr = new AssetManager(as, cm)
    const result = await mgr.getAssetFolder(tighteningSystem)
    expect(result).toBe(fakeNode)
    expect(sh.pathtoidPromise).toHaveBeenCalledOnce()
    expect(as.findOrLoadNode).toHaveBeenCalledWith(fakeNodeId)
  })
})

// ---------------------------------------------------------------------------
// setupAndLoadAllAssets
// ---------------------------------------------------------------------------

describe('AssetManager — setupAndLoadAllAssets', () => {
  it('returns empty object when loadAllAssetsSupport returns empty array', async () => {
    const sh = makeMockSocketHandler()
    const fakeNodeId = { NamespaceIndex: 2, Identifier: 500 }
    sh.pathtoidPromise = vi.fn().mockResolvedValue({
      message: { nodeid: JSON.stringify(fakeNodeId) }
    })
    const cm = makeMockConnectionManager(sh)

    const assetsFolder = makeMockNode('Assets')
    assetsFolder.getChildRelations = vi.fn(() => []) // empty — no children

    const as = makeMockAddressSpace()
    as.parseMaybeJson = vi.fn(v => (typeof v === 'string' ? JSON.parse(v) : v))
    as.findOrLoadNode = vi.fn().mockResolvedValue(assetsFolder)

    const mgr = new AssetManager(as, cm)
    const result = await mgr.setupAndLoadAllAssets()
    expect(result).toEqual({})
  })

  it('returns empty object and logs error when addressSpacePromise rejects', async () => {
    const sh = makeMockSocketHandler()
    const cm = makeMockConnectionManager(sh)

    const as = makeMockAddressSpace()
    as.addressSpacePromise = vi.fn().mockRejectedValue(new Error('not connected'))

    const mgr = new AssetManager(as, cm)
    // Should not throw — catches internally
    const result = await mgr.setupAndLoadAllAssets()
    expect(result).toEqual({})
  })

  it('builds returnObject from nodeList rows', async () => {
    const sh = makeMockSocketHandler()
    const fakeNodeId = { NamespaceIndex: 2, Identifier: 600 }
    sh.pathtoidPromise = vi.fn().mockResolvedValue({
      message: { nodeid: JSON.stringify(fakeNodeId) }
    })
    const cm = makeMockConnectionManager(sh)

    const leafNode = makeMockNode('Machine A')
    leafNode.getChildRelations = vi.fn(() => [])

    const subFolderRelations = [{ BrowseName: { Name: 'SubFolder' } }]
    const assetsFolder = makeMockNode('Assets')
    assetsFolder.getChildRelations = vi.fn(() => subFolderRelations)

    const as = makeMockAddressSpace()
    as.parseMaybeJson = vi.fn(v => (typeof v === 'string' ? JSON.parse(v) : v))
    as.findOrLoadNode = vi.fn().mockResolvedValue(assetsFolder)
    as.relationsToNodes = vi.fn().mockResolvedValue([leafNode])

    const mgr = new AssetManager(as, cm)
    const result = await mgr.setupAndLoadAllAssets()
    expect(result['Machine A']).toEqual([])
  })
})
