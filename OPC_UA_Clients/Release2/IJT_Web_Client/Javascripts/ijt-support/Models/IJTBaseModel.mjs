// The purpose of this class is to capture all common functionality of
// the Industrial Joining Technologies Models
export default class IJTBaseModel {
  constructor (parameters, modelManager, castMapping) {
    this.debugValues = parameters // This contains the original input for debug purposes

    // Loop through the key-value-pairs and send them to the factory
    for (const [key, value] of Object.entries(parameters)) {
      if (key !== 'pythonclass') {
        if (!value) {
          this[key] = null
        } else {
          // console.log(`${key}: ${value}`);
          if (Array === value.constructor) {
            this[key] = []
            for (const element of value) {
              this[key].push(modelManager.factory(key, element, castMapping))
            }
          } else if (typeof value === 'object') {
            // console.log('IJTBAseclass: ' + key)
            this[key] = modelManager.factory(key, value, castMapping)
          } else {
            this[key] = value
          }
        }
      }
    }
  }
}
