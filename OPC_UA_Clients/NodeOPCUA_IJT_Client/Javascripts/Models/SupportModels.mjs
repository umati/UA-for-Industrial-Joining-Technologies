import IJTBaseModel from './IJTBaseModel.mjs';

// The purpose of this class is to represent a localized string
export  class localizationModel extends IJTBaseModel {
    constructor(parameters, modelManager) { 
        super(parameters, modelManager);
        
    }
}

// The purpose of this class is to represent the simplest type of name-value pairs
export class keyValuePair extends IJTBaseModel {
    constructor(parameters, modelManager) { 
        super(parameters, modelManager);
        
    }

    toHTML(brief, parentName){
        let container = document.createElement('li');
        let li1 = document.createElement('li');
        li1.innerHTML = this.key+': ' +this.value;
        container.appendChild(li1);
        container.expandLong = function () {}; //Override expand
        return container;
    }
}