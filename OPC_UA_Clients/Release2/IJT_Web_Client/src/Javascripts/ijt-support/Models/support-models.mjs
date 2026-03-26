import IJTBaseModel from './ijt-base-model.mjs'

// The purpose of this class is to represent a localized string
export class LocalizationModel extends IJTBaseModel {
  // eslint-disable-next-line no-useless-constructor
  constructor (parameters, modelManager, castMapping) {
    super(parameters, modelManager, castMapping)
  }
}

// The purpose of this class is to represent the simplest type of name-value pairs
export class KeyValuePair extends IJTBaseModel {
  toHTML (brief, parentName) {
    const container = document.createElement('li')
    const li1 = document.createElement('li')
    li1.innerHTML = `${this.key}: ${this.value}`
    container.appendChild(li1)
    container.expandLong = function () { } // Override expand
    return container
  }
}

// The purpose of this class is to represent the simplest type of name-value pairs
export class NodeId extends IJTBaseModel {
  constructor (parameters, modelManager, castMapping) {
    super(parameters, modelManager)
    // IJTBaseModel converts all falsy values (including 0) to null.
    // NamespaceIndex=0 is the core OPC UA namespace and must be preserved as-is.
    if (parameters != null && 'NamespaceIndex' in parameters) {
      this.NamespaceIndex = parameters.NamespaceIndex
    }
  }

  /**
   * Serialise to OPC UA NodeId string format (e.g. "ns=2;i=1234" or "ns=1;s=name").
   * @returns {string}
   */
  stringify () {
    const ns = this.NamespaceIndex ?? 0
    const id = this.Identifier
    const separator = Number.isInteger(id) || (typeof id === 'string' && !isNaN(Number(id)) && id !== '')
      ? ';i='
      : ';s='
    return `ns=${ns}${separator}${id}`
  }

  /**
   * Compare this NodeId's identifier (and optionally namespace) against given values.
   * @param {number|string} identity
   * @param {number}        [namespace]
   * @returns {boolean}
   */
  compare (identity, namespace) {
    if (identity !== this.Identifier) return false
    if (namespace !== undefined && namespace !== (this.NamespaceIndex ?? 0)) return false
    return true
  }
}

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export class ErrorInformationDataType extends IJTBaseModel {
}

// The purpose of this class is to model the Processing times data structure
export class ProcessingTimesDataType extends IJTBaseModel {
}
