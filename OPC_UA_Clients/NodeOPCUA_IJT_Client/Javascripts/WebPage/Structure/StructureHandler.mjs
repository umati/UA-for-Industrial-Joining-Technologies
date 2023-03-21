import TreeDisplayer from './TreeDisplayer.mjs';
import ModelToHTML from './ModelToHTML.mjs';


export default class StructureHandler {

    constructor(container, socket, addressSpace) {
        this.socket=socket;
        this.addressSpace=addressSpace;
        
        let backGround=document.createElement('div');
        backGround.classList.add("datastructure");
        container.appendChild(backGround);

        let leftHalf=document.createElement('div');
        leftHalf.classList.add("lefthalf");
        leftHalf.classList.add("scrollableInfoArea");
        backGround.appendChild(leftHalf);

        let nodeDiv=document.createElement('div');
        nodeDiv.classList.add("myHeader");
        nodeDiv.innerText='Nodes';
        leftHalf.appendChild(nodeDiv);

        let leftArea=document.createElement('ul');
        leftArea.innerText='Nodes';
        leftHalf.appendChild(leftArea);
        this.leftArea=leftArea;

        let rightHalf=document.createElement('div');
        rightHalf.classList.add("righthalf");
        rightHalf.classList.add("scrollableInfoArea");
        backGround.appendChild(rightHalf);

        let comDiv=document.createElement('div');
        comDiv.classList.add("myHeader");
        comDiv.innerText='Model communication';
        rightHalf.appendChild(comDiv);


        let messageArea=document.createElement('div');
        messageArea.setAttribute("id","messageArea");
        rightHalf.appendChild(messageArea);

        this.messages=document.createElement('ul');
        this.messages.setAttribute("id","messages");
        messageArea.appendChild(this.messages);

        this.treeDisplayer= null;
        this.modelToHTML= new ModelToHTML(this.messages);
    }

    initiateNodeTree(){
        this.treeDisplayer= new TreeDisplayer(this);
        this.addressSpace.reset();
        this.addressSpace.setGUIGenerator(this.treeDisplayer); 

        this.addressSpace.initiate();

        //this.addressSpace.createObjectFolder();
        
        //this.socket.emit('browse', 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/AssetManagement/Assets/Controllers/TighteningController', 'read', true);
        //this.socket.emit('browse', 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement/Results/Result', 'read', true);
        //this.socket.emit('browse', 'ns=0;i=85', 'read', true);
    }

    generateTree(msg){
        if (!this.leftArea) {
            alert('too early call to generateTree');
            this.treeDisplayer= new TreeDisplayer(this, ['Root', 'Objects', 'TighteningSystem', 'ResultManagement', 'Results']);
        }
        this.treeDisplayer.generateTree(msg);
    }

    
    displayModel(model){
        this.modelToHTML.display(model);
    }

    messageDisplay(msg) {    
        let item = document.createElement('li');
        item.textContent = msg; 
        this.messages.appendChild(item);
        this.messages.scrollTo(0, this.messages.scrollHeight);
        item.scrollIntoView();
    }
}
