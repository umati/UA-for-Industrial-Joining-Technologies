import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class JoiningResultDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      overallResultValues: 'ResultValueDataType',
      stepResults: 'StepResultDataType',
      errors: 'ErrorInformationDataType',
      resultMetaData: 'ResultMetaData',
      trace: 'TighteningTraceDataType'
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

  getTaggedValues (tag) {
    if (!this.StepResults || this.StepResults.length < 1) {
      throw new Error('Could not find stepResults, when looking for tag')
    }
    const listOfValues = []
    for (const step of this.StepResults) {
      for (const stepvalue of step.StepResultValues) {
        if (parseInt(stepvalue.ValueTag) === parseInt(tag)) {
          listOfValues.push(stepvalue)
        }
      }
    }
    return listOfValues
  }

  get isReference () {
    return this.ResultMetaData && !this.ResultMetaData.CreationTime
  }

  /**
   * This function resolves all references to child results
   * @param {*} resultManager an object tracking old results (must implement resultFromId())
   * @returns true
   *
  resolve (resultManager) {
    if (this.isReference) {
      const stored = resultManager.resultFromId(this.ResultMetaData.ResultId)
      if (stored) {
        return stored // We have a match. Copy in the data
      } else {
        return false // Im not loaded yet
      }
    } else {
      return this
    }
  } */
}
