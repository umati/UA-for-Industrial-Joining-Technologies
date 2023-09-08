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

  getChildRelations (type) {
    return Object.values(this.data.relations).filter(
      x => { return x.isForward && (!type || type === x.referenceTypeName) })
  }

  getParentRelations () {
    return Object.values(this.data.relations).filter(
      (x) => { return (x.isForward === false) })
  }

  getTypeDefinitionRelations (typeDefinition) {
    return Object.values(this.data.relations).filter(
      (x) => { return (x.typeDefinition === typeDefinition) })
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
    if (data?.displayname?.value?.text) {
      this.aname = data.displayname.value.text + ' Object' // To simplify debugging
    }
  }
}

class VariableNode extends PartialNode {
  constructor (data) {
    super(data)
    if (data?.displayname?.value?.text) {
      this.aname = data.displayname.value.text + 'Variable' // To simplify debugging
    }
  }
}

class MethodNode extends PartialNode {
  constructor (data) {
    super(data)
    if (data?.displayname?.value?.text) {
      this.aname = data.displayname.value.text + ' Method' // To simplify debugging
    }
  }
}
