// import AddressSpaceTree from './AddressSpaceTree.mjs'
import ModelToHTML from './ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

const nodeClassColor = {
  Object: 'grey',
  Method: 'green',
  Variable: 'red'
}

/**
 * This class is a simple example of a graphical representation of address space
 */
export default class AddressSpaceGraphics extends ControlMessageSplitScreen {
  constructor (addressSpace) {
    super('Address Space', 'Address Space', 'Messages', 'subscribed')
    this.addressSpace = addressSpace
  }

  /**
   * initiateNodeTree creates the start of the nodetree on the left side of the screen
   */
  initiateNodeTree () {
    // Clean any old stuff
    this.controlArea.innerHTML = ''
    this.addressSpace.reset()

    // Subscribe to browse results to show in right column for debug purposes
    this.addressSpace.socketHandler.registerMandatory('browseresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      modelToHTML.display(msg.browseresult, `Browse ${msg.nodeid}:`)
    })

    // Subscribe to read results to show in right column for debug purposes
    this.addressSpace.socketHandler.registerMandatory('readresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      let shortId = msg.nodeid
      if (shortId.length > 30) {
        shortId = '...' + shortId.substring(shortId.length - 27, shortId.length)
      }
      modelToHTML.display(msg.dataValue.value.value, `Read ${shortId} (${msg.attribute}):`)
    })

    // Initially display the ROOT and toggle it open
    this.addressSpace.findOrLoadNode('ns=0;i=84').then((newNode) => {
      const rootArea = this.createGUINode(newNode) // Create the root node button
      this.toggleNodeContent(newNode, rootArea) // Show the content of the root
      rootArea.children[1].children[0].onclick() // Click on the first (The Objects) button
    })
  }

  /**
   * Create a new graphical representation of a node in context
   * @param {*} node the node that you want to get a graphical representation
   * @param {*} context Where do you want the new node
   * @returns a graphical representation of the node
   */
  createGUINode (node, context) {
    // Support function to replace a relation at the right position
    function ReplaceOldButtonArea (context, newNodeGUIComponent, newNodeId) {
      for (const child of context.children) {
        if (child.nodeId === newNodeId) {
          context.insertBefore(newNodeGUIComponent, child)
          context.removeChild(child)
          return
        }
      }
      context.appendChild(newNodeGUIComponent)
    } // END Support function

    if (!context) {
      context = this.controlArea
    }

    let name = 'undefined'
    if (node.browseName) {
      name = node.browseName
    }
    const buttonArea = document.createElement('div')
    buttonArea.style.margin = '0px 0px 0px 10px'
    buttonArea.nodeId = node.nodeId
    ReplaceOldButtonArea(context, buttonArea, node.nodeId)

    if (!node.browseButton) {
      const browse = document.createElement('button')
      browse.classList.add('buttonAreaStyle')
      browse.innerHTML = name
      browse.classList.add('invisButton')
      browse.classList.add('pointer')
      browse.classList.add('treeButton')
      browse.style.margin = '-5px 0px -5px -5px'
      browse.title = 'Browse this node from the server'
      browse.style.color = 'black'
      browse.buttonArea = buttonArea
      browse.onclick = () => { return this.toggleNodeContent(node, buttonArea) }

      buttonArea.appendChild(browse)
      node.browseButton = browse
    }
    return buttonArea
  }

  /**
   * When a node is browsed, a lot of the content is represented by relations rather than
   * actual variables. These are represented as a sort of temporal buttons that will clickCallback
   * when they are clicked
   * @param {*} relation the relation data
   * @param {*} context where should the relation graphical representation be placed
   * @param {*} clickCallback what should be done when the relation graphical representation is clicked
   * @returns a graphical representation of the relation
   */
  createRelation (relation, context, clickCallback) {
    const buttonArea = document.createElement('div')
    buttonArea.style.margin = '0px 0px 0px 10px'
    buttonArea.nodeId = relation.nodeId
    context.appendChild(buttonArea)

    const browse = document.createElement('button')
    browse.classList.add('buttonAreaStyle')
    browse.innerHTML = relation.browseName.name + '  [' + relation.referenceTypeName + ']'
    browse.callback = clickCallback
    browse.relation = relation
    browse.classList.add('invisButton')
    browse.classList.add('pointer')
    browse.classList.add('treeButton')
    browse.style.margin = '-5px 0px -5px -5px'
    browse.title = 'Browse this node from the server'
    browse.style.color = nodeClassColor[relation.nodeClass]

    browse.onclick = function () {
      this.callback()
    }

    buttonArea.appendChild(browse)
    return browse
  }

  /**
   * Recursively close down all children under a node
   * @param {*} area the graphical representation you want to close down
   */
  cleanse (area) {
    while (area.children.length > 1) {
      this.cleanse(area.children[1])
      area.removeChild(area.children[1])
    }
  }

  /**
   * What should happen when you click on a node.
   * If already open then close it down.
   * If closed, then display all the relations
   * @param {*} node The node that should be toggloed
   * @param {*} buttonArea The area where the result should go
   */
  toggleNodeContent (node, buttonArea) {
    if (buttonArea.children.length > 1) {
      this.cleanse(buttonArea)
    } else {
      for (const relation of node.getChildRelations()) {
        switch (relation.referenceTypeName) {
          case 'hasType': // skip the boring FolderTypes
            break
          default:
            this.createRelation(relation, buttonArea, x => this.convertRelationToNode(relation, buttonArea))
        }
      }
    }
  }

  /**
   * Governs how a relation should be converted to a node
   * @param {*} relation shall be translated into a node
   * @param {*} subscriberArea is where the result should be put
   */
  convertRelationToNode (relation, subscriberArea) {
    switch (relation.nodeClass) {
      case 'Method':

        break
      case 'Variable':
        this.addressSpace.findOrLoadNode(relation.nodeId).then((newNode) => {
        })
        break
      default:
        this.addressSpace.findOrLoadNode(relation.nodeId).then((newNode) => {
          const newArea = this.createGUINode(newNode, subscriberArea)
          this.toggleNodeContent(newNode, newArea)
        })
    }
  }
}
