import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
/**
 * This illustrates how a simple view of all the assets can be done using the assetManager.
 * Start by making sure all assets are loaded, then loop through the controllers and draw them and their
 * associated assets
 */
export default class AssetGraphics extends BasicScreen {
  constructor (assetManager) {
    super('Assets', 'tighteningsystem')
    this.assetManager = assetManager

    const displayArea = document.createElement('div')
    displayArea.classList.add('drawAssetBox')
    this.backGround.appendChild(displayArea)

    this.container = displayArea
  }

  /**
   * Run every time the page is opened and first load all the Assets using the assetmanager and
   * then sends the result to the draw function
   */
  initiate () {
    this.assetManager.setupAndLoadAllAssets().then((assetObject) => {
      this.draw(assetObject)
    })
  }

  /**
   * Takes an object containing all the Assets and then draw graphics to represent them
   * @param {*} assetObject an object from assetManager.setupAndLoadAllAssets that contain all assets
   */
  draw (assetObject) {
    function drawAssetRecursive (asset) {
      drawAssetWithExternals(asset.getRelations('association'), asset)
    }

    function mySet (associations) {
      const idMapping = {}
      for (const ass of associations) {
        idMapping[ass.NodeId.Identifier] = ass
      }
      return Object.values(idMapping)
    }

    const drawAssetWithExternals = (associations2, containerNode) => {
      const associations = mySet(associations2)
      for (const external of externals) {
        for (const association of associations) {
          if (association.NodeId.Identifier === external.nodeId.Identifier) {
            this.addExternal(external, containerNode)
            drawAssetRecursive(external)
          }
        }
      }
      for (const internal of internals) {
        for (const association of associations) {
          if (association.NodeId.Identifier === internal.nodeId.Identifier) {
            this.addInternal(internal, containerNode)
            drawAssetRecursive(internal)
          }
        }
      }
    }

    let i = 0
    const externals = [ // What goues outside the box
      ...assetObject.PowerSupplies,
      ...assetObject.Feeders,
      ...assetObject.Cables,
      ...assetObject.Accessories]
    const internals = [ // What goes inside the box
      ...assetObject.Servos,
      ...assetObject.MemoryDevices,
      ...assetObject.SubComponents,
      ...assetObject.Batteries,
      ...assetObject.Sensors]

    for (const controller of assetObject.Controllers) {
      this.createController(controller, i, assetObject.Controllers.length) // Create a controller graphic object

      const associations = controller.getRelations('association') // Check the connected assets

      drawAssetWithExternals(associations, controller) // Draw it

      for (const tool of assetObject.Tools) { // Draw the tool separately
        const drawnTools = {}
        for (const association of associations) { // But only the tools assocoated to the above controller
          if (association.NodeId.Identifier === tool.nodeId.Identifier &&
            !drawnTools[association.NodeId.Identifier]) {
            this.createTool(tool, controller)
            drawAssetRecursive(tool)
            drawnTools[association.NodeId.Identifier] = true
          }
        }
      }
      // this.assetGraphic.addExternal({ nodeId: 1, displayName: { text: 'Example Stacklight' } }, controller)

      i++
    }
  }

  createController (node, controllerNr, parts) {
    const rightPercent = 75
    // const nodeId = node.NodeId
    const height = 100 / parts
    if (!node.assetGraphicData) {
      node.assetGraphicData = {}
    }
    const mainbox = document.createElement('div')
    mainbox.classList.add('assetArea')
    mainbox.style.top = Math.round(controllerNr * height) + '%'
    mainbox.style.height = height + '%'
    this.container.appendChild(mainbox)

    const leftbox = document.createElement('div')
    leftbox.classList.add('assetArea')
    leftbox.innerText = ''
    leftbox.style.right = (100 - rightPercent) + '%'
    leftbox.style.height = '100%'
    mainbox.appendChild(leftbox)

    const rightbox = document.createElement('div')
    rightbox.classList.add('assetArea')
    rightbox.innerText = 'Tools'
    rightbox.style.left = rightPercent + '%'
    rightbox.style.height = '100%'
    mainbox.appendChild(rightbox)
    node.assetGraphicData.tools = rightbox
    rightbox.assetInternals = []

    return this.createAssetContainer(node, leftbox)
  }

  addInternal (node, containerNode) {
    this.addHorizontal(node, containerNode.assetGraphicData.internals)
  }

  addExternal (node, containerNode) {
    this.addHorizontal(node, containerNode.assetGraphicData.externals)
  }

  createTool (node, containerNode) {
    this.addVertical(node, containerNode.assetGraphicData.tools)
  }

  createAssetContainer (node, container) {
    if (!node.assetGraphicData) {
      node.assetGraphicData = {}
    }
    const asset = document.createElement('div')
    asset.classList.add('assetArea')
    asset.innerText = node.displayName
    asset.style.backgroundColor = 'brown'
    asset.style.left = '10%'
    asset.style.right = '10%'
    asset.style.top = '5%'
    asset.style.height = '40%'
    container.appendChild(asset)
    node.assetGraphicData.internals = asset
    asset.assetInternals = []

    const externals = document.createElement('div')
    externals.classList.add('assetArea')
    externals.style.top = '50%'
    externals.style.height = '50%'
    container.appendChild(externals)
    node.assetGraphicData.externals = externals
    externals.assetInternals = []
    return asset
  }

  addHorizontal (node, container) {
    const mainbox = document.createElement('div')
    mainbox.classList.add('assetBox')
    mainbox.innerText = node.displayName
    mainbox.style.top = '60%'
    mainbox.style.bottom = '10%'
    container.appendChild(mainbox)
    container.assetInternals.push(mainbox)
    const width = 100 / container.assetInternals.length
    let i = 0
    for (const internal of container.assetInternals) {
      internal.style.left = ((i++ * width) + (width / 10)) + '%'
      internal.style.width = (0.8 * width) + '%'
    }
    return mainbox
  }

  addVertical (node, container) {
    const mainbox = document.createElement('div')
    mainbox.classList.add('assetBox')
    mainbox.style.left = '10%'
    mainbox.style.right = '10%'
    container.appendChild(mainbox)
    container.assetInternals.push(mainbox)
    const height = 100 / container.assetInternals.length
    let i = 0
    for (const internal of container.assetInternals) {
      internal.style.top = ((i++ * height) + (height / 10)) + '%'
      internal.style.height = (0.8 * height) + '%'
    }
    this.createAssetContainer(node, mainbox)

    return mainbox
  }
}
