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

    this.aaaa = 'Joining'

    if (this.Trace) {
      this.Trace.createConnections(this)
    }
  }

  /*
  constructor (parameters, modelManager) {
    const castMapping = {
      overallResultValues: 'ResultValueDataType',
      stepResults: 'StepResultDataType',
      errors: 'ErrorInformationDataType',
      trace: 'TighteningTraceDataType'
    }

    super(parameters, modelManager, castMapping)

    // Here we connect the trace steps with the result steps to simplify the use
    if (this.Trace) {
      this.Trace.createConnections(this)
    }
  } */

  getStep (Id) {
    if (!this.StepResults || this.StepResults.length < 1) {
      throw new Error('Could not find stepResult with Id: ' + Id)
    }
    for (const step of this.StepResults) {
      if (step.getIdentifier() === Id) {
        return step
      }
    }
    // throw new Error('Could not find stepResult with Id: '+Id);
  }
}
