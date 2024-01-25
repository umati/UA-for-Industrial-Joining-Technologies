import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class ResultDataType extends IJTBaseModel {
  constructor (parameters, modelManager, castMapping = {}) {
    castMapping.ResultMetaData = 'ResultMetaData'
    if (!castMapping.ResultContent) {
      castMapping.ResultContent = 'ResultContent'
    }

    if (parameters.Value) {
      parameters = parameters.Value
    }

    super(parameters, modelManager, castMapping)
  }

  get id () {
    return this.ResultMetaData?.ResultId
  }

  get name () {
    return this.ResultMetaData?.Name
  }

  get classification () {
    return this.ResultMetaData?.Classification
  }

  get isPartial () {
    return this.ResultMetaData?.IsPartial
  }

  get evaluation () {
    if (this.ResultMetaData?.ResultEvaluation) {
      return true
    }
    return false
  }
}
