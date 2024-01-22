import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class BatchModel extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      resultContent: 'BasedOnClassificationParameter',
      resultMetaData: 'ResultMetaData'
    }
    if (parameters.Value) {
      parameters = parameters.Value
    }
    super(parameters, modelManager, castMapping)
  }
}
