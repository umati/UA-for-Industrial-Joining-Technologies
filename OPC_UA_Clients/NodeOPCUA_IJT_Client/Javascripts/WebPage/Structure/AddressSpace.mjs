


class Reference {
    constructor(parent, reference, socketHandler, graphicGenerator) {
        this.parent = parent;
        for (const [key, value] of Object.entries(reference)) {
            this[key] = value;
        }
        this.graphicGenerator = graphicGenerator

        this.socketHandler = socketHandler;
        if (reference.browseName) {
            this.createGUIReference();
        }
    }

    get associatedNodeId() {
        return this.nodeId;
    }

    explore() {
        this.socketHandler.browse(this.nodeId, () => { this.socketHandler.read(this.nodeId, null) }, true);
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
    constructor(parent, reference, socketHandler, graphicGenerator) {
        this.parent = parent;
        this.relations = {};
        this.graphicGenerator = graphicGenerator
        this.value = null;
        this.browseData = {}
        this.socketHandler = socketHandler;
        this.addBrowseData(reference);
        this.createGUINode();

    }

    // using organizes and component
    getChild(browseName, callback) {
        let handleBrowsed = () => {
            let children = [...this.getRelations('component'), ...this.getRelations('organizes')];

            for (const child of children) {
                //console.log('getChild'+child.browseName.name);
                if (child.browseName.name == browseName) {
                    callback(child);
                    return;
                }
            }
            throw new Error(`Node ${this.browseName.name} does not contain a child named ${browseName}`)
        }
        if (this.explored) {
            handleBrowsed();
        } else {
            this.socketHandler.browse(this.nodeId, handleBrowsed, true);
        }

    }

    /*
    hasInterface(interfaceName) {
        this.explorePromise().then(
            (node) => {
                let children = node.getRelations('interface');

                for (const child of children) {
                    console.log('getFilteredChildren: ' + child.browseName.name);
                    if (child.browseName.name == interfaceName) {
                        callback(child);
                        return;
                    }
                }
            },
            function failed() { }
        )
    }*/

    addRelation(type, id, obj) {
        let row = this.relations[type];
        if (!row) {
            row = {};
        }
        row[id] = obj;
        this.relations[type] = row;
    }

    getRelation(type, nodeId) {
        let row = this.relations[type];
        if (!row) {
            return;
        }
        return row[nodeId];
    }

    getRelations(type) {
        let row = this.relations[type];
        if (!row) {
            return [];
        }
        return Object.values(row);
    }

    get nodeId() {
        return this.browseData.nodeId;
    }

    get browseName() {
        return this.browseData.browseName;
    }
    get displayName() {
        return this.browseData.displayName;
    }
    get referenceTypeId() {
        return this.browseData.referenceTypeId;
    }

    get typeDefinition() {
        return this.browseData.typeDefinition;
    }
/*
    explorePromise() {
        return new Promise((resolve, reject) => {
            if (this.explored) {
                return resolve(this);
            }
            this.socketHandler.browsePromise(this.nodeId, true).then(
                () => {
                    this.explored = true;
                    return new Promise((resolve2, reject2) => {
                        this.socketHandler.readPromise(this.nodeId).then(
                            () => {
                                resolve2(
                                    resolve(this)
                                );
                            }
                        )
                    })
                },
                function rejected() {
                    reject();
                }
            )
        });
    }*/

    explore(f) {
        this.socketHandler.browse(this.nodeId, () => {
            this.socketHandler.read(this.nodeId);
            if (f) {
                return f();
            }
        }, true);
        this.explored = true;
        //console.log('SEND Browse: '+this.nodeId);
    }

    read() {
        this.socketHandler.read(this.nodeId, null);
        //console.log('SEND Read: '+this.nodeId);
    }

    addReadData(value) {
        this.read = true;
        this.value = value;
        if (this.browseData != {}) {
            return true;
        }
        return false;
    }

    addBrowseData(input) {
        this.browsed = true;
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

    scrollTo() {
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
    constructor(socketHandler) {
        this.socketHandler = socketHandler;
        this.nodeMapping = {};
        this.objectFolder = null;
        this.selectedTighteningSystem = null;
    }

    /**
     * A promise to browse and read a node, given a nodeId
     * @param {*} nodeId 
     * @returns 
     */
    browseAndRead(nodeId) {
        return this.socketHandler.browsePromise(nodeId, true).then(
            (browsecall) => {
                 return new Promise((resolve, reject2) => {
                    this.socketHandler.readPromise(nodeId).then(
                        (response) => {
                            resolve(response.node);
                        }
                    )
            }
        )
    })}


    handleNamespaces(namespaces) {
        this.nsIJT = namespaces.indexOf("http://opcfoundation.org/UA/IJT/");
        this.nsMachinery = namespaces.indexOf("http://opcfoundation.org/UA/Machinery/");
        this.nsDI = namespaces.indexOf("http://opcfoundation.org/UA/DI/");
    }

    /**
     * Sets up root and the Object folder
     */
    initiate() {
        this.createNode({
            nodeId: 'ns=0;i=84',
            browseName: { name: 'Root' },
            displayName: { text: 'Root' },
            referenceTypeId: 'ns=0;i=35',
            typeDefinition: 'ns=0;i=61',
            nodeClass: 'Object'
        });
        this.socketHandler.browse('ns=0;i=85', () => { this.socketHandler.read('ns=0;i=85') }, true);
    }

    reset() {
        this.nodeMapping = {};
    }

    setGUIGenerator(graphicGenerator) {
        this.graphicGenerator = graphicGenerator;
    }

    // This is called whenever a node has been being browsed
    addNodeByBrowse(msg) {

        function findOrCreateNode(reference, parent, self, type = 'component') {
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

        let thisNode = findOrCreateNode({ 'nodeId': msg.nodeid }, null, this);


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
                        findOrCreateNode(reference, thisNode, this, 'organizes');
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

        if (thisNode.nodeId == 'ns=0;i=85') { // Setting up objectFolder
            this.objectFolder = thisNode;
            let tighteningSystems = this.getTighteningSystems();
            for (let ts of tighteningSystems) {
                ts.read();
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
        let node = this.nodeMapping[msg.nodeid];
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


    createNode(reference, parent) {
        let newNode = new Node(parent, reference, this.socketHandler, this.graphicGenerator);
        this.nodeMapping[newNode.nodeId] = newNode;
        return newNode;
    }

    createAssociation(reference, caller) {
        let newReference = new Reference(caller, reference, this.socketHandler, this.graphicGenerator);
        return newReference;
    }

    getTighteningSystems() {
        if (!this.objectFolder) {
            throw new Error('Root/Objects folder not found');
        }
        let organizes = this.objectFolder.getRelations('organizes');
        let tighteningSystems = [];
        for (let node of organizes) {
            //let a = findOrCreateNode(relation, objectFolder, self, 'organizes')
            if (node.typeDefinition == 'ns=4;i=1005') {
                tighteningSystems.push(node);
            }
        }
        return tighteningSystems;
    }

}