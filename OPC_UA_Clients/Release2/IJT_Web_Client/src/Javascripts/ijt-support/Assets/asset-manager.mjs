/**
 * AssetManager — loads and organises OPC UA asset nodes.
 *
 * Traverses the AssetManagement/Assets folder of the TighteningSystem node,
 * identifying machines (nodes containing MachineryBuildingBlocks) and
 * recursively collecting sub-folder structures.
 */
import { ijtLog } from '../ijt-logger.mjs'

export class AssetManager {
  constructor (addressSpace, connectionManager) {
    this.socketHandler = connectionManager.socketHandler
    this.addressSpace = addressSpace
    this.counter = 0
  }

  /**
   * Load all assets from scratch and return a name → list map.
   * @returns {Promise<Object.<string, any[]>>}
   */
  async setupAndLoadAllAssets () {
    try {
      const tighteningSystem = await this.addressSpace.addressSpacePromise()
      const assetFolder = await this.getAssetFolder(tighteningSystem)
      const nodeList = await this.loadAllAssetsSupport(assetFolder)
      const returnObject = {}
      for (const row of nodeList) {
        returnObject[row[0]] = row[1]
      }
      return returnObject
    } catch (err) {
      ijtLog.error('setupAndLoadAllAssets failed:', err)
      return {}
    }
  }

  /**
   * Recursively collect assets under a folder node.
   * @param {object} node
   * @returns {Promise<Array>}
   */
  async loadAllAssetsSupport (node) {
    const relations = node.getChildRelations('component')
    if (relations.length === 0) return []

    const assetFolders = await this.addressSpace.relationsToNodes(relations)
    const promiseList = assetFolders.map(async (assetFolder) => {
      const components = assetFolder.getChildRelations('component')
      if (components.length === 0) {
        return [assetFolder.displayName, []]
      }
      const isMachine = components.filter(
        x => x.BrowseName.Name === 'MachineryBuildingBlocks'
      )
      if (isMachine.length > 0) {
        return assetFolder
      }
      const subList = await this.loadAllAssetsSupport(assetFolder)
      return [assetFolder.displayName, subList]
    })

    return Promise.all(promiseList)
  }

  /**
   * Resolve and return the Assets folder node under the TighteningSystem.
   * @param {object} tighteningSystem
   * @returns {Promise<object>}
   */
  async getAssetFolder (tighteningSystem) {
    const nsIJT = this.addressSpace.nsIJT
    const assetsFolderMessage = await this.socketHandler.pathtoidPromise(
      tighteningSystem.nodeId,
      JSON.stringify([
        { namespaceindex: nsIJT, identifier: 'AssetManagement' },
        { namespaceindex: nsIJT, identifier: 'Assets' }
      ])
    )
    return this.addressSpace.findOrLoadNode(
      this.addressSpace.parseMaybeJson(assetsFolderMessage.message.nodeid)
    )
  }
}
