import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class StepResultDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      stepResultValues: 'ResultValueDataType'
    }
    super(parameters, modelManager, castMapping)
  }

  getIdentifier () {
    return this.stepResultId
  }
}
