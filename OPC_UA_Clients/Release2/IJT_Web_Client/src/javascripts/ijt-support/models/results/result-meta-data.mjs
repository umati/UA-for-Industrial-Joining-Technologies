import IJTBaseModel from '../ijt-base-model.mjs'

// The purpose of this class is to model the tag structure for external identifiers
export default class ResultMetaData extends IJTBaseModel {
  constructor (parameters, modelManager) {
    const castMapping = {
      AssociatedEntities: 'EntityDataType',
      ResultCounters: 'ResultCounters'
    }

    super(parameters, modelManager, castMapping)

    // Some servers send a single AssociatedEntities object instead of a list.
    // Normalize to an array so callers can always iterate safely.
    if (!this.AssociatedEntities) {
      this.AssociatedEntities = []
    } else if (!Array.isArray(this.AssociatedEntities)) {
      this.AssociatedEntities = [this.AssociatedEntities]
    }
  }
}
