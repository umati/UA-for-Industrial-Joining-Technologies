import ResultDataType from './ResultDataType.mjs'
// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
export default class TighteningDataType extends ResultDataType {
  constructor (parameters, modelManager) {
    let simplifiedParameters
    if (parameters.Value) {
      simplifiedParameters = {
        ResultMetaData: parameters.Value.ResultMetaData,
        ResultContent: parameters.Value.ResultContent
      }
    } else {
      simplifiedParameters = {
        ResultMetaData: parameters.ResultMetaData,
        ResultContent: parameters.ResultContent
      }
    }
    const castMapping = {
      ResultContent: 'JoiningResultDataType'
    }
    super(simplifiedParameters, modelManager, castMapping)

    this.consolidatedResultType = 'Joining'

    if (this.ResultContent[0]?.Trace) {
      this.ResultContent[0].Trace.createConnections(this)
    }
  }

  getStep (Id) {
    if (!this.ResultContent[0].StepResults || this.ResultContent[0].StepResults.length < 1) {
      throw new Error('Could not find stepResult with Id: ' + Id)
    }
    for (const step of this.ResultContent[0].StepResults) {
      if (step.getIdentifier() === Id) {
        return step
      }
    }
    // throw new Error('Could not find stepResult with Id: '+Id);
  }

  getTaggedValues (tag) {
    if (!this.ResultContent[0].StepResults || this.ResultContent[0].StepResults.length < 1) {
      throw new Error('Could not find stepResults, when looking for tag')
    }
    const listOfValues = []
    for (const step of this.ResultContent[0].StepResults) {
      for (const stepvalue of step.StepResultValues) {
        if (parseInt(stepvalue.ValueTag) === parseInt(tag)) {
          listOfValues.push(stepvalue)
        }
      }
    }
    return listOfValues
  }
}
