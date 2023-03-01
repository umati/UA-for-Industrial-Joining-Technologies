
export default class AssetHandler {

    constructor(container, structure, socket) {
        this.socket = socket;
        this.structure = structure;
        this.mapping = {};

        let backGround = document.createElement('div');
        backGround.classList.add("datastructure");
        container.appendChild(backGround);

        let leftHalf = document.createElement('div');
        leftHalf.classList.add("lefthalf");
        leftHalf.classList.add("scrollableInfoArea");
        backGround.appendChild(leftHalf);
        this.displayArea = leftHalf;

        let nodeDiv = document.createElement('div');
        nodeDiv.classList.add("myHeader");
        nodeDiv.innerText = 'AssetView';
        leftHalf.appendChild(nodeDiv);


        let rightHalf = document.createElement('div');
        rightHalf.classList.add("righthalf");
        rightHalf.classList.add("scrollableInfoArea");
        backGround.appendChild(rightHalf);

        let comDiv = document.createElement('div');
        comDiv.classList.add("myHeader");
        comDiv.innerText = 'Asset communication';
        rightHalf.appendChild(comDiv);


        let messageArea = document.createElement('div');
        messageArea.setAttribute("id", "messageArea");
        rightHalf.appendChild(messageArea);

        this.messages = document.createElement('ul');
        this.messages.setAttribute("id", "messages");
        messageArea.appendChild(this.messages);

        let serverDiv = document.getElementById('connectedServer');
        serverDiv.addEventListener("tabOpened", (event) => {
            if (event.detail.title == 'Assets') {
                this.initiate();
            }
        }, false);

    }

    messageDisplay(item) {
        this.messages.appendChild(item);
        this.messages.scrollTo(0, this.messages.scrollHeight);
        item.scrollIntoView();
    }

    initiate() {
        let tighteningSystems = this.structure.getTighteningSystems();
        if (!tighteningSystems || tighteningSystems.length < 1) {
            return;
        }
        this.tighteningSystem = tighteningSystems[0];
        this.mapping[this.tighteningSystem] = 'dummy';
        this.socket.emit('browse', this.tighteningSystem);

    }

    receivedBrowse(msg) {
        if (this.mapping[msg.callernodeid]) {
            switch (msg.callernodeid.split('/').pop()) {
                case "Accessories":
                case "Batteries":
                case "Cables":
                case "Controllers":
                case "MemoryDevices":
                case "Sensors":
                case "Servos":
                case "Subcomponents":
                case "Tools":
                    for(let ref of msg.browseresult.references) {
                    this.createAsset(ref);
                    }
                    break;
                default:

                    for (let ref of msg.browseresult.references) {
                        switch (ref.browseName.name) {
                            case "AssetManagement":
                            case "Assets":
                            case "Accessories":
                            case "Batteries":
                            case "Cables":
                            case "Controllers":
                            case "MemoryDevices":
                            case "Sensors":
                            case "Servos":
                            case "Subcomponents":
                            case "Tools":
                                this.mapping[ref.nodeId] = 'folder';
                                this.socket.emit('browse', ref.nodeId,true);
                                console.log('browse::' + ref.nodeId);
                                break;
                            default:
                                console.log('Other Folder:' + ref.browseName.name);

                        }
                    }
            }
        }
    }

    createAsset(reference) {
        let nodeId=reference.NodeId;
        let mainbox = document.createElement('div');
        mainbox.classList.add("controllerBox");
        mainbox.innerText = reference.displayName.text;
        this.displayArea.appendChild(mainbox);

        this.mapping[nodeId] = mainbox;

        this.socket.emit('browse', {'nodeId':nodeId, 'details':true});
    }
}
