import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class JoiningResultDataType extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      // AssociatedEntities: 'AssociatedEntities',
      // ProcessingTimes: 'ProcessingTimes'
      // tags: 'TagDataType',
      // Value: 'TighteningResultDataType',
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
  }
}
