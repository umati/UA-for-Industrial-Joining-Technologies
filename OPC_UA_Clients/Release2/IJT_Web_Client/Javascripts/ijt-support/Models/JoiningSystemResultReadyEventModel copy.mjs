import IJTBaseModel from './IJTBaseModel.mjs'

// The purpose of this class is to model the Event data structure
export default class ResultReadyEventModel extends IJTBaseModel {
  constructor (parameters, modelManager, castMapping = {}) {
    super(parameters, modelManager, castMapping)
  }
}
