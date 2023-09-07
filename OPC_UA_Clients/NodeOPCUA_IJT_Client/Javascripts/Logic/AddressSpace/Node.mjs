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

class PartialNode {
  constructor (data) {
    this.data = data
    for (const x of data.relations) {
      x.referenceTypeName = typeMapping[x.referenceTypeId.substring(x.referenceTypeId.indexOf(';i=') + 3)].name
    }
  }

  get nodeId () {
    return this.data.nodeid
  }

  get nodeClass () {
    return this.data.nodeclass
  }

  get browseName () {
    return this.data.displayname.value.text
  }

  get displayName () {
    return this.data.displayname.value.text
  }

  getRelation (nodeId) {
    return Object.values(this.data.relations).find(
      x => nodeId === x.nodeId)
  }

  getNamedRelation (browseName) {
    return Object.values(this.data.relations).find(
      x => browseName === x.browseName.name)
  }

  getRelations (type) {
    return Object.values(this.data.relations).filter(
      x => type === x.referenceTypeName)
  }

  getChildRelations () {
    return Object.values(this.data.relations).filter(
      x => x.isForward)
  }

  getParentRelations () {
    return Object.values(this.data.relations).filter(
      (x) => { return (x.isForward === false) })
  }
}

export class Reference {
  constructor (data) {
    this.data = data
  }
}
export class Placeholder {
  constructor (data) {
    this.data = data
  }
}

export function NodeFactory (data) {
  switch (data.nodeclass.value) {
    case 1:
      return new ObjectNode(data)
    case 2:
      return new VariableNode(data)
    case 4:
      return new MethodNode(data)
    default:
      throw new Error('NodeFactory trying to create unknown type of NodeClass')
  }
}
class ObjectNode extends PartialNode {
  constructor (data) {
    super(data)
    this.a = 1
  }
}

class VariableNode extends PartialNode {
  constructor (data) {
    super(data)
    this.a = 1
  }
}

class MethodNode extends PartialNode {
  constructor (data) {
    super(data)
    this.a = 1
  }

  get referenceTypeId () {
    return this.browseData.referenceTypeId
  }

  // using organizes and component
  getChild (browseName, callback) {

  }

  addRelation (type, id, obj) {

  }

  getRelation (type, nodeId) {

  }

  getRelations (type) {

  }

  getNamedRelation (type, browseName) {

  }

  addReadData (value) {
  }

  isComplete () {

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
