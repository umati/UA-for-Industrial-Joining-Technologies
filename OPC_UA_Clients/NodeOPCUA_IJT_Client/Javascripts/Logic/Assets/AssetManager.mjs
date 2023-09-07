/**
 * The purpose of this tab is to automatically generate a
 * a representation of the assets
 */
export default class AssetHandler {
  constructor (addressSpace, socketHandler) {
    this.socketHandler = socketHandler
    this.addressSpace = addressSpace
  }

  fixAssets (assetTypes, doneCallback) {
    this.addressSpace.getTighteningsSystemsPromise().then(
      (tighteningSystems) => {
        this.tighteningSystem = tighteningSystems
        console.log('Selected TighteningSystem: ' + this.tighteningSystem.nodeId)
        this.loadAllAssets().then(
          () => {
            // console.log('All assets loaded.')
            let fullList = []
            for (const assetType of assetTypes) {
              fullList = [...fullList, ...this[assetType]]
            }
            this.browseAndReadList(fullList).then(
              () => { doneCallback() }
            )
          }
        )
      },
      () => {
        throw new Error('No TighteningSystem found in Objects folder')
      }
    )
  }

  /*
  initiate () {
    // const tighteningSystems = this.addressSpace.getTighteningSystems()

    this.addressSpace.getTighteningsSystemsPromise().then(
      (tighteningSystems) => {
        this.tighteningSystem = tighteningSystems[0]
        console.log('Selected TighteningSystem: ' + this.tighteningSystem.nodeId)
        this.loadAllAssets().then(
          () => {
            // console.log('All assets loaded.')
            this.browseAndReadList([...this.controllers, ...this.tools]).then(
              () => { this.assetGraphics.draw() }
            )
          }
        )
      },
      () => {
        throw new Error('No TighteningSystem found in Objects folder')
      }
    )
  }
  */

  /**
   *
   * @returns A promise to load all assets
   */
  loadAllAssets () {
    function addAssetGraphicData (list, folderName) {
      for (const node of list) {
        if (!node.assetGraphicData) {
          node.addAssetGraphicData = {}
        }
        node.addAssetGraphicData.folderName = folderName
      }
    }

    this.controllers = []
    const assetFolders = [
      'Controllers',
      'Tools',
      'Servos',
      'MemoryDevices',
      'Sensors',
      'Cables',
      'Batteries',
      'PowerSupplies',
      'Feeders',
      'Accessories',
      'SubComponents'
    ]

    const promiseList = []
    for (const folderName of assetFolders) {
      promiseList.push(
        this.findContentInFolder(folderName).then((list) => {
          addAssetGraphicData(list, folderName)
          this[folderName.toLowerCase()] = list
        })
      )
    }

    return Promise.all(promiseList)
  }

  browseAndReadList (nodeList) {
    const promiseList = []
    for (const node of nodeList) {
      promiseList.push(
        this.addressSpace.findOrLoadNode(node.nodeId).then(
          () => { })
      )
    }

    return Promise.all(promiseList)
  }

  findContentInFolder (folderName) {
    return new Promise(
      (resolve) => {
        this.findAssetFolder(folderName).then(
          (nodeId) => {
            this.addressSpace.findOrLoadNode(nodeId).then(
              (folderNode) => {
                resolve(folderNode.getRelations('component'))
              }
            )
          })
      },
      (fail) => { fail(`Failed to find asset folder ${folderName}`) }
    )
  }

  // This should be renamed and maybe use the findFolder in addressSpace instead, but works for now.
  findAssetFolder (folderName) {
    return new Promise((resolve) => {
      const nsIJT = this.addressSpace.nsIJT
      this.socketHandler.pathtoidPromise(
        this.tighteningSystem.nodeId,
        `/${nsIJT}:AssetManagement/${nsIJT}:Assets/${nsIJT}:${folderName}`
      ).then(
        (msg) => {
          resolve(msg.message.nodeid)
        }
      )
    },
    (fail) => { fail(`Failed to get assets in folder ${folderName}`) }
    )
  }
}