import AssetGraphic from './AssetGraphic.mjs';

export default class AssetHandler {

    constructor(container, addressSpace, socketHandler) {
        this.socketHandler = socketHandler;
        this.addressSpace = addressSpace;

        let backGround = document.createElement('div');
        backGround.classList.add("datastructure");
        container.appendChild(backGround);

        let leftHalf = document.createElement('div');
        leftHalf.classList.add("lefthalf");
        leftHalf.classList.add("scrollableInfoArea");
        backGround.appendChild(leftHalf);

        let nodeDiv = document.createElement('div');
        nodeDiv.classList.add("myHeader");
        nodeDiv.innerText = 'AssetView';
        leftHalf.appendChild(nodeDiv);

        let displayArea = document.createElement('div');
        displayArea.classList.add("drawAssetBox");
        leftHalf.appendChild(displayArea);

        let serverDiv = document.getElementById('connectedServer');
        serverDiv.addEventListener("tabOpened", (event) => {
            if (event.detail.title == 'Assets') {
                this.initiate();
            }
        }, false);

        this.assetGraphic = new AssetGraphic(displayArea);
    }

    messageDisplay(item) {
        alert('AssetHandler has no message area');
    }

    initiate() {
        let tighteningSystems = this.addressSpace.getTighteningSystems();
        if (!tighteningSystems || tighteningSystems.length < 1) {
            throw new Error('No TighteningSystem found in Objects folder');
        }
        this.tighteningSystem = tighteningSystems[0];
        console.log('Selected TighteningSystem: ' + this.tighteningSystem.nodeId);
        this.loadAllAssets().then(
            () => {
                //console.log('All assets loaded.');
                this.browseAndReadList([...this.controllers, ...this.tools]).then(
                    () => { this.draw() }
                )
            }
        );
    }

    /**
     * 
     * @returns A promise to load all assets
     */
    loadAllAssets() {
        function addAssetGraphicData(list, folderName) {
            for (let node of list) {
                if (!node.assetGraphicData) {
                    node.addAssetGraphicData = {};
                }
                node.addAssetGraphicData.folderName = folderName;
            }
        }

        this.controllers = [];
        let assetFolders=[
            'Controllers',
            'Tools',
            'Servos',
            'MemoryDevices',
            'Sensors',
            'Cables',
            'Batteries',
            'PowerSupplies',
            'Feeders',
            'Accessories',
            'SubComponents'
        ];

        let promiseList = [];
        for (let folderName of assetFolders) {
            promiseList.push(
                this.findContentInFolder(folderName).then((list) => {
                    addAssetGraphicData(list, folderName)
                    this[folderName.toLowerCase()] = list;
                })
            )
        }

        return Promise.all(promiseList);
    }


    browseAndReadList(nodeList) {
        let promiseList = [];
        for (let node of nodeList) {
            promiseList.push(
                this.addressSpace.browseAndRead(node.nodeId).then(
                    () => { })
            )
        }

        return Promise.all(promiseList);
    }

    findContentInFolder(folderName) {
        return new Promise(
            (resolve) => {
                this.findFolder(folderName).then(
                    (nodeId) => {
                        this.addressSpace.browseAndRead(nodeId).then(
                            (folderNode) => {
                                let assets = folderNode.getRelations('component');
                                resolve(assets);
                            }
                        );
                    })
            },
            (fail) => { fail(`Failed to find asset folder ${folderName}`) }
        )
    }

    findFolder(folderName) {
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
        },
            (fail) => { fail(`Failed to get assets in folder ${folderName}`) }
        );
    }

    draw() {
        let assetGraphic = this.assetGraphic;

        function drawAssetRecursive(asset) {
            drawAssetWithExternals(asset.getRelations('association'), asset);
        }

        function drawAssetWithExternals(associations, containerNode) {
            for (let external of externals) {
                for (let association of associations) {
                    if (association.associatedNodeId == external.nodeId) {
                        assetGraphic.addExternal(external, containerNode);
                        drawAssetRecursive(external);
                    }
                }
            }
            for (let internal of internals) {
                for (let association of associations) {
                    if (association.associatedNodeId == internal.nodeId) {
                        assetGraphic.addInternal(internal, containerNode);
                        drawAssetRecursive(internal);
                    }
                }
            }
        }

        let i = 0;
        let externals = [
            ...this.powersupplies,
            ...this.feeders,
            ...this.cables,
            ...this.accessories];
        let internals = [
            ...this.servos,
            ...this.memorydevices,
            ...this.subcomponents,
            ...this.batteries,
            ...this.sensors];
        for (let controller of this.controllers) {
            this.assetGraphic.createController(controller, i, this.controllers.length);

            let associations = controller.getRelations('association');

            drawAssetWithExternals(associations, controller);

            for (let tool of this.tools) {
                for (let association of associations) {
                    if (association.associatedNodeId == tool.nodeId) {
                        let context = this.assetGraphic.addTool(tool, controller);
                        drawAssetRecursive(tool)
                    };
                }
            }

            //this.assetGraphic.addExternal({ nodeId: 1, displayName: { text: 'Example Stacklight' } }, controller);

            i++;
        }

    }


}
