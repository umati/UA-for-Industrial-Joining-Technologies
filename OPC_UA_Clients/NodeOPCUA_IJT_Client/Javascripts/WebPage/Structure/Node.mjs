
class PartialNode {
  constructor (parent, graphicGenerator, socketHandler, makeGUI) {
    this.parent = parent
    this.graphicGenerator = graphicGenerator
    this.socketHandler = socketHandler
    this.makeGUI = makeGUI
    this.browseData = {}
  }

  /**
   * Use addressSpace.browseAndReadWithNodeId if only the Id is available
   * @param {*} response
   * @returns
   */
  GUIexplore (details = false) {
    return this.socketHandler.browsePromise(this.nodeId, details).then(
      () => {
        return new Promise((resolve) => {
          this.socketHandler.readPromise(this.nodeId).then(
            (response) => {
              resolve(response.node)
            })
        })
      })
  }

  read () {
    // console.log('SEND Read: '+this.nodeId)
    return new Promise((resolve) => {
      this.socketHandler.readPromise(this.nodeId).then(
        (response) => {
          resolve(response.node)
        })
    })
  }

  createGUINode () {
    if (this.graphicGenerator && this.graphicGenerator.generateGUINode) {
      if (!this.graphicRepresentation) {
        this.graphicRepresentation = this.graphicGenerator.generateGUINode(this)
      }
    }
  }

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
  constructor (parent, reference, socketHandler, graphicGenerator, makeGUI = true) {
    super(parent, graphicGenerator, socketHandler, makeGUI)
    for (const [key, value] of Object.entries(reference)) {
      this[key] = value
    }

    if (reference.browseName && this.makeGUI) {
      this.createGUINode()
    }
  }

  get associatedNodeId () {
    return this.nodeId
  }
}

export class Node extends PartialNode {
  constructor (parent, reference, socketHandler, graphicGenerator, makeGUI = true) {
    super(parent, graphicGenerator, socketHandler, makeGUI)
    this.relations = {}
    this.value = null
    this.addBrowseData(reference)
    if (this.makeGUI) {
      this.createGUINode()
    }
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

  setParent (parent) {
    if (this.graphicRepresentation &&
      this.graphicRepresentation.whole &&
      parent.graphicRepresentation &&
      this.graphicRepresentation.whole.parentElement !== parent.graphicRepresentation.container) {
      this.graphicGenerator.addChild(parent.graphicRepresentation, this.graphicRepresentation)
    }
  }
}
