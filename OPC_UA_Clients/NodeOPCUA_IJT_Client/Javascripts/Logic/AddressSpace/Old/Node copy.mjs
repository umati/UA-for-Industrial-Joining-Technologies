class PartialNode {
  constructor (parent, addressSpace, makeGUI) {
    this.parent = parent
    this.addressSpace = addressSpace
    this.graphicGenerator = addressSpace.graphicGenerator
    this.socketHandler = addressSpace.socketHandler
    this.makeGUI = makeGUI
    this.browseData = {}
  }

  get nodeId () {
    return this.browseData.nodeId
  }

  set nodeId (id) {
    this.browseData.nodeId = id
  }

  get browseName () {
    return this.browseData.browseName
  }

  set browseName (name) {
    this.browseData.browseName = name
  }

  get displayName () {
    return this.browseData.displayName
  }

  set displayName (name) {
    this.browseData.displayName = name
  }

  get typeDefinition () {
    if (this.browseData.typeDefinition) { // If a READ operation has been performed
      return this.browseData.typeDefinition
    } else { // Loop through the relation and find the hasType relation and return its NodeId
      const typeRelation = this.getRelations('hasType')[0]
      if (typeRelation) {
        return typeRelation.nodeId
      } else {
        return ''
      }
    }
  }

  set typeDefinition (def) {
    this.browseData.typeDefinition = def
  }

  get associatedNodeId () {
    return this.nodeId
  }

  /**
   * Use addressSpace.browseAndReadWithNodeId if only the Id is available
   * @param {*} response
   * @returns
   */
  browseAndRead (details = false) {
    return this.addressSpace.browseAndRead(this.nodeId, details)
  }

  read () {
    // console.log('SEND Read: '+this.nodeId)
    return this.addressSpace.read(this.nodeId)
  }

  // should be handled by caller
  /* createGUINode () {
    if (this.graphicGenerator && this.graphicGenerator.generateGUINode) {
      if (!this.graphicRepresentation) {
        this.graphicRepresentation = this.graphicGenerator.generateGUINode(this)
      }
    }
  } */

  scrollTo () {
    if (this.graphicRepresentation) {
      this.graphicGenerator.scrollTo(this.graphicRepresentation)
    }
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
}

export class Reference extends PartialNode {
  constructor (parent, reference, addressSpace, makeGUI = true) {
    super(parent, addressSpace, makeGUI)
    for (const [key, value] of Object.entries(reference)) {
      this[key] = value
    }

    if (reference.browseName && this.makeGUI) {
      this.createGUINode()
    }
  }
}

export class Node extends PartialNode {
  constructor (parent, reference, addressSpace, makeGUI = true) {
    super(parent, addressSpace, makeGUI)
    this.relations = {}
    this.value = null
    this.addBrowseData(reference)
    if (this.makeGUI) {
      this.createGUINode()
    }
  }

  get referenceTypeId () {
    return this.browseData.referenceTypeId
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

  addReadData (value) {
    this.hasBeenRead = true
    this.value = value
    if (this.browseData !== {}) {
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

  /* setParent (parent) {
    if (this.graphicRepresentation &&
      this.graphicRepresentation.whole &&
      parent.graphicRepresentation &&
      this.graphicRepresentation.whole.parentElement !== parent.graphicRepresentation.container) {
      this.graphicGenerator.addChild(parent.graphicRepresentation, this.graphicRepresentation)
    }
  } */
}

// SetParent createGUINode ScrollTo
