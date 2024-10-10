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
    // modelManager.resultTypeNotification(this)
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

  /**
   * This function resolves all references to child results
   * @param {*} resultManager an object tracking old results (must implement resultFromId())
   * @returns false if this result is not fully recieved (including all subresults)
   */
  resolve (resultManager) {
    if (this.isReference) {
      const stored = resultManager.resultFromId(this.ResultMetaData.ResultId)
      if (stored) {
        Object.assign(this, stored) // We have a match. Copy in the data
      } else {
        return false // Im not loaded yet
      }
    }

    // Go through all children and resolve them. If atleast one fails, I am still unresolved
    let returnValue = true
    for (const child of this.ResultContent) {
      if (!child.resolve(resultManager)) {
        returnValue = false // A child still lack a result
      }
    }
    return returnValue
  }
}
