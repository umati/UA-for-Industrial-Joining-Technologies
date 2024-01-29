import ResultDataType from './ResultDataType.mjs'

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class BatchDataModel extends ResultDataType {
  constructor (parameters, modelManager, castMapping) {
    super(parameters, modelManager, castMapping)
    this.aaaa = 'Batch'
  }
}
