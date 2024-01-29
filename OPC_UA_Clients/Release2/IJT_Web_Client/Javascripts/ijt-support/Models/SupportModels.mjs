import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to represent a localized string
export class LocalizationModel extends IJTBaseModel {
  // eslint-disable-next-line no-useless-constructor
  constructor (parameters, modelManager, castMapping) {
    super(parameters, modelManager, castMapping)
  }
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

// The purpose of this class is to represent the simplest type of name-value pairs
export class NodeId extends IJTBaseModel {
  constructor (parameters, modelManager, castMapping) {
    super(parameters, modelManager)
  }

  stringify () {
    let st = ';s='
    if (Number(this.Identifier)) {
      st = ';i='
    }
    return 'ns=' + this.NamespaceIndex + st + this.Identifier
  }

  compare (identity, namespace) {
    if (identity !== this.Identifier) {
      return false
    }
    if (namespace && namespace !== this.NamespaceIndex) {
      return false
    }
    return true
  }
}

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export class ErrorInformationDataType extends IJTBaseModel {
}

// The purpose of this class is to model the Processing times data structure
export class ProcessingTimesDataType extends IJTBaseModel {
}
