
// The purpose of this class is to generate a tree of the things that can be
// clicked in order to subscribe or read data

export default class TreeDisplayer {

    constructor(structure) {
        this.generatedObjectFolder = structure.leftArea;
        this.structure = structure;
        this.generatedObjectFolder.innerHTML = '';
        this.addressSpace = structure.addressSpace;
        this.socket = structure.socket;
        this.mapping = {};
    }


    generateGUINode(node) {
        let container;
        if (!node.parent) {
            container = this.generatedObjectFolder;
        } else {
            container = this.mapping[node.parent.nodeId];
        }
       
        let innerContainer = this.generateGUINodeSupport(node, container);
        
        return innerContainer;
    }

    scrollTo(innerContainer) {
        if (innerContainer && innerContainer.whole) {
            innerContainer.whole.scrollIntoView({behavior: "smooth", block: "end", inline: "nearest"});
        }
    }

    generateGUINodeSupport(node, context) {
        let nodeId = node.nodeId;
        let name = 'undefined';
        if (node.browseName && node.browseName.name) {
            name=node.browseName.name;
        }
        let browse = document.createElement('button');

        let type = 0;
        if(node.referenceTypeId) {
            type = node.referenceTypeId.split('=').pop();
        }

        if (type == '40') {
            if(node && node.parent && node.parent.readButton) {
                node.parent.typeName=node.browseName.name;
                node.parent.readButton.title+='\nType: '+node.browseName.name;
                return;
            }
        }

        var buttonArea = document.createElement('div');
        context.appendChild(buttonArea);
        browse.classList.add('buttonAreaStyle');

        browse.innerHTML = '+';
        browse.myNodeId = nodeId;
        browse.socket = this.socket;
        browse.addressSpace = this.addressSpace;
        browse.node = node;
        browse.classList.add('invisButton');
        browse.classList.add('updownpointer');
        browse.classList.add('treeButton');
        browse.style.margin = '-5px 0px -5px -5px';
        browse.title = 'Browse this node from the server';
      
        browse.onclick = function () {
            if (this.myContainer.style.display == 'block' && this.innerHTML != '+') { // Close
                this.myContainer.style.display = 'none';
                this.innerHTML = '+';
            } else {                                        // Open
                this.node.explore();
                this.myContainer.style.display = 'block';
                this.innerHTML = '-';
            }
        };
        buttonArea.appendChild(browse);
        var read = document.createElement('button');
        node.readButton=read;
        read.innerHTML = name;
        read.node = node;
        read.socket = this.socket;
        read.structure = this.structure;
        read.classList.add('invisButton');
        read.classList.add('selectpointer');
        read.classList.add('treeButton');
        read.style.margin = '-5px'
      
        read.onclick = function () {
            if(this.node.read) {
            this.node.explore();
            if(this.innerHTML != '+') {
                this.myContainer.style.display = 'none';
            }
            } else {
                this.node.explore();
            }
        };

        switch (type) {
            case '47': // HasComponent
                read.style.color = 'black';
                read.title='Role: Component';
                break;
           /* case '40': // HasTypeDefinition
                //read.style.color = 'blue';
                //read.title='Role: HasTypeDefinition';
                if(node && node.parent && node.parent.readButton) {
                node.parent.readButton.title+='\nType: '+node.browseName.name;
                }
                break; */
            case '17603': // HasInterface
                read.style.color = 'green';
                read.title='Role: Interface';
                break;
            case '17604': // HasAddin
                read.style.color = 'brown';
                read.title='Role: Addin';
                break;
            case '24137': // AssociatedWith
                read.style.color = 'grey';
                read.title='Role: Association';
                break;
            default:
                read.style.color = 'black';
        }
        buttonArea.appendChild(read);

        var container = document.createElement('div');
        container.classList.add('treeDiv');
        container.style.display = 'block';
        
        //container.innerText='node-area: '+name;
        buttonArea.appendChild(container);
        browse.myContainer = container;
        read.myContainer = container;
        this.mapping[node.nodeId] = container;

        return {'whole':buttonArea, 
        'container':container, 
        'button':read, 
        'browse':browse};
    }

    addChild(parent, child) {
        parent.container.appendChild(child.whole);
        parent.browse.innerHTML = '-';
        parent.container.style.display = 'block';
        child.container.style.display = 'block';
        child.browse.innerHTML = '-';
    }

    generateGUIReference(reference) {
        let container;
        if (!reference.parent) {
            container = this.generatedObjectFolder;
        } else {
            container = this.mapping[reference.parent.nodeId];
        }
       
        this.generateGUIReferenceSupport(reference, container)
        return container;
    }

    generateGUIReferenceSupport(reference, context) {
        let nodeId = reference.nodeId;
        let name = reference.browseName.name;
        let browse = document.createElement('button');

        let type =reference.referenceTypeId.split('=').pop();

        var buttonArea = document.createElement('div');
        context.appendChild(buttonArea);
        browse.classList.add('buttonAreaStyle');

        browse.innerHTML = name;
        browse.myNodeId = nodeId;
        browse.socket = this.socket;
        browse.addressSpace = this.addressSpace;
        browse.reference = reference;
        browse.classList.add('invisButton');
        browse.classList.add('updownpointer');
        browse.classList.add('treeButton');
        browse.style.margin = '-5px 0px -5px -5px';
        browse.title = 'Browse this node from the server';
        
        browse.onclick = function () {
                this.reference.explore();
        };
        buttonArea.appendChild(browse);

        var container = document.createElement('div');
        container.classList.add('treeDiv');
        buttonArea.appendChild(container);
        browse.myContainer = container;
        this.mapping[reference.nodeId] = container;

        return {'whole':buttonArea, 'container':container, 'button':browse};;
    }

}
