import { Node, Reference } from './Node.mjs'

const typeMapping = {
  0: { name: 'error' },
  61: { name: 'relation' },
  40: { name: 'hasType' },
  46: { name: 'hasProperty' },
  35: { name: 'organizes' },
  47: { name: 'component', color: 'black' },
  17603: { name: 'hasInterface', color: 'green' },
  17604: { name: 'hasAddin', color: 'brown' },
  24137: { name: 'association', color: 'grey' }
}

export default class AddressSpace {
  constructor (socketHandler) {
    this.socketHandler = socketHandler
    this.nodeMapping = {}
    this.objectFolder = null
    this.selectedTighteningSystem = null
    this.typeMapping = typeMapping
  }

  /**
   * This is called whenever a node has been being browsed
   * @param {*} msg The message from the NodeOPCUA_IJT_Client
   * @returns the node
   */
  addNodeByBrowse (msg) {
    const makeGUI = msg.details
    const thisNode = this.findOrCreateNode({ nodeId: msg.nodeid }, null, null, makeGUI)
    thisNode.references = msg.browseresult.references
    let componentOf = null
    let organizedBy = null

    for (const reference of msg.browseresult.references) {
      const type = reference.referenceTypeId.split('=').pop()
      if (reference.isForward) {
        this.findOrCreateNode(reference, thisNode, typeMapping[type].name, makeGUI)
      } else { // upwards references
        switch (type) {
          case ('35'): // OrganizedBy
            if (!organizedBy) {
              organizedBy = reference
            }
            break
          case ('47'): // ComponentOf
            componentOf = this.makeParentAndConnect(reference, thisNode, makeGUI)
            break
        }
      }
    }

    if (thisNode.nodeId === 'ns=0;i=85') { // Setting up objectFolder
      this.objectFolder = thisNode
      const tighteningSystems = this.getTighteningSystems()
      for (const ts of tighteningSystems) {
        ts.read().then(
          () => {})
      }
    }

    // Prioritize the component relation, but if no parent componentowner exist, use organizedBy reference instead
    if (!componentOf && organizedBy) {
      this.makeParentAndConnect(organizedBy, thisNode, makeGUI)
    }

    return thisNode
  }

  /**
   * Core function theat either finds an already created Node or create a new if none exists
   * @param {*} reference the type of reference the relation have
   * @param {*} parent the parent node in the hierarhy
   * @param {*} type the type of the component (as a string name)
   * @param {*} makeGUI Should this generate a representation in the structure view
   * @returns a node
   */
  findOrCreateNode (reference, parent, type = 'component', makeGUI) {
    let returnNode
    let referencedNode = this.nodeMapping[reference.nodeId]
    if (type === 'association') {
      referencedNode = parent.getRelation(type, reference.nodeId)
    }
    if (referencedNode) {
      if (referencedNode.browseName && !referencedNode.makeGUI && makeGUI) {
        referencedNode.parent = parent
        referencedNode.createGUINode()
      }
      returnNode = referencedNode
      returnNode.addBrowseData(reference)
    } else {
      if (type === 'association') {
        returnNode = this.createAssociation(reference, parent, makeGUI)
      } else {
        returnNode = this.createNode(reference, parent, makeGUI)
      }
    }
    if (parent) {
      parent.addRelation(type, reference.nodeId, returnNode)
    }
    returnNode.scrollTo()
    return returnNode
  }

  /**
   * Core function that creates a parent if none exists and creates the current node to it
   * @param {*} reference the reference data type
   * @param {*} thisNode the current node
   * @param {*} makeGUI Should this generate a representation in the structure view
   * @returns a reference
   */
  makeParentAndConnect (reference, thisNode, makeGUI) {
    let parent = this.nodeMapping[reference.nodeId]
    if (parent) {
      parent.addBrowseData(reference)
      thisNode.setParent(parent)
      if (!thisNode.browseName) {
        parent.GUIexplore(makeGUI) // Forcing parent to get this node's name
      }
    } else {
      parent = this.createNode(reference)
      parent.addRelation('component', thisNode.nodeId, thisNode)
      parent.GUIexplore(makeGUI)
      thisNode.setParent(parent)
    }
    return parent
  }

  handleNamespaces (namespaces) {
    this.nsIJT = namespaces.indexOf('http://opcfoundation.org/UA/IJT/')
    this.nsMachinery = namespaces.indexOf('http://opcfoundation.org/UA/Machinery/')
    this.nsDI = namespaces.indexOf('http://opcfoundation.org/UA/DI/')
    this.nsIJTApplication = namespaces.indexOf('http://www.atlascopco.com/TighteningApplication/')
  }

  /**
   * Sets up root and the Object folder
   */
  initiate () {
    this.browseAndReadWithNodeId('ns=0;i=84', true).then() // Get root
    this.browseAndReadWithNodeId('ns=0;i=85', true).then() // Get Objects
  }

  reset () {
    this.nodeMapping = {}
  }

  setGUIGenerator (graphicGenerator) {
    this.graphicGenerator = graphicGenerator
  }

  /**
   * A promise to browse and read a node, given only a nodeId
   * @param {*} nodeId
   * @returns the node
   */
  browseAndReadWithNodeId (nodeId, details = false) {
    let referencedNode = this.nodeMapping[nodeId]
    if (!referencedNode) {
      referencedNode = this.createNode({ nodeId }, null, details)
    }
    return referencedNode.GUIexplore(details)
  }

  // This is called whenever a node has been being read
  addNodeByRead (msg) {
    if (!msg.dataValue.value) {
      return
    }
    const node = this.nodeMapping[msg.nodeid]
    if (node) {
      node.addReadData(msg.dataValue.value)
    }
    return node
  }

  toString (nodeId) {
    const node = this.nodeMapping[nodeId]
    if (!node) {
      return nodeId + ' has not been browsed yet'
    }
    return node.toString()
  }

  createNode (reference, parent, makeGUI) {
    const newNode = new Node(parent, reference, this.socketHandler, this.graphicGenerator, makeGUI)
    this.nodeMapping[newNode.nodeId] = newNode
    return newNode
  }

  createAssociation (reference, caller, makeGUI) {
    return new Reference(caller, reference, this.socketHandler, this.graphicGenerator, makeGUI)
  }

  getTighteningSystems () {
    if (!this.objectFolder) {
      throw new Error('Root/Objects folder not found')
    }
    const tighteningSystems = []
    for (const node of this.objectFolder.getRelations('organizes')) {
      // let a = findOrCreateNode(relation, objectFolder, self, 'organizes')
      if (node.typeDefinition === 'ns=4;i=1005') {
        tighteningSystems.push(node)
      }
    }
    return tighteningSystems
  }

  /**
   * note that this normally only returns the call message, not the actual node as might be expected.
   * The nodeId needs to be extracted from the message.
   * @param {*} path The path that should be traversed
   * @param {*} startFolderId The starting node
   * @returns the call message
   */
  findFolder (path, startFolderId) {
    if (!startFolderId) {
      const tgtSystem = this.getTighteningSystems()
      if (tgtSystem.length > 0) {
        startFolderId = tgtSystem[0].nodeId
      } else {
        throw new Error('Failed to find starting folder')
      }
    }
    return this.socketHandler.pathtoidPromise(startFolderId, path)
  }
}
