import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class ResultDataType extends IJTBaseModel {
  constructor (parameters, modelManager, castMapping = {}) {
    castMapping.ResultMetaData = 'ResultMetaData'
    if (!castMapping.ResultContent) {
      castMapping.ResultContent = 'JoiningResultDataType'
    }

    if (parameters.Value) {
      parameters = parameters.Value
    }

    super(parameters, modelManager, castMapping)
    this.ClientData = {
      rebuildState: {
        claimed: false,
        resolved: false,
        partial: false
      }
    }
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
    return this.ResultMetaData?.IsPartial === 'True'
  }

  get evaluation () {
    if (this.ResultMetaData?.ResultEvaluation === 'ResultEvaluationEnum.OK') {
      return true
    }
    return false
  }

  get time () {
    if (this.ResultMetaData?.ProcessingTimes?.EndTime) {
      return this.ResultMetaData.ProcessingTimes.EndTime
    }
    return 'No Time'
  }

  get isReference () {
    return !this.ResultMetaData.CreationTime
  }

  replaceReference (child, newChild, children) {
    const index = children.indexOf(child)
    children[index] = newChild
  }
}
