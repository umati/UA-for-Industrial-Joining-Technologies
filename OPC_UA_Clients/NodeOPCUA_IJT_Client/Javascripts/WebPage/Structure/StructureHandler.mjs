import TreeDisplayer from './TreeDisplayer.mjs';
import ModelToHTML from './ModelToHTML.mjs';


export default class StructureHandler {

    constructor(container, socket) {
        
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

        let treeArea=document.createElement('ul');
        treeArea.innerText='Nodes';
        leftHalf.appendChild(treeArea);

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

        this.treeDisplayer= new TreeDisplayer(treeArea, socket);
        this.modelToHTML= new ModelToHTML(this.messages);
    }

    generateTree(msg){
        this.treeDisplayer.generateTree(msg);
    }

    displayModel(model){
        this.modelToHTML.display(model);
    }

    messageDisplay(item) {     
        this.messages.appendChild(item);
        this.messages.scrollTo(0, this.messages.scrollHeight);
        item.scrollIntoView();
    }
}
