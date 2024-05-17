/**
 * The purpose of this tab is to automatically generate a
 * a representation of the assets
 */
export class AssetManager {
  constructor (addressSpace, connectionManager) {
    this.socketHandler = connectionManager.socketHandler
    this.addressSpace = addressSpace
    this.counter = 0
  }

  /**
   * Main function for ennsuring all assets are loaded from scratch
   */
  setupAndLoadAllAssets () {
    return new Promise((resolve, reject) => {
      this.addressSpace.addressSpacePromise().then(
        (tighteningSystem) => {
          this.getAssetFolder(tighteningSystem).then((assetFolder) => {
            this.loadAllAssetsSupport(assetFolder).then((nodeList) => {
              const returnObject = {}
              for (const row of nodeList) {
                returnObject[row[0]] = row[1]
              }
              resolve(returnObject)
            })
          })
        })
    })
  }

  /**
   * Support function that given the Assets node loads all assets and return a list of Assets
   * @param {*} node the Assets folder node
   * @returns list of assets
   */
  loadAllAssetsSupport (node) {
    return new Promise((_resolve, reject) => {
      const promiseList = []
      const relations = node.getChildRelations('component')
      if (relations.length > 0) {
        this.addressSpace.relationsToNodes(relations).then((assetFolders) => {
          for (const assetFolder of assetFolders) {
            const components = assetFolder.getChildRelations('component')
            if (components.length > 0) {
              // const nsMachinery = this.addressSpace.nsMachinery
              const isMachine = components.filter(
                x => ( // x.TypeDefinition.Identifier === '1012' || // Machine
                  x.BrowseName.Name === 'MachineryBuildingBlocks')) // Machinery Component
              if (isMachine.length > 0) {
                promiseList.push(new Promise((resolve, reject) => {
                  resolve(assetFolder)
                }))
              } else {
                promiseList.push(
                  new Promise((resolve, reject) => {
                    this.loadAllAssetsSupport(assetFolder).then((list) => {
                      if (list && list.length > 0) {
                        resolve([assetFolder.displayName, list])
                      } else {
                        resolve([assetFolder.displayName, list])
                      }
                    })
                  })
                )
              }
            } else {
              promiseList.push(
                new Promise((resolve, reject) => {
                  resolve([assetFolder.displayName, []])
                }))
            }
          }
          if (promiseList.length > 0) {
            return Promise.all(promiseList).then((a) => {
              _resolve(a)
            },
            (b) => {
              console.log(b)
            }
            )
          } else {
            _resolve([])
          }
        })
      } else {
        _resolve([])
      }
    })
  }

  /**
   * Support function that finds the Assets Folder
   * @param {*} tighteningSystem The tightening system node
   * @returns the Assdet folder node
   */
  getAssetFolder (tighteningSystem) {
    return new Promise((resolve, reject) => {
      const nsIJT = this.addressSpace.nsIJT
      this.socketHandler.pathtoidPromise(
        tighteningSystem.nodeId,
        JSON.stringify(
          [{ namespaceindex: nsIJT, identifier: 'AssetManagement' },
            { namespaceindex: nsIJT, identifier: 'Assets' }])).then((assetsFolderMessage) => {
        this.addressSpace.findOrLoadNode(JSON.parse(assetsFolderMessage.message.nodeid)).then(
          (node) => {
            resolve(node)
          },
          (error) => {
            reject(error)
          })
      })
    })
  }
}

// [{ namespaceindex: nsIJT, identifier: 'AssetManagement' }],
// { namespaceindex: this.addressSpace.nsTighteningServer, identifier: 'SimulateResults' }],
