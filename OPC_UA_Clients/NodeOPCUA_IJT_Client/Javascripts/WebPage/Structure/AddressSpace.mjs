

class Reference {
    constructor(parent, reference, socket, graphicGenerator) {
        this.parent = parent;
        for (const [key, value] of Object.entries(reference)) {
            this[key] = value;
        }
        this.graphicGenerator = graphicGenerator

        this.socket = socket;
        if (reference.browseName) {
            this.createGUIReference();
        }
    }

    explore() {
        this.socket.emit('browse', this.nodeId, 'read', true);
    }
    createGUIReference() {
        if (this.graphicGenerator && this.graphicGenerator.generateGUIReference) {
            if (!this.graphicRepresentation) {
                this.graphicRepresentation = this.graphicGenerator.generateGUINode(this);
            }
        }
    }
}
class Node {
    constructor(parent, reference, socket, graphicGenerator) {
        this.parent = parent;
        this.relations={};
        this.graphicGenerator = graphicGenerator
        this.value = null;
        this.browseData = {}
        this.socket = socket;
        this.addBrowseData(reference);
        this.createGUINode();

    }

    addRelation(type, id, obj) {
        let row = this.relations[type];
        if (!row) {
            row={};
        }
        row[id]=obj;
        this.relations[type]=row;
    }

    getRelation(type, nodeId) {
        let row = this.relations[type];
        if (!row) {
            return;
        }
        return row[nodeId];
    }

    get nodeId() {
        return this.browseData.nodeId;
    }

    get browseName() {
        return this.browseData.browseName;
    }
    get referenceTypeId() {
        return this.browseData.referenceTypeId;
    }

    get typeDefinition() {
        return this.browseData.typeDefinition;
    }

    explore() {
        this.socket.emit('browse', this.nodeId, 'read', true);
        //console.log('SEND Browse: '+this.nodeId);
    }

    read() {
        this.socket.emit('read item', this.nodeId);
        //console.log('SEND Read: '+this.nodeId);
    }

    addReadData(value) {
        this.value = value;
        if (this.browseData != {}) {
            return true;
        }
        return false;
    }

    addBrowseData(input) {
        for (const [key, value] of Object.entries(input)) {
            this.browseData[key] = value;
        }
        if (this.browseName && this.graphicRepresentation) {
            this.graphicRepresentation.button.innerText = this.browseName.name;
        }
        if (this.value) {
            return true;
        }
        return false;
    }

    isComplete() {
        if (this.value && this.browseData != {}) {
            return true;
        }
        else {
            return false;
        }
    }

    setParent(parent) {
        if (this.graphicRepresentation.whole.parentElement != parent.graphicRepresentation.container) {
            this.graphicGenerator.addChild(parent.graphicRepresentation, this.graphicRepresentation);
        }
    }

    scrollTo(){
        if (this.graphicRepresentation) {
            this.graphicGenerator.scrollTo(this.graphicRepresentation);
        }
    }

    createGUINode() {
        if (this.graphicGenerator && this.graphicGenerator.generateGUINode) {
            if (!this.graphicRepresentation) {
                this.graphicRepresentation = this.graphicGenerator.generateGUINode(this);
            }
        }
    }

}

export default class AddressSpace {
    constructor(socket) {
        this.socket = socket;
        this.nodeMapping = {};
        this.tighteningSystems = [];

    }

    reset() {
        this.nodeMapping = {};
    }

    setGUIGenerator(graphicGenerator) {
        this.graphicGenerator = graphicGenerator;
    }
    // This is called whenever a node has been being browsed
    addNodeByBrowse(msg) {

        function findOrCreateNode(reference, parent, self, type='component') {
            let returnNode;
            let referencedNode = self.nodeMapping[reference.nodeId];
            if (referencedNode) {
                returnNode = referencedNode;
                returnNode.addBrowseData(reference);
            } else {
                returnNode = self.createNode(reference, parent);
                if (parent) {
                    parent.addRelation(type, reference.nodeId, returnNode);
                }
            }
            returnNode.scrollTo();
            return returnNode;
        }

        function findOrCreateAssociation(reference, parent, self) {
            let returnNode;
            let referencedNode = parent.getRelation('association', reference.nodeId);
            if (referencedNode) {
                returnNode = referencedNode;
            } else {
                returnNode = self.createAssociation(reference, thisNode);
                parent.addRelation('association', reference.nodeId, returnNode);
            }
            return returnNode;
        }

        function makeParentAndConnect(reference, thisNode, self) {
            let parent = self.nodeMapping[reference.nodeId];
            if (parent) {
                parent.addBrowseData(reference);
                thisNode.setParent(parent);
                if (!thisNode.browseName) {
                    parent.explore(); // Forcing parent to get this node's name
                }
            } else {
                parent = self.createNode(reference);
                parent.addRelation('component', thisNode.nodeId, thisNode);
                parent.explore();
                thisNode.setParent(parent);
            }
            return parent;
        }

        let thisNode = findOrCreateNode({ 'nodeId': msg.callernodeid }, null, this);

        thisNode.references = msg.browseresult.references;

        let componentOf = null;
        let organizedBy = null;

        for (let reference of msg.browseresult.references) {
            let type = reference.referenceTypeId.split('=').pop();
            switch (type) {
                case ('61'): // Hastype?????
                    findOrCreateNode(reference, thisNode, this, 'relation?')
                    break;
                case ('40'): // HasTypeDefinition
                    findOrCreateNode(reference, thisNode, this, 'hasType')
                    break;
                case ('46'): // HasProperty
                    findOrCreateNode(reference, thisNode, this, 'hasProperty')
                    break;
                case ('35'): //Organizes/OrganizedBy
                    if (reference.isForward) {
                        findOrCreateNode(reference, thisNode, this, 'Organizes');
                    } else {
                        if (!organizedBy) {
                            organizedBy = reference;
                        }
                    }
                    break;
                case ('47'): // Component/ComponentOf
                    if (reference.isForward) {
                        findOrCreateNode(reference, thisNode, this);
                    } else {
                        componentOf = makeParentAndConnect(reference, thisNode, this)
                    }
                    break;
                case '17603': // HasInterface
                findOrCreateNode(reference, thisNode, this, 'hasInterface')
                    break;
                case '17604': // HasAddin
                
                findOrCreateNode(reference, thisNode, this, 'hasAddin')
                    break;
                case '24137': // AssociatedWith
                    let newReferenceId = findOrCreateAssociation(reference, thisNode, this)
                    break;
                default:
                    alert('Unhandled type in reference of node:' + type)
            }
        }
        // Prioritize the component relation, but if no parent componentowner exist, use organizedBy reference instead
        if (!componentOf && organizedBy) {
            makeParentAndConnect(organizedBy, thisNode, this)
        }

        return thisNode;
    }

    setParent(parent, child) {
        child.setParent(parent)
    }

    // This is called whenever a node has been being read
    addNodeByRead(msg) {
        if (!msg.dataValue.value) {
            return;
        }
        let node = this.nodeMapping[msg.path];
        if (node) {
            node.addReadData(msg.dataValue.value);
        }
        return node;

    }

    // This is called whenever a node has been being read
    getNodeParentId(references) {
        for (let reference of references) {
            if (reference.isForward == false && reference.referenceTypeId == 'ns=0;i=47') {
                return reference.nodeId;
            }
        }
    }

    toString(nodeId) {
        let node = this.nodeMapping[nodeId];
        if (!node) {
            return nodeId + ' has not been browsed yet';
        }
        return node.toString();
    }

    getTighteningSystems() {
        return this.tighteningSystems;
    }

    createNode(reference, parent) {
        let newNode = new Node(parent, reference, this.socket, this.graphicGenerator);
        this.nodeMapping[newNode.nodeId] = newNode;
        return newNode;
    }

    createAssociation(reference, caller) {
        let newReference = new Reference(caller, reference, this.socket, this.graphicGenerator);
        return newReference;
    }
}