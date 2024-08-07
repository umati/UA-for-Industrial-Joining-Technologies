import IJTBaseModel from '../IJTBaseModel.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class ResultMetaData extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      AssociatedEntities: 'EntityDataType',
      ResultCounters: 'ResultCounters'
    }

    super(parameters, modelManager, castMapping)
  }
}
