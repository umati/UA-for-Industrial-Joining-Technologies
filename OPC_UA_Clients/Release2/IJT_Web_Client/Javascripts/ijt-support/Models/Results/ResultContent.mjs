import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class ResultContent extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      // AssociatedEntities: 'AssociatedEntities',
      // ProcessingTimes: 'ProcessingTimes'
      // tags: 'TagDataType',
      overallResultValues: 'ResultValueDataType',
      stepResults: 'StepResultDataType',
      errors: 'ErrorInformationDataType',
      resultMetaData: 'ResultMetaData',
      trace: 'TighteningTraceDataType'
    }

    if (parameters.Value) {
      parameters = parameters.Value
    }
    /*
    switch(parameters.ResultMetaData.Classification)
    case () */
    super(parameters.Value, modelManager, castMapping)
  }
}
