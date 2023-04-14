import AssetGraphic from './AssetGraphic.mjs'

/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the assets
 */
export default class AssetHandler {
  constructor (container, addressSpace, socketHandler) {
    this.socketHandler = socketHandler
    this.addressSpace = addressSpace

    const backGround = document.createElement('div')
    backGround.classList.add('datastructure')
    container.appendChild(backGround)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    leftHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(leftHalf)

    const nodeDiv = document.createElement('div')
    nodeDiv.classList.add('myHeader')
    nodeDiv.innerText = 'AssetView'
    leftHalf.appendChild(nodeDiv)

    const displayArea = document.createElement('div')
    displayArea.classList.add('drawAssetBox')
    leftHalf.appendChild(displayArea)

    const serverDiv = document.getElementById('connectedServer')
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Assets') {
        this.initiate()
      }
    }, false)

    this.assetGraphic = new AssetGraphic(displayArea)
  }

  messageDisplay (item) {
    alert('AssetHandler has no message area')
  }

  initiate () {
    const tighteningSystems = this.addressSpace.getTighteningSystems()
    if (!tighteningSystems || tighteningSystems.length < 1) {
      throw new Error('No TighteningSystem found in Objects folder')
    }
    this.tighteningSystem = tighteningSystems[0]
    console.log('Selected TighteningSystem: ' + this.tighteningSystem.nodeId)
    this.loadAllAssets().then(
      () => {
        // console.log('All assets loaded.')
        this.browseAndReadList([...this.controllers, ...this.tools]).then(
          () => { this.draw() }
        )
      }
    )
  }

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
        node.GUIexplore().then(
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
            this.addressSpace.browseAndReadWithNodeId(nodeId).then(
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

  draw () {
    const assetGraphic = this.assetGraphic

    function drawAssetRecursive (asset) {
      drawAssetWithExternals(asset.getRelations('association'), asset)
    }

    function drawAssetWithExternals (associations, containerNode) {
      for (const external of externals) {
        for (const association of associations) {
          if (association.associatedNodeId === external.nodeId) {
            assetGraphic.addExternal(external, containerNode)
            drawAssetRecursive(external)
          }
        }
      }
      for (const internal of internals) {
        for (const association of associations) {
          if (association.associatedNodeId === internal.nodeId) {
            assetGraphic.addInternal(internal, containerNode)
            drawAssetRecursive(internal)
          }
        }
      }
    }

    let i = 0
    const externals = [
      ...this.powersupplies,
      ...this.feeders,
      ...this.cables,
      ...this.accessories]
    const internals = [
      ...this.servos,
      ...this.memorydevices,
      ...this.subcomponents,
      ...this.batteries,
      ...this.sensors]
    for (const controller of this.controllers) {
      this.assetGraphic.createController(controller, i, this.controllers.length)

      const associations = controller.getRelations('association')

      drawAssetWithExternals(associations, controller)

      for (const tool of this.tools) {
        for (const association of associations) {
          if (association.associatedNodeId === tool.nodeId) {
            this.assetGraphic.addTool(tool, controller)
            drawAssetRecursive(tool)
          }
        }
      }

      // this.assetGraphic.addExternal({ nodeId: 1, displayName: { text: 'Example Stacklight' } }, controller)

      i++
    }
  }
}
