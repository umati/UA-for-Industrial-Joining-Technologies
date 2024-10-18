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
    this.rebuildState = {
      claimed: false,
      resolved: false,
      partial: false
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

  /**
   * This function resolves all references to child results
   * @param {*} resultManager an object tracking old results (must implement resultFromId())
   * @returns false if this result is not fully recieved (including all subresults)
   *
  resolve (resultManager) {
    if (this.isReference) {
      const stored = resultManager.resultFromId(this.ResultMetaData.ResultId)
      if (stored) {
        stored.rebuildState.claimed = true // This could be purged now
        return stored
      } else {
        return false // Im not loaded yet
      }
    }

    // Go through all children and resolve them. If atleast one fails, I am still unresolved
    let returnValue = this
    for (const child of this.ResultContent) {
      const newChild = child.resolve(resultManager)
      if (!newChild) {
        returnValue = false // A child still lack a result
        this.rebuildState.resolved = false
      } else {
        this.replaceReference(child, newChild, this.ResultContent)
      }
    }
    if (returnValue) {
      this.rebuildState.resolved = true
    }
    return returnValue
  } */
}
