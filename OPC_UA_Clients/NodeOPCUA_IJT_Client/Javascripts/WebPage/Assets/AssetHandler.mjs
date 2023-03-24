
export default class AssetHandler {

    constructor(container, addressSpace, socketHandler) {
        this.socketHandler = socketHandler;
        this.addressSpace = addressSpace;
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
        let tighteningSystems = this.addressSpace.getTighteningSystems();
        if (!tighteningSystems || tighteningSystems.length < 1) {
            throw new Error('No TighteningSystem found in Objects folder');
        }
        this.tighteningSystem = tighteningSystems[0];
        console.log('Selected TighteningSystem: ' + this.tighteningSystem.nodeId);
        this.concurrentStart().then(
            ()=>{console.log('Horrayyy')}
        );
    }

    concurrentStart() {
        this.controllers = [];
        console.log("==CONCURRENT START with await==");

        return Promise.all([
            this.findFolder('Controllers').then((list) => {
                this.controllers = list;
            }),
            this.findFolder('Tools').then((list) => {
                this.tools = list;
            }),
            this.findFolder('Servos').then((list) => {
                this.servos = list;
            }),
            this.findFolder('MemoryDevices').then((list) => {
                this.memoryDevices = list;
            }),
            this.findFolder('Sensors').then((list) => {
                this.sensors = list;
            }),
            this.findFolder('Cables').then((list) => {
                this.cables = list;
            }),
            this.findFolder('Batteries').then((list) => {
                this.batteries = list;
            }),
            this.findFolder('PowerSupplies').then((list) => {
                this.powerSupplies = list;
            }),
            this.findFolder('Feeders').then((list) => {
                this.feeders = list;
            }),
            this.findFolder('Accessories').then((list) => {
                this.assecories = list;
            }),
            this.findFolder('SubComponents').then((list) => {
                this.subComponents = list;
            }),

        ])
    }

    findFolder(folderName) {
        return new Promise(
            (resolve) => {
                this.getAssetsInFolderPromise(folderName).then(
                    (contr) => {
                        this.addressSpace.browseAndRead(contr).then(
                            (a) => {
                                let controllers = a.getRelations('component');
                                resolve(controllers);
                            }
                        );
                    })
            })
    }

    getAssetsInFolderPromise(folderName) {
        console.log(`Starting finding folder ${folderName}`);
        return new Promise((resolve) => {
            let nsIJT = this.addressSpace.nsIJT;
            this.socketHandler.pathtoidPromise(
                this.tighteningSystem.nodeId,
                `/${nsIJT}:AssetManagement/${nsIJT}:Assets/${nsIJT}:${folderName}`
            ).then(
                (msg) => {
                    resolve(msg.message.nodeid);
                }
            )
        });
    }

    getAssetsInFolder(folderName) {
        console.log(`Starting finding folder ${folderName}`);
        return new Promise((resolve) => {
            let nsIJT = this.addressSpace.nsIJT;
            this.socketHandler.pathtoid(
                this.tighteningSystem.nodeId,
                `/${nsIJT}:AssetManagement/${nsIJT}:Assets/${nsIJT}:${folderName}`,
                (msg) => {
                    resolve(msg.nodeid);
                }
            );
        });
    }

    getAssetsInFolder3(folderName) {
        console.log(`Starting finding folder ${folderName}`);
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve([1, 2, 3, folderName]);
                console.log(`Done finding folder ${folderName}`);
            }, 2000);
        });
    }

    getAssetsInFolder2(list, folderName) {
        let nsIJT = this.addressSpace.nsIJT;

        this.socketHandler.pathtoid(
            this.tighteningSystem.nodeId,
            `/${nsIJT}:AssetManagement/${nsIJT}:Assets/${nsIJT}:${folderName}`,
            (msg) => {
                // Now get all the children and draw figures for them ... eventdriven
                console.log(msg.nodeid);
            });

    }

    receivedBrowse(msg) {
        if (this.mapping[msg.callid]) {
            switch (msg.callid.split('/').pop()) {
                case "Accessories":
                case "Batteries":
                case "Cables":
                case "Controllers":
                case "MemoryDevices":
                case "Sensors":
                case "Servos":
                case "Subcomponents":
                case "Tools":
                    for (let ref of msg.browseresult.references) {
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
                                this.socketHandler.emit('browse', ref.nodeId, 'read', true);
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
        let nodeId = reference.NodeId;
        let mainbox = document.createElement('div');
        mainbox.classList.add("controllerBox");
        mainbox.innerText = reference.displayName.text;
        this.displayArea.appendChild(mainbox);

        this.mapping[nodeId] = mainbox;

    }
}
