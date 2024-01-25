import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class ResultCounters extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      // AssociatedEntities: 'AssociatedEntities',
      // ProcessingTimes: 'ProcessingTimes'
      // tags: 'TagDataType',
      // resultContent: 'TighteningResultDataType'
    }

    super(parameters, modelManager, castMapping)
  }
}
