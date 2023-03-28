
export default class AssetGraphics {

    constructor(container) {
        this.container=container;
    }

    createController(node, controllerNr, parts){ 
        let rightPercent=75;
        let nodeId = node.NodeId;
        let height= 100/parts;
        if (!node.assetGraphicData) {
            node.assetGraphicData={};
        }
        let mainbox = document.createElement('div');
        mainbox.classList.add("assetArea");
        mainbox.style.left= '0%';
        mainbox.style.right= '0%';
        mainbox.style.top= Math.round(controllerNr*height)+'%';
        mainbox.style.height = height+'%';
        this.container.appendChild(mainbox);

        let leftbox = document.createElement('div');
        leftbox.classList.add("assetArea");
        leftbox.innerText = '';
        leftbox.style.left= '0%';
        leftbox.style.right= (100-rightPercent)+'%';
        leftbox.style.top= '0%';
        leftbox.style.height= '100%';
        mainbox.appendChild(leftbox);

        let rightbox = document.createElement('div');
        rightbox.classList.add("assetArea");
        rightbox.innerText = 'Tools';
        rightbox.style.left= rightPercent+'%';
        rightbox.style.right= '0%';
        rightbox.style.top= '0%';
        rightbox.style.height= '100%';
        mainbox.appendChild(rightbox);
        node.assetGraphicData.tools=rightbox;
        rightbox.assetInternals=[];


        return this.createAssetContainer(node, leftbox)
    }

    addInternal(node,containerNode) {
        this.addHorizontal(node, containerNode.assetGraphicData.internals)
    }

    addExternal(node,containerNode) {
        this.addHorizontal(node, containerNode.assetGraphicData.externals)
    }
    addTool(node,containerNode) {
        this.addVertical(node, containerNode.assetGraphicData.tools)
    }

    createAssetContainer(node, container){ 
        if (!node.assetGraphicData) {
        node.assetGraphicData={};
    }
        let asset = document.createElement('div');
        asset.classList.add("assetArea");
        asset.innerText = node.displayName.text;
        asset.style.backgroundColor= 'brown';
        asset.style.left= '10%';
        asset.style.right= '10%';
        asset.style.top= '5%';
        asset.style.height= '40%';
        container.appendChild(asset);
        node.assetGraphicData.internals=asset;
        asset.assetInternals=[];

        let externals = document.createElement('div');
        externals.classList.add("assetArea");
        externals.style.left= '0%';
        externals.style.right= '0%';
        externals.style.top= '50%';
        externals.style.height= '50%';
        container.appendChild(externals);
        node.assetGraphicData.externals=externals;
        externals.assetInternals=[];
        return asset;
    }


    addHorizontal(node, container) {
        let mainbox = document.createElement('div');
        mainbox.classList.add("assetBox");
        mainbox.innerText = node.displayName.text;
        mainbox.style.top= '60%';
        mainbox.style.bottom= '10%';
        container.appendChild(mainbox);
        container.assetInternals.push(mainbox);
        let width=100/container.assetInternals.length;
        let i=0;
        for(let internal of container.assetInternals) {
            internal.style.left=((i++*width)+(width/10))+'%';
            internal.style.width=(0.8*width)+'%';
        }
        return mainbox;
    }

    addVertical(node, container) {
        let mainbox = document.createElement('div');
        mainbox.classList.add("assetBox");
        mainbox.style.left= '10%';
        mainbox.style.right= '10%';
        container.appendChild(mainbox);
        container.assetInternals.push(mainbox);
        let height=100/container.assetInternals.length;
        let i=0;
        for(let internal of container.assetInternals) {
            internal.style.top=((i++*height)+(height/10))+'%';
            internal.style.height=(0.8*height)+'%';
        }
        this.createAssetContainer(node, mainbox)

        return mainbox;
    }

}