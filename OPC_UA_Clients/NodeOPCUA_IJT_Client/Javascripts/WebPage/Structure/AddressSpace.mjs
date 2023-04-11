
class Reference {
  constructor (parent, reference, socketHandler, graphicGenerator) {
    this.parent = parent
    for (const [key, value] of Object.entries(reference)) {
      this[key] = value
    }
    this.graphicGenerator = graphicGenerator

    this.socketHandler = socketHandler
    if (reference.browseName) {
      this.createGUIReference()
    }
  }

  get associatedNodeId () {
    return this.nodeId
  }

  explore () {
    this.socketHandler.browse(this.nodeId, () => { this.socketHandler.read(this.nodeId, null) }, true)
  }

  createGUIReference () {
    if (this.graphicGenerator && this.graphicGenerator.generateGUIReference) {
      if (!this.graphicRepresentation) {
        this.graphicRepresentation = this.graphicGenerator.generateGUINode(this)
      }
    }
  }
}
class Node {
  constructor (parent, reference, socketHandler, graphicGenerator) {
    this.parent = parent
    this.relations = {}
    this.graphicGenerator = graphicGenerator
    this.value = null
    this.browseData = {}
    this.socketHandler = socketHandler
    this.addBrowseData(reference)
    this.createGUINode()
  }

  // using organizes and component
  getChild (browseName, callback) {
    const handleBrowsed = () => {
      const children = [...this.getRelations('component'), ...this.getRelations('organizes')]

      for (const child of children) {
        // console.log('getChild'+child.browseName.name);
        if (child.browseName.name === browseName) {
          callback(child)
          return
        }
      }
      throw new Error(`Node ${this.browseName.name} does not contain a child named ${browseName}`)
    }
    if (this.explored) {
      handleBrowsed()
    } else {
      this.socketHandler.browse(this.nodeId, handleBrowsed, true)
    }
  }

  addRelation (type, id, obj) {
    let row = this.relations[type]
    if (!row) {
      row = {}
    }
    row[id] = obj
    this.relations[type] = row
  }

  getRelation (type, nodeId) {
    const row = this.relations[type]
    if (!row) {
      return
    }
    return row[nodeId]
  }

  getRelations (type) {
    const row = this.relations[type]
    if (!row) {
      return []
    }
    return Object.values(row)
  }

  getNamedRelation (type, browseName) {
    const row = this.relations[type]
    if (!row) {
      return []
    }
    const resNode = Object.values(row).find(
      x => browseName === x.browseName.name)
    return resNode
  }

  get nodeId () {
    return this.browseData.nodeId
  }

  get browseName () {
    return this.browseData.browseName
  }

  get displayName () {
    return this.browseData.displayName
  }

  get referenceTypeId () {
    return this.browseData.referenceTypeId
  }

  get typeDefinition () {
    return this.browseData.typeDefinition
  }

  explore (f) {
    this.socketHandler.browse(this.nodeId, () => {
      this.socketHandler.read(this.nodeId)
      if (f) {
        return f()
      }
    }, true)
    this.explored = true
    // console.log('SEND Browse: '+this.nodeId)
  }

  read () {
    this.socketHandler.read(this.nodeId, null)
    // console.log('SEND Read: '+this.nodeId)
  }

  addReadData (value) {
    this.read = true
    this.value = value
    if (this.browseData !== {}) {
      return true
    }
    return false
  }

  addBrowseData (input) {
    this.browsed = true
    for (const [key, value] of Object.entries(input)) {
      this.browseData[key] = value
    }
    if (this.browseName && this.graphicRepresentation) {
      this.graphicRepresentation.button.innerText = this.browseName.name
    }
    if (this.value) {
      return true
    }
    return false
  }

  isComplete () {
    if (this.value && this.browseData !== {}) {
      return true
    } else {
      return false
    }
  }

  setParent (parent) {
    if (this.graphicRepresentation.whole.parentElement !== parent.graphicRepresentation.container) {
      this.graphicGenerator.addChild(parent.graphicRepresentation, this.graphicRepresentation)
    }
  }

  scrollTo () {
    if (this.graphicRepresentation) {
      this.graphicGenerator.scrollTo(this.graphicRepresentation)
    }
  }

  createGUINode () {
    if (this.graphicGenerator && this.graphicGenerator.generateGUINode) {
      if (!this.graphicRepresentation) {
        this.graphicRepresentation = this.graphicGenerator.generateGUINode(this)
      }
    }
  }
}

export default class AddressSpace {
  constructor (socketHandler) {
    this.socketHandler = socketHandler
    this.nodeMapping = {}
    this.objectFolder = null
    this.selectedTighteningSystem = null
  }

  /**
   * A promise to browse and read a node, given a nodeId
   * @param {*} nodeId
   * @returns
   */
  browseAndRead (nodeId) {
    return this.socketHandler.browsePromise(nodeId, true).then(
      (browsecall) => {
        return new Promise((resolve) => {
          this.socketHandler.readPromise(nodeId).then(
            (response) => {
              resolve(response.node)
            }
          )
        }
        )
      })
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
    this.createNode({
      nodeId: 'ns=0;i=84',
      browseName: { name: 'Root' },
      displayName: { text: 'Root' },
      referenceTypeId: 'ns=0;i=35',
      typeDefinition: 'ns=0;i=61',
      nodeClass: 'Object'
    })
    this.socketHandler.browse('ns=0;i=85', () => { this.socketHandler.read('ns=0;i=85') }, true)
  }

  reset () {
    this.nodeMapping = {}
  }

  setGUIGenerator (graphicGenerator) {
    this.graphicGenerator = graphicGenerator
  }

  // This is called whenever a node has been being browsed
  addNodeByBrowse (msg) {
    function findOrCreateNode (reference, parent, self, type = 'component') {
      let returnNode
      const referencedNode = self.nodeMapping[reference.nodeId]
      if (referencedNode) {
        returnNode = referencedNode
        returnNode.addBrowseData(reference)
      } else {
        returnNode = self.createNode(reference, parent)
        if (parent) {
          parent.addRelation(type, reference.nodeId, returnNode)
        }
      }
      returnNode.scrollTo()
      return returnNode
    }

    function findOrCreateAssociation (reference, parent, self) {
      let returnNode
      const referencedNode = parent.getRelation('association', reference.nodeId)
      if (referencedNode) {
        returnNode = referencedNode
      } else {
        returnNode = self.createAssociation(reference, thisNode)
        parent.addRelation('association', reference.nodeId, returnNode)
      }
      return returnNode
    }

    function makeParentAndConnect (reference, thisNode, self) {
      let parent = self.nodeMapping[reference.nodeId]
      if (parent) {
        parent.addBrowseData(reference)
        thisNode.setParent(parent)
        if (!thisNode.browseName) {
          parent.explore() // Forcing parent to get this node's name
        }
      } else {
        parent = self.createNode(reference)
        parent.addRelation('component', thisNode.nodeId, thisNode)
        parent.explore()
        thisNode.setParent(parent)
      }
      return parent
    }

    const thisNode = findOrCreateNode({ nodeId: msg.nodeid }, null, this)

    thisNode.references = msg.browseresult.references

    let componentOf = null
    let organizedBy = null

    for (const reference of msg.browseresult.references) {
      const type = reference.referenceTypeId.split('=').pop()
      switch (type) {
        case ('61'): // Hastype?????
          findOrCreateNode(reference, thisNode, this, 'relation?')
          break
        case ('40'): // HasTypeDefinition
          findOrCreateNode(reference, thisNode, this, 'hasType')
          break
        case ('46'): // HasProperty
          findOrCreateNode(reference, thisNode, this, 'hasProperty')
          break
        case ('35'): // Organizes/OrganizedBy
          if (reference.isForward) {
            findOrCreateNode(reference, thisNode, this, 'organizes')
          } else {
            if (!organizedBy) {
              organizedBy = reference
            }
          }
          break
        case ('47'): // Component/ComponentOf
          if (reference.isForward) {
            findOrCreateNode(reference, thisNode, this)
          } else {
            componentOf = makeParentAndConnect(reference, thisNode, this)
          }
          break
        case '17603': // HasInterface
          findOrCreateNode(reference, thisNode, this, 'hasInterface')
          break
        case '17604': // HasAddin

          findOrCreateNode(reference, thisNode, this, 'hasAddin')
          break
        case '24137': // AssociatedWith
          findOrCreateAssociation(reference, thisNode, this)
          break
        default:
          alert('Unhandled type in reference of node:' + type)
      }
    }

    if (thisNode.nodeId === 'ns=0;i=85') { // Setting up objectFolder
      this.objectFolder = thisNode
      const tighteningSystems = this.getTighteningSystems()
      for (const ts of tighteningSystems) {
        ts.read()
      }
    }

    // Prioritize the component relation, but if no parent componentowner exist, use organizedBy reference instead
    if (!componentOf && organizedBy) {
      makeParentAndConnect(organizedBy, thisNode, this)
    }

    return thisNode
  }

  setParent (parent, child) {
    child.setParent(parent)
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

  // This is called whenever a node has been being read
  getNodeParentId (references) {
    for (const reference of references) {
      if (reference.isForward === false && reference.referenceTypeId === 'ns=0;i=47') {
        return reference.nodeId
      }
    }
  }

  toString (nodeId) {
    const node = this.nodeMapping[nodeId]
    if (!node) {
      return nodeId + ' has not been browsed yet'
    }
    return node.toString()
  }

  createNode (reference, parent) {
    const newNode = new Node(parent, reference, this.socketHandler, this.graphicGenerator)
    this.nodeMapping[newNode.nodeId] = newNode
    return newNode
  }

  createAssociation (reference, caller) {
    return new Reference(caller, reference, this.socketHandler, this.graphicGenerator)
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

    /*
    return new Promise((resolve) => {
      this.socketHandler.pathtoidPromise(startFolderId, path).then(
        (msg) => {
          resolve(msg.message.nodeid)
        },
        (err) => {
          throw new Error(`Failed to find node ${startFolderId} when looking for path ${path}. ${err}`)
        }
      )
    }) */
  }
}
