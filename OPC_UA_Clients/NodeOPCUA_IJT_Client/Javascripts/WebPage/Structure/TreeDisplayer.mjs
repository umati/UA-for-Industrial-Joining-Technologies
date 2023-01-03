
// The purpose of this class is to generate a tree of the things that can be
// clicked in order to subscribe or read data

export default class TreeDisplayer {

    constructor(generatedObjectFolder, socket) {
        this.generatedObjectFolder=generatedObjectFolder;
        generatedObjectFolder.innerHTML = '';
        this.socket=socket;
    }

    generateTree(msg) {
        this.generatedObjectFolder.innerHTML = '';
        this.generateTreeSupport(msg, this.generatedObjectFolder, 'ns=1;s=');
    }

    generateTreeSupport(structure, parent, path) {
        var name = structure.name;
        var container = document.createElement('div');
        container.classList.add('treeDiv');
        var read = document.createElement('button');
        read.innerHTML = name;
        read.myPath = path + '/' + name;
        read.socket = this.socket;
        read.classList.add('myButton');
        read.style.margin = '-5px'
        read.title='Read this node from the server'
        read.onclick =  function () {
            console.log(this.myPath);
            this.socket.emit('read item', this.myPath);
        };
        container.appendChild(read);
        var subscribe = document.createElement('button');
        subscribe.innerHTML = 's';
        subscribe.title ='Subscribe to changes in this node';
        subscribe.myPath = path + '/' + name;
        subscribe.style.backgroundColor = 'Salmon';
        subscribe.onclick = () => {
            console.log(this.myPath);
            this.socket.emit('subscribe item', this.myPath);
        };
        container.appendChild(subscribe);

        parent.appendChild(container);
        if (structure.content) {
            for (let child of structure.content) {
                this.generateTreeSupport(child, container, path + '/' + name)
            }
        }
    }
}

