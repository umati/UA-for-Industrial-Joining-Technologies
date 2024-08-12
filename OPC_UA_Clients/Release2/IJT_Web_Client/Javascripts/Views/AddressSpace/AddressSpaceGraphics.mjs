// import AddressSpaceTree from './AddressSpaceTree.mjs'
import ModelToHTML from './ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

const nodeClassColor = {
  'NodeClass.Object': 'grey',
  'NodeClass.Method': 'green',
  'NodeClass.Variable': 'red'
}

/**
 * This class is a simple example of a graphical representation of address space
 */
export default class AddressSpaceGraphics extends ControlMessageSplitScreen {
  constructor (addressSpace) {
    super('Address Space', 'Address Space', 'Messages', 'subscribed')
    this.addressSpace = addressSpace

    addressSpace.connectionManager.subscribe('connection', (setToTrue) => {
      if (setToTrue) {
        this.initiateNodeTree()
      }
    })
  }

  initiate () {
    this.messageDisplay('')
  }

  /**
   * initiateNodeTree creates the root of the nodetree on the left side of the screen
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
    this.addressSpace.socketHandler.registerMandatory('read', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      let shortId = msg.nodeid
      if (shortId.length > 30) {
        shortId = '...' + shortId.substring(shortId.length - 27, shortId.length)
      }
      modelToHTML.display(msg.value, `Read ${shortId} (${msg.command}):`)
    })

    // Initially display the ROOT and toggle it open
    this.addressSpace.connectionManager.subscribe('tighteningsystem', () => {
      this.addressSpace.findOrLoadNode('ns=0;i=84').then((newNode) => {
        const rootArea = this.createGUINode(newNode) // Create the root node button
        this.toggleNodeContent(newNode, rootArea) // Show the content of the root
        rootArea.children[1].children[0].onclick() // Click on the first (The Objects) button
      })
    })
  }

  /**
   * Create a new graphical representation of a node in context
   * @param {*} node the node that you want to get a graphical representation
   * @param {*} context Where do you want the new node
   * @returns a graphical representation of the node
   */
  createGUINode (node, context, relation) {
    // Support function to replace a relation at the right position
    function ReplaceOldButtonArea (context, newNodeGUIComponent, newNodeId) {
      for (const child of context.children) {
        if (child.nodeId?.Identifier === newNodeId.Identifier && child.nodeId?.NamespaceIndex === newNodeId.NamespaceIndex) {
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
    buttonArea.classList.add('buttonArea')
    buttonArea.nodeId = node.nodeId
    ReplaceOldButtonArea(context, buttonArea, node.nodeId)

    // if (node.relations hasProperty, EnumStrings)

    if (!node.browseButton) {
      const browse = document.createElement('button')
      browse.classList.add('buttonAreaStyle')
      browse.innerHTML = name
      browse.classList.add('invisButton')
      browse.classList.add('pointer')
      browse.classList.add('treeButton')
      browse.classList.add('treeButtonPlace')
      browse.title = 'Browse this node from the server'
      if (relation) {
        browse.style.color = nodeClassColor[relation.NodeClass_]
      }
      browse.buttonArea = buttonArea
      browse.onclick = () => {
        return this.toggleNodeContent(node, buttonArea)
      }

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
    buttonArea.nodeId = relation.NodeId
    context.appendChild(buttonArea)

    const browse = document.createElement('button')
    browse.classList.add('buttonAreaStyle')
    browse.innerHTML = relation.BrowseName.Name // + '  [' + relation.referenceTypeName + ']'
    browse.callback = clickCallback
    browse.relation = relation
    browse.classList.add('invisButton')
    browse.classList.add('pointer')
    browse.classList.add('treeButton')
    browse.style.margin = '-5px 0px -5px -5px'
    browse.title = 'Browse this node from the server'
    browse.style.color = nodeClassColor[relation.NodeClass_]

    browse.onclick = function () {
      this.callback()
    }
    if (relation.ReferenceTypeId.Identifier === '46') { // Why 47 in health
      clickCallback()
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
      const enumRelation = node.getNamedRelation('EnumStrings')

      if (enumRelation) {
        this.addressSpace.relationsToNodes([enumRelation]).then((enumNodeList) => {
          const nameList = enumNodeList[0].value
          const index = parseInt(this.nodeValueToText(node.data.value))
          const value = nameList[index]

          const area = buttonArea.children[0]
          area.innerText += ' = ' + value.Text + ' [' + index + ']'
          buttonArea.appendChild(area)
        })
        return
      }

      for (const relation of node.getChildRelations()) {
        switch (relation.referenceTypeName) {
          case 'hasTypeDefinition': // skip the boring FolderTypes
            break
          case 'hasNotifier': // skip the Notifiers
            break
          default:
            this.createRelation(relation, buttonArea, x => this.convertRelationToNode(relation, buttonArea))
        }
      }
    }
    if (buttonArea.children.length === 1 && node.data.value) {
      const value = buttonArea.children[0]
      value.innerText += ' = ' + this.nodeValueToText(node.data.value)
      buttonArea.appendChild(value)
    }
  }

  nodeValueToText (value) {
    if (!value && value === '{}') {
      return ''
    }
    if (Array.isArray(value)) {
      let result = ''
      for (const item of value) {
        result += this.nodeValueToText(item) + ' '
      }
      return result
    }
    if (value.Text) {
      return value.Text
    }
    if (value.DisplayName) {
      if (value.DisplayName.Text) {
        return value.DisplayName.Text
      } else {
        return ''
      }
    }
    if (value.value) {
      if (value.value.displayname) {
        return value.value.displayname.Text
      } else {
        throw new Error('value.value format error')
      }
    } else {
      return value
    }
  }

  /**
   * Governs how a relation should be converted to a node
   * @param {*} relation shall be translated into a node
   * @param {*} subscriberArea is where the result should be put
   */
  convertRelationToNode (relation, subscriberArea) {
    switch (relation.NodeClass_) {
      case 'NodeClass.Method':

        break
      case 'NodeClass.Variable':
        this.addressSpace.findOrLoadNode(relation.NodeId).then((newNode) => {
          const newArea = this.createGUINode(newNode, subscriberArea, relation)
          this.toggleNodeContent(newNode, newArea)
        })
        break
      case 'NodeClass.Object':
        this.addressSpace.findOrLoadNode(relation.NodeId).then((newNode) => {
          const newArea = this.createGUINode(newNode, subscriberArea, relation)
          this.toggleNodeContent(newNode, newArea)
        })
        break
      default:
        this.addressSpace.findOrLoadNode(relation.NodeId).then((newNode) => {
          const newArea = this.createGUINode(newNode, subscriberArea, relation)
          this.toggleNodeContent(newNode, newArea)
        })
    }
  }
}
