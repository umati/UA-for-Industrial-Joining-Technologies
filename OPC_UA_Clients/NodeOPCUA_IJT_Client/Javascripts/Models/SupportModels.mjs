import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to represent a localized string
export class localizationModel extends IJTBaseModel {
}

// The purpose of this class is to represent the simplest type of name-value pairs
export class keyValuePair extends IJTBaseModel {
  toHTML (brief, parentName) {
    const container = document.createElement('li')
    const li1 = document.createElement('li')
    li1.innerHTML = this.key + ': ' + this.value
    container.appendChild(li1)
    container.expandLong = function () { } // Override expand
    return container
  }
}
